"""Bể CLMM kiểu Uniswap v3 (float), đúng chữ ký INTERFACE mục 2.

Cấu trúc dữ liệu tổng quát theo tick (liquidity_net/gross, feeGrowthOutside) nên vị thế có độ
rộng bất kỳ — không giả định một tick. Phí cộng dồn theo feeGrowth + checkpoint như v3.

GĐ3: `fee_weight = φ(w)` chia lại phí theo L_i·φ(w_i) / Σ L_j·φ(w_j) trong số vị thế đang hoạt động
(tổng phí giữ nguyên). Cài bằng cách tính feeGrowth trên mỗi đơn vị "thanh khoản có trọng số"
L·φ(w) thay vì L; giá vẫn đi theo L thật. φ = None ⇔ φ ≡ 1 ⇔ pro-rata như v3.
"""
from __future__ import annotations

import bisect
import math
from collections.abc import Callable
from dataclasses import dataclass

from .log import EventLog
from .tick_math import (
    MAX_TICK, MIN_TICK, amount0_delta, amount1_delta, amounts_for_liquidity, sqrt_price_at_tick,
    tick_at_sqrt_price,
)


@dataclass
class Position:
    id: int
    owner: str
    tick_lower: int
    tick_upper: int          # tick_upper > tick_lower; độ rộng w = tick_upper - tick_lower
    liquidity: float


@dataclass
class SwapResult:
    amount_in: float         # lượng vào (đã gồm phí), token vào
    amount_out: float        # lượng ra, token ra
    fee: float               # phí, tính bằng token vào
    zero_for_one: bool       # True = bán token0 lấy token1 (giá giảm)
    sqrt_price_before: float
    sqrt_price_after: float
    tick_before: int
    tick_after: int
    ticks_crossed: int


@dataclass
class _Tick:
    liquidity_gross: float = 0.0
    liquidity_net: float = 0.0           # cộng vào L_active khi giá đi lên qua tick này
    weighted_net: float = 0.0            # như trên nhưng với L·φ(w)
    fee_growth_outside0: float = 0.0     # token0 trên mỗi đơn vị L, phía "bên kia" tick
    fee_growth_outside1: float = 0.0


@dataclass
class _PositionState:
    pos: Position
    weight: float = 1.0                  # φ(w) của vị thế
    fee_growth_inside0_last: float = 0.0
    fee_growth_inside1_last: float = 0.0
    owed0: float = 0.0
    owed1: float = 0.0


def _mat_so(L: float, scale: float) -> bool:
    """True khi L (vừa trừ đi lượng cỡ `scale`) nhỏ tới mức sai số float đáng kể → cần cộng lại."""
    return L <= 1e-6 * abs(scale)


class Pool:
    """Bể một cặp token0/token1 với thanh khoản tập trung, swap cross-tick."""

    def __init__(self, fee: float, sqrt_price: float, tick_spacing: int = 1,
                 fee_weight: Callable[[int], float] | None = None):
        if not 0 <= fee < 1:
            raise ValueError("fee phải trong [0, 1)")
        if tick_spacing < 1:
            raise ValueError("tick_spacing phải ≥ 1")
        self.fee = fee
        self.tick_spacing = tick_spacing
        self.sqrt_price = float(sqrt_price)
        self.tick = tick_at_sqrt_price(self.sqrt_price)
        self.liquidity = 0.0                     # L_active
        self.fee_weight = fee_weight             # φ(w), w tính bằng số tick; None = pro-rata
        self.liquidity_weighted = 0.0            # Σ L·φ(w) của vị thế đang hoạt động
        self.fee_growth_global0 = 0.0            # token0 trên mỗi đơn vị L·φ(w)
        self.fee_growth_global1 = 0.0
        self.t = 0                               # bước thời gian, bộ chạy đặt
        self.log = EventLog()
        self._ticks: dict[int, _Tick] = {}
        self._sorted_ticks: list[int] = []       # các tick đã khởi tạo, tăng dần
        self._positions: dict[int, _PositionState] = {}
        self._next_id = 1

    # ---------- nội bộ ----------
    def _check_range(self, tick_lower: int, tick_upper: int) -> None:
        if tick_lower >= tick_upper:
            raise ValueError("cần tick_lower < tick_upper")
        if tick_lower % self.tick_spacing or tick_upper % self.tick_spacing:
            raise ValueError(f"tick phải chia hết cho tick_spacing={self.tick_spacing}")
        sqrt_price_at_tick(tick_lower)
        sqrt_price_at_tick(tick_upper)

    def _update_tick(self, i: int, dL: float, dLw: float, upper: bool) -> None:
        """Cộng dL vào tick i (biên dưới nếu upper=False). Khởi tạo feeGrowthOutside như v3."""
        info = self._ticks.get(i)
        if info is None:
            info = _Tick()
            if i <= self.tick:                   # quy ước v3: coi mọi phí trước đây nằm dưới tick
                info.fee_growth_outside0 = self.fee_growth_global0
                info.fee_growth_outside1 = self.fee_growth_global1
            self._ticks[i] = info
            bisect.insort(self._sorted_ticks, i)
        info.liquidity_gross += dL
        info.liquidity_net += -dL if upper else dL
        info.weighted_net += -dLw if upper else dLw
        if info.liquidity_gross <= 1e-12 * max(1.0, abs(dL)):
            del self._ticks[i]
            self._sorted_ticks.pop(bisect.bisect_left(self._sorted_ticks, i))

    def _fee_growth_inside(self, lo: int, hi: int) -> tuple[float, float]:
        """feeGrowth trong khoảng [lo, hi) (token0, token1 trên mỗi đơn vị L)."""
        g0, g1 = self.fee_growth_global0, self.fee_growth_global1
        tl, tu = self._ticks.get(lo, _Tick()), self._ticks.get(hi, _Tick())
        if self.tick >= lo:
            b0, b1 = tl.fee_growth_outside0, tl.fee_growth_outside1
        else:
            b0, b1 = g0 - tl.fee_growth_outside0, g1 - tl.fee_growth_outside1
        if self.tick < hi:
            a0, a1 = tu.fee_growth_outside0, tu.fee_growth_outside1
        else:
            a0, a1 = g0 - tu.fee_growth_outside0, g1 - tu.fee_growth_outside1
        return g0 - b0 - a0, g1 - b1 - a1

    def _accrue(self, st: _PositionState) -> None:
        """Chuyển phí phát sinh từ checkpoint trước vào owed của vị thế."""
        p = st.pos
        in0, in1 = self._fee_growth_inside(p.tick_lower, p.tick_upper)
        Lw = p.liquidity * st.weight
        st.owed0 += Lw * (in0 - st.fee_growth_inside0_last)
        st.owed1 += Lw * (in1 - st.fee_growth_inside1_last)
        st.fee_growth_inside0_last, st.fee_growth_inside1_last = in0, in1

    def _active_sums(self, tick: int) -> tuple[float, float]:
        """(Σ L, Σ L·φ) của các vị thế chứa `tick`, cộng trực tiếp (không trừ) — chính xác, O(số vị thế)."""
        L = Lw = 0.0
        for st in self._positions.values():
            p = st.pos
            if p.liquidity > 0 and p.tick_lower <= tick < p.tick_upper:
                L += p.liquidity
                Lw += p.liquidity * st.weight
        return L, Lw

    def _in_range(self, p: Position) -> bool:
        return p.tick_lower <= self.tick < p.tick_upper

    def _log(self, kind: str, owner: str, **fields) -> None:
        self.log.append(self.t, kind, owner, sqrt_price_after=self.sqrt_price,
                        tick_after=self.tick, liquidity_active_after=self.liquidity, **fields)

    def _state(self, position_id: int) -> _PositionState:
        try:
            return self._positions[position_id]
        except KeyError:
            raise KeyError(f"không có vị thế {position_id}") from None

    # ---------- thao tác đổi trạng thái ----------
    def mint(self, owner: str, tick_lower: int, tick_upper: int, liquidity: float) -> tuple[int, float, float]:
        """Thêm vị thế thanh khoản L trên [tick_lower, tick_upper). Trả (id, token0, token1) phải nạp."""
        self._check_range(tick_lower, tick_upper)
        if liquidity <= 0:
            raise ValueError("liquidity phải dương")
        weight = 1.0 if self.fee_weight is None else float(self.fee_weight(tick_upper - tick_lower))
        if not weight > 0:
            raise ValueError(f"φ(w) phải dương, nhận {weight}")
        Lw = liquidity * weight
        self._update_tick(tick_lower, liquidity, Lw, upper=False)
        self._update_tick(tick_upper, liquidity, Lw, upper=True)
        pid = self._next_id
        self._next_id += 1
        pos = Position(pid, owner, tick_lower, tick_upper, float(liquidity))
        in0, in1 = self._fee_growth_inside(tick_lower, tick_upper)
        self._positions[pid] = _PositionState(pos, weight, in0, in1)
        if self._in_range(pos):
            self.liquidity += liquidity
            self.liquidity_weighted += Lw
        a0, a1 = amounts_for_liquidity(self.sqrt_price, sqrt_price_at_tick(tick_lower),
                                       sqrt_price_at_tick(tick_upper), liquidity)
        self._log("mint", owner, position_id=pid, tick_lower=tick_lower, tick_upper=tick_upper,
                  liquidity=float(liquidity), amount0=a0, amount1=a1)
        return pid, a0, a1

    def burn(self, position_id: int, liquidity: float | None = None) -> tuple[float, float]:
        """Rút L (None = rút hết) khỏi vị thế. Trả (token0, token1) nhận về, CHƯA gồm phí."""
        st = self._state(position_id)
        p = st.pos
        L = p.liquidity if liquidity is None else float(liquidity)
        if L < 0 or L > p.liquidity * (1 + 1e-12):
            raise ValueError(f"rút {L} vượt thanh khoản vị thế {p.liquidity}")
        L = min(L, p.liquidity)
        self._accrue(st)
        a0, a1 = amounts_for_liquidity(self.sqrt_price, sqrt_price_at_tick(p.tick_lower),
                                       sqrt_price_at_tick(p.tick_upper), L)
        if L > 0:
            Lw = L * st.weight
            p.liquidity -= L
            if self._in_range(p):
                self.liquidity -= L
                self.liquidity_weighted -= Lw
                if _mat_so(self.liquidity, L) or _mat_so(self.liquidity_weighted, Lw):
                    self.liquidity, self.liquidity_weighted = self._active_sums(self.tick)
            self._update_tick(p.tick_lower, -L, -Lw, upper=False)
            self._update_tick(p.tick_upper, -L, -Lw, upper=True)
        self._log("burn", p.owner, position_id=p.id, tick_lower=p.tick_lower,
                  tick_upper=p.tick_upper, liquidity=L, amount0=-a0, amount1=-a1)
        return a0, a1

    def collect(self, position_id: int) -> tuple[float, float]:
        """Thu toàn bộ phí đã tích lũy của vị thế, trả (fee0, fee1) và đặt lại về 0."""
        st = self._state(position_id)
        self._accrue(st)
        f0, f1 = st.owed0, st.owed1
        st.owed0 = st.owed1 = 0.0
        self._log("collect", st.pos.owner, position_id=position_id, fee0=f0, fee1=f1)
        return f0, f1

    def swap(self, owner: str, zero_for_one: bool, amount_in: float | None = None,
             sqrt_price_limit: float | None = None) -> SwapResult:
        """Swap cross-tick. amount_in (token vào, đã gồm phí) và/hoặc sqrt_price_limit; dừng ở điều
        kiện đến trước hoặc khi hết thanh khoản. zero_for_one=True: bán token0, giá giảm."""
        res = self._swap_core(zero_for_one, amount_in, sqrt_price_limit, commit=True)
        if zero_for_one:
            self._log("swap", owner, amount0=res.amount_in, amount1=-res.amount_out, fee0=res.fee)
        else:
            self._log("swap", owner, amount0=-res.amount_out, amount1=res.amount_in, fee1=res.fee)
        return res

    def quote_swap(self, zero_for_one: bool, amount_in: float | None = None,
                   sqrt_price_limit: float | None = None) -> SwapResult:
        """Như swap nhưng KHÔNG đổi trạng thái, không ghi log — để farmer tính trượt giá MC(v)."""
        return self._swap_core(zero_for_one, amount_in, sqrt_price_limit, commit=False)

    def _next_initialized(self, zero_for_one: bool, tick: int) -> int | None:
        """Tick đã khởi tạo kế tiếp theo chiều swap: ≤ tick nếu đi xuống, > tick nếu đi lên."""
        ts = self._sorted_ticks
        if zero_for_one:
            k = bisect.bisect_right(ts, tick) - 1
            return ts[k] if k >= 0 else None
        k = bisect.bisect_right(ts, tick)
        return ts[k] if k < len(ts) else None

    def _swap_core(self, zero_for_one: bool, amount_in: float | None,
                   sqrt_price_limit: float | None, commit: bool) -> SwapResult:
        """Vòng lặp swap kiểu v3 trên biến cục bộ; commit=True mới ghi trạng thái vào bể."""
        if amount_in is None and sqrt_price_limit is None:
            raise ValueError("cần amount_in hoặc sqrt_price_limit")
        if amount_in is not None and amount_in < 0:
            raise ValueError("amount_in phải ≥ 0")
        down = zero_for_one
        if sqrt_price_limit is None:
            limit = sqrt_price_at_tick(MIN_TICK if down else MAX_TICK)
        else:
            limit = float(sqrt_price_limit)
        z, tick, L, Lw = self.sqrt_price, self.tick, self.liquidity, self.liquidity_weighted
        z0, tick0 = z, tick
        g = self.fee_growth_global0 if down else self.fee_growth_global1
        remaining = math.inf if amount_in is None else float(amount_in)
        total_in = total_out = total_fee = 0.0
        crossed: list[tuple[int, float]] = []          # (tick, feeGrowthGlobal lúc qua)
        gamma = 1.0 - self.fee

        while remaining > 0 and (z > limit if down else z < limit):
            nxt = self._next_initialized(down, tick)
            if nxt is None:
                if L <= 0:
                    break                                  # hết thanh khoản theo chiều này
                z_tick = None
                target = limit
            else:
                z_tick = sqrt_price_at_tick(nxt)
                target = max(z_tick, limit) if down else min(z_tick, limit)

            if L > 0:
                net_max = amount0_delta(target, z, L) if down else amount1_delta(z, target, L)
                gross_max = net_max / gamma
                if remaining >= gross_max:
                    z_new, net, step_in = target, net_max, gross_max
                else:
                    step_in = remaining
                    net = step_in * gamma
                    z_new = 1.0 / (1.0 / z + net / L) if down else z + net / L
                    z_new = max(z_new, target) if down else min(z_new, target)
                out = amount1_delta(z_new, z, L) if down else amount0_delta(z, z_new, L)
                fee_amt = step_in - net
                g += fee_amt / Lw
                total_in += step_in
                total_out += out
                total_fee += fee_amt
                if remaining != math.inf:
                    remaining = 0.0 if step_in == remaining else remaining - step_in
            else:
                z_new = target                             # khoảng trống: nhảy giá, không tốn gì

            z = z_new
            if z_tick is not None and z == z_tick:         # chạm tick đã khởi tạo → qua tick
                net_L, net_w = self._ticks[nxt].liquidity_net, self._ticks[nxt].weighted_net
                crossed.append((nxt, g))
                if down:
                    L -= net_L
                    Lw -= net_w
                    tick = nxt - 1
                else:
                    L += net_L
                    Lw += net_w
                    tick = nxt
                if _mat_so(L, net_L) or _mat_so(Lw, net_w):
                    # trừ hai số gần nhau (ví dụ rời tường lớn) → cộng lại chính xác từ các vị thế,
                    # để vị thế nhỏ còn lại không bị coi là rỗng và L, Lw cùng về 0 đúng lúc
                    L, Lw = self._active_sums(tick)
            else:
                tick = tick_at_sqrt_price(z)

        if commit:
            for i, g_at in crossed:                        # lật feeGrowthOutside như v3
                info = self._ticks[i]
                if down:
                    info.fee_growth_outside0 = g_at - info.fee_growth_outside0
                    info.fee_growth_outside1 = self.fee_growth_global1 - info.fee_growth_outside1
                else:
                    info.fee_growth_outside0 = self.fee_growth_global0 - info.fee_growth_outside0
                    info.fee_growth_outside1 = g_at - info.fee_growth_outside1
            if down:
                self.fee_growth_global0 = g
            else:
                self.fee_growth_global1 = g
            self.sqrt_price, self.tick, self.liquidity, self.liquidity_weighted = z, tick, L, Lw
        return SwapResult(total_in, total_out, total_fee, zero_for_one, z0, z, tick0, tick,
                          abs(tick - tick0))

    # ---------- đọc trạng thái ----------
    def position_amounts(self, position_id: int) -> tuple[float, float]:
        """(token0, token1) hiện nằm trong vị thế theo giá hiện tại, chưa gồm phí."""
        p = self._state(position_id).pos
        return amounts_for_liquidity(self.sqrt_price, sqrt_price_at_tick(p.tick_lower),
                                     sqrt_price_at_tick(p.tick_upper), p.liquidity)

    def fees_owed(self, position_id: int) -> tuple[float, float]:
        """Phí chưa thu (fee0 token0, fee1 token1), không đổi trạng thái."""
        st = self._state(position_id)
        p = st.pos
        in0, in1 = self._fee_growth_inside(p.tick_lower, p.tick_upper)
        Lw = p.liquidity * st.weight
        return (st.owed0 + Lw * (in0 - st.fee_growth_inside0_last),
                st.owed1 + Lw * (in1 - st.fee_growth_inside1_last))

    def positions(self, owner: str | None = None) -> list[Position]:
        """Các vị thế còn thanh khoản > 0 (bản sao), lọc theo owner nếu có."""
        return [Position(**vars(st.pos)) for st in self._positions.values()
                if st.pos.liquidity > 0 and (owner is None or st.pos.owner == owner)]

    def liquidity_at(self, tick: int) -> float:
        """Thanh khoản hoạt động nếu giá nằm ở tick này: Σ liquidity_net của các tick ≤ tick."""
        return sum(info.liquidity_net for i, info in self._ticks.items() if i <= tick)

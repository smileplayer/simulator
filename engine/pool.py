"""Bể CLMM kiểu Uniswap v3 (float), đúng chữ ký INTERFACE mục 2.

Cấu trúc dữ liệu tổng quát theo tick (liquidity_net/gross, feeGrowthOutside) nên vị thế có độ
rộng bất kỳ — không giả định một tick. Phí cộng dồn theo feeGrowth + checkpoint như v3.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .log import EventLog
from .tick_math import amounts_for_liquidity, sqrt_price_at_tick, tick_at_sqrt_price


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
    fee_growth_outside0: float = 0.0     # token0 trên mỗi đơn vị L, phía "bên kia" tick
    fee_growth_outside1: float = 0.0


@dataclass
class _PositionState:
    pos: Position
    fee_growth_inside0_last: float = 0.0
    fee_growth_inside1_last: float = 0.0
    owed0: float = 0.0
    owed1: float = 0.0


class Pool:
    """Bể một cặp token0/token1 với thanh khoản tập trung, swap cross-tick."""

    def __init__(self, fee: float, sqrt_price: float, tick_spacing: int = 1):
        if not 0 <= fee < 1:
            raise ValueError("fee phải trong [0, 1)")
        if tick_spacing < 1:
            raise ValueError("tick_spacing phải ≥ 1")
        self.fee = fee
        self.tick_spacing = tick_spacing
        self.sqrt_price = float(sqrt_price)
        self.tick = tick_at_sqrt_price(self.sqrt_price)
        self.liquidity = 0.0                     # L_active
        self.fee_growth_global0 = 0.0            # token0 trên mỗi đơn vị L
        self.fee_growth_global1 = 0.0
        self.t = 0                               # bước thời gian, bộ chạy đặt
        self.log = EventLog()
        self._ticks: dict[int, _Tick] = {}
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

    def _update_tick(self, i: int, dL: float, upper: bool) -> None:
        """Cộng dL vào tick i (biên dưới nếu upper=False). Khởi tạo feeGrowthOutside như v3."""
        info = self._ticks.get(i)
        if info is None:
            info = _Tick()
            if i <= self.tick:                   # quy ước v3: coi mọi phí trước đây nằm dưới tick
                info.fee_growth_outside0 = self.fee_growth_global0
                info.fee_growth_outside1 = self.fee_growth_global1
            self._ticks[i] = info
        info.liquidity_gross += dL
        info.liquidity_net += -dL if upper else dL
        if info.liquidity_gross <= 1e-12 * max(1.0, abs(dL)):
            del self._ticks[i]

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
        st.owed0 += p.liquidity * (in0 - st.fee_growth_inside0_last)
        st.owed1 += p.liquidity * (in1 - st.fee_growth_inside1_last)
        st.fee_growth_inside0_last, st.fee_growth_inside1_last = in0, in1

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
        self._update_tick(tick_lower, liquidity, upper=False)
        self._update_tick(tick_upper, liquidity, upper=True)
        pid = self._next_id
        self._next_id += 1
        pos = Position(pid, owner, tick_lower, tick_upper, float(liquidity))
        in0, in1 = self._fee_growth_inside(tick_lower, tick_upper)
        self._positions[pid] = _PositionState(pos, in0, in1)
        if self._in_range(pos):
            self.liquidity += liquidity
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
            if self._in_range(p):
                self.liquidity = max(self.liquidity - L, 0.0)
            self._update_tick(p.tick_lower, -L, upper=False)
            self._update_tick(p.tick_upper, -L, upper=True)
            p.liquidity -= L
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
        """Swap cross-tick (chưa cài — việc kế tiếp của vai A)."""
        raise NotImplementedError("swap cross-tick: việc kế tiếp của vai A")

    def quote_swap(self, zero_for_one: bool, amount_in: float | None = None,
                   sqrt_price_limit: float | None = None) -> SwapResult:
        """Như swap nhưng không đổi trạng thái (chưa cài — việc kế tiếp của vai A)."""
        raise NotImplementedError("quote_swap: việc kế tiếp của vai A")

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
        return (st.owed0 + p.liquidity * (in0 - st.fee_growth_inside0_last),
                st.owed1 + p.liquidity * (in1 - st.fee_growth_inside1_last))

    def positions(self, owner: str | None = None) -> list[Position]:
        """Các vị thế còn thanh khoản > 0 (bản sao), lọc theo owner nếu có."""
        return [Position(**vars(st.pos)) for st in self._positions.values()
                if st.pos.liquidity > 0 and (owner is None or st.pos.owner == owner)]

    def liquidity_at(self, tick: int) -> float:
        """Thanh khoản hoạt động nếu giá nằm ở tick này: Σ liquidity_net của các tick ≤ tick."""
        return sum(info.liquidity_net for i, info in self._ticks.items() if i <= tick)

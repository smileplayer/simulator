"""GĐ3 (RQ3): phân bổ phí theo độ rộng φ(w) — lời giải giải tích cho victim chọn (vốn, độ rộng) và LP lành mạnh.

Engine chia phí trong tick đang hoạt động theo L_i·φ(w_i) / Σ_j L_j·φ(w_j) (quyết định chốt 6). Victim có vốn C
(token1), đặt dải w tick quanh giá: L = C·ℓ(w), với ℓ(w) = L trên mỗi token1 vốn, tính **đúng hình học CLMM**
(`amounts_for_liquidity` tại giá hiện tại) thay vì xấp xỉ ℓ ≈ 1/(κw), κ = z·ln(1,0001)/2 (sai < 0,3% với w ≤ 200).

Trọng số trên mỗi đơn vị vốn g(w) = φ(w)·ℓ(w). Với W = Σ L_j·φ(w_j) của LP khác trong tick tường (tường: L_A·φ(1)),
khối lượng V (token1/cửa sổ), phí f, chi phí vốn c (token1 trên mỗi token1 vốn mỗi cửa sổ, quyết định chốt 5):
    Π_V(C, w) = f·V·C·g/(W + C·g) − c·C
    C_V*(w)   = [√(f·V·W·g/c) − W] / g          (0 nếu âm)
    Π_V*(w)   = (√(f·V) − √(c·W/g))²            → w* = argmax g(w), KHÔNG phụ thuộc V, W, c (khi victim vào)
φ ≡ 1, w = 1 ⇒ trùng Lemma 4 với c_V (theo L) = c/ℓ(1).
"""
from __future__ import annotations

import math
from typing import Any, Callable

from engine import amounts_for_liquidity, sqrt_price_at_tick

LUOI_W = (1, 2, 5, 10, 20, 50, 100, 200)
LN_TICK = math.log(1.0001)


class PhiLuyThua:
    """Họ φ(w) = min(1, (w/w₀)^α), w tính bằng tick; α = 0 ⇔ pro-rata (φ ≡ 1)."""

    def __init__(self, alpha: float, w0: float):
        self.alpha, self.w0 = float(alpha), float(w0)

    def __call__(self, w: int) -> float:
        """Trọng số φ(w) (không thứ nguyên), w = tick_upper − tick_lower."""
        return min(1.0, (w / self.w0) ** self.alpha)

    def __repr__(self) -> str:
        return f"PhiLuyThua(alpha={self.alpha}, w0={self.w0})"


def tao_phi(cfg_phi: dict | None) -> Callable[[int], float] | None:
    """Config `{"alpha": α, "w0": w₀}` → φ; None hoặc α = 0 → None (engine chia pro-rata như v3)."""
    if not cfg_phi or float(cfg_phi.get("alpha", 0.0)) == 0.0:
        return None
    return PhiLuyThua(cfg_phi["alpha"], cfg_phi["w0"])


def khoang_tick(tick: int, w: int, vi_tri: str = "giua") -> tuple[int, int]:
    """Dải w tick quanh tick chứa giá (spacing 1), như `agents.base.khoang_quanh_gia`."""
    lui = {"tren": 0, "giua": w // 2, "duoi": w - 1}[vi_tri]
    return tick - lui, tick - lui + w


def von_tren_L(z: float, lo: int, hi: int) -> float:
    """Vốn (token1, định giá theo giá hiện tại z² ) của 1 đơn vị L trên [lo, hi) tại √P = z."""
    a0, a1 = amounts_for_liquidity(z, sqrt_price_at_tick(lo), sqrt_price_at_tick(hi), 1.0)
    return a0 * z * z + a1


def l_tren_von(w: int, z: float, tick: int | None = None, vi_tri: str = "giua") -> float:
    """ℓ(w): L trên mỗi token1 vốn cho dải w tick đặt theo `vi_tri` quanh tick chứa giá (hình học CLMM đúng)."""
    from engine import tick_at_sqrt_price
    tick = tick_at_sqrt_price(z) if tick is None else tick
    return 1.0 / von_tren_L(z, *khoang_tick(tick, w, vi_tri))


def l_tren_von_xap_xi(w: int, z: float) -> float:
    """Xấp xỉ tuyến tính ℓ(w) ≈ 1/(κ·w), κ = z·ln(1,0001)/2 (token1 trên mỗi L mỗi tick)."""
    return 2.0 / (z * LN_TICK * w)


def g_w(w: int, phi: Callable[[int], float] | None, z: float, tick: int | None = None,
        vi_tri: str = "giua") -> float:
    """g(w) = φ(w)·ℓ(w): thanh khoản có trọng số trên mỗi token1 vốn."""
    return (1.0 if phi is None else phi(w)) * l_tren_von(w, z, tick, vi_tri)


def C_V_sao(f: float, V: float, W: float, g: float, c: float) -> float:
    """C_V*(w) (token1): vốn tối ưu của victim; W = Σ L_j·φ(w_j) của LP khác trong tick, c theo vốn mỗi cửa sổ."""
    if W <= 0 or g <= 0:
        return 0.0
    return max(0.0, (math.sqrt(f * V * W * g / c) - W) / g)


def Pi_V(C: float, f: float, V: float, W: float, g: float, c: float) -> float:
    """Π_V(C, w) (token1 mỗi cửa sổ) = f·V·C·g/(W + C·g) − c·C."""
    return f * V * C * g / (W + C * g) - c * C if C > 0 else 0.0


def chon_w(f: float, V: float, W: float, c: float, phi: Callable[[int], float] | None, z: float,
           luoi=LUOI_W, tick: int | None = None, vi_tri: str = "giua", W_theo_w=None) -> dict:
    """Victim toàn tri: duyệt lưới w, chọn w cho Π_V*(w) lớn nhất (hòa → w nhỏ hơn).
    `W_theo_w(w)` (tùy chọn) nếu W phụ thuộc w; mặc định W hằng. Trả {w, C, Pi, g, bang: [(w, g, C, Π)]}.
    Victim không vào ở mọi w (Π* = 0) → vẫn trả w = argmax g (C = 0)."""
    bang = []
    for w in luoi:
        g = g_w(w, phi, z, tick, vi_tri)
        Ww = W if W_theo_w is None else W_theo_w(w)
        C = C_V_sao(f, V, Ww, g, c)
        bang.append((w, g, C, Pi_V(C, f, V, Ww, g, c)))
    tot = max(bang, key=lambda r: (r[3], r[1], -r[0]))      # Π trước, rồi g; hòa tuyệt đối → w nhỏ
    return dict(w=tot[0], g=tot[1], C=tot[2], Pi=tot[3], bang=bang)


def w_sao_hinh_hoc(phi: Callable[[int], float] | None, z: float, luoi=LUOI_W, tick: int | None = None,
                   vi_tri: str = "giua", tol: float = 1e-12) -> int:
    """w* = argmax g(w) trên lưới (đúng khi victim vào: Π* tăng theo g). Hòa trong `tol` tương đối → w nhỏ."""
    gs = [(w, g_w(w, phi, z, tick, vi_tri)) for w in luoi]
    g_max = max(g for _, g in gs)
    return min(w for w, g in gs if g >= g_max * (1 - tol))


def alpha_sao(w0: float, z: float = 1.0, luoi=LUOI_W, tick: int | None = None, vi_tri: str = "giua",
              hi: float = 5.0, tol: float = 1e-6) -> float:
    """α* nhỏ nhất làm w* (họ φ = min(1, (w/w₀)^α)) rời khỏi 1, chia đôi trên [0, hi].
    "Rời khỏi 1" đơn điệu theo α vì φ(w)/φ(1) không giảm theo α với mọi w ≥ 1. Trả inf nếu không rời ở hi."""
    roi = lambda a: w_sao_hinh_hoc(PhiLuyThua(a, w0), z, luoi, tick, vi_tri) != 1
    if not roi(hi):
        return math.inf
    lo_a, hi_a = 0.0, hi
    while hi_a - lo_a > tol:
        mid = (lo_a + hi_a) / 2
        lo_a, hi_a = (lo_a, mid) if roi(mid) else (mid, hi_a)
    return hi_a


def ty_le_von(k: float, u: float) -> float:
    """C_V*(RA) / C_V*(pro-rata) khi c theo vốn: k = c_V·L_A/(f·V) (như RQ1), u = [g(1)/g(w*)]·[W_RA/W_PR]
    (W_PR = L_A, W_RA = L_A·φ(1) + phần LP rộng). Công thức: (√(u/k) − u)/(1/√k − 1), cắt ở 0.
    > 1 ⇔ (1/√k − 1)² < u < 1 khi k > 1/4: range-aware KÉO victim vào nhiều vốn hơn (tường mất phần phí)."""
    pr = 1 / math.sqrt(k) - 1
    return max(0.0, math.sqrt(u / k) - u) / pr if pr > 0 else math.nan


class LPLanhManh:
    """LP thụ động không bị nhắm: vào ở `t_vao` với vốn `von` (token1, chia đúng tỷ lệ tại giá lúc vào), dải `w`
    tick đặt theo `vi_tri`, rút + thu phí ở `t_ra`. Mỗi bước còn giữ vị thế: ghi tick chứa giá có trong dải không,
    L hoạt động tại giá, và trượt giá của lệnh mua tham chiếu `lenh_mau` token1 (quote_swap, không đổi trạng thái)."""

    def __init__(self, owner: str, von: float, w: int, t_vao: int, t_ra: int, vi_tri: str = "giua",
                 lenh_mau: float = 1000.0):
        self.owner, self.von, self.w = owner, von, w
        self.t_vao, self.t_ra, self.vi_tri, self.lenh_mau = t_vao, t_ra, vi_tri, lenh_mau
        self.pid: int | None = None
        self.L = 0.0
        self.von_thuc = 0.0                       # vốn nạp thật (token1, theo giá lúc vào)
        self.trong_dai: list[bool] = []
        self.L_gia: list[float] = []
        self.truot: list[float] = []
        self.phi1 = 0.0                           # phí thu về quy token1 theo giá lúc rút

    def act(self, t: int, pool: Any, market: Any) -> None:
        """Mint ở t_vao, đo mỗi bước, burn + collect ở t_ra."""
        from agents.base import khoang_quanh_gia, tick_chua_gia
        if t == self.t_vao and self.pid is None:
            lo, hi = khoang_quanh_gia(pool, self.w, self.vi_tri)
            self.L = self.von / von_tren_L(pool.sqrt_price, lo, hi)
            self.pid, a0, a1 = pool.mint(self.owner, lo, hi, self.L)
            self.von_thuc = a0 * pool.sqrt_price ** 2 + a1
            self.lo, self.hi = lo, hi
        if self.pid is None or t > self.t_ra:
            return
        if t == self.t_ra:
            pool.burn(self.pid)
            f0, f1 = pool.collect(self.pid)
            self.phi1 = f1 + f0 * pool.sqrt_price ** 2
            self.pid = None
            return
        tick = tick_chua_gia(pool)
        self.trong_dai.append(self.lo <= tick < self.hi)
        self.L_gia.append(pool.liquidity)
        q = pool.quote_swap(zero_for_one=False, amount_in=self.lenh_mau)
        self.truot.append((q.sqrt_price_after / q.sqrt_price_before) ** 2 - 1)

    def tom_tat(self, W: int) -> dict:
        """Chỉ số cho meta: phí/vốn mỗi cửa sổ W bước, tỷ lệ bước trong dải, L tại giá TB, trượt giá TB lệnh mẫu."""
        n = max(len(self.trong_dai), 1)
        return dict(w=self.w, von=self.von_thuc, phi1=self.phi1,
                    phi_tren_von=self.phi1 / self.von_thuc * W / n if self.von_thuc > 0 else math.nan,
                    trong_dai=sum(self.trong_dai) / n,
                    L_gia=sum(self.L_gia) / n if self.L_gia else math.nan,
                    truot=sum(self.truot) / n if self.truot else math.nan)

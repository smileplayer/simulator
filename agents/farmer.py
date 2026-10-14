"""Farmer săn trợ cấp: tối ưu U(v) = thưởng(v) − [v − P_e·x(v)] với x(v) lấy từ quote_swap trên bể thật.

Farmer chỉ mua token0 bằng token1 (INTERFACE mục 3). Phần `v − P_e·x(v)` = phí f·v + MC(v), trong đó
MC(v) là trượt giá so với giá ngoài — tường dày (L lớn) làm MC nhỏ, nên farmer giao dịch nhiều hơn.
Với bể L hằng, nghiệm khớp Theorem 1: V* = (L/(1−f))·(√(P_e(1−f)/(1−σ)) − z₀), chặn trên bởi Q.
"""
from __future__ import annotations

import math
from typing import Any, Callable

from agents.base import Market

Thuong = Callable[[float], float]
TY_LE_VANG = (math.sqrt(5) - 1) / 2


def thuong_tuyen_tinh(sigma: float, Q: float) -> Thuong:
    """Trợ cấp bài gốc σ·min{v, Q}; v = khối lượng mua cộng dồn trong cửa sổ (token1), trả token1."""
    return lambda v: sigma * min(v, Q)


def thuong_log(sigma: float, Q: float) -> Thuong:
    """Trợ cấp dạng log (giả định kiểu Binance Alpha): σ·Q·log₂(1 + v/Q), token1.

    Bằng σ·Q tại v = Q như dạng tuyến tính, nhưng không có trần cứng và lợi biên giảm dần.
    """
    return lambda v: sigma * Q * math.log2(1 + v / Q)


class Farmer:
    """Farmer chỉ mua, mỗi bước chọn v (token1) tối đa hóa phần thưởng tăng thêm trừ chi phí thực hiện."""

    def __init__(self, owner: str, thuong: Thuong, Q: float | None = None, window: int = 24,
                 v_tran: float | None = None, so_vong: int = 80):
        """`Q`: trần cộng dồn mỗi cửa sổ (token1), None = không trần (dạng log); `window`: số bước một
        cửa sổ trợ cấp; `v_tran`: cận trên tìm kiếm mỗi bước khi không có trần (mặc định 10·Q)."""
        if Q is None and v_tran is None:
            raise ValueError("cần Q hoặc v_tran để chặn miền tìm kiếm")
        self.owner = owner
        self.thuong = thuong
        self.Q = Q
        self.window = window
        self.v_tran = v_tran if v_tran is not None else 10 * Q
        self.so_vong = so_vong
        self.v_cua_so = 0.0          # khối lượng mua đã làm trong cửa sổ hiện tại (token1)
        self._cua_so = None

    def loi_ich(self, pool: Any, p_e: float, v: float) -> float:
        """U tăng thêm (token1) nếu mua v token1 ngay bây giờ, trượt giá tính bằng quote_swap."""
        if v <= 0:
            return 0.0
        r = pool.quote_swap(zero_for_one=False, amount_in=v)
        vao = r.amount_in            # có thể < v nếu hết thanh khoản
        return (self.thuong(self.v_cua_so + vao) - self.thuong(self.v_cua_so)) - (vao - p_e * r.amount_out)

    def ke_hoach(self, pool: Any, p_e: float) -> tuple[float, float]:
        """Trả (v*, U(v*)) tối ưu cho bước này; v* = 0 nếu không có lãi. Đơn vị token1."""
        hi = self.v_tran if self.Q is None else max(0.0, min(self.v_tran, self.Q - self.v_cua_so))
        if hi <= 0:
            return 0.0, 0.0
        a, b = 0.0, hi                                   # U lõm theo v → tìm kiếm tỷ lệ vàng
        c, d = b - TY_LE_VANG * (b - a), a + TY_LE_VANG * (b - a)
        uc, ud = self.loi_ich(pool, p_e, c), self.loi_ich(pool, p_e, d)
        for _ in range(self.so_vong):
            if uc >= ud:
                b, d, ud = d, c, uc
                c = b - TY_LE_VANG * (b - a)
                uc = self.loi_ich(pool, p_e, c)
            else:
                a, c, uc = c, d, ud
                d = a + TY_LE_VANG * (b - a)
                ud = self.loi_ich(pool, p_e, d)
        ung_vien = [(0.0, 0.0), ((a + b) / 2, self.loi_ich(pool, p_e, (a + b) / 2)),
                    (hi, self.loi_ich(pool, p_e, hi))]
        v, u = max(ung_vien, key=lambda vu: vu[1])
        if v <= 1e-9 * hi or u <= 0:                     # hội tụ về 0 = không giao dịch
            return 0.0, 0.0
        return v, u

    def act(self, t: int, pool: Any, market: Market) -> None:
        """Đặt lại khối lượng khi sang cửa sổ mới, rồi mua v* token0 bằng token1 (nếu có lãi)."""
        if t // self.window != self._cua_so:
            self._cua_so, self.v_cua_so = t // self.window, 0.0
        v, u = self.ke_hoach(pool, market.external_price(t))
        if v > 1e-9 and u > 0:
            r = pool.swap(self.owner, zero_for_one=False, amount_in=v)
            self.v_cua_so += r.amount_in

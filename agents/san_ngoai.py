"""Sàn ngoài có độ sâu hữu hạn: giá ngoài nội sinh thay cho giá ghim (cải tiến H, 12/11/2026).

Mô hình: sàn ngoài là một bể tích hằng x·y = L_s² (token0, token1), giá P_s = y/x = z_s². Mỗi bước:
1. cú sốc ngoại sinh (trader khác trên sàn ngoài) đổi giá: z_s ← z_s·exp(vol·ε/2), ε cùng dòng ngẫu nhiên với
   giá ngoài cũ nên cặp phản thực vẫn dùng chung số ngẫu nhiên;
2. farmer mua token0 trong bể rồi bán lại trên sàn ngoài (chiều bán của lệnh cày khối lượng) → z_s giảm;
3. arbitrageur kéo hai giá về một giá chung z*: lượng token0 đi ra khỏi một nơi bằng lượng đi vào nơi kia
   (giải bằng chia đôi trên z*, bể tính bằng `quote_swap` xuyên tick), rồi khớp thật trên bể và cập nhật sàn.
Không có giá ghim: tường giữ giá được hay không là kết quả, phụ thuộc độ dày tường so với độ sâu sàn ngoài.
Độ sâu tính bằng token1 ở một phía của sàn tại giá đầu: `do_sau` = y = L_s·z_s ⇒ L_s = do_sau / z_s.
Giới hạn: farmer lập kế hoạch theo giá biên của sàn (bỏ qua trượt giá khi bán trên sàn); sàn không thu phí.
"""
from __future__ import annotations

import math
from typing import Any


class SanNgoai:
    """Bể tích hằng ngoài chuỗi bể đang xét; giữ √P (token1/token0) và L (đơn vị √(token0·token1))."""

    def __init__(self, do_sau: float, P0: float):
        """`do_sau`: token1 ở một phía của sàn tại giá đầu `P0` (token1/token0)."""
        if do_sau <= 0:
            raise ValueError("do_sau phải > 0")
        self.z = math.sqrt(P0)
        self.L = do_sau / self.z
        self.ban0 = 0.0                                   # token0 farmer đã bán trên sàn (cộng dồn)
        self.arb0 = 0.0                                   # token0 ròng arbitrageur mua trên sàn (dương = mua)

    @property
    def gia(self) -> float:
        """Giá biên của sàn (token1/token0)."""
        return self.z * self.z

    def soc(self, vol: float, eps: float) -> None:
        """Cú sốc ngoại sinh: P_s nhân exp(vol·eps) (vol mỗi bước, eps chuẩn hóa)."""
        self.z *= math.exp(0.5 * vol * eps)

    def ban_token0(self, dx: float) -> None:
        """Có người bán `dx` token0 vào sàn: x tăng, giá giảm."""
        if dx > 0:
            self.z = self.L / (self.L / self.z + dx)

    def mua_token0(self, dx: float) -> None:
        """Có người mua `dx` token0 từ sàn: x giảm, giá tăng (dx phải nhỏ hơn kho token0 của sàn)."""
        if dx > 0:
            x = self.L / self.z - dx
            if x <= 0:
                raise ValueError("mua quá kho token0 của sàn ngoài")
            self.z = self.L / x

    def token0_de_toi(self, z_dich: float) -> float:
        """Lượng token0 (dương) đổi chủ để đưa giá sàn từ z hiện tại tới `z_dich` (√P)."""
        return abs(self.L / self.z - self.L / z_dich)


def can_bang(pool: Any, san: SanNgoai, owner: str = "arb:0", nguong: float = 1e-12, so_vong: int = 60) -> float:
    """Arbitrageur kéo bể và sàn về một giá chung; trả lượng token0 đã chuyển (dương = từ sàn vào bể)."""
    z_p, z_s = pool.sqrt_price, san.z
    if abs(z_p / z_s - 1.0) <= nguong:
        return 0.0
    ban_vao_be = z_p > z_s                                # bể đắt hơn: mua token0 trên sàn, bán vào bể

    def lech(z: float) -> float:
        """Token0 bể cần (hoặc nhả) để tới z trừ token0 sàn nhả (hoặc nhận) khi tới z; đơn điệu theo z."""
        q = pool.quote_swap(ban_vao_be, sqrt_price_limit=z)
        be = q.amount_in if ban_vao_be else q.amount_out
        return be - san.token0_de_toi(z)

    lo, hi = (z_s, z_p) if ban_vao_be else (z_p, z_s)
    # ban_vao_be: lech(lo=z_s) > 0, lech(hi=z_p) < 0; ngược lại: lech(lo=z_p) < 0, lech(hi=z_s) > 0
    for _ in range(so_vong):
        mid = math.sqrt(lo * hi)
        d = lech(mid)
        if (d > 0) == ban_vao_be:
            lo = mid
        else:
            hi = mid
    z_star = math.sqrt(lo * hi)
    r = pool.swap(owner, zero_for_one=ban_vao_be, sqrt_price_limit=z_star)
    if ban_vao_be:
        san.mua_token0(r.amount_in)
        san.arb0 += r.amount_in
        return r.amount_in
    san.ban_token0(r.amount_out)
    san.arb0 -= r.amount_out
    return -r.amount_out

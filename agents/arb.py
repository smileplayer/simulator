"""Arbitrageur `arb:0`: cuối mỗi bước kéo giá bể về giá ngoài P_e(t) (INTERFACE mục 3)."""
from __future__ import annotations

import math
from typing import Any

from agents.base import Market


class Arbitrageur:
    """Swap tới đúng √P_e bằng sqrt_price_limit; hết thanh khoản thì dừng ở đó."""

    def __init__(self, owner: str = "arb:0", nguong: float = 1e-12, bat: bool = True,
                 von: float | None = None):
        """`nguong`: chênh lệch tương đối của √P dưới mức này thì bỏ qua; `bat=False` để tắt (pha Attack).

        `von` (token1, cấu hình `arb_budget`): tổng token1 tối đa arbitrageur được bỏ ra để MUA token0 cộng dồn cả
        kịch bản (đã gồm phí; tiền thu về khi bán token0 không hoàn lại ngân sách). `None` = không giới hạn, đúng
        hành vi cũ. Bán token0 vẫn dùng kho token0 vô hạn. Hết vốn thì không kéo giá lên được nữa."""
        self.owner = owner
        self.nguong = nguong
        self.bat = bat
        self.von = von
        self.da_chi = 0.0                                  # token1 đã bỏ ra mua token0 (cộng dồn)

    def act(self, t: int, pool: Any, market: Market) -> None:
        """Bán token0 nếu giá bể > P_e, mua token0 nếu giá bể < P_e (P_e: token1/token0)."""
        if not self.bat:
            return
        z_e = math.sqrt(market.external_price(t))
        if abs(pool.sqrt_price / z_e - 1) <= self.nguong:
            return
        ban = pool.sqrt_price > z_e
        if self.von is None or ban:                        # nhánh cũ: không giới hạn vốn (hoặc bán token0)
            kq = pool.swap(self.owner, zero_for_one=ban, sqrt_price_limit=z_e)
            if not ban:
                self.da_chi += kq.amount_in                # chỉ ghi sổ, không ảnh hưởng hành vi
            return
        con = self.von - self.da_chi                       # nhánh mua token0 bằng token1 có hạn mức
        if con <= 0:
            return
        kq = pool.swap(self.owner, zero_for_one=False, amount_in=con, sqrt_price_limit=z_e)
        self.da_chi += kq.amount_in

"""Arbitrageur `arb:0`: cuối mỗi bước kéo giá bể về giá ngoài P_e(t) (INTERFACE mục 3)."""
from __future__ import annotations

import math
from typing import Any

from agents.base import Market


class Arbitrageur:
    """Swap tới đúng √P_e bằng sqrt_price_limit; hết thanh khoản thì dừng ở đó."""

    def __init__(self, owner: str = "arb:0", nguong: float = 1e-12, bat: bool = True):
        """`nguong`: chênh lệch tương đối của √P dưới mức này thì bỏ qua; `bat=False` để tắt (pha Attack)."""
        self.owner = owner
        self.nguong = nguong
        self.bat = bat

    def act(self, t: int, pool: Any, market: Market) -> None:
        """Bán token0 nếu giá bể > P_e, mua token0 nếu giá bể < P_e (P_e: token1/token0)."""
        if not self.bat:
            return
        z_e = math.sqrt(market.external_price(t))
        if abs(pool.sqrt_price / z_e - 1) <= self.nguong:
            return
        pool.swap(self.owner, zero_for_one=pool.sqrt_price > z_e, sqrt_price_limit=z_e)

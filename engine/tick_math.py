"""Toán CLMM kiểu Uniswap v3 bằng float: đổi tick ↔ √P và lượng token ↔ thanh khoản L.

Quy ước: P = token1/token0, z = √P, P(i) = 1.0001^i. Một vị thế [tick_lower, tick_upper)
có biên giá z_l = z(tick_lower), z_u = z(tick_upper).
"""
from __future__ import annotations

import math

CO_SO = 1.0001
_LOG_CO_SO = math.log(CO_SO)
MIN_TICK = -887272
MAX_TICK = 887272


def sqrt_price_at_tick(i: int) -> float:
    """√P tại biên dưới của tick i (không thứ nguyên, √(token1/token0))."""
    if not MIN_TICK <= i <= MAX_TICK:
        raise ValueError(f"tick {i} ngoài [{MIN_TICK}, {MAX_TICK}]")
    return CO_SO ** (i / 2)


def tick_at_sqrt_price(z: float) -> int:
    """Tick i lớn nhất sao cho z(i) ≤ z, tức tick chứa giá √P = z."""
    if z <= 0:
        raise ValueError("√P phải dương")
    i = math.floor(2 * math.log(z) / _LOG_CO_SO)
    # sửa sai số làm tròn của log ở sát biên tick
    if i + 1 <= MAX_TICK and sqrt_price_at_tick(i + 1) <= z:
        i += 1
    elif sqrt_price_at_tick(i) > z:
        i -= 1
    return i


def amount0_delta(za: float, zb: float, L: float) -> float:
    """Lượng token0 ứng với L khi giá đi giữa √P = za và zb: L·(1/za − 1/zb), za ≤ zb."""
    za, zb = min(za, zb), max(za, zb)
    return L * (zb - za) / (za * zb)


def amount1_delta(za: float, zb: float, L: float) -> float:
    """Lượng token1 ứng với L khi giá đi giữa √P = za và zb: L·(zb − za), za ≤ zb."""
    za, zb = min(za, zb), max(za, zb)
    return L * (zb - za)


def amounts_for_liquidity(z: float, z_lower: float, z_upper: float, L: float) -> tuple[float, float]:
    """(token0, token1) nằm trong vị thế thanh khoản L trên [z_lower, z_upper] khi giá là z.

    Giá dưới khoảng → toàn token0; trên khoảng → toàn token1; trong khoảng → cả hai.
    """
    if z <= z_lower:
        return amount0_delta(z_lower, z_upper, L), 0.0
    if z >= z_upper:
        return 0.0, amount1_delta(z_lower, z_upper, L)
    return amount0_delta(z, z_upper, L), amount1_delta(z_lower, z, L)


def liquidity_for_amounts(z: float, z_lower: float, z_upper: float,
                          amount0: float, amount1: float) -> float:
    """L lớn nhất mua được bằng (amount0 token0, amount1 token1) trên [z_lower, z_upper] tại giá z."""
    if z <= z_lower:
        return amount0 * z_lower * z_upper / (z_upper - z_lower)
    if z >= z_upper:
        return amount1 / (z_upper - z_lower)
    L0 = amount0 * z * z_upper / (z_upper - z)
    L1 = amount1 / (z - z_lower)
    return min(L0, L1)

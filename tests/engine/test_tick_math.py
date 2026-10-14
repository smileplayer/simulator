"""Test toán tick ↔ √P và lượng token ↔ L."""
import math

import pytest

from engine.tick_math import (
    amount0_delta, amount1_delta, amounts_for_liquidity, liquidity_for_amounts,
    sqrt_price_at_tick, tick_at_sqrt_price,
)


@pytest.mark.parametrize("i", [-887272, -100_000, -1, 0, 1, 7, 12_345, 887271])
def test_tick_khu_dao(i):
    z = sqrt_price_at_tick(i)
    assert tick_at_sqrt_price(z) == i                      # đúng biên → chính tick đó
    assert tick_at_sqrt_price(z * (1 + 1e-12)) == i
    if i > -887272:
        assert tick_at_sqrt_price(z * (1 - 1e-12)) == i - 1  # sát dưới biên → tick dưới


def test_tick_ngoai_bien():
    with pytest.raises(ValueError):
        sqrt_price_at_tick(887273)


def test_vi_du_phan_cong_1000_usdt_mot_tick():
    """1.000 USDT trong tick [-1, 0) khi P₀ = 1 → L = 1000/(1 − 1.0001^-½) ≈ 20.001.000."""
    zl, zu = sqrt_price_at_tick(-1), sqrt_price_at_tick(0)
    L = liquidity_for_amounts(1.0, zl, zu, 0.0, 1000.0)
    assert L == pytest.approx(1000 / (1 - 1.0001 ** -0.5), rel=1e-12)
    assert L == pytest.approx(20_000_000, rel=1e-4)
    x, y = amounts_for_liquidity(1.0, zl, zu, L)
    assert x == 0.0 and y == pytest.approx(1000, rel=1e-12)


def test_ba_trang_thai():
    zl, zu, L = sqrt_price_at_tick(-10), sqrt_price_at_tick(10), 1e6
    x, y = amounts_for_liquidity(zl * 0.99, zl, zu, L)     # dưới khoảng: toàn token0
    assert y == 0 and x == pytest.approx(L * (1 / zl - 1 / zu))
    x, y = amounts_for_liquidity(zu * 1.01, zl, zu, L)     # trên khoảng: toàn token1
    assert x == 0 and y == pytest.approx(L * (zu - zl))
    x, y = amounts_for_liquidity(1.0, zl, zu, L)           # trong khoảng: cả hai
    assert x == pytest.approx(L * (1 - 1 / zu)) and y == pytest.approx(L * (1 - zl))


def test_liquidity_for_amounts_nghich_dao():
    zl, zu, z = sqrt_price_at_tick(-50), sqrt_price_at_tick(30), sqrt_price_at_tick(-5)
    x, y = amounts_for_liquidity(z, zl, zu, 3.7e5)
    assert liquidity_for_amounts(z, zl, zu, x, y) == pytest.approx(3.7e5, rel=1e-12)
    # dư token1 → bị giới hạn bởi token0
    assert liquidity_for_amounts(z, zl, zu, x, 2 * y) == pytest.approx(3.7e5, rel=1e-12)


def test_delta_doi_xung():
    assert amount0_delta(1.2, 1.1, 5.0) == amount0_delta(1.1, 1.2, 5.0)
    assert amount1_delta(1.2, 1.1, 5.0) == pytest.approx(0.5)
    assert math.isclose(amount0_delta(1.0, 2.0, 4.0), 2.0)

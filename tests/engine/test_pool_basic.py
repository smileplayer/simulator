"""Test Pool: mint/burn/collect, L_active, liquidity_at, log — chưa có swap."""
import math

import pytest

from engine.log import COLUMNS
from engine.pool import Pool
from engine.tick_math import sqrt_price_at_tick


def test_khoi_tao():
    pool = Pool(fee=0.0025, sqrt_price=1.0)
    assert pool.tick == 0 and pool.liquidity == 0 and len(pool.log) == 0
    assert Pool(0.003, sqrt_price_at_tick(-7) * 1.000001).tick == -7


def test_mint_mot_tick_duoi_gia():
    """Tường kiểu bài gốc: vị thế [-1, 0) dưới P₀ = 1 chỉ chứa token1, chưa hoạt động."""
    pool = Pool(0.0025, 1.0)
    L = 1000 / (1 - 1.0001 ** -0.5)
    pid, a0, a1 = pool.mint("attacker:0", -1, 0, L)
    assert a0 == 0 and a1 == pytest.approx(1000, rel=1e-12)
    assert pool.liquidity == 0                     # giá ở tick 0, vị thế ở tick -1
    assert pool.liquidity_at(-1) == pytest.approx(L)
    assert pool.liquidity_at(0) == 0 and pool.liquidity_at(-2) == 0
    assert pool.position_amounts(pid) == pytest.approx((0, 1000))


def test_vi_the_rong_bat_ky_va_L_active():
    pool = Pool(0.003, 1.0)
    pool.mint("victim:0", -100, 100, 1e6)
    pool.mint("victim:1", 0, 5, 2e6)
    pool.mint("bg:0", 50, 300, 4e6)
    assert pool.liquidity == pytest.approx(3e6)
    assert [pool.liquidity_at(i) for i in (-101, -100, 4, 5, 50, 100, 299, 300)] == \
        pytest.approx([0, 1e6, 3e6, 1e6, 5e6, 4e6, 4e6, 0])
    assert len(pool.positions()) == 3 and len(pool.positions("victim:1")) == 1


def test_burn_tra_lai_dung_luong_mint():
    pool = Pool(0.003, sqrt_price_at_tick(3) * 1.00001)
    pid, a0, a1 = pool.mint("victim:0", -20, 40, 5e5)
    assert a0 > 0 and a1 > 0
    b0, b1 = pool.burn(pid, 2e5)
    assert (b0, b1) == pytest.approx((a0 * 0.4, a1 * 0.4), rel=1e-12)
    assert pool.liquidity == pytest.approx(3e5)
    b0, b1 = pool.burn(pid)                        # rút nốt
    assert (b0, b1) == pytest.approx((a0 * 0.6, a1 * 0.6), rel=1e-12)
    assert pool.liquidity == 0 and pool.positions() == [] and pool.liquidity_at(3) == 0
    assert pool._ticks == {}                       # tick trống được dọn
    with pytest.raises(ValueError):
        pool.burn(pid, 1.0)


def test_kiem_tra_dau_vao():
    pool = Pool(0.003, 1.0, tick_spacing=10)
    with pytest.raises(ValueError):
        pool.mint("a:0", 10, 10, 1.0)
    with pytest.raises(ValueError):
        pool.mint("a:0", 5, 20, 1.0)
    with pytest.raises(ValueError):
        pool.mint("a:0", 0, 10, 0.0)
    with pytest.raises(KeyError):
        pool.burn(99)


def test_collect_khi_chua_co_swap():
    pool = Pool(0.003, 1.0)
    pid, *_ = pool.mint("victim:0", -5, 5, 1e6)
    assert pool.fees_owed(pid) == (0.0, 0.0)
    assert pool.collect(pid) == (0.0, 0.0)


def test_log_dung_dinh_dang():
    pool = Pool(0.003, 1.0)
    pool.t = 4
    pid, a0, a1 = pool.mint("victim:2", -5, 5, 1e6)
    pool.burn(pid, 4e5)
    pool.t = 5
    pool.collect(pid)
    df = pool.log.to_frame()
    assert list(df.columns) == COLUMNS
    assert list(df["kind"]) == ["mint", "burn", "collect"]
    assert list(df["t"]) == [4, 4, 5] and list(df["seq"]) == [0, 1, 0]
    assert set(df["role"]) == {"victim"}
    m, b, c = df.to_dict("records")
    assert m["amount0"] == pytest.approx(a0) and m["amount1"] == pytest.approx(a1)
    assert b["amount0"] == pytest.approx(-0.4 * a0) and b["liquidity"] == 4e5   # rút: âm
    assert c["amount0"] == 0 and c["fee0"] == 0
    assert m["liquidity_active_after"] == 1e6 and b["liquidity_active_after"] == pytest.approx(6e5)
    assert math.isnan(m["external_price"])

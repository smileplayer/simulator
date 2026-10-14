"""Kiểm chéo engine với bể giả `_BeGia` của vai C (cài độc lập, phí pro-rata trực tiếp) và các
tính năng phụ: tick_spacing > 1, liquidity_at sau nhiều lần qua tick, export gói."""
import random

import pytest

import engine
from engine import Pool, sqrt_price_at_tick
from scenarios.fake_log import _BeGia


@pytest.mark.parametrize("seed", range(4))
def test_trung_khop_voi_be_gia(seed):
    """Cùng chuỗi mint + swap ngẫu nhiên: giá, tick, lượng vào/ra, phí từng vị thế phải trùng."""
    rng = random.Random(seed)
    fee = 0.003
    pool, gia = Pool(fee, 1.0), _BeGia(fee, 1.0)
    ids = []                                             # (id engine, id bể giả)
    # nền rộng và dày để giá không chạm biên: _BeGia dừng khi gặp L = 0 ngay tại tick hiện tại
    # (kể cả khi vừa chạm biên trên rồi đổi chiều), còn engine đi tiếp như v3
    a = pool.mint("bg:0", -20000, 20000, 2e6)[0]
    ids.append((a, gia.mint("bg:0", -20000, 20000, 2e6)))
    for k in range(30):
        lo = rng.randint(-500, 400)
        hi = lo + rng.choice([1, 1, 2, 5, 20, 100])
        L = rng.uniform(1e4, 5e6)
        ids.append((pool.mint(f"victim:{k}", lo, hi, L)[0], gia.mint(f"victim:{k}", lo, hi, L)))
    for _ in range(200):
        down = rng.random() < 0.5
        if rng.random() < 0.3:
            lim = sqrt_price_at_tick(rng.randint(-600, 500)) * rng.uniform(1, 1.0001)
            r = pool.swap("arb:0", down, sqrt_price_limit=lim)
            gia.swap("arb:0", down, z_limit=lim)
        else:
            amt = rng.uniform(1, 2e4)
            r = pool.swap("bg:0", down, amount_in=amt)
            gia.swap("bg:0", down, amount_in=amt)
        d = gia.dong[-1]
        assert pool.sqrt_price == pytest.approx(gia.z, rel=1e-12)
        assert pool.tick == gia.tick
        assert pool.liquidity == pytest.approx(gia.L_tai(gia.tick), rel=1e-9)
        vao, ra = (d["amount0"], -d["amount1"]) if down else (d["amount1"], -d["amount0"])
        assert r.amount_in == pytest.approx(vao, rel=1e-9, abs=1e-9)
        assert r.amount_out == pytest.approx(ra, rel=1e-9, abs=1e-9)
    for pid, gid in ids:
        f0, f1 = pool.fees_owed(pid)
        p = gia.vi_the[gid]
        assert f0 == pytest.approx(p["phi0"], rel=1e-8, abs=1e-9)
        assert f1 == pytest.approx(p["phi1"], rel=1e-8, abs=1e-9)
        assert pool.position_amounts(pid) == pytest.approx(gia._luong(p, p["L"]), rel=1e-9, abs=1e-9)


def test_tick_spacing_10():
    pool = Pool(0.003, 1.0, tick_spacing=10)
    pool.mint("victim:0", -100, 100, 1e6)
    pool.mint("victim:1", -30, -10, 3e6)
    lim = sqrt_price_at_tick(-25)
    r = pool.swap("bg:0", True, sqrt_price_limit=lim)
    assert pool.tick == -25 and pool.liquidity == pytest.approx(4e6)
    z10 = sqrt_price_at_tick(-10)
    need = 1e6 * (1 / z10 - 1) + 4e6 * (1 / lim - 1 / z10)
    assert r.amount_in * 0.997 == pytest.approx(need, rel=1e-12)
    pool.swap("bg:0", False, sqrt_price_limit=sqrt_price_at_tick(5))
    assert pool.tick == 5 and pool.liquidity == pytest.approx(1e6)


def test_liquidity_at_sau_nhieu_lan_qua_tick():
    """liquidity_at chỉ phụ thuộc vị thế, không đổi sau khi giá đi tới đi lui; L_active khớp nó."""
    rng = random.Random(7)
    pool = Pool(0.003, 1.0)
    for k in range(20):
        lo = rng.randint(-200, 150)
        pool.mint(f"victim:{k}", lo, lo + rng.randint(1, 60), rng.uniform(1e4, 1e6))
    ban_do = [pool.liquidity_at(i) for i in range(-260, 260)]
    for _ in range(100):
        pool.swap("arb:0", rng.random() < 0.5,
                  sqrt_price_limit=sqrt_price_at_tick(rng.randint(-250, 250)) * 1.00001)
        assert pool.liquidity == pytest.approx(pool.liquidity_at(pool.tick), rel=1e-9, abs=1e-6)
    assert [pool.liquidity_at(i) for i in range(-260, 260)] == pytest.approx(ban_do, rel=1e-12)


def test_export_goi():
    for ten in engine.__all__:
        assert hasattr(engine, ten)

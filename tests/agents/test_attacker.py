"""Attacker trên engine thật: dựng tường, rút trước khi xả, ba điều kiện dừng của Lemma 5."""
import math

import pytest

from agents.attacker import Attacker
from agents.base import ThiTruongCoDinh
from engine.pool import Pool

F = 0.0025
TT = ThiTruongCoDinh(1.0)


def be(L_nen=1e6, rong=20_000):
    pool = Pool(F, 1.00001)                          # giá nằm trong tick 0
    pool.mint("bg:1", -rong, rong, L_nen)
    return pool


def chay(att, pool, buoc, them=None):
    for t in buoc:
        pool.t = t
        if them:
            them(t, pool)
        att.act(t, pool, TT)


def test_dung_tuong_hai_dot():
    pool = be()
    att = Attacker("attacker:0", L_A=1e8, t_m=2, kho_token0=0, c_A=0.0,
                   dung_tuong=[(2, 0.6), (5, 0.4)], t_0=100)
    chay(att, pool, range(7))
    assert att.tick_lower == 0
    assert pool.liquidity_at(0) == pytest.approx(1e6 + 1e8)
    assert [p.liquidity for p in pool.positions("attacker:0")] == pytest.approx([6e7, 4e7])


def test_rut_truoc_khi_xa_va_dung_o_z_bar():
    pool = be()
    c_A = 0.8
    att = Attacker("attacker:0", L_A=1e8, t_m=0, kho_token0=1e7, c_A=c_A, t_0=3)
    chay(att, pool, range(5))
    df = pool.log.to_frame()
    a = df[df.role == "attacker"]
    assert list(a.kind) == ["mint", "burn", "collect", "swap"]
    assert pool.positions("attacker:0") == []
    assert att.t_rut == 3 and not att.dang_xa(4)
    assert pool.sqrt_price == pytest.approx(math.sqrt(c_A / (1 - F)), rel=1e-12)   # z̄
    assert 0 < att.kho < 1e7                                                       # còn kho


def test_dung_khi_het_kho():
    pool = be()
    att = Attacker("attacker:0", L_A=1e8, t_m=0, kho_token0=5e4, c_A=0.5, t_0=1)
    chay(att, pool, range(3))
    assert att.kho == pytest.approx(0.0, abs=1e-6)
    assert pool.sqrt_price ** 2 > 0.5 / (1 - F)      # chưa chạm z̄


def test_dung_khi_het_thanh_khoan():
    pool = be(L_nen=1e5, rong=500)                  # nền chỉ tới tick −500
    att = Attacker("attacker:0", L_A=1e8, t_m=0, kho_token0=1e9, c_A=0.0, t_0=1)
    chay(att, pool, range(3))
    assert pool.tick <= -500 and att.kho > 0
    assert pool.liquidity == pytest.approx(0.0, abs=1e-6)


def test_rut_theo_nguong_victim_va_victim_om_token0():
    pool = be()
    att = Attacker("attacker:0", L_A=1e8, t_m=0, kho_token0=1e6, c_A=0.0, nguong_victim=0.5)

    def victim_vao(t, p):
        if t == 4:
            p.mint("victim:0", 0, 1, 6e7)

    chay(att, pool, range(8), them=victim_vao)
    assert att.t_rut == 4
    pos = pool.positions("victim:0")[0]
    x, y = pool.position_amounts(pos.id)
    assert x > 0 and y == pytest.approx(0.0, abs=1e-9)    # nạn nhân chỉ còn token0 sau cú xả


def test_xa_chia_nhieu_buoc():
    pool = be()
    att = Attacker("attacker:0", L_A=1e8, t_m=0, kho_token0=1e5, c_A=0.0, t_0=2, so_buoc_xa=3)
    chay(att, pool, range(7))
    df = pool.log.to_frame()
    xa = df[(df.role == "attacker") & (df.kind == "swap")]
    assert list(xa.t) == [2, 3, 4]
    assert xa.amount0.tolist() == pytest.approx([1e5 / 3] * 3)
    assert [att.dang_xa(t) for t in range(1, 6)] == [False, True, True, True, False]

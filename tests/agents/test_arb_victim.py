"""Arb, victim toàn tri (Lemma 4) và farmer chạy trên engine thật."""
import math

import pytest

from agents.arb import Arbitrageur
from agents.base import ThiTruongCoDinh
from agents.farmer import Farmer, thuong_tuyen_tinh
from agents.victim import VictimToanTri, l_v_sao
from engine.pool import Pool

F = 0.0025


def be_co_tuong(L_A, z0=1.0):
    """Bể engine thật: tường L_A trong tick [0, 1) và nền mỏng rộng để giá không kẹt."""
    pool = Pool(F, z0)
    pool.mint("attacker:0", 0, 1, L_A)
    return pool


# ---------- Lemma 4 ----------
def test_lemma4_moc_LA_toi_uu():
    Q, c_V = 1e5, 1e-6
    L_A = F * Q / (4 * c_V)                          # = 62.500
    assert l_v_sao(F, Q, L_A, c_V) == pytest.approx(L_A, rel=1e-12)


def test_lemma4_nguong_tham_gia():
    Q, c_V, L_A = 1e5, 1e-6, 1e5
    nguong_Q = c_V * L_A / F                          # tham gia ⟺ Q > c_V·L_A/f = 40
    assert l_v_sao(F, 0.99 * nguong_Q, L_A, c_V) == 0.0
    assert l_v_sao(F, 1.01 * nguong_Q, L_A, c_V) > 0.0
    # L_V* là cực đại của Π_V
    pi = lambda L: F * Q * L / (L_A + L) - c_V * L
    Ls = l_v_sao(F, Q, L_A, c_V)
    assert pi(Ls) >= max(pi(0.99 * Ls), pi(1.01 * Ls))


def test_victim_tren_engine_LV_bang_LA():
    Q, c_V = 1e5, 1e-6
    L_A = F * Q / (4 * c_V)
    pool, tt = be_co_tuong(L_A), ThiTruongCoDinh(1.0)
    vic = VictimToanTri("victim:0", V=Q, c_V=c_V)
    for t in range(5):
        vic.act(t, pool, tt)
    assert vic.L_hien_tai(pool) / L_A == pytest.approx(1.0, rel=0.01)
    assert pool.liquidity_at(0) == pytest.approx(2 * L_A, rel=0.01)
    assert len(vic.vi_the) == 1                       # đã đạt mục tiêu, không mint lặp


def test_victim_rut_bot_khi_tuong_day_len():
    Q, c_V = 1e5, 1e-6
    L_A = F * Q / (4 * c_V)
    pool, tt = be_co_tuong(L_A), ThiTruongCoDinh(1.0)
    vic = VictimToanTri("victim:0", V=Q, c_V=c_V)
    vic.act(0, pool, tt)
    pool.mint("attacker:0", 0, 1, 3 * L_A)           # tường thành 4·L_A → L_V* = √(4)·L_A·... − 4L_A = 0
    vic.act(1, pool, tt)
    assert vic.L_hien_tai(pool) == pytest.approx(0.0, abs=1e-6)


def test_victim_ngoai_khoang_thi_giu_nguyen():
    Q, c_V = 1e5, 1e-6
    pool, tt = be_co_tuong(F * Q / (4 * c_V)), ThiTruongCoDinh(1.0)
    pool.mint("bg:1", -5000, 5000, 1e4)
    vic = VictimToanTri("victim:0", V=Q, c_V=c_V)
    vic.act(0, pool, tt)
    L0 = vic.L_hien_tai(pool)
    pool.swap("attacker:0", zero_for_one=True, amount_in=1e3)   # đẩy giá ra khỏi tick 0
    assert pool.tick < 0
    n = len(pool.log.to_frame())
    vic.act(1, pool, tt)
    assert len(pool.log.to_frame()) == n and vic.L_hien_tai(pool) == L0


# ---------- Arb ----------
@pytest.mark.parametrize("p_e", [0.98, 1.0, 1.03])
def test_arb_keo_gia_ve_Pe(p_e):
    pool = Pool(F, 1.0)
    pool.mint("bg:1", -5000, 5000, 1e6)
    arb = Arbitrageur()
    arb.act(0, pool, ThiTruongCoDinh(p_e))
    assert pool.sqrt_price == pytest.approx(math.sqrt(p_e), rel=1e-12)
    n = len(pool.log.to_frame())
    arb.act(1, pool, ThiTruongCoDinh(p_e))           # đã cân bằng → không giao dịch
    assert len(pool.log.to_frame()) == n


def test_arb_tat():
    pool = Pool(F, 1.0)
    pool.mint("bg:1", -5000, 5000, 1e6)
    Arbitrageur(bat=False).act(0, pool, ThiTruongCoDinh(0.9))
    assert pool.sqrt_price == 1.0


# ---------- Farmer trên engine thật ----------
def test_farmer_engine_khop_theorem1_trong_mot_tick():
    L_A, sigma = 1e9, 0.003
    z1 = 1.00002                                     # nghiệm nằm trong tick [0,1): √P biên trên ≈ 1.00005
    p_e = z1 ** 2 * (1 - sigma) / (1 - F)            # chọn P_e để √(P_e(1−f)/(1−σ)) = z1
    v_sao = L_A / (1 - F) * (z1 - 1.0)               # ≈ 20.050 USDT
    pool = be_co_tuong(L_A)
    v, _ = Farmer("farmer:0", thuong_tuyen_tinh(sigma, 1e9), 1e9).ke_hoach(pool, p_e)
    assert v == pytest.approx(v_sao, rel=1e-7)


def test_farmer_va_arb_mot_buoc():
    L_A = 1e9
    p_e = 1.00001 ** 2
    pool, tt = be_co_tuong(L_A, z0=1.00001), ThiTruongCoDinh(p_e)
    fa = Farmer("farmer:0", thuong_tuyen_tinh(0.01, 5e3), 5e3)
    fa.act(0, pool, tt)
    assert pool.tick == 0 and pool.sqrt_price > 1.00001
    Arbitrageur().act(0, pool, tt)
    assert pool.sqrt_price == pytest.approx(1.00001, rel=1e-12)
    df = pool.log.to_frame()
    assert list(df[df.kind == "swap"].role) == ["farmer", "arb"]

"""GĐ3: lời giải giải tích victim chọn (vốn, độ rộng) dưới φ(w), khớp engine; bộ quét quet_gd3 chạy được."""
import math

import pytest

from agents.base import khoang_quanh_gia
from agents.do_rong import (
    LUOI_W, C_V_sao, PhiLuyThua, Pi_V, alpha_sao, g_w, l_tren_von, l_tren_von_xap_xi, tao_phi, ty_le_von,
    von_tren_L, w_sao_hinh_hoc,
)
from agents.victim import VictimToanTri, l_v_sao
from engine import Pool, amounts_for_liquidity, liquidity_for_amounts, sqrt_price_at_tick

Z = sqrt_price_at_tick(0) * 1.0001 ** 0.25          # giữa tick 0, như bộ chạy


def test_l_tren_von_khop_hinh_hoc_va_xap_xi():
    for w in LUOI_W:
        l = l_tren_von(w, Z, 0)
        assert abs(l / l_tren_von_xap_xi(w, Z) - 1) < 3e-3      # xấp xỉ C/(κw) sai < 0,3% tới w = 200
        lo, hi = w // 2, w - w // 2                              # dải giữa: [−⌊w/2⌋, w − ⌊w/2⌋)
        za, zb = sqrt_price_at_tick(-lo), sqrt_price_at_tick(hi)
        a0, a1 = amounts_for_liquidity(Z, za, zb, l)             # vốn 1 token1 chia đúng tỷ lệ
        assert a0 * Z * Z + a1 == pytest.approx(1.0, rel=1e-12)
        assert liquidity_for_amounts(Z, za, zb, a0, a1) == pytest.approx(l, rel=1e-9)


def test_phi_hang_la_pro_rata_va_trung_lemma4():
    assert tao_phi(None) is None and tao_phi({"alpha": 0, "w0": 50}) is None
    f, V, W, c_V = 0.0025, 72000.0, 4e8, 3.375e-7
    l1 = l_tren_von(1, Z, 0)
    C = C_V_sao(f, V, W, l1, c_V * l1)                           # c theo vốn = c_V·ℓ(1)
    assert C * l1 == pytest.approx(l_v_sao(f, V, W, c_V), rel=1e-9)


@pytest.mark.parametrize("w0", [10, 50, 200])
def test_w_sao_va_alpha_sao(w0):
    for a in (0.0, 0.5, 0.9):
        assert w_sao_hinh_hoc(tao_phi({"alpha": a, "w0": w0}), Z, tick=0) == 1
    for a in (1.01, 1.5, 2.0, 3.0):
        assert w_sao_hinh_hoc(tao_phi({"alpha": a, "w0": w0}), Z, tick=0) == w0   # nhảy thẳng 1 → w₀
    a_sao = alpha_sao(w0, Z, tick=0)
    assert 0.99 < a_sao <= 1.0                                    # cần siêu tuyến tính (α ≥ 1, hòa ở α = 1)


def test_Pi_toi_uu_tai_C_sao():
    f, V, W, c = 0.0025, 72000.0, 2e5, 6.75e-3
    g = g_w(50, PhiLuyThua(2, 50), Z, 0)
    C = C_V_sao(f, V, W, g, c)
    assert C > 0
    p = Pi_V(C, f, V, W, g, c)
    assert p > Pi_V(0.99 * C, f, V, W, g, c) and p > Pi_V(1.01 * C, f, V, W, g, c)
    assert p == pytest.approx((math.sqrt(f * V) - math.sqrt(c * W / g)) ** 2, rel=1e-9)


def test_ty_le_von_nguong():
    for k in (0.1, 0.45, 0.64, 0.95):
        assert ty_le_von(k, 1.0) == pytest.approx(1.0)
        assert ty_le_von(k, (1 / math.sqrt(k) - 1) ** 2) == pytest.approx(1.0)


def test_khoang_quanh_gia_vi_tri():
    p = Pool(0.0025, Z)
    assert khoang_quanh_gia(p, 1, "giua") == khoang_quanh_gia(p, 1) == (0, 1)
    assert khoang_quanh_gia(p, 10, "giua") == (-5, 5)
    assert khoang_quanh_gia(p, 10, "duoi") == (-9, 1)


def test_victim_theo_von_khop_giai_tich_va_phi_engine():
    """Victim toàn tri GĐ3 trên bể có φ: L mint khớp C_V*(w)·ℓ(w); phí engine chia đúng L·φ/Σ."""
    f, V, L_A = 0.0025, 72000.0, 4e8
    phi = PhiLuyThua(2.0, 10)
    pool = Pool(f, Z, fee_weight=phi)
    pid_tuong, _, _ = pool.mint("attacker:0", 0, 1, L_A)
    c_V = 0.8 * f * V / L_A
    c_von = c_V * l_tren_von(1, Z, 0)
    w = w_sao_hinh_hoc(phi, Z, tick=0)
    assert w == 10
    v = VictimToanTri("victim:0", V=V, c_V=c_V, w=w, c_von=c_von, vi_tri="giua")
    v.act(0, pool, None)
    (pos,) = pool.positions("victim:0")
    assert (pos.tick_lower, pos.tick_upper) == (-5, 5)
    W = L_A * phi(1)
    C = C_V_sao(f, V, W, g_w(w, phi, Z, 0), c_von)
    assert pos.liquidity == pytest.approx(C * l_tren_von(w, Z, 0), rel=1e-9)
    a0, a1 = amounts_for_liquidity(Z, sqrt_price_at_tick(-5), sqrt_price_at_tick(5), pos.liquidity)
    assert a0 * Z * Z + a1 == pytest.approx(C, rel=1e-9)
    # swap nhỏ trong tick: phí chia theo L·φ(w)
    for _ in range(5):
        pool.swap("farmer:0", False, amount_in=100.0)
        pool.swap("arb:0", True, sqrt_price_limit=Z)
    phi_v = pool.fees_owed(pos.id)
    phi_t = pool.fees_owed(pid_tuong)
    Xv = pos.liquidity * phi(10)
    ty_le = Xv / (Xv + W)
    tong1 = phi_v[1] + phi_t[1]
    assert phi_v[1] / tong1 == pytest.approx(ty_le, rel=1e-6)


def test_quet_gd3_khoi():
    from scenarios.quet_gd3 import LUOI_PHI, danh_sach_viec, dong_ket_qua, to_hop_gd3
    assert len(LUOI_PHI) == 16 and len(to_hop_gd3()) == 6
    assert len(danh_sach_viec(10)) == 6 * 16 * 2 * 10
    vu = to_hop_gd3()[0]
    r0 = dong_ket_qua(vu, 0.0, 0, "omniscient", 0)
    assert r0["w_victim"] == 1 and r0["lp0_w"] == 1                  # α = 0 → w* = 1
    assert 0.2 < r0["LV_chia_LA"] < 0.3                              # k = 0,64 → L_V*/L_A ≈ 0,25 (Lemma 4)
    r2 = dong_ket_qua(vu, 2.0, 50, "omniscient", 0)
    assert r2["w_victim"] == 50 and r2["lp1_w"] == 10
    assert 0.45 < r2["phan_duong_sap"] < 0.6                         # sập sâu ≫ w/2: ~nửa vốn bị quét (phần token1)
    for r in (r0, r2):
        assert not math.isnan(r["dc_excess"]) and r["von_victim"] > 0


def test_w_A_giai_tich_noi_tuong():
    """Tường vốn cố định: w_A = w_v = 1 pro-rata → u = 1; nới tường tới w₀ → u ≈ 1 (RA vô hiệu với k < 1/4);
    k ≥ 1/4 → đạt u* = 1/(4k), tỷ lệ vốn victim 1/(4k(1/√k − 1))."""
    from agents.do_rong import u_hieu_dung, w_A_toi_uu
    assert u_hieu_dung(1, 1, None, Z, 0.0, 0) == pytest.approx(1.0)
    phi = PhiLuyThua(2.0, 50)
    assert u_hieu_dung(50, 50, phi, Z, 0.0, 0) == pytest.approx(1.0, rel=5e-3)
    assert u_hieu_dung(1, 50, phi, Z, 0.0, 0) == pytest.approx(1 / 50, rel=5e-3)
    r = w_A_toi_uu(0.10, phi, 50, Z, luoi=[1, 12, 25, 50], tick=0)
    assert r["w_A"] == 50 and r["ty_le"] == pytest.approx(1.0, abs=0.01)
    r = w_A_toi_uu(0.64, phi, 50, Z, luoi=range(1, 51), tick=0)
    assert r["ty_le"] == pytest.approx(1 / (4 * 0.64 * (1 / 0.8 - 1)), rel=0.02)


def test_tuong_rong_von_co_dinh_trong_bo_chay():
    from scenarios.quet_gd3 import cau_hinh_gd3, muc_w_A, to_hop_gd3
    from scenarios.run import run_frame
    assert muc_w_A(0) == [1] and muc_w_A(10) == [1, 2, 5, 10] and muc_w_A(200) == [1, 50, 100, 200]
    vu = to_hop_gd3()[0]
    df = run_frame(cau_hinh_gd3(vu, 2.0, 50, "omniscient", w_A=25), 0)
    m = df.attrs["meta"]
    lo, hi = m["wall_range"]
    assert hi - lo == 25 and lo == m["wall_tick"]                    # dải "tren": tick giá ghim là tick dưới cùng
    assert m["L_A_eff"] == pytest.approx(m["L_A"] * l_tren_von(25, Z, 0, "tren") / l_tren_von(1, Z, 0, "tren"))
    a = df[(df.owner == "attacker:0") & df.kind.isin(["mint", "burn"])]
    assert set(a.tick_upper - a.tick_lower) == {25}
    assert a[a.kind == "burn"].liquidity.sum() == pytest.approx(a[a.kind == "mint"].liquidity.sum())   # rút cả dải
    df1 = run_frame(cau_hinh_gd3(vu, 2.0, 50, "omniscient", w_A=1), 0)
    assert df1.attrs["meta"]["L_A_eff"] == df1.attrs["meta"]["L_A"]

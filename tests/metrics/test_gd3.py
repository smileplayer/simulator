"""Test `metrics.gd3` (so cặp với pro-rata, đối chiếu giải tích, w_A tối ưu) và `plots.hinh_gd3` trên dữ liệu giả."""
import math

import numpy as np
import pandas as pd
import pytest

from metrics.gd3 import (bang_gd3, bang_gon_gd3, chon_w_A_toi_uu, chuan_bi, doi_chieu, ma_phi, ty_le_von_wA_giai_tich,
                         u_giai_tich, vung)

MUC = [(0.0, 0), (1.0, 50), (2.0, 50)]


def _bang(n_seed=4):
    """GĐ3 giả: 2 vụ (k 0,1 / 0,8), vốn victim = 1000·tỷ lệ cố định theo mức φ, dc_excess = vốn/10."""
    tl = {(0.0, 0): 1.0, (1.0, 50): 0.9, (2.0, 50): 2.0}
    dong = []
    for vu, k in (("A", 0.1), ("B", 0.8)):
        for (a, w0) in MUC:
            for vt in ("omniscient", "adaptive"):
                for s in range(n_seed):
                    von = 1000 * tl[(a, w0)] * (1 + 0.01 * s)
                    dong.append(dict(scenario_id=vu, k=k, alpha=a, w0=w0, victim_type=vt, seed=s, von_victim=von,
                                     w_victim=1 if a == 0 else w0, LV_chia_LA=0.1, phan_duong_sap=0.5,
                                     vl_lai_tien=-von / 5, vl_loss_full=np.nan if s == 0 else von / 5,
                                     dc_excess=von / 10, dc_lai_tong=1e4, do_sap=-0.3, vol_tong=1e6, vol_farmer=1e5,
                                     lp0_w=1 if a == 0 else w0, lp0_phi_tren_von=0.03, lp1_phi_tren_von=0.04,
                                     lp0_trong_dai=1.0, lp0_L_gia=1e8, lp0_truot=0.007, lp1_truot=0.007))
    return pd.DataFrame(dong)


def test_bang_gd3_ty_le_von():
    d = chuan_bi(_bang())
    assert set(d["bp"]) == {"khong", "a1_w50", "a2_w50"} and ma_phi(0, 0) == "khong"
    assert d.loc[d["seed"] == 0, "breached"].eq(0).all()
    dai = bang_gd3(d, B=50)
    gon = bang_gon_gd3(dai).set_index(["scenario_id", "victim_type", "bp"])
    assert gon.loc[("A", "omniscient", "a1_w50"), "ty_le_von"] == pytest.approx(0.9)
    assert gon.loc[("B", "adaptive", "a2_w50"), "ty_le_von"] == pytest.approx(2.0)
    h = dai[(dai["chi_so"] == "vl_loss_full")].iloc[0]
    assert h["n_loai_khong_sap"] == 1                       # seed 0 không có thiệt hại đo được → loại cặp


def test_u_giai_tich_va_vung():
    l = lambda w: 1.0 / w                                   # noqa: E731 — xấp xỉ ℓ ∝ 1/w
    # w* = w₀, B ≪ L_A: u ≈ w₀^(1−α) + w₀·B/L_A (công thức của C)
    u = u_giai_tich(1.5, 50, 50, 4e8, 2.15e5, l)
    assert u == pytest.approx(50 ** -0.5 + 50 * 2.15e5 / 4e8, rel=1e-3)
    assert u_giai_tich(0.0, 0, 1, 4e8, 2.15e5, l) == pytest.approx(1.0)
    assert vung(0.1, 0.3) == "giam" and vung(0.8, 0.3) == "tang" and vung(0.5, 1.0) == "bang"


def test_doi_chieu_khop_khi_mo_phong_dung_giai_tich():
    from agents.do_rong import PhiLuyThua, l_tren_von, ty_le_von, w_sao_hinh_hoc
    from engine import sqrt_price_at_tick
    z0 = sqrt_price_at_tick(0) * 1.0001 ** 0.25
    nen = pd.DataFrame([dict(scenario_id="A", L_A=4e8, B=2.15e5, wall_tick=0)])
    dong = []
    for a, w0 in [(1.5, 50), (3.0, 10)]:
        w = w_sao_hinh_hoc(PhiLuyThua(a, w0), z0, tick=0)
        u = u_giai_tich(a, w0, w, 4e8, 2.15e5, lambda x: l_tren_von(int(x), z0, 0))
        tl = ty_le_von(0.8, u)
        dong.append(dict(scenario_id="A", k=0.8, victim_type="omniscient", alpha=a, w0=w0, w_victim=w,
                         ty_le_von=tl, ty_le_von_lo=tl, ty_le_von_hi=tl))
    dc = doi_chieu(pd.DataFrame(dong), nen)
    assert dc["sai_so"].abs().max() < 1e-9 and dc["khop_vung"].all()


def test_chon_w_A_toi_uu():
    d = pd.DataFrame(dict(scenario_id="A", seed=0, victim_type="omniscient", alpha=[2.0] * 3 + [0.0], w0=[50] * 3 + [0],
                          w_A=[1, 12, 25, 1], dc_excess=[100.0, 300.0, 300.0, 50.0]))
    o = chon_w_A_toi_uu(d)
    assert len(o) == 2
    assert o.loc[o["alpha"] == 2.0, "w_A_toi_uu"].item() == 12      # hòa → w_A nhỏ hơn
    # hai seed: seed 0 thích w_A = 1 (nhiễu lớn), seed 1 thích 25; trung vị chọn một w_A chung, theo seed thì tách
    d2 = pd.DataFrame(dict(scenario_id="A", victim_type="omniscient", alpha=2.0, w0=50, seed=[0, 0, 1, 1],
                           w_A=[1, 25, 1, 25], dc_excess=[500.0, 200.0, 100.0, 300.0]))
    tv = chon_w_A_toi_uu(d2)
    assert len(tv) == 2 and tv["w_A_toi_uu"].nunique() == 1 and tv["w_A_toi_uu"].iloc[0] == 1   # trung vị 300 vs 250
    ts = chon_w_A_toi_uu(d2, cach="theo_seed")
    assert list(ts["w_A_toi_uu"]) == [1, 25] and ts["dc_excess"].mean() > tv["dc_excess"].mean()
    assert ty_le_von_wA_giai_tich(0.64) == pytest.approx(1.5625)
    assert ty_le_von_wA_giai_tich(0.1) == 1.0


def test_phases_doc_wall_range():
    """Tường rộng 4 tick (meta wall_range) — `phases` tự đọc, không dò theo 1 tick."""
    from metrics.phases import phases
    rows = [dict(t=0, seq=0, kind="mint", owner="attacker:0", tick_lower=10, tick_upper=14, liquidity=1e6),
            dict(t=0, seq=1, kind="mint", owner="lp:0", tick_lower=10, tick_upper=11, liquidity=5e6),
            dict(t=5, seq=2, kind="burn", owner="attacker:0", tick_lower=10, tick_upper=14, liquidity=1e6)]
    for t in range(8):
        rows.append(dict(t=t, seq=10 + t, kind="step", owner=None, tick_lower=np.nan, tick_upper=np.nan,
                         liquidity=np.nan, sqrt_price_after=1.0001 ** 6 if t < 5 else 0.8))
    df = pd.DataFrame(rows)
    df["tick_after"] = np.nan
    df["amount0"] = df["amount1"] = 0.0
    df.attrs["meta"] = dict(wall_range=[10, 14])
    ph = phases(df)
    assert (ph["wall_tick_lower"], ph["wall_tick_upper"]) == (10, 14) and ph["t_0"] == 5 and ph["t_b"] == 5


def test_ve_gd3(tmp_path):
    from plots.hinh_gd3 import ve_ban_do_vung, ve_lp, ve_theo_alpha
    gon = bang_gon_gd3(bang_gd3(chuan_bi(_bang()), B=20))
    gon = pd.concat([gon, gon.assign(w0=10), gon.assign(w0=200)])
    dc = pd.DataFrame(dict(u=[0.1, 0.5, 1.2], k=[0.1, 0.8, 0.8], ty_le_mo_phong=[0.5, 2.0, 0.0]))
    ve_ban_do_vung(dc, gon, tmp_path / "a.png")
    ve_theo_alpha(gon, tmp_path / "b.png")
    ve_lp(gon, tmp_path / "c.png")
    for f in "abc":
        assert (tmp_path / f"{f}.png").stat().st_size > 1000


def test_so_sanh_wA_va_hinh(tmp_path):
    from metrics.gd3 import so_sanh_wA
    from plots.hinh_gd3 import ve_so_sanh_wA, ve_theo_wA
    gon = bang_gon_gd3(bang_gd3(chuan_bi(_bang()), B=20))
    opt = gon.assign(w_A_toi_uu=1, ty_le_von_giai_tich_wA=[ty_le_von_wA_giai_tich(k) for k in gon["k"]])
    ss = so_sanh_wA(gon, opt)
    assert len(ss) == len(gon)
    r = ss[(ss["k"] == 0.8)].iloc[0]
    assert r["sai_so_tuong_doi_wA"] == pytest.approx(r["ty_le_von_toi_uu"] / ty_le_von_wA_giai_tich(0.8) - 1)
    ve_so_sanh_wA(ss, tmp_path / "a.png")
    tv = _bang().assign(w_A=1).groupby(["scenario_id", "k", "victim_type", "alpha", "w0", "w_A"])[
        ["von_victim", "dc_excess"]].median().reset_index()
    ve_theo_wA(tv, opt, tmp_path / "b.png", vu=("A", "B"), alpha=2.0)
    assert (tmp_path / "a.png").stat().st_size > 1000 and (tmp_path / "b.png").stat().st_size > 1000

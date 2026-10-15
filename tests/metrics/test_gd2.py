"""Test `metrics.gd2` (bảng đánh đổi GĐ2, tỷ lệ sập, Q* thực nghiệm) và `plots.hinh_gd2` (vẽ được) trên dữ liệu giả."""
import math

import numpy as np
import pandas as pd
import pytest

from metrics.gd2 import (_khoang, bang_danh_doi, bang_gon, ghep_cap, hieu_cap, q_sao_vu, them_cot,
                         tom_tat_q_sao, ty_le_sap)

MUC = {"khong": 1.0, "cap75": 0.75, "cap50": 0.5, "cap25": 0.25}


def _bang(n_vu=4, n_seed=3, bps=("khong", "cap50"), victim=("omniscient",), k=0.64):
    """Bảng tóm tắt giả: victim toàn tri theo Lemma 4 (L_V/L_A = √(r/k) − 1), loss = 100·L_V/L_A,
    excess = loss + 5, vol_tong = 1000·r. Mọi lượt sập."""
    dong = []
    for v in range(n_vu):
        for s in range(n_seed):
            for vt in victim:
                for bp in bps:
                    r = MUC[bp]
                    lv = max(0.0, math.sqrt(r / k) - 1)
                    dong.append(dict(scenario_id=f"V{v}", seed=s, victim_type=vt, bp=bp, L_A=2e8, k=k, sigma=0.01,
                                     Q=12000 * (v + 1), bg_band=0.25, attacker_inventory=25000, subsidy_form="linear",
                                     LV_chia_LA=lv, victim_loss_full=100 * lv + s, attacker_profit_excess=100 * lv + 5,
                                     attacker_farm_pnl=0.0, attacker_farm_pending=0.0, breached=True, do_sap=-0.3,
                                     vol_tong=1000 * r + v, vol_farmer=500 * r, L_mean_before=1e8, L_mean_post=5e7,
                                     subsidy_total=100 * r, subsidy_clawed=0.0))
    return pd.DataFrame(dong)


def test_them_cot_cong_farm_va_treo():
    d = pd.DataFrame(dict(attacker_profit_excess=[10.0, np.nan], attacker_farm_pnl=[3.0, np.nan],
                          attacker_farm_pending=[2.0, np.nan], breached=[True, False]))
    o = them_cot(d)
    assert o["loi_tan_cong"].iloc[0] == 13 and o["loi_tan_cong_treo"].iloc[0] == 15
    assert np.isnan(o["loi_tan_cong"].iloc[1])
    # bảng không có cột farm: farm = 0
    o2 = them_cot(pd.DataFrame(dict(attacker_profit_excess=[7.0], breached=[True])))
    assert o2["loi_tan_cong"].iloc[0] == 7 and o2["loi_tan_cong_treo"].iloc[0] == 7


def test_hieu_cap_hang_so_va_pct():
    d = them_cot(_bang())
    P = ghep_cap(d, "cap50")
    assert len(P) == 12
    r = hieu_cap(P, "vol_tong", False, "trung_vi")
    assert r["hieu"] == pytest.approx(-500) and r["hieu_lo"] == pytest.approx(-500) and r["hieu_hi"] == pytest.approx(-500)
    tb_goc = np.mean([1000 + v for v in range(4)])
    assert r["pct"] == pytest.approx(100 * -500 / tb_goc)
    # cap50 < k = 0.64 → victim không vào, loss chỉ còn phần seed; giảm thiệt hại 100% phần L_V
    r = hieu_cap(P, "LV_chia_LA", False)
    assert r["tk_bp"] == 0 and r["pct"] == pytest.approx(-100)


def test_cap_khong_sap_bi_loai_va_dem():
    d = _bang()
    d.loc[(d.bp == "cap50") & (d.seed == 0), "breached"] = False
    d.loc[(d.bp == "cap50") & (d.seed == 0), "victim_loss_full"] = np.nan
    P = ghep_cap(them_cot(d), "cap50")
    r = hieu_cap(P, "victim_loss_full", True)
    assert r["n_cap"] == 8 and r["n_loai_khong_sap"] == 4
    r = hieu_cap(P, "breached", False, "trung_binh")
    assert r["hieu"] == pytest.approx(-4 / 12) and r["n_loai_khong_sap"] == 0


def test_bang_danh_doi_va_gon():
    d = _bang(victim=("omniscient", "adaptive"))
    dai = bang_danh_doi(d, ("victim_type",), B=50)
    assert set(dai["victim_type"]) == {"omniscient", "adaptive"} and set(dai["bp"]) == {"cap50"}
    assert {"victim_loss_full", "loi_tan_cong", "vol_tong", "subsidy_total", "breached"} <= set(dai["chi_so"])
    c = dai.dropna(subset=["pct"])                      # gốc trung bình 0 (farm_pnl) → pct NaN
    assert len(c) and (c["pct_lo"] <= c["pct"] + 1e-9).all() and (c["pct"] <= c["pct_hi"] + 1e-9).all()
    g = bang_gon(dai)
    assert len(g) == 2 and "thiet_hai_victim_%" in g and g["n_loai_khong_sap"].eq(0).all()


def test_ty_le_sap():
    d = _bang()
    d.loc[d.scenario_id == "V0", "breached"] = False
    t = ty_le_sap(d, B=100).set_index("bp")
    assert t.loc["khong", "ty_le"] == pytest.approx(0.75) and t.loc["khong", "n"] == 12
    assert 0 <= t.loc["khong", "ci_lo"] <= 0.75 <= t.loc["khong", "ci_hi"] <= 1


def test_khoang():
    assert _khoang({0.25: True, 0.5: True, 0.75: False, 1.0: False})[:2] == (0.5, 0.75)
    lo, hi, chu = _khoang({0.25: False, 0.5: False, 0.75: False, 1.0: False})
    assert (lo, hi) == (0.0, 0.25) and "dưới lưới" in chu
    lo, hi, chu = _khoang({0.25: True, 0.5: True, 0.75: True, 1.0: True})
    assert lo == 1.0 and hi == math.inf and "trên lưới" in chu
    assert "không đơn điệu" in _khoang({0.25: True, 0.5: False, 0.75: True, 1.0: False})[2]


def test_q_sao_khop_lemma4():
    d = _bang(bps=tuple(MUC), k=0.64)
    q = q_sao_vu(d)
    assert len(q) == 4
    # victim vào ⇔ r > k = 0,64 → khoảng Q*_V = (0,5; 0,75], r_V nội suy = k
    assert (q["qs_V_lo"] == 0.5).all() and (q["qs_V_hi"] == 0.75).all()
    assert q["r_V"].to_numpy() == pytest.approx(0.64, rel=1e-6)
    assert q["k_trong_khoang_V"].all() and q["don_dieu_loi"].all()
    # excess = 5 > 0 ngay cả khi không victim → tiêu chí A không bao giờ an toàn
    assert (q["qs_A_lo"] == 0).all()
    t = tom_tat_q_sao(q)
    assert set(t["tieu_chi"]) == {"V", "A", "gop", "r_V"}


def test_ve_gd2(tmp_path):
    from plots.hinh_gd2 import luoi_nhiet, ve_danh_doi, ve_danh_doi_farm, ve_nhiet, ve_q_sao
    d = _bang(bps=tuple(MUC), victim=("omniscient", "adaptive"))
    dai = bang_danh_doi(d, ("victim_type",), B=20)
    ve_danh_doi(dai, tmp_path / "a.png")
    ve_danh_doi_farm(dai.assign(farm_share=0.3), tmp_path / "b.png")
    gt, so = luoi_nhiet(them_cot(d), "victim_loss_full", "omniscient")
    assert gt.shape == (1, 4) and so.to_numpy().sum() == 12
    ve_nhiet(them_cot(d), tmp_path / "c.png")
    ve_q_sao(q_sao_vu(d), tmp_path / "d.png")
    for f in "abcd":
        assert (tmp_path / f"{f}.png").stat().st_size > 1000

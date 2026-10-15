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
    assert set(t["tieu_chi"]) == {"V", "A", "gop", "r_V", "con_o_muc_thap_nhat"}


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


# ---------------------------------------------------------------- v3: dc_*, k hiệu dụng, giả định, ba vùng

def _bang_v3(**kw):
    """Như `_bang` nhưng thêm cột v3: dc_excess = 100·L_V/L_A, dc_farm_pnl = 50 (lãi farm có cả khi không victim)."""
    d = _bang(**kw)
    return d.assign(dc_excess=100 * d["LV_chia_LA"], dc_farm_pnl=50.0, dc_farm_treo=5.0, dc_lai_tong=1e4)


def test_them_cot_v3_va_chi_so():
    d = them_cot(_bang_v3())
    assert (d["loi_tang_them"] == d["dc_excess"] + 50).all() and (d["loi_tang_them_treo"] == d["loi_tang_them"] + 5).all()
    dai = bang_danh_doi(d, B=20)
    assert {"dc_excess", "loi_tang_them", "dc_lai_tong"} <= set(dai["chi_so"])
    assert "attacker_profit_excess" not in set(dai["chi_so"])
    h = dai[dai["chi_so"] == "loi_tang_them"].iloc[0]
    assert h["n_loai_khong_sap"] == 0                     # chỉ số dc_* không loại cặp không sập


def test_q_sao_v3_bo_lai_farm_va_k_hieu_dung():
    d = _bang_v3(bps=tuple(MUC), k=0.64)
    q = q_sao_vu(d)
    # tiêu chí A dùng dc_excess (= 0 khi victim rút) — lãi farm 50 không làm "không an toàn"
    assert (q["qs_A_lo"] == 0.5).all() and (q["qs_A_hi"] == 0.75).all()
    q2 = q_sao_vu(d.assign(farm_share=0.3))
    assert q2["k_hieu_dung"].to_numpy() == pytest.approx(0.64 * 0.7)


def _log_gia(ra_tick: bool) -> pd.DataFrame:
    """Log giả 4 bước Prep: tường tick [0, 1), farmer mua 1 token1/bước (trần 1/bước), giá sau lệnh ở tick 0 hoặc 3."""
    dong = [dict(t=0, kind="mint", owner="attacker:0", tick_lower=0, tick_upper=1, amount1=0.0, tick_after=np.nan)]
    for t in range(4):
        dong.append(dict(t=t, kind="swap", owner="farmer:0", tick_lower=np.nan, tick_upper=np.nan, amount1=1.0,
                         tick_after=3 if (ra_tick and t % 2) else 0))
    df = pd.DataFrame(dong)
    df.attrs["meta"] = dict(t_m=0, t_rut=4, n_farmers=1, Q_eff=24.0, subsidy_window=24)
    return df


def test_kiem_gia_dinh():
    from metrics.gd2 import kiem_gia_dinh
    r = kiem_gia_dinh(_log_gia(False))
    assert r["lap_day"] == pytest.approx(1.0) and r["ra_tick"] == 0 and r["tick_xa_nhat"] == 0
    r = kiem_gia_dinh(_log_gia(True))
    assert r["ra_tick"] == pytest.approx(0.5) and r["tick_xa_nhat"] == 3


def test_ba_vung():
    from metrics.gd2 import ba_vung
    dong = []
    for sg in (0.0025, 0.01):
        for Q in (6000, 48000):
            k = 0.75 * 24000 / Q
            lv = max(0.0, math.sqrt(1 / k) - 1) if sg > 0.0025 else 0.0
            for s in range(3):
                dong.append(dict(victim_type="omniscient", bp="khong", sigma=sg, Q=Q, k=k, seed=s, meta_fee=0.0025,
                                 vol_farmer=(10 if sg == 0.0025 else 100) * Q, LV_chia_LA=lv, dc_excess=100 * lv,
                                 dc_farm_pnl=0.0, dc_farm_treo=0.0, victim_loss_full=50 * lv, breached=True,
                                 attacker_profit_excess=0.0))
    gd = pd.DataFrame([dict(victim_type="omniscient", bp="khong", sigma=0.01, Q=48000, lap_day=1.0, ra_tick=0.3,
                            tick_xa_nhat=50)])
    b = ba_vung(pd.DataFrame(dong), gd).set_index(["sigma", "Q"])
    assert b.loc[(0.0025, 6000), "vung"] == "i_khong_KL" and b.loc[(0.0025, 6000), "vung_ly_thuyet"] == "i_khong_KL"
    assert b.loc[(0.01, 6000), "vung"] == "ii_an_toan" and b.loc[(0.01, 6000), "khop_ly_thuyet"]
    assert b.loc[(0.01, 48000), "vung"] == "iii_co_lai" and b.loc[(0.01, 48000), "vung_ly_thuyet"] == "iii_co_lai"
    assert bool(b.loc[(0.01, 48000), "vp_GD2"]) and bool(b.loc[(0.01, 48000), "ngoai_gia_dinh"])


def test_ve_v3(tmp_path):
    from metrics.gd2 import ba_vung
    from plots.hinh_gd2 import ve_ba_vung, ve_pareto
    d = _bang_v3(bps=tuple(MUC), victim=("omniscient", "adaptive"))
    dai = bang_danh_doi(d, B=20)
    ve_pareto({"a": dai, "b": dai}, tmp_path / "p.png")
    lu = d.assign(sigma=0.01, meta_fee=0.0025)
    lu = pd.concat([lu, lu.assign(sigma=0.0025, vol_farmer=1.0)])
    lu = lu[lu["bp"].isin(["khong", "cap50"])]
    ve_ba_vung(ba_vung(lu), tmp_path / "b.png")
    assert (tmp_path / "p.png").stat().st_size > 1000 and (tmp_path / "b.png").stat().st_size > 1000


def test_kiem_don_dieu():
    from metrics.gd2 import kiem_don_dieu
    d = _bang_v3(bps=tuple(MUC), k=0.64)
    gop, vu = kiem_don_dieu(d, B=50)
    assert set(gop["buoc"]) == {"cap50→cap25", "cap75→cap50", "khong→cap75"}
    assert (gop["tb_d"] <= 1e-9).all() and gop["so_vu_tang_y_nghia"].eq(0).all()
    # vụ V0: lợi tăng 100 khi hạ cap75 → cap50 ở mọi seed (có nhiễu nhỏ) → tăng có ý nghĩa
    m = (d["scenario_id"] == "V0") & (d["bp"] == "cap50")
    d.loc[m, "dc_excess"] = d.loc[(d["scenario_id"] == "V0") & (d["bp"] == "cap75"), "dc_excess"].to_numpy() + 100 \
        + np.arange(m.sum())
    gop, vu = kiem_don_dieu(d, B=200)
    h = vu[(vu["scenario_id"] == "V0") & (vu["buoc"] == "cap75→cap50")].iloc[0]
    assert h["tang_co_y_nghia"] and h["tb_d"] == pytest.approx(101)
    assert gop.set_index("buoc").loc["cap75→cap50", "so_vu_tang_y_nghia"] == 1

"""GĐ2 v3: cảnh báo rủi ro (tăng c_V, §7.3), trần động (§7.4), lợi nhuận theo địa chỉ thật, vùng k nhỏ."""
import math

import pytest

from defenses.thuong import ten_bien_phap
from defenses.tran_dong import TranDong, c_V_hieu_luc
from scenarios.hieu_chinh import LV_chia_LA
from scenarios.run import nap_config, run_frame


def cfg_nho(**sua):
    cfg = nap_config("co_so")
    cfg.update(steps=120, t_m=24, wall_schedule=[[24, 0.6], [36, 0.4]], t_0=96, victim_delay=12)
    cfg.update(sua)
    return cfg


def c_V_theo_k(cfg, k):
    """c_V để L_A = k·fV/c_V với V = n_farmers·Q (như ap_k)."""
    return k * cfg["fee"] * cfg["n_farmers"] * cfg["Q"] / cfg["L_A"]


def test_c_V_hieu_luc_va_ten():
    assert c_V_hieu_luc(2.0, None) == 2.0
    assert c_V_hieu_luc(2.0, {"name": "cap", "ty_le": 0.5}) == 2.0
    assert c_V_hieu_luc(2.0, {"name": "warn", "he_so": 4.0}) == 8.0
    assert ten_bien_phap({"name": "warn", "he_so": 2}) == "warn"
    assert ten_bien_phap({"name": "dyncap"}) == "dyncap"


def test_warn_ha_L_victim_theo_lemma4():
    """k = 0,25 → L_V*/L_A ≈ 1; cảnh báo ×2 → k_eff = 0,5 → 1/√0,5 − 1 ≈ 0,414; ×4 → k_eff = 1 → 0."""
    cfg = cfg_nho()
    cV = c_V_theo_k(cfg, 0.25)
    goc = LV_chia_LA(run_frame(cfg_nho(c_V=cV), 0))
    x2 = LV_chia_LA(run_frame(cfg_nho(c_V=cV, defense={"name": "warn", "he_so": 2.0}), 0))
    x4 = LV_chia_LA(run_frame(cfg_nho(c_V=cV, defense={"name": "warn", "he_so": 4.0}), 0))
    # L_A của Lemma 4 = mọi L khác trong tick (tường + nền) nên tỷ lệ theo L tường hơi lớn hơn lý thuyết
    assert goc == pytest.approx(1.0, rel=0.05)
    assert x2 == pytest.approx(1 / math.sqrt(0.5) - 1, rel=0.05)
    assert x4 == pytest.approx(0.0, abs=0.01)


def test_tran_dong_don_vi():
    td = TranDong(Q=1000.0, ty_le=0.25, m=3.0, N=4, H=3)
    for t in range(4):                                   # đường nền L = 10
        assert not td.quan_sat(t, 10.0)
        assert td.Q_hien_tai(t + 1) == 1000.0
    assert not td.quan_sat(4, 29.0)                      # 29 < 3·10: chưa báo
    assert td.quan_sat(5, 1000.0) and td.t_bao_dau == 5
    assert [td.Q_hien_tai(t) for t in (5, 6, 8, 9)] == [1000.0, 250.0, 250.0, 1000.0]
    for t in range(6, 20):                               # tường đứng: đường nền đóng băng → báo liên tục
        assert td.quan_sat(t, 1000.0)
    assert td.Q_hien_tai(22) == 250.0 and td.Q_hien_tai(23) == 1000.0
    with pytest.raises(ValueError):
        TranDong(Q=1.0, m=1.0)


def test_dyncap_khong_bao_gia_khi_khong_tuong_va_siet_khi_co_tuong():
    dc = {"name": "dyncap", "ty_le": 0.25, "m": 3.0, "N": 24, "H": 24}
    khong_tuong = run_frame(cfg_nho(defense=dc, wall_schedule=[[500, 1.0]]), 0)
    assert khong_tuong.attrs["meta"]["dyncap_t_bao_dau"] is None
    assert khong_tuong.attrs["meta"]["dyncap_so_buoc"] == 0
    cfg = cfg_nho(defense=dc)
    df = run_frame(cfg, 0)
    m = df.attrs["meta"]
    assert m["dyncap_t_bao_dau"] == cfg["t_m"]
    # báo động từ t_m + 1 tới H bước sau lần đọc cuối còn tường (bước t_rut − 1)
    assert m["dyncap_so_buoc"] == m["t_rut"] - 1 - cfg["t_m"] + dc["H"]
    W, Q = cfg["subsidy_window"], cfg["Q"]
    mua = df[(df.kind == "swap") & (df.role == "farmer") & (df.t > cfg["t_m"] + W) & (df.t < m["t_rut"])]
    theo_cua_so = mua.groupby([mua.owner, mua.t // W]).amount1.sum()
    assert len(theo_cua_so) and theo_cua_so.max() <= 0.25 * Q * (1 + 1e-6)
    # victim toàn tri thấy V = n·Q_dyn: co_so k = 0,75 → k_eff = 3 → không vào
    assert LV_chia_LA(df) == pytest.approx(0.0, abs=1e-9)


def test_loi_nhuan_dia_chi_khop_B_va_co_ca_khi_khong_sap():
    from metrics.phases import phases
    from metrics.pnl import attacker_profit
    from scenarios.quet_gd2 import loi_nhuan_dia_chi
    cfg = nap_config("co_so")
    cfg["dump_steps"] = 1                                # cửa sổ [t_0, t_b] của B gồm trọn cú xả
    df = run_frame(cfg, 0)
    r = loi_nhuan_dia_chi(df)
    ph = phases(df)
    ap = attacker_profit(df, ph).loc["attacker:0"]
    assert r["dc_paper"] == pytest.approx(ap["paper"], rel=1e-9)
    assert r["dc_ban_thang"] == pytest.approx(ap["ban_thang"], rel=1e-6)
    assert r["dc_lai_tong"] == pytest.approx(ap["full"], rel=1e-6)
    assert r["dc_loi_them"] == pytest.approx(r["dc_lai_tan_cong"] - r["dc_lai_ban_thang"])
    # kho rất nhỏ: giá không sập ≥ 10% nhưng vẫn có số theo địa chỉ thật
    cfg["attacker_inventory"] = 500
    df2 = run_frame(cfg, 0)
    r2 = loi_nhuan_dia_chi(df2)
    assert all(math.isfinite(r2[k]) for k in ("dc_lai_tan_cong", "dc_excess", "dc_ban_thang", "dc_lai_tong"))
    assert r2["dc_x_xa"] == pytest.approx(500, rel=1e-9)


def test_phat_lai_khong_victim_excess_bang_0_co_victim_duong():
    """Phát lại log không tường/không victim: không victim → bể phát lại trùng bể thật → excess = 0;
    có victim (co_so, xả 2 bước) → excess > 0."""
    from scenarios.quet_gd2 import loi_nhuan_dia_chi
    cfg = nap_config("co_so")
    cfg["n_victims"] = 0
    r0 = loi_nhuan_dia_chi(run_frame(cfg, 0))
    assert r0["dc_paper"] > 1000 and r0["dc_phat_lai_hut"] == 0
    assert abs(r0["dc_excess"]) < 1e-6 * r0["dc_paper"]
    r1 = loi_nhuan_dia_chi(run_frame(nap_config("co_so"), 0))
    assert r1["dc_excess"] > 1.0 and r1["dc_ban_thang"] < r1["dc_paper"]


def test_loi_nhuan_dia_chi_khong_tuong_la_nan():
    from scenarios.quet_gd2 import loi_nhuan_dia_chi
    df = run_frame(cfg_nho(wall_schedule=[[500, 1.0]]), 0)
    r = loi_nhuan_dia_chi(df)
    assert math.isnan(r["dc_excess"]) and r["dc_x_xa"] == 0.0


def test_to_hop_k_nho_va_danh_sach_viec():
    from scenarios.quet_gd2 import (BIEN_PHAP, BIEN_PHAP_KNHO, K_NHO, LOAI_VICTIM, danh_sach_viec,
                                    to_hop_k_nho)
    ds = to_hop_k_nho()
    assert len(ds) == 30 and all(v["id"].startswith("KN_") for v in ds)
    assert sorted({v["k"] for v in ds}) == K_NHO
    assert sum(v["k"] == 0.10 for v in ds[:27]) == 9                     # L27 cân bằng
    assert len(danh_sach_viec("k_nho", 10)) == 30 * len(BIEN_PHAP_KNHO) * len(LOAI_VICTIM) * 10
    assert len(danh_sach_viec("chinh", 10)) == 30 * len(BIEN_PHAP) * len(LOAI_VICTIM) * 10
    assert {"warn15", "warn20", "warn40", "dyncap", "claw72"} <= set(BIEN_PHAP_KNHO)


@pytest.mark.parametrize("bp,fs", [("cap50", 0.3), ("dyncap", 0.0)])
def test_phat_lai_toi_uu_lai_farmer_khong_victim_van_bang_0(bp, fs):
    """Farmer trong pha xả được tối ưu lại trên bể phát lại; không victim → trùng đúng lệnh thật → excess = 0."""
    from scenarios.quet_gd2 import BIEN_PHAP, loi_nhuan_dia_chi
    cfg = nap_config("co_so")
    cfg.update(n_victims=0, attacker_farm_share=fs, defense=BIEN_PHAP[bp])
    r = loi_nhuan_dia_chi(run_frame(cfg, 0))
    assert abs(r["dc_excess"]) < 1e-6 * r["dc_paper"]


def test_phat_lai_L27_25_khong_phu_thuoc_luong_farm_that():
    """Vụ L27_25 (victim thích nghi): trước đây phát lại nguyên lượng farm thật trong pha xả (victim đỡ giá → farmer
    mua nhiều) làm phản thực ở `khong` cao hơn `cap75` ~1.700 → excess không đơn điệu theo trần. Nay phản thực
    tối ưu lại farmer nên hai bp cho cùng ban_thang (nền + kho như nhau) và excess(khong) ≥ excess(cap75)."""
    import json
    from scenarios.batch import FILE_TO_HOP, cau_hinh
    from scenarios.quet_gd2 import BIEN_PHAP, loi_nhuan_dia_chi
    vu = next(v for v in json.loads(FILE_TO_HOP.read_text(encoding="utf-8")) if v["id"] == "L27_25")
    kq = {}
    for bp in ("khong", "cap75"):
        cfg = cau_hinh(vu)
        cfg.update(defense=BIEN_PHAP[bp], victim_type="adaptive")
        kq[bp] = loi_nhuan_dia_chi(run_frame(cfg, 0))
    assert kq["khong"]["dc_ban_thang"] == pytest.approx(kq["cap75"]["dc_ban_thang"], rel=1e-3)
    assert kq["khong"]["dc_excess"] >= kq["cap75"]["dc_excess"]

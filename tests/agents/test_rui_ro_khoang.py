"""Nạn nhân tính rủi ro theo khoảng (kiểm độ bền RQ3, 30/10): thiệt hại sập theo khoảng, chi phí hiệu dụng, chọn khoảng."""
import pytest

from agents.do_rong import (
    DO_SAP_PRIOR, VI_TRI, PhiLuyThua, c_hieu_dung, chon_khoang_rui_ro, chon_w, h_rui_ro, l_tren_von, mat_khi_sap,
)
from engine import sqrt_price_at_tick

Z0 = sqrt_price_at_tick(0) * 1.0001 ** 0.25
F, V, W = 0.0025, 72_000.0, 4e8


@pytest.fixture(scope="module")
def C():
    """c_V_von của kịch bản cơ sở, tính như scenarios.quet_gd3.cau_hinh_gd3."""
    from scenarios.run import nap_config
    return nap_config("co_so")["c_V"] * l_tren_von(1, Z0, 0)


def test_c_hieu_dung_bang_c_o_mot_tick_tren():
    assert c_hieu_dung(0.002, 0.7, 1, Z0, 0, "tren") == pytest.approx(0.002)


def test_lam_0_khong_doi_chi_phi():
    for w in (1, 10, 200):
        for d in VI_TRI:
            assert c_hieu_dung(0.002, 0.0, w, Z0, 0, d) == pytest.approx(0.002)


def test_mat_khi_sap_trong_0_1_va_tang_theo_delta():
    for w in (1, 50, 2000):
        for d in VI_TRI:
            m = [mat_khi_sap(w, Z0, 0, d, x) for x in (0.1, 0.2, 0.5)]
            assert all(0.0 <= v <= 1.0 for v in m) and m[0] <= m[1] <= m[2]


def test_h_rui_ro_la_trung_binh_tren_prior():
    h = h_rui_ro(50, Z0, 0, "giua")
    assert h == pytest.approx(sum(mat_khi_sap(50, Z0, 0, "giua", x) for x in DO_SAP_PRIOR) / len(DO_SAP_PRIOR))


def test_lam_0_chon_giong_chon_w_cu(C):
    phi = PhiLuyThua(2.0, 50)
    r = chon_khoang_rui_ro(F, V, W, C, 0.0, phi, Z0, 0, vi_tri=("giua",))
    assert r["w"] == chon_w(F, V, W, C, phi, Z0, tick=0, vi_tri="giua")["w"] and r["vi_tri"] == "giua"
    assert r["c_eff"] == pytest.approx(C)


def test_khong_vao_o_dau_ca_tra_w_argmax_g(C):
    r = chon_khoang_rui_ro(F, 1e-9, W, C, 0.5, None, Z0, 0)
    assert r["Pi"] == 0.0 and r["w"] == 1


def test_lam_ngoai_khoang_bao_loi(C):
    with pytest.raises(ValueError):
        chon_khoang_rui_ro(F, V, W, C, 1.5, None, Z0, 0)
    with pytest.raises(ValueError):
        chon_khoang_rui_ro(F, V, W, C, 0.5, None, Z0, 0, prior=())


@pytest.fixture(scope="module")
def cfg_gd3():
    from scenarios.quet_gd3 import cau_hinh_gd3, to_hop_gd3
    vu = {v["id"]: v for v in to_hop_gd3()}["L27_16"]
    cfg = cau_hinh_gd3(vu, 2.0, 50, "omniscient")
    cfg.update(steps=120, t_0=96)
    return cfg


def test_lam_0_log_trung_nan_nhan_cu(cfg_gd3):
    from scenarios.run import run_frame
    goc = run_frame(cfg_gd3, 0)
    moi = run_frame({**cfg_gd3, "victim_rui_ro": {"lam": 0.0}}, 0)
    import pandas as pd
    pd.testing.assert_frame_equal(goc.drop(columns="seq"), moi.drop(columns="seq"))
    assert moi.attrs["meta"]["victim_vi_tri_chon"] == "giua"


def test_meta_ghi_lua_chon_rui_ro(cfg_gd3):
    import json
    from scenarios.run import run_frame
    m = run_frame({**cfg_gd3, "victim_rui_ro": {"lam": 0.5}}, 0).attrs["meta"]
    assert m["victim_vi_tri_chon"] in VI_TRI and m["victim_c_eff"] > 0
    json.dumps(m, default=lambda o: o.tolist())


def test_canh_bao_nhan_len_c_eff(cfg_gd3):
    from scenarios.run import run_frame
    a = run_frame({**cfg_gd3, "victim_rui_ro": {"lam": 0.5}}, 0).attrs["meta"]["victim_c_eff"]
    b = run_frame({**cfg_gd3, "victim_rui_ro": {"lam": 0.5}, "defense": {"name": "warn", "he_so": 2.0}},
                  0).attrs["meta"]["victim_c_eff"]
    assert b == pytest.approx(2.0 * a)


def test_danh_sach_viec_rui_ro_du_3600_luot():
    from scenarios.quet_gd3 import LAM_RR, LUOI_PHI_RR, danh_sach_viec
    viec = danh_sach_viec(10, rui_ro=True)
    assert len(viec) == 6 * len(LUOI_PHI_RR) * len(LAM_RR) * 2 * 10 == 3600
    assert len(danh_sach_viec(10, nhanh=True, rui_ro=True)) == 2 * len(LAM_RR) * 2


def test_dong_ket_qua_rui_ro_co_cot_moi():
    from scenarios.quet_gd3 import dong_ket_qua, to_hop_gd3
    vu = to_hop_gd3()[0]
    r = dong_ket_qua(vu, 2.0, 50, "omniscient", 0, lam=0.5)
    assert r["lam"] == 0.5 and r["vi_tri_victim"] in VI_TRI and r["c_eff"] > 0


def test_co_dinh_vi_tri_bang_khoa_vi_tri(cfg_gd3):
    from scenarios.run import run_frame
    m = run_frame({**cfg_gd3, "victim_rui_ro": {"lam": 0.5, "vi_tri": ["giua"]}}, 0).attrs["meta"]
    assert m["victim_vi_tri_chon"] == "giua"


def test_quet_rui_ro_co_dinh_giua():
    from scenarios.quet_gd3 import cau_hinh_gd3, to_hop_gd3
    cfg = cau_hinh_gd3(to_hop_gd3()[0], 2.0, 50, "omniscient", lam=1.0)
    assert cfg["victim_rui_ro"] == {"lam": 1.0, "vi_tri": ["giua"]}

"""Test `scenarios.quet_vu_that`: hồ sơ nền → vị thế, kho xả, và nền `bg_vi_the` trong `scenarios.run`."""
import math
from types import SimpleNamespace

import pytest

from scenarios.batch import cau_hinh_bien_the
from scenarios.quet_vu_that import cau_hinh_vu, kho_xa, vi_the_nen
from scenarios.run import run_frame

MEP = [0, 10, 100, 887272]


def test_vi_the_nen_phia_xa_nam_duoi_tick_0():
    vt = vi_the_nen(MEP, [1e-3, 2e-3, 0.0], [3e-3, 0.0, 4e-3], L_A=1000.0)
    assert [-10, 0, 1.0] in vt and [-100, -10, 2.0] in vt and [0, 10, 3.0] in vt
    assert all(L > 0 and lo < hi for lo, hi, L in vt) and len(vt) == 4


def test_kho_xa_bang_cong_thuc_mot_doan():
    vt = [[-10000, 0, 50.0]]
    sap = -0.2
    dich = math.log(0.8) / math.log(1.0001)
    can = 50.0 * (1.0001 ** (-dich / 2) - 1) + 1000.0 * (1 / math.sqrt(0.25) - 1) * (1 - 1.0001 ** -0.5)
    assert kho_xa(sap, 0.25, vt, L_A=1000.0) == pytest.approx(can, rel=1e-9)


def test_kich_ban_vu_sap_dung_muc_that():
    r = SimpleNamespace(vu_id="thu", k=0.5, sap_400=-0.3, gio_tuong=30.0)
    nen = dict(mep=MEP, nen_xa=[5e-4, 5e-4, 1e-5], nen_kia=[5e-4, 5e-4, 1e-5])
    vu = cau_hinh_vu(r, nen)
    assert vu["t_0"] - vu["t_m"] == 30 and vu["c_A_ty_le"] == pytest.approx(0.7, rel=1e-3)
    df = run_frame(cau_hinh_bien_the(vu, "f001"), 0)
    m = df.attrs["meta"]
    P = df[df.kind == "step"].set_index("t").sqrt_price_after ** 2
    assert P.loc[m["t_rut"]] / P.loc[m["t_rut"] - 1] - 1 == pytest.approx(-0.3, abs=0.01)
    assert set(df[df.kind == "mint"].owner.str.split(":").str[0]) >= {"bg", "attacker", "victim"}


def test_buoc_con_1_giong_mac_dinh_va_buoc_min_cho_nhieu_khoi_luong_hon():
    from scenarios.hieu_chinh import LV_chia_LA
    from scenarios.run import nap_config
    c = nap_config("co_so")
    goc, mot = run_frame(c, 0), run_frame(dict(c, buoc_con=1), 0)
    assert len(goc) == len(mot) and (goc.sqrt_price_after.dropna().to_numpy() == mot.sqrt_price_after.dropna().to_numpy()).all()
    m = 8                                                  # Q × 8 và c_V × 8 giữ k; 8 vòng mỗi giờ
    min_ = run_frame(dict(c, buoc_con=m, Q=c["Q"] * m, c_V=c["c_V"] * m), 0)
    vol = lambda d: d[(d.kind == "swap") & (d.role == "farmer")].amount1.clip(lower=0).sum()
    assert vol(min_) > 0.8 * m * vol(goc)                  # chở được gần đủ khối lượng gấp 8
    assert LV_chia_LA(min_) == pytest.approx(LV_chia_LA(goc), rel=1e-6)
    tho = run_frame(dict(c, Q=c["Q"] * m, c_V=c["c_V"] * m), 0)       # cùng Q lớn nhưng một lệnh mỗi giờ: không chở nổi
    assert vol(tho) < 0.8 * vol(min_)


def test_cau_hinh_vu_min_dat_Q_va_so_vong():
    r = SimpleNamespace(vu_id="thu", k=0.5, sap_400=-0.3, gio_tuong=30.0, farm_24h=0.01)
    nen = dict(mep=MEP, nen_xa=[5e-4, 5e-4, 1e-5], nen_kia=[5e-4, 5e-4, 1e-5])
    vu = cau_hinh_vu(r, nen, min_=True)
    assert vu["Q"] == pytest.approx(0.01 * 4e8 / 3) and vu["buoc_con"] == math.ceil(vu["Q"] / 24 / (0.6e-5 * 4e8))
    assert "buoc_con" not in cau_hinh_vu(r, nen)
    lon = cau_hinh_vu(SimpleNamespace(vu_id="thu", k=0.5, sap_400=-0.3, gio_tuong=30.0, farm_24h=5.0), nen, min_=True)
    assert lon["buoc_con"] == 300 and lon["farm_phu"] < 1

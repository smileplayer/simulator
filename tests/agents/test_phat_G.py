"""Cải tiến G (22/10) ở cấp kịch bản: phạt rút sớm, hai cách né của kẻ tấn công."""
import pytest

from metrics.pnl import phat_rut_som, victim_fee_balances
from scenarios.quet_gd2 import BIEN_PHAP_PHAT, dong_ket_qua
from scenarios.run import nap_config, run_frame


def _chay(defense=None, **doi):
    cfg = nap_config("co_so")
    cfg.update(victim_type="omniscient", defense=defense, **doi)
    return run_frame(cfg, 0)


def _phi_nan_nhan(df):
    return victim_fee_balances(df, {o for o in df.owner.unique() if str(o).startswith("victim:")}, 1.0)["accrued"]


@pytest.fixture(scope="module")
def ba_log():
    return (_chay(), _chay({"name": "phat", "cua_so": 168}),
            _chay({"name": "phat", "cua_so": 168}, so_lat_rut=10))


def test_khong_bien_phap_khong_co_donate(ba_log):
    goc, _, _ = ba_log
    assert phat_rut_som(goc) == dict(phat_tong=0.0, phat_attacker=0.0, phat_mat=0.0)


def test_phat_trich_tuong_va_nan_nhan_nhan_them(ba_log):
    goc, phat, _ = ba_log
    p = phat_rut_som(phat)
    assert p["phat_attacker"] > 0 and p["phat_mat"] == 0
    assert _phi_nan_nhan(phat) > _phi_nan_nhan(goc)
    # trước khi rút tường hai log trùng nhau (biện pháp chỉ tác động lúc burn)
    t_rut = int(phat[(phat.owner == "attacker:0") & (phat.kind == "burn")].t.min())
    a = goc[goc.t < t_rut].drop(columns="seq").reset_index(drop=True)
    b = phat[phat.t < t_rut].drop(columns="seq").reset_index(drop=True)
    assert a.equals(b)


def test_rut_theo_lat_lam_nan_nhan_nhan_it_hon(ba_log):
    goc, phat, lat = ba_log
    them_mot_lan = _phi_nan_nhan(phat) - _phi_nan_nhan(goc)
    them_theo_lat = _phi_nan_nhan(lat) - _phi_nan_nhan(goc)
    assert 0 <= them_theo_lat < them_mot_lan


def test_giu_du_cua_so_thi_khong_bi_phat():
    vu = {"id": "co_so_test", "k": 0.75}
    r = dong_ket_qua(vu, "phat168_giu168", "omniscient", 0, bang=BIEN_PHAP_PHAT)
    assert r["t_0"] == 72 + 168 and r["steps"] == r["t_0"] + 72
    assert r["phat_attacker"] == 0.0

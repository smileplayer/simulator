"""Cải tiến F (22/10): đổi độ dày tường L_A nhưng giữ c_V vật lý của nạn nhân (k đổi theo)."""
import pytest

from scenarios.quet_gd2 import BIEN_PHAP_F, dong_ket_qua


def test_doi_LA_giu_c_V():
    vu = {"id": "co_so_test", "k": 0.75}
    r1 = dong_ket_qua(dict(vu, _m_LA=1.0), "khong", "omniscient", 0, bang=BIEN_PHAP_F)
    r2 = dong_ket_qua(dict(vu, _m_LA=2.0), "khong", "omniscient", 0, bang=BIEN_PHAP_F)
    assert r2["L_A"] == pytest.approx(2 * r1["L_A"])
    assert r2["c_V"] == pytest.approx(r1["c_V"])
    assert r1["k_thuc"] == pytest.approx(0.75) and r2["k_thuc"] == pytest.approx(1.5)
    assert r2["LV_chia_LA"] < 1e-9                 # k > 1: nạn nhân toàn tri không vào

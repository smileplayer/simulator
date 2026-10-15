"""Test `metrics.pnl` khi giá không sập (mốc thay thế / NaN có kiểm soát) và victim dải rộng phủ tick tường (GĐ3)."""
import math

import pytest

from metrics.phases import phases
from metrics.pnl import identify_roles, moc_thay_the, victim_loss


@pytest.fixture(scope="module")
def df_rong():
    """Một lượt GĐ3: vụ k nhỏ KN_L27_10, φ = min(1, w/50), victim toàn tri tự chọn w* = 50 (có sập)."""
    from scenarios.quet_gd3 import cau_hinh_gd3, to_hop_gd3
    from scenarios.run import run_frame
    vu = {v["id"]: v for v in to_hop_gd3()}["KN_L27_10"]
    return run_frame(cau_hinh_gd3(vu, 1.0, 50, "omniscient"), 0)


@pytest.fixture(scope="module")
def df_khong_sap():
    """Lượt không sập ≥ 10%: L27_22 (độ sập nông), pro-rata, victim thích nghi, seed 0 (do_sap ≈ −6%)."""
    from scenarios.quet_gd3 import cau_hinh_gd3, to_hop_gd3
    from scenarios.run import run_frame
    vu = {v["id"]: v for v in to_hop_gd3()}["L27_22"]
    return run_frame(cau_hinh_gd3(vu, 0.0, 0, "adaptive"), 0)


def test_victim_dai_rong(df_rong):
    ph = phases(df_rong)
    assert ph["t_b"] is not None
    assert identify_roles(df_rong, ph)["victims"] == set()          # bài gốc: chỉ đúng tick tường → bỏ sót
    vai = identify_roles(df_rong, ph, w_max=200)
    assert vai["victims"] == {"victim:0"}                            # không gộp LP nền dải rộng (bg:*)
    assert "attacker:0" in vai["attackers"]
    vl = victim_loss(df_rong, ph, w_max=200)
    assert "victim:0" in vl.index and vl.loc["TOTAL", "loss_full"] > 0


def test_khong_sap(df_khong_sap):
    ph = phases(df_khong_sap)
    assert ph["t_b"] is None and ph["t_0"] is not None
    with pytest.raises(ValueError):
        victim_loss(df_khong_sap, ph)                                # mặc định giữ hành vi cũ
    vl = victim_loss(df_khong_sap, ph, khong_sap="nan")
    assert list(vl.index) == ["TOTAL"] and math.isnan(vl.loc["TOTAL", "loss_full"])
    assert vl.loc["TOTAL", "moc"] == "khong_sap"
    t = moc_thay_the(df_khong_sap, ph)
    assert t == min(ph["t_0"] + ph["W"], int(df_khong_sap["t"].max()))
    vl = victim_loss(df_khong_sap, ph, khong_sap="moc_thay_the")
    assert (vl["moc"] == "thay_the").all() and "victim:0" in vl.index
    assert math.isfinite(vl.loc["TOTAL", "E_full"]) and vl.loc["TOTAL", "loss_full"] >= 0
    vai = identify_roles(df_khong_sap, ph, khong_sap="moc_thay_the")
    assert "victim:0" in vai["victims"]

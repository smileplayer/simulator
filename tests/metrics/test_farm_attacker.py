"""Kẻ tấn công cũng farm (CH-6), trợ cấp còn treo (CH-2), lợi nhuận tăng thêm so với bán thẳng (CH-1)."""
import numpy as np
import pytest

from metrics.indicators import subsidy_cost
from metrics.phases import phases
from metrics.pnl import attacker_profit, ban_thang, farm_pnl, identify_roles
from metrics.report import summarize
from scenarios.run import nap_config, run_frame


def _chay(**kw):
    cfg = nap_config("co_so")
    cfg.update(kw)
    return run_frame(cfg, 0)


@pytest.fixture(scope="module")
def df6():
    return _chay(attacker_farm_share=0.6)


def test_vai_khong_lan_khi_attacker_farm(df6):
    ph = phases(df6)
    r = identify_roles(df6, ph)
    assert r["attackers"] == {"attacker:0"} and r["main_attacker"] == "attacker:0"
    assert not any(o.startswith("farmer") for o in r["pressure_traders"])     # farmer chỉ mua
    assert "attacker:0" not in r["victims"]
    mua = df6[(df6["owner"] == "attacker:0") & (df6["kind"] == "swap") & (df6["amount1"] > 0)]
    assert len(mua) > 50                                                      # có lệnh farm thật


def test_loi_nhuan_tach_farm(df6):
    ph = phases(df6)
    a = attacker_profit(df6, ph).loc["attacker:0"]
    sw = df6[(df6["owner"] == "attacker:0") & (df6["kind"] == "swap") & (df6["t"] >= ph["t_0"])
             & (df6["t"] <= ph["t_b"])]
    ban = sw[sw["amount0"] > 0]
    assert a["paper"] == pytest.approx(-ban["amount1"].sum())                # lệnh mua farm không vào paper
    assert a["x_dump"] == pytest.approx(ban["amount0"].sum())
    fm = farm_pnl(df6, "attacker:0")
    mua = df6[(df6["owner"] == "attacker:0") & (df6["kind"] == "swap") & (df6["amount1"] > 0)]
    assert fm["farm_volume"] == pytest.approx(mua["amount1"].sum())
    assert 0 < fm["farm_cost"] < 0.01 * fm["farm_volume"]                    # phí + trượt giá, không phải cả vốn
    assert a["farm_pnl"] == pytest.approx(a["farm_subsidy"] - a["farm_cost"])
    assert a["full"] == pytest.approx(a["net_cash1"] + a["delta_token0"] * a["alpha_cost"] + a["farm_pnl"])
    # phần tấn công không bị lệnh farm làm méo: |net_cash1| cỡ paper, không phải cỡ khối lượng farm
    assert abs(a["net_cash1"]) < 2 * a["paper"]
    sc = subsidy_cost(df6)
    assert a["farm_subsidy"] == pytest.approx(sc["by_owner"]["attacker:0"])
    assert sc["to_attacker"] == pytest.approx(a["farm_subsidy"])
    assert sc["to_farmers"] == pytest.approx(sc["total"] - sc["to_attacker"]) and sc["to_farmers"] > 0


def test_excess_bang_0_khi_khong_co_victim():
    for s in (0.0, 0.6):
        df = _chay(n_victims=0, attacker_farm_share=s)
        a = attacker_profit(df, phases(df)).loc["TOTAL"]
        assert a["paper"] > 5000
        assert a["excess"] == pytest.approx(0.0, abs=1e-6 * a["paper"])       # không victim → tấn công = bán thẳng


def test_excess_duong_khi_co_victim():
    df = _chay()
    a = attacker_profit(df, phases(df)).loc["TOTAL"]
    assert 0 < a["excess"] < a["paper"]
    assert a["ban_thang"] == pytest.approx(a["paper"] - a["excess"])


def test_ban_thang_luong_nho_theo_gia():
    df = _chay()
    ph = phases(df)
    bt = ban_thang(df, ph, 1.0)
    assert bt["out"] == pytest.approx(bt["P_truoc"] * (1 - 0.0025), rel=1e-4)
    assert bt["x_sold"] == pytest.approx(1.0) and bt["L_nen"] > 0
    bt2 = ban_thang(df, ph, 1e9, alpha_cost=0.5)                              # kho khổng lồ → dừng ở z̄
    assert bt2["x_left"] > 0 and bt2["value"] == pytest.approx(bt2["out"] + 0.5 * bt2["x_left"])


def test_tro_cap_cong_khoan_treo():
    df = _chay(defense={"name": "delay", "D": 168, "don_vi": "token0"})
    sc = subsidy_cost(df)
    m = df.attrs["meta"]
    assert m["subsidy_pending"] > 0
    assert sc["pending"] == pytest.approx(m["subsidy_pending"])
    assert sc["total"] == pytest.approx(sc["paid"] + sc["pending"])
    assert sc["paid"] == pytest.approx(df.loc[df["kind"] == "subsidy", "amount1"].sum())
    r = summarize(df)
    assert r["subsidy_total"] == pytest.approx(sc["total"]) and r["subsidy_pending"] > 0


def test_tro_cap_clawback_bao_rieng():
    df = _chay(attacker_farm_share=0.6, defense={"name": "delay", "D": 72, "clawback": 0.10})
    sc = subsidy_cost(df)
    m = df.attrs["meta"]
    assert sc["clawed"] == pytest.approx(m["subsidy_clawed"]) and sc["clawed"] > 0
    assert sc["total"] == pytest.approx(sc["paid"] + sc["pending"])           # phần đã hủy không cộng
    assert sc["pending_attacker"] == pytest.approx(m["subsidy_pending_attacker"])


def test_tro_cap_meta_thieu():
    df = _chay()
    df.attrs["meta"] = {}
    sc = subsidy_cost(df)
    assert sc["pending"] == 0 and sc["clawed"] == 0 and sc["total"] == pytest.approx(sc["paid"])
    assert np.isfinite(summarize(df)["attacker_profit_excess"])

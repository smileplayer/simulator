import math

import pytest

from metrics.indicators import pool_liquidity, subsidy_cost
from metrics.phases import phases
from metrics.pnl import attacker_profit
from metrics.report import derived, summarize, summarize_many
from scenarios.fake_log import make_fake_log


@pytest.fixture(scope="module")
def dfs():
    return [make_fake_log(s) for s in (0, 1, 2)]


def test_derived_dinh_nghia(dfs):
    df = dfs[0]
    ph = phases(df)
    d = derived(df, ph)
    S = subsidy_cost(df)["total"]
    pl = pool_liquidity(df, ph)
    ap = attacker_profit(df, ph)
    assert d["eff_L"] == pytest.approx(pl["mean_post"] / S)
    assert d["eff_gain"] == pytest.approx((pl["mean_post"] - pl["mean_before"]) / S)
    assert d["leak_paper"] == pytest.approx(ap.loc["TOTAL", "paper"] / S)
    assert d["leak_full"] == pytest.approx(ap.loc["TOTAL", "full"] / S)


def test_summarize_mot_vu(dfs):
    r = summarize(dfs[0])
    assert r["meta_seed"] == 0 and r["breached"]
    assert r["t_m"] == 48 and r["t_0"] == 144
    assert r["lift_Before"] == pytest.approx(1.0) and r["lift_Attack"] > 5
    assert r["n_victims"] == 3 and r["victim_loss_full"] > 0
    assert r["attacker_profit_paper"] > 0 and r["main_attacker"] == "attacker:0"
    assert all(not isinstance(v, (dict, list, set)) for v in r.values())    # phẳng, vào được DataFrame


def test_summarize_many(dfs):
    bang = summarize_many(dfs)
    assert len(bang) == 3 and list(bang["meta_seed"]) == [0, 1, 2]
    assert bang["victim_loss_full"].notna().all()


def test_vu_khong_sap(dfs):
    df = dfs[0]
    r = summarize(df[df["t"] < df.attrs["meta"]["t_0"]])
    assert not r["breached"] and math.isnan(r["victim_loss_full"]) and math.isnan(r["leak_paper"])

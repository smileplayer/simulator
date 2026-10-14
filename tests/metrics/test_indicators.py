import numpy as np
import pytest

from metrics.indicators import phase_stats, pool_liquidity, price_changes, subsidy_cost, vwap
from metrics.phases import phases
from scenarios.fake_log import make_fake_log


@pytest.fixture(scope="module", params=[0, 1, 2])
def df(request):
    return make_fake_log(request.param)


@pytest.fixture(scope="module")
def ph(df):
    return phases(df)


@pytest.fixture(scope="module")
def bang(df, ph):
    return phase_stats(df, ph)


def test_subsidy_cost(df):
    sc = subsidy_cost(df)
    assert sc["total"] == pytest.approx(df.loc[df["kind"] == "subsidy", "amount1"].sum())
    assert sc["by_owner"].sum() == pytest.approx(sc["total"])
    assert sc["total"] > 0 and set(sc["by_owner"].index) <= {f"farmer:{k}" for k in range(10)}


def test_lift_dinh_nghia(bang, ph):
    assert list(bang.index) == ["Before", "Prep", "Attack", "Post"]
    assert bang.loc["Before", "lift"] == pytest.approx(1.0)
    assert np.allclose(bang["lift"], bang["vol_mean"] / bang.loc["Before", "vol_mean"])
    assert np.allclose(bang["lift_trade"], bang["vol_trade_mean"] / bang.loc["Before", "vol_trade_mean"])
    assert (bang["vol_mean"] >= bang["vol_trade_mean"]).all()          # vol_total gồm cả arb
    assert bang["hours"].tolist() == [24, 96, ph["t_b"] - ph["t_0"] + 1, 24]


def test_dau_hieu_log_gia(bang):
    assert bang.loc["Attack", "lift"] > 5
    assert bang.loc["Prep", "RV"] < bang.loc["Attack", "RV"]
    assert bang.loc["Prep", "RV"] < bang.loc["Post", "RV"]
    assert bang.loc["Post", "lift_trade"] < 1                           # dòng lệnh không-arb dưới nền


def test_price_changes(df, ph):
    pc = price_changes(df, ph)
    assert abs(pc["before_price_change"]) < 0.02                         # tường ghim giá
    assert pc["attack_price_change"] < -0.05


def test_vwap(df):
    P = vwap(df)
    assert len(P) == df.attrs["meta"]["steps"] and (P > 0).all()


def test_pool_liquidity(df, ph):
    pl = pool_liquidity(df, ph)
    L_A = df.attrs["meta"]["L_A"]
    assert pl["L_max"] == pytest.approx(ph["peak_liquidity"])
    assert pl["drop_at_tb"] == pytest.approx(L_A / pl["L_max"])           # chỉ tường bị rút, victim còn kẹt
    assert pl["mean_before"] > 0 and pl["ratio_post_before"] == pytest.approx(
        pl["mean_post"] / pl["mean_before"])

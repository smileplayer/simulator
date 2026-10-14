import numpy as np
import pytest

from metrics.phases import phases
from metrics.pnl import attacker_profit, identify_roles, victim_loss
from scenarios.fake_log import make_fake_log


@pytest.fixture(scope="module", params=[0, 1, 2])
def df(request):
    return make_fake_log(request.param)


@pytest.fixture(scope="module")
def ph(df):
    return phases(df)


def test_vai_suy_ra_khop_nhan(df, ph):
    r = identify_roles(df, ph)
    nhan_victim = set(df.loc[df["role"] == "victim", "owner"])
    assert r["victims"] == nhan_victim                         # cả 3 victim còn kẹt tại t_b
    assert r["attackers"] == {"attacker:0"} and r["main_attacker"] == "attacker:0"
    assert "attacker:0" not in r["victims"]
    assert r["wall_share"].sum() == pytest.approx(1.0)


def test_victim_loss_cong_thuc(df, ph):
    vl = victim_loss(df, ph)
    v = vl.drop(index="TOTAL")
    assert np.allclose(v["E_full"] - v["E_nonalpha"], v["p_alpha"] * v["x_dep"])
    assert (v["loss_full"] > 0).all()                           # giá rơi khỏi tick → kẹt toàn alpha
    assert np.allclose(v["y_back"], 0, atol=1e-6)               # không ai rút trước t_b
    assert (v["loss_full"] >= v["loss_nonalpha"]).all()
    for c in ("loss_full", "loss_nonalpha", "x_dep", "y_dep"):
        assert vl.loc["TOTAL", c] == pytest.approx(v[c].sum())


def test_victim_loss_t_oot(df, ph):
    assert len(victim_loss(df, ph, end="t_oot").drop(index="TOTAL")) == 3


def test_attacker_profit(df, ph):
    ap = attacker_profit(df, ph)
    a = ap.loc["attacker:0"]
    sw = df[(df["owner"] == "attacker:0") & (df["kind"] == "swap")
            & (df["t"] >= ph["t_0"]) & (df["t"] <= ph["t_b"])]
    assert a["paper"] == pytest.approx(-sw["amount1"].sum()) and a["paper"] > 0
    assert a["delta_token0"] < 0                                 # đã xả alpha từ kho
    ap0 = attacker_profit(df, ph, alpha_cost=0.0)
    assert ap0.loc["attacker:0", "full"] == pytest.approx(a["net_cash1"])
    assert ap.loc["TOTAL", "paper"] == pytest.approx(a["paper"])


def test_khong_sap_bao_loi(df):
    ph = phases(df[df["t"] < df.attrs["meta"]["t_0"]])
    with pytest.raises(ValueError):
        victim_loss(df, ph)

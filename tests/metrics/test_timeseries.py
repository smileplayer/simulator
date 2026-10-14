import numpy as np
import pytest

from metrics.timeseries import build_timeseries, step_frame, swap_volume
from scenarios.fake_log import make_fake_log


@pytest.fixture(scope="module")
def df():
    return make_fake_log(0)


@pytest.fixture(scope="module")
def ts(df):
    return build_timeseries(df)


def test_moi_buoc_mot_dong(df, ts):
    steps = df.attrs["meta"]["steps"]
    assert len(ts) == steps
    assert list(ts.index) == list(range(steps))


def test_gia_khop_dong_step(df):
    sf = step_frame(df)
    s = df[df["kind"] == "step"].set_index("t")
    assert np.allclose(sf["price"], s["sqrt_price_after"] ** 2)
    assert np.allclose(sf["L_active"], s["liquidity_active_after"])


def test_tong_khoi_luong_bao_toan(df, ts):
    sw = df[df["kind"] == "swap"]
    assert ts["vol_total"].sum() == pytest.approx(sw["amount1"].abs().sum())
    assert ts["n_swap"].sum() == len(sw)
    vol = swap_volume(df)
    assert {"vol_bg", "vol_farmer", "vol_attacker", "vol_arb", "vol_victim"} <= set(vol.columns)


def test_khoi_luong_dung_pha(df, ts):
    m = df.attrs["meta"]
    t_m, t_0 = m["t_m"], m["t_0"]
    assert (ts.loc[: t_m - 1, "vol_farmer"] == 0).all()        # farmer chỉ có trong Prep
    assert (ts.loc[t_m:t_0 - 1, "vol_farmer"] > 0).all()
    assert ts.loc[t_0, "vol_attacker"] > 0                       # xả tại t_0
    assert ts.loc[t_0, "vol_trade"] > 5 * ts.loc[: t_m - 1, "vol_trade"].mean()


def test_gia_sut_va_bien_dong(df, ts):
    t_0 = df.attrs["meta"]["t_0"]
    assert ts.loc[t_0 + 1, "price"] < 0.8 * ts.loc[t_0 - 1, "price"]
    assert np.isnan(ts["ret"].iloc[0])
    assert ts.loc[t_0, "abs_ret"] > 10 * ts["abs_ret"].loc[: t_0 - 1].median()

import pandas as pd
import pytest

from metrics.phases import label_phases, phases, wall_liquidity
from metrics.timeseries import build_timeseries
from scenarios.fake_log import make_fake_log


@pytest.fixture(scope="module", params=[0, 1, 2])
def df(request):
    return make_fake_log(request.param)


@pytest.fixture(scope="module")
def ph(df):
    return phases(df)


def test_do_dung_tuong(df, ph):
    m = df.attrs["meta"]
    assert ph["wall_tick_lower"] == m["wall_tick"]
    assert ph["wall_tick_upper"] == m["wall_tick"] + 1


def test_moc_khop_kich_ban(df, ph):
    m = df.attrs["meta"]
    assert ph["t_m"] == m["t_m"]
    assert ph["t_0"] == m["t_0"] == ph["t_0_burn"]
    assert ph["t_peak"] == max(m["victim_mint_t"])            # victim mint cuối = đỉnh tường
    assert ph["t_m"] <= ph["t_50"] <= ph["t_peak"] < ph["t_0"]


def test_sap_gia(df, ph):
    t_0 = df.attrs["meta"]["t_0"]
    assert ph["breached"]
    assert t_0 <= ph["t_oot"] <= ph["t_b"] <= t_0 + 2            # sập trong 2 giờ như bài gốc
    assert ph["delta_extract"] <= 2 and ph["delta_build"] == 96


def test_cua_so_va_nhan(df, ph):
    w = ph["windows"]
    assert w["Before"] == (24, 47) and w["Prep"] == (48, 143)
    assert w["Attack"] == (144, ph["t_b"]) and w["Post"] == (ph["t_b"] + 1, ph["t_b"] + 24)
    nhan = label_phases(build_timeseries(df), ph)
    dem = nhan.value_counts()
    assert dem["Before"] == 24 and dem["Prep"] == 96 and dem["Post"] == 24
    assert pd.isna(nhan.loc[0])


def test_khong_sap_thi_khong_co_t_b(df):
    t_0 = df.attrs["meta"]["t_0"]
    truoc = df[df["t"] < t_0 + 0].copy()                       # cắt log trước khi rút tường
    ph = phases(truoc)
    assert ph["t_0"] is None and not ph["breached"]
    assert ph["windows"]["Attack"] is None


def test_wall_liquidity_cong_don(df):
    wl = wall_liquidity(df)
    lo = df.attrs["meta"]["wall_tick"]
    e = wl[wl["tick_lower"] == lo]
    assert e["L_wall"].iloc[-1] == pytest.approx(e["dL"].sum())
    assert (e["L_wall"] >= -1e-6).all()

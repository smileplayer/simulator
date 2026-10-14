"""Kiểm tra log giả đúng định dạng INTERFACE mục 4 và đúng trình tự tấn công."""
import math

import numpy as np
import pytest

from scenarios.fake_log import COT, make_fake_log


@pytest.fixture(scope="module")
def df():
    return make_fake_log(0)


def test_dung_cot(df):
    assert list(df.columns) == COT
    assert set(df["kind"]) == {"mint", "burn", "collect", "swap", "subsidy", "step"}
    assert (df["role"] == df["owner"].str.split(":").str[0]).all()


def test_seq_va_dong_step(df):
    m = df.attrs["meta"]
    for t, g in df.groupby("t"):
        assert list(g["seq"]) == list(range(len(g)))
        assert g["kind"].iloc[-1] == "step"
    assert (df["kind"] == "step").sum() == m["steps"]
    assert df.loc[df.kind != "step", "external_price"].isna().all()
    assert df.loc[df.kind == "step", "external_price"].notna().all()


def test_quy_uoc_dau(df):
    assert (df[["fee0", "fee1"]] >= 0).all().all()
    mint, burn = df[df.kind == "mint"], df[df.kind == "burn"]
    assert (mint[["amount0", "amount1"]] >= 0).all().all()
    assert (burn[["amount0", "amount1"]] <= 0).all().all()
    sw = df[df.kind == "swap"]
    # mỗi swap: đúng một token vào (dương), token kia ra (≤ 0)
    assert ((sw.amount0 > 0) ^ (sw.amount1 > 0)).all()
    assert ((sw.amount0 > 0) == (sw.fee0 > 0)).all()
    sub = df[df.kind == "subsidy"]
    assert (sub.amount1 > 0).all() and (sub.role == "farmer").all()


def test_trinh_tu_tan_cong(df):
    m = df.attrs["meta"]
    att_mint = df[(df.kind == "mint") & (df.role == "attacker")]
    vic_mint = df[(df.kind == "mint") & (df.role == "victim")]
    att_burn = df[(df.kind == "burn") & (df.role == "attacker")]
    xa = df[(df.kind == "swap") & (df.role == "attacker")]
    assert att_mint.t.min() == m["t_m"]
    assert att_mint.t.min() < vic_mint.t.min() <= vic_mint.t.max() < att_burn.t.min() == m["t_0"]
    assert att_burn.index.max() < xa.index.min()
    # vị thế tường và victim là một tick, cùng tick
    for g in (att_mint, vic_mint):
        assert ((g.tick_upper - g.tick_lower) == 1).all()
        assert (g.tick_lower == m["wall_tick"]).all()


def test_gia_sap_sau_khi_rut(df):
    m = df.attrs["meta"]
    st = df[df.kind == "step"].set_index("t")
    p_truoc = st.loc[m["t_0"] - 1, "sqrt_price_after"] ** 2
    p_sau = st.loc[m["t_0"] + 1, "sqrt_price_after"] ** 2
    assert p_sau / p_truoc < 0.9                       # giảm > 10% trong 2 giờ
    assert st.loc[m["t_0"] + 1, "tick_after"] < m["wall_tick"] - 1000   # xuyên > 1000 tick


def test_nhat_quan_gia_tick(df):
    gia = df["sqrt_price_after"] ** 2
    tick_tinh = np.floor(np.log(gia) / math.log(1.0001) + 1e-6).astype(int)
    assert (np.abs(tick_tinh - df["tick_after"]) <= 1).all()


def test_tai_lap_theo_seed():
    a, b, c = make_fake_log(3), make_fake_log(3), make_fake_log(4)
    assert a.equals(b)
    assert not a.equals(c)

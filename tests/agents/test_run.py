"""Bộ chạy kịch bản trên engine thật: đúng thứ tự, đúng định dạng log, khớp mốc Lemma 4."""
import math

import pytest

from scenarios.run import nap_config, run, run_frame


def cfg_nho(**sua):
    cfg = nap_config("co_so")
    cfg.update(steps=120, t_m=24, wall_schedule=[[24, 0.6], [36, 0.4]], t_0=96, victim_delay=12,
               bg_band=0.2)                          # dải nền rộng để chắc chắn sập > 10% trong test
    cfg.update(sua)
    return cfg


@pytest.fixture(scope="module")
def df():
    return run_frame(cfg_nho(), 0)


def test_mot_dong_step_moi_buoc_va_seq(df):
    st = df[df.kind == "step"]
    assert list(st.t) == list(range(120))
    for _, g in df.groupby("t"):
        assert list(g.seq) == list(range(len(g))) and g.kind.iloc[-1] == "step"


def test_tro_cap_cuoi_cua_so_va_khong_vuot_Q(df):
    cfg = cfg_nho()
    sub = df[df.kind == "subsidy"]
    assert set((sub.t + 1) % cfg["subsidy_window"]) == {0}
    assert (sub.amount1 <= cfg["sigma"] * cfg["Q"] * (1 + 1e-9)).all()
    mua = df[(df.kind == "swap") & (df.role == "farmer")]
    theo_cua_so = mua.groupby([mua.owner, mua.t // cfg["subsidy_window"]]).amount1.sum()
    assert (theo_cua_so <= cfg["Q"] * (1 + 1e-9)).all()


def _L_victim(df):
    """L ròng của nạn nhân ngay trước khi rút tường (mint − burn, victim có thể rút bớt khi tường dày lên)."""
    v = df[(df.role == "victim") & (df.t < df.attrs["meta"]["t_rut"])]
    return v[v.kind == "mint"].liquidity.sum() - v[v.kind == "burn"].liquidity.sum()


def test_victim_khop_lemma4_cau_hinh_co_so(df):
    cfg = cfg_nho()
    L_khac = cfg["L_A"] + cfg["L_bg"]
    k = cfg["c_V"] * L_khac / (cfg["fee"] * cfg["n_farmers"] * cfg["Q"])
    assert 0.64 <= k < 1                                   # miền tường chiếm ≥ 80%
    assert _L_victim(df) / L_khac == pytest.approx(1 / math.sqrt(k) - 1, rel=0.02)


def test_victim_moc_LA_bang_fV_chia_4cV():
    cfg = cfg_nho(steps=60, t_0=50)
    L_khac = cfg["L_A"] + cfg["L_bg"]
    cfg["c_V"] = cfg["fee"] * cfg["n_farmers"] * cfg["Q"] / (4 * L_khac)
    assert _L_victim(run_frame(cfg, 0)) / L_khac == pytest.approx(1.0, rel=0.02)


def test_nen_huu_han_trong_dai():
    from scenarios.run import dai_nen
    ds = dai_nen(1.0, 0.10, 5)
    assert len(ds) == 5 and all(a[0] > b[0] and a[1] < b[1] for a, b in zip(ds, ds[1:]))
    assert ds[-1][0] == pytest.approx(-1054, abs=1) and ds[-1][1] == pytest.approx(954, abs=1)


def test_tan_cong_rut_roi_xa_arb_nghi(df):
    m = df.attrs["meta"]
    assert m["t_rut"] == 96 and m["c_A"] == 0.5
    a = df[df.role == "attacker"]
    assert a[a.kind == "burn"].index.max() < a[a.kind == "swap"].index.min()
    xa = set(a[a.kind == "swap"].t)
    assert xa == {96, 97}
    assert df[(df.role == "arb") & df.t.isin(xa)].empty
    st = df[df.kind == "step"].set_index("t")
    assert st.loc[97, "sqrt_price_after"] ** 2 < 0.9 * st.loc[95, "sqrt_price_after"] ** 2


def test_collect_cuoi_kich_ban(df):
    c = df[(df.kind == "collect") & (df.t == 119)]
    assert {"victim", "bg"} <= set(c.role)
    assert (c.fee0 + c.fee1 > 0).all()


def test_tai_lap_theo_seed_va_dang_log():
    cfg = cfg_nho(steps=60, t_0=50)
    assert run(cfg, 1).to_frame().equals(run(cfg, 1).to_frame())
    assert not run(cfg, 1).to_frame().equals(run(cfg, 2).to_frame())
    df_log = run_frame(cfg_nho(steps=60, t_0=50, subsidy_form="log"), 0)
    assert (df_log[df_log.kind == "subsidy"].amount1 > 0).all()


def test_chua_cai_thi_bao_loi():
    with pytest.raises(NotImplementedError):
        run(cfg_nho(defense={"name": "chua_co"}), 0)
    with pytest.raises(ValueError):
        run(cfg_nho(victim_type="khong_co"), 0)


def test_duoi_nen_toan_dai():
    from engine import MAX_TICK, MIN_TICK
    df = run_frame(cfg_nho(steps=30, t_0=28, bg_tail=0.075), 0)
    duoi = df[(df.kind == "mint") & (df.tick_lower == MIN_TICK) & (df.tick_upper == MAX_TICK)]
    assert len(duoi) == 1 and duoi.liquidity.iloc[0] == pytest.approx(0.075 * cfg_nho()["L_bg"])

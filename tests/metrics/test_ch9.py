"""CH-9 (20/10): thanh khoản không tính vị thế nạn nhân/kẻ tấn công, phí và lợi nhuận ròng của nạn nhân."""
import pytest

from metrics.indicators import liquidity_excluding, pool_liquidity
from metrics.phases import phases
from metrics.pnl import victim_fees
from metrics.report import summarize
from scenarios.fake_log import make_fake_log
from scenarios.run import nap_config, run_frame


@pytest.fixture(scope="module")
def log_that():
    cfg = nap_config("co_so")
    cfg.update(victim_type="omniscient")
    return run_frame(cfg, 0)


@pytest.mark.parametrize("seed", [0, 1])
def test_khong_bo_vai_trung_L_active(seed):
    df = make_fake_log(seed)
    ph = phases(df)
    pl, lk = pool_liquidity(df, ph), liquidity_excluding(df, ph, bo_vai=())
    assert lk["mean_before"] == pytest.approx(pl["mean_before"], rel=1e-9)
    assert lk["mean_post"] == pytest.approx(pl["mean_post"], rel=1e-9)


def test_khong_bo_vai_trung_L_active_log_that(log_that):
    ph = phases(log_that)
    pl, lk = pool_liquidity(log_that, ph), liquidity_excluding(log_that, ph, bo_vai=())
    assert lk["mean_before"] == pytest.approx(pl["mean_before"], rel=1e-9)
    assert lk["mean_post"] == pytest.approx(pl["mean_post"], rel=1e-9)


def test_bo_vai_khong_lon_hon(log_that):
    ph = phases(log_that)
    pl, lk = pool_liquidity(log_that, ph), liquidity_excluding(log_that, ph)
    assert lk["mean_post"] <= pl["mean_post"] * (1 + 1e-12)
    assert lk["mean_before"] == pytest.approx(pl["mean_before"], rel=1e-9)   # trước khi có tường và nạn nhân


def test_phi_va_loi_rong_nan_nhan(log_that):
    r = summarize(log_that)
    assert r["victim_fees"] > 0                       # bộ chạy collect ở bước cuối
    assert r["victim_net"] == pytest.approx(r["victim_fees"] - r["victim_E_full"])
    phi = victim_fees(log_that, {o for o in log_that.owner.unique() if str(o).startswith("victim:")}, 1.0)
    assert phi > 0

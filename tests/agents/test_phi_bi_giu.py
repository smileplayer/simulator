"""Cải tiến G, phí bị giữ khi collect sớm (26/10): ảnh chụp phí cuối kịch bản và các cột quyền nhận / tiền đã thu."""
import pandas as pd
import pytest

from metrics.pnl import victim_fee_balances
from metrics.report import summarize
from scenarios.run import nap_config, run_frame


@pytest.fixture(scope="module")
def log_phat():
    cfg = nap_config("co_so")
    cfg["defense"] = {"name": "phat", "cua_so": 168}
    return run_frame(cfg, 0)


def test_anh_chup_phi_va_cot_bao_cao(log_phat):
    nan_nhan = {o for o in log_phat.owner.unique() if str(o).startswith("victim:")}
    b = victim_fee_balances(log_phat, nan_nhan, 1.0)
    assert b["locked"] > 0 and b["outstanding"] >= b["locked"]
    assert b["accrued"] == pytest.approx(b["cash"] + b["outstanding"])
    r = summarize(log_phat)
    assert r["victim_fees_locked"] > 0
    assert r["victim_net"] == pytest.approx(r["victim_net_cash"] + r["victim_fees_outstanding"])


def test_tat_phat_thi_khong_co_phi_treo():
    df = run_frame(nap_config("co_so"), 0)
    assert df.attrs["meta"]["fee_balances"] == []
    r = summarize(df)
    assert r["victim_fees_outstanding"] == 0.0 and r["victim_net"] == r["victim_net_cash"]


def test_bang_G_co_cot_tien_mat_va_phi_bi_giu():
    from metrics.chay_GF import bang_G
    from scenarios.quet_gd2 import BIEN_PHAP_PHAT, dong_ket_qua
    dong = [dong_ket_qua({"id": "co_so_test", "k": .75}, bp, vt, 0, bang=BIEN_PHAP_PHAT)
            for bp in BIEN_PHAP_PHAT for vt in ("omniscient", "adaptive")]
    bang = bang_G(pd.DataFrame(dong), B=20)
    assert {"victim_net", "victim_net_cash", "victim_fees_locked", "victim_fees_outstanding"} <= set(bang.chi_so)

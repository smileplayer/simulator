"""Bộ phát hiện tường (phát lại luật trần động trên log): khớp bản chạy thật, mốc và độ sớm đúng, cách né từng nấc."""
import math

import pandas as pd
import pytest

from metrics.phat_hien import cac_buoc_bao, chuoi_L, danh_gia, ne_tu_tu
from scenarios.run import nap_config, run_frame


@pytest.fixture(scope="module")
def co_so():
    return run_frame(nap_config("co_so"), 0)


def test_bao_dung_buoc_dung_tuong(co_so):
    r = danh_gia(co_so, m=3.0, N=24)
    m = co_so.attrs["meta"]
    assert r["t_bao"] == m["t_m"] and r["bat_truoc_rut"]
    assert r["som_hon_rut"] == m["t_rut"] - m["t_m"]
    assert r["som_hon_victim"] == r["t_victim"] - m["t_m"] > 0
    assert r["bao_nham"] == 0 and r["gio_nen"] == m["t_m"] - 24
    assert r["ty_so"] > 100


def test_khop_tran_dong_chay_that():
    """Bước báo đầu khi phát lại trên log không biện pháp = `dyncap_t_bao_dau` của lượt bật trần động."""
    cfg = nap_config("co_so")
    goc = run_frame(cfg, 0)
    bat = run_frame(dict(cfg, defense={"name": "dyncap"}), 0)
    assert cac_buoc_bao(chuoi_L(goc))[0] == bat.attrs["meta"]["dyncap_t_bao_dau"]


def test_nguong_qua_cao_thi_khong_bat(co_so):
    r = danh_gia(co_so, m=1e6)
    assert not r["bat_truoc_rut"] and r["t_bao"] is None and math.isnan(r["som_hon_rut"])


def test_chuoi_phang_khong_bao():
    assert cac_buoc_bao(pd.Series([5.0] * 100)) == []


def test_ne_tu_tu():
    assert ne_tu_tu(1.0) == 0
    assert ne_tu_tu(2.9, m=3.0) == 1                     # dưới ngưỡng: một bước là xong
    # mỗi nấc nhân gần m, và đường nền (trung vị N bước) cần N/2 + 1 bước mới theo kịp
    n = ne_tu_tu(1000.0, m=3.0, N=24)
    so_nac = math.ceil(math.log(1000.0) / math.log(3.0 * 0.999))
    assert (so_nac - 1) * 12 < n <= so_nac * 13
    assert ne_tu_tu(1000.0, m=10.0) < n < ne_tu_tu(1000.0, m=1.5)

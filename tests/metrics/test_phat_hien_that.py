"""Bộ phát hiện tường trên log thật: đổi swap sang chuỗi L theo giờ và đánh giá luật (không cần mạng)."""
import numpy as np
import pandas as pd

from metrics.phat_hien_that import bao_nham_sach, chuoi_L_that, danh_gia_that, gio_block

MOC = pd.DataFrame({"block": [0, 1000], "ts": [0, 1000 * 3600]})            # 1 block = 1 giờ


def _swap(block, L, tick=0):
    return dict(block=block, tx_index=0, log_index=0, liquidity_active=L, tick=tick)


def test_gio_block_noi_suy_va_ngoai_suy():
    assert list(gio_block([0, 500, 1000, 1200], MOC)) == [0.0, 500.0, 1000.0, 1200.0]


def test_chuoi_L_that_lay_swap_cuoi_gio_va_giu_gio_trong():
    sw = pd.DataFrame([_swap(10, 5.0), _swap(10, 7.0, 3) | {"log_index": 1}, _swap(13, 9.0, 4)])
    ch = chuoi_L_that(sw, MOC)
    assert list(ch.index) == [0, 1, 2, 3]
    assert list(ch["L"]) == [7.0, 7.0, 7.0, 9.0] and list(ch["tick"]) == [3, 3, 3, 4] and list(ch["n"]) == [2, 0, 0, 1]


def test_danh_gia_that_bat_tuong_va_dem_bao_truoc():
    L = pd.Series([1.0] * 30 + [10.0] * 20 + [1.0] * 5)                      # tường gấp 10 nền ở giờ 30–49
    r = danh_gia_that(L, h_m=30, h_b=50, m=3.0, N=24)
    assert r["bat"] and r["t_bao"] == 30 and r["som_hon_rut"] == 20.0 and r["bao_truoc_tm"] == 0
    assert r["gio_nen"] == 6 and abs(r["ty_so_tm"] - 10.0) < 1e-9
    assert not danh_gia_that(L, 30, 50, m=20.0)["bat"]


def test_danh_gia_that_tuong_doi_cho_khong_bao():
    """Nền đã có tường khác (L lớn hơn): tường mới không vượt ngưỡng, luật im lặng."""
    L = pd.Series([13.0] * 30 + [3.0] * 20)
    r = danh_gia_that(L, 30, 50, m=1.5)
    assert not r["bat"] and r["ty_so_tm"] < 1 and np.isnan(r["som_hon_rut"])


def test_bao_nham_sach_dem_gio_va_dot():
    L = pd.Series([1.0] * 30 + [5.0, 5.0] + [1.0] * 10 + [5.0] + [1.0] * 5)   # hai đợt vọt: 2 giờ và 1 giờ
    r = bao_nham_sach(L, m=3.0, N=24)
    assert (r["so_gio_bao"], r["so_dot"], r["gio_xet"]) == (3, 2, len(L) - 24)
    assert bao_nham_sach(pd.Series([1.0] * 60), m=1.5)["so_gio_bao"] == 0

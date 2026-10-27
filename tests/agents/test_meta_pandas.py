"""Meta của log sau các phép pandas (Hoàng báo 27/10): so sánh, chép sâu, ghép, groupby không lỗi ở pandas 2.x."""
import pickle
from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from scenarios.run import MangMeta, nap_config, run_frame


@pytest.fixture(scope="module")
def frame():
    cfg = nap_config("co_so")
    cfg.update(steps=120, t_m=24, wall_schedule=[[24, 0.6], [36, 0.4]], t_0=96, victim_delay=12, bg_band=0.2)
    return run_frame(cfg, 0)


def test_meta_so_sanh_sau_deepcopy(frame):
    assert frame.attrs == deepcopy(frame.attrs)


def test_ghep_hai_phan_log_giu_meta(frame):
    trai, phai = frame.iloc[:10].copy(), frame.iloc[10:20].copy()
    kq = pd.concat([trai, phai])
    pd.testing.assert_frame_equal(kq, frame.iloc[:20])
    assert kq.attrs == frame.attrs


def test_groupby_theo_khoa_ngoai_bao_toan_khoi_luong(frame):
    mua = frame[(frame.role == "farmer") & (frame.kind == "swap")]
    assert len(mua) > 0
    nhom = mua.groupby([mua.owner, mua.t // 24]).amount1.sum()
    assert nhom.sum() == pytest.approx(mua.amount1.sum())


def test_mang_meta_doc_nhu_mang():
    m = MangMeta([1.0, 2.5, float("nan")])
    assert len(m) == 3 and m[1] == 2.5 and float(np.asarray(m)[0]) == 1.0
    assert m == MangMeta([1.0, 2.5, float("nan")]) and m != MangMeta([1.0, 2.5, 0.0])
    assert deepcopy(m) is m and pickle.loads(pickle.dumps(m)) == m
    assert m.tolist()[:2] == [1.0, 2.5]
    with pytest.raises(ValueError):
        np.asarray(m)[0] = 9.0

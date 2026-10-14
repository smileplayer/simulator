"""Bộ tổ hợp RQ1: L27 trực giao, 30 vụ, k → c_V đúng miền, chạy/ghi/đọc lại được."""
import itertools
from collections import Counter

import pytest

from scenarios.batch import MUC, cau_hinh, chay, doc_ket_qua, mang_L27, to_hop_rq1


def test_L27_truc_giao_do_manh_2():
    L = mang_L27()
    assert len(L) == 27 and len(set(L)) == 27
    for i, j in itertools.combinations(range(6), 2):
        assert set(Counter((r[i], r[j]) for r in L).values()) == {3}


def test_30_vu_va_c_V_theo_k():
    ds = to_hop_rq1()
    assert len(ds) == 30 and len({d["id"] for d in ds}) == 30
    for d in ds:
        cfg = cau_hinh(d)
        assert 0.64 <= cfg["k"] < 1
        V = cfg["n_farmers"] * cfg["Q"]
        assert cfg["c_V"] == pytest.approx(cfg["k"] * cfg["fee"] * V / cfg["L_A"])
        assert cfg["bg_band"] in MUC["bg_band"] and cfg["scenario_id"] == d["id"]


def test_chay_bo_qua_phan_da_xong(tmp_path):
    chay(1, tmp_path, nhanh=True)
    files = sorted(tmp_path.glob("*.csv"))
    assert len(files) == 3
    mtime = [f.stat().st_mtime_ns for f in files]
    chay(1, tmp_path, nhanh=True)                    # chạy lại: không ghi đè
    assert [f.stat().st_mtime_ns for f in files] == mtime
    dfs = doc_ket_qua(tmp_path)
    assert len(dfs) == 3 and all("c_V" in d.attrs["meta"] for d in dfs)

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


def test_bien_the_do_nhay():
    """Biến thể "goc" tái lập đúng config RQ1; f001 giữ k và σ/f; vol đặt vol_prep = vol_post = vol_pre."""
    import json
    from scenarios.batch import FILE_TO_HOP, cau_hinh, cau_hinh_bien_the
    for vu in json.loads(FILE_TO_HOP.read_text(encoding="utf-8"))[:3]:
        a, g = cau_hinh(vu), cau_hinh_bien_the(vu, "goc")
        assert g.pop("bien_the") == "goc" and a == g
        f = cau_hinh_bien_the(vu, "f001")
        assert f["fee"] == 0.0001 and abs(f["sigma"] / f["fee"] - a["sigma"] / a["fee"]) < 1e-9
        assert f["k"] == a["k"] and abs(f["c_V"] / a["c_V"] - 0.04) < 1e-12
        assert f["scenario_id"] == a["scenario_id"]                   # cùng dòng ngẫu nhiên → so cặp được
        v = cau_hinh_bien_the(vu, "vol")
        assert v["vol_prep"] == v["vol_post"] == a["vol_pre"]
        assert cau_hinh_bien_the(vu, "vol_prep")["vol_post"] == a["vol_post"]

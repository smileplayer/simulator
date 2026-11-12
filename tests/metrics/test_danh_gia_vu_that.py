"""Đọc bảng vụ, kế hoạch tải, tóm tắt đánh giá vụ thật (không gọi mạng)."""
import pandas as pd

from metrics.danh_gia_vu_that import nen_co_tuong_khac, tom_tat
from scenarios.tai_vu_that import doc_bang_vu, doc_doi_chung, ke_hoach

A, B = "0x" + "a" * 40, "0x" + "b" * 40
BANG = f"""# Table
| Pool | tick_lower | tick_upper | `t_m` block | `t_m` tx_idx | `t_b` block | `t_b` tx_idx | Victim count | Main wall provider |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `{A}` | 10 | 11 | 1000000 | 1 | 1100000 | 2 | 3 | `0xdead` |
| `{A}` | 20 | 21 | 1200000 | 1 | 1300000 | 2 | 1 | `0xdead` |
| `{A}` | 30 | 31 | 2000000 | 1 | 2100000 | 2 | 2 | `0xdead` |
| `{B}` | 5 | 6 | 3000000 | 1 | 3100000 | 2 | 4 | `0xbeef` |
"""
DC = f"""| Alias | pool | token0 |
| --- | --- | --- |
| `P1` | `{B}` | USDT |
| `P2` | `{A.upper().replace('0X', '0x')}` | UB |
"""


def _doc(tmp_path):
    f, g = tmp_path / "vu.md", tmp_path / "dc.md"
    f.write_text(BANG, encoding="utf-8")
    g.write_text(DC, encoding="utf-8")
    return doc_bang_vu(f), doc_doi_chung(g)


def test_doc_bang(tmp_path):
    vu, dc = _doc(tmp_path)
    assert len(vu) == 4 and list(vu["t_b"][:2]) == [1100000, 1300000]
    assert vu["vu_id"][0] == "0xaaaa_10" and vu["n_victim"][3] == 4
    assert list(dc["alias"]) == ["P1", "P2"] and dc["pool"][1] == A


def test_ke_hoach_gop_va_tach(tmp_path):
    vu, dc = _doc(tmp_path)
    kh = ke_hoach(vu, dc, dem_truoc_gio=1, dem_sau_gio=2, giay_block=1.0)
    v = [k for k in kh if k["kieu"] == "vu"]
    assert len(v) == 3                                    # bể A: vụ 1+2 gộp (cách 100k), vụ 3 tách (cách 700k); bể B một đoạn
    a1 = v[0]
    assert (a1["tu"], a1["den"], a1["so_vu"]) == (1000000 - 3600, 1300000 + 7200, 2)
    assert v[1]["so_vu"] == 1 and v[1]["tu"] == 2000000 - 3600
    dcs = [k for k in kh if k["kieu"] == "doi_chung"]
    assert len(dcs) == 6 and all(k["so_block"] == 14 * 86400 for k in dcs)
    assert min(k["tu"] for k in dcs) == 1000000 and max(k["den"] for k in dcs) == 3100000


def test_tom_tat_gop():
    vu = pd.DataFrame(dict(m=[2.0, 2.0, 3.0, 3.0], bat=[True, True, True, False], som_hon_rut=[10.0, 30.0, 5.0, float("nan")]))
    dc = pd.DataFrame(dict(m=[2.0, 2.0, 3.0, 3.0], so_gio_bao=[1, 2, 0, 0], gio_xet=[100, 100, 100, 100]))
    t = tom_tat(vu, dc).set_index("m")
    assert t.loc[2.0, "vu_bat"] == 2 and t.loc[2.0, "vu_co_du_lieu"] == 2 and t.loc[2.0, "trung_vi_som_gio"] == 20.0
    assert t.loc[2.0, "gio_bao_nham"] == 3 and t.loc[2.0, "gio_xet"] == 200 and t.loc[3.0, "vu_bat"] == 1


def test_nen_co_tuong_khac():
    ch = pd.DataFrame(dict(L=[10.0] * 5 + [10.0], tick=[7, 7, 7, 7, 7, 1]), index=range(6))
    assert nen_co_tuong_khac(ch, 5, 1) is True            # 5 giờ trước ở tick 7 ≠ 1 và L bằng nhau
    ch["L"] = [1.0] * 5 + [10.0]
    assert nen_co_tuong_khac(ch, 5, 1) is False

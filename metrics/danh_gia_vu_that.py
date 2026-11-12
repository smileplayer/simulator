"""Đánh giá bộ phát hiện tường trên log thật của mọi vụ (29 vụ của bài gốc) và bể đối chứng đã tải.

    python -m metrics.danh_gia_vu_that [--N 24]

Đọc kế hoạch từ `scenarios.tai_vu_that.ke_hoach`; với mỗi vụ có dữ liệu phủ tới t_b (thư mục kế hoạch, hoặc thư mục cũ
`ket_qua/that/0x9485_hai_vu`) chạy luật báo động (`metrics.phat_hien_that`) với nhiều m; với mỗi đoạn đối chứng có dữ liệu
(kể cả `ket_qua/that/P1_doi_chung`) đếm báo nhầm. Ghi `ket_qua/that/danh_gia_vu.csv` (vụ × m) và
`ket_qua/that/danh_gia_doi_chung.csv` (đoạn × m), in bảng tóm tắt theo m. Không ghi gì vào các thư mục dữ liệu.

`nen_co_tuong_khac` = True nếu trong 24 giờ trước t_m có giờ mà tick chứa giá khác tick tường và L (đơn vị L thô) ≥ 0,5 ×
L giờ t_m: dấu hiệu bể đã có tường cũ, nên báo trước t_m chưa chắc là báo nhầm.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from metrics.phat_hien_that import bao_nham_sach, chuoi_L_that, danh_gia_that, gio_block
from scenarios.tai_vu_that import BANG_DOI_CHUNG, BANG_VU, GOC, doc_bang_vu, doc_doi_chung, ke_hoach

CAC_M = (1.5, 2.0, 3.0, 5.0, 10.0)
# Thư mục tải từ trước khi có kế hoạch: (pool, block đầu, block cuối, thư mục).
VU_CU = [("0x9485ff32b6b4444c21d5abe4d9a2283d127075a2", 53300000, 54760000, GOC / "0x9485_hai_vu")]
DOI_CHUNG_CU = [("P1", "0x172fcd41e0913e95784454622d1c3724f546f849", 53300000, 54760000, GOC / "P1_doi_chung")]


def _tien_do(ra: Path) -> dict:
    f = ra / "tien_do.json"
    return json.loads(f.read_text()) if f.exists() else {}


def _co_swap(ra: Path) -> bool:
    """Thư mục có swap.csv và moc.csv với ít nhất một dòng dữ liệu."""
    s, m = ra / "swap.csv", ra / "moc.csv"
    if not (s.exists() and m.exists() and s.stat().st_size > 0):
        return False
    return len(pd.read_csv(s, usecols=["block"], nrows=2)) > 0 and len(pd.read_csv(m)) >= 2


def thu_muc_cho_vu(v, ke: list[dict]) -> Path | None:
    """Thư mục dữ liệu phủ [t_m, t_b] của vụ `v` (hàng của bảng vụ): ưu tiên thư mục kế hoạch, rồi thư mục cũ; None nếu chưa có."""
    for k in ke:
        if k["kieu"] == "vu" and v.vu_id in k["vu_ids"] and _co_swap(k["ra"]) and _tien_do(k["ra"]).get("swap", -1) >= v.t_b:
            return k["ra"]
    for pool, tu, den, ra in VU_CU:
        if pool == v.pool and tu <= v.t_m and v.t_b <= den and _co_swap(ra):
            return ra
    return None


def doan_doi_chung_co_du_lieu(ke: list[dict]) -> list[tuple[str, Path]]:
    """Các đoạn đối chứng có swap (ten, thư mục): đoạn trong kế hoạch rồi `P1_doi_chung`."""
    kq = [(k["ten"], k["ra"]) for k in ke if k["kieu"] == "doi_chung" and _co_swap(k["ra"])]
    kq += [(ten, ra) for ten, _, _, _, ra in DOI_CHUNG_CU if _co_swap(ra)]
    return kq


def nen_co_tuong_khac(ch: pd.DataFrame, h_m: int, tick_tuong: int) -> bool:
    """Dấu hiệu tường cũ: trong 24 giờ trước `h_m` có giờ tick chứa giá ≠ `tick_tuong` mà L ≥ 0,5 × L giờ `h_m`."""
    if h_m not in ch.index:
        return False
    L0 = float(ch.loc[h_m, "L"])
    w = ch.loc[max(ch.index[0], h_m - 24):h_m - 1]
    return bool(((w["tick"] != tick_tuong) & (w["L"] >= 0.5 * L0)).any())


def danh_gia_vu(ra: Path, v, N: int = 24, cac_m=CAC_M) -> pd.DataFrame:
    """Đánh giá một vụ `v` trên dữ liệu trong `ra` (không ghi file); mỗi dòng một m. Rỗng nếu t_m ở trước mốc đầu dữ liệu."""
    swap, moc = pd.read_csv(ra / "swap.csv"), pd.read_csv(ra / "moc.csv")
    ch = chuoi_L_that(swap, moc)
    g0 = gio_block([int(swap["block"].min())], moc)[0]
    h_m, h_b = (int(math.floor(gio_block([x], moc)[0] - g0)) for x in (v.t_m, v.t_b))
    if h_m < 0 or h_b <= h_m:
        return pd.DataFrame()
    nen = nen_co_tuong_khac(ch, h_m, int(v.tick_lower))
    kq = pd.DataFrame([danh_gia_that(ch["L"], h_m, h_b, m, N) for m in cac_m])
    kq.insert(0, "nen_co_tuong_khac", nen)
    kq.insert(0, "h_b", h_b)
    kq.insert(0, "h_m", h_m)
    kq.insert(0, "n_victim", int(v.n_victim))
    kq.insert(0, "vu_id", v.vu_id)
    kq["thu_muc"] = Path(ra).as_posix()
    return kq


def danh_gia_doi_chung(ten: str, ra: Path, N: int = 24, cac_m=CAC_M) -> pd.DataFrame:
    """Báo nhầm trên một đoạn đối chứng (không ghi file); mỗi dòng một m. Rỗng nếu đoạn không đủ giờ."""
    ch = chuoi_L_that(pd.read_csv(ra / "swap.csv"), pd.read_csv(ra / "moc.csv"))
    kq = pd.DataFrame([bao_nham_sach(ch["L"], m, N) for m in cac_m])
    kq.insert(0, "thu_muc", Path(ra).as_posix())
    kq.insert(0, "doan", ten)
    return kq


def tom_tat(vu: pd.DataFrame, dc: pd.DataFrame) -> pd.DataFrame:
    """Tóm tắt theo m: số vụ bắt được / số vụ có dữ liệu, trung vị giờ báo sớm (các vụ bắt được), tổng giờ báo nhầm / giờ xét."""
    rows = []
    for m in sorted(set(vu["m"]) | set(dc["m"])):
        a, b = vu[vu["m"] == m], dc[dc["m"] == m]
        bat = a[a["bat"].astype(bool)]
        rows.append(dict(m=m, vu_bat=int(len(bat)), vu_co_du_lieu=int(len(a)),
                         trung_vi_som_gio=float(bat["som_hon_rut"].median()) if len(bat) else math.nan,
                         gio_bao_nham=int(b["so_gio_bao"].sum()), gio_xet=int(b["gio_xet"].sum()),
                         ty_le_nham=float(b["so_gio_bao"].sum() / b["gio_xet"].sum()) if b["gio_xet"].sum() else math.nan))
    return pd.DataFrame(rows)


def chay(N: int = 24, goc: Path = GOC, bang_vu: Path = BANG_VU, bang_dc: Path = BANG_DOI_CHUNG) -> tuple:
    """Chạy toàn bộ: ghi `danh_gia_vu.csv`, `danh_gia_doi_chung.csv` vào `goc`; trả (bảng vụ, bảng đối chứng, tóm tắt)."""
    vu_df = doc_bang_vu(bang_vu)
    ke = ke_hoach(vu_df, doc_doi_chung(bang_dc), goc=goc)
    cac = []
    for v in vu_df.itertuples():
        ra = thu_muc_cho_vu(v, ke)
        if ra is None:
            continue
        r = danh_gia_vu(ra, v, N)
        if len(r):
            cac.append(r)
    vu = pd.concat(cac, ignore_index=True) if cac else pd.DataFrame(
        columns=["vu_id", "n_victim", "h_m", "h_b", "nen_co_tuong_khac", "m", "bat", "som_hon_rut", "ty_so_max", "bao_truoc_tm"])
    ds = []
    for ten, ra in doan_doi_chung_co_du_lieu(ke):
        ds.append(danh_gia_doi_chung(ten, ra, N))
    dc = pd.concat(ds, ignore_index=True) if ds else pd.DataFrame(
        columns=["doan", "m", "gio_xet", "so_gio_bao", "so_dot", "ty_le"])
    goc.mkdir(parents=True, exist_ok=True)
    cot_vu = ["vu_id", "n_victim", "h_m", "h_b", "m", "bat", "som_hon_rut", "ty_so_max", "bao_truoc_tm", "nen_co_tuong_khac",
              "t_bao", "so_gio_bao", "ty_so_tm", "thu_muc"]
    vu[[c for c in cot_vu if c in vu.columns]].to_csv(goc / "danh_gia_vu.csv", index=False, encoding="utf-8-sig")
    dc.to_csv(goc / "danh_gia_doi_chung.csv", index=False, encoding="utf-8-sig")
    return vu, dc, tom_tat(vu, dc)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--N", type=int, default=24, help="số giờ đường nền")
    a = ap.parse_args()
    vu, dc, tt = chay(a.N)
    pd.set_option("display.width", 200)
    print("== Từng vụ ==")
    print(vu.drop(columns=["thu_muc"], errors="ignore").round(2).to_string(index=False))
    print("== Đối chứng ==")
    print(dc.drop(columns=["thu_muc"], errors="ignore").round(4).to_string(index=False))
    print("== Tóm tắt theo m ==")
    print(tt.round(3).to_string(index=False))
    print(f"→ {GOC / 'danh_gia_vu.csv'}, {GOC / 'danh_gia_doi_chung.csv'}")

"""Bảng đánh giá bộ phát hiện tường bằng một lệnh: `python -m metrics.chay_phat_hien [--vao ket_qua/rq1_tohop]`.

Đọc log RQ1 (không biện pháp), phát lại luật trần động với nhiều bội số m, ghi vào `ket_qua/rq1/`:
`phat_hien_theo_luot.csv` (một dòng mỗi lượt × m), `phat_hien.csv` (gộp theo m), `phat_hien_ne.csv` (số giờ dựng
tường từng nấc để không chạm ngưỡng, theo m và tỷ số tường/nền). Chạy khoảng nửa phút với 300 log.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from metrics.phat_hien import danh_gia, ne_tu_tu
from scenarios.batch import doc_ket_qua

CAC_M = (1.5, 2.0, 3.0, 5.0, 10.0, 30.0, 100.0, 300.0, 1000.0, 3000.0)
M_NE = (1.5, 2.0, 3.0, 5.0, 10.0)


def main(vao: str = "ket_qua/rq1_tohop", ra: str = "ket_qua/rq1", N: int = 24) -> pd.DataFrame:
    """Tính và ghi ba bảng; trả bảng gộp theo m."""
    rows = []
    for df in doc_ket_qua(vao):
        meta = df.attrs["meta"]
        for m in CAC_M:
            rows.append(dict(vu=meta.get("scenario_id"), seed=meta.get("seed"), m=m, **danh_gia(df, m, N)))
    luot = pd.DataFrame(rows)
    out = Path(ra)
    out.mkdir(parents=True, exist_ok=True)
    luot.to_csv(out / "phat_hien_theo_luot.csv", index=False, encoding="utf-8-sig")
    gop = luot.groupby("m").agg(
        n=("seed", "size"), ty_le_bat=("bat_truoc_rut", "mean"),
        som_hon_rut_tv=("som_hon_rut", "median"), som_hon_victim_tv=("som_hon_victim", "median"),
        som_hon_victim_min=("som_hon_victim", "min"), bao_nham=("bao_nham", "sum"), gio_nen=("gio_nen", "sum"),
    ).reset_index()
    gop.to_csv(out / "phat_hien.csv", index=False, encoding="utf-8-sig")
    ty = luot[luot["m"] == CAC_M[0]]["ty_so"]
    moc = {"nho_nhat": ty.min(), "trung_vi": ty.median(), "lon_nhat": ty.max()}
    ne = pd.DataFrame([dict(m=m, **{f"gio_{k}": ne_tu_tu(v, m, N) for k, v in moc.items()}) for m in M_NE])
    ne.to_csv(out / "phat_hien_ne.csv", index=False, encoding="utf-8-sig")
    print(f"{luot[['vu', 'seed']].drop_duplicates().shape[0]} lượt; tỷ số tường/nền lúc dựng: "
          f"{moc['nho_nhat']:.0f} / {moc['trung_vi']:.0f} / {moc['lon_nhat']:.0f} (nhỏ nhất / trung vị / lớn nhất)")
    print(gop.round(3).to_string(index=False))
    print(ne.to_string(index=False))
    return gop


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--vao", default="ket_qua/rq1_tohop")
    ap.add_argument("--ra", default="ket_qua/rq1")
    ap.add_argument("--N", type=int, default=24)
    a = ap.parse_args()
    main(a.vao, a.ra, a.N)

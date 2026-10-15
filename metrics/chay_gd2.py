"""Bảng GĐ2 (RQ2) bằng một lệnh: `python -m metrics.chay_gd2 [--gd2 ket_qua/gd2] [--B 2000] [--nhanh]`.

Đọc `tomtat_v2.csv` (biện pháp × victim) và `tomtat_farm_v2.csv` (× farm_share), ghi `ket_qua/gd2/bang/`:
`danh_doi.csv`, `danh_doi_farm.csv` (bảng dài: hiệu cặp so với `khong`, CI, % thay đổi), `*_theo_dang.csv`
(tách tuyến tính/log), `gon*.csv` (bảng rộng cho bài báo), `ty_le_sap*.csv`, `q_sao_vu.csv`, `q_sao_tomtat.csv`.
`--nhanh`: B = 200 (thử nhanh).
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd

from metrics.gd2 import bang_danh_doi, bang_gon, q_sao_vu, them_cot, tom_tat_q_sao, ty_le_sap


def main(gd2: str = "ket_qua/gd2", B: int = 2000) -> list[Path]:
    """Tính mọi bảng, trả danh sách file đã ghi."""
    d = Path(gd2)
    ra = d / "bang"
    ra.mkdir(parents=True, exist_ok=True)
    tt = them_cot(pd.read_csv(d / "tomtat_v2.csv"))
    fm = them_cot(pd.read_csv(d / "tomtat_farm_v2.csv"))
    out = {}
    t0 = time.time()
    out["danh_doi"] = bang_danh_doi(tt, ("victim_type",), B=B)
    out["danh_doi_theo_dang"] = bang_danh_doi(tt, ("subsidy_form", "victim_type"), B=B)
    out["danh_doi_farm"] = bang_danh_doi(fm, ("farm_share", "victim_type"), B=B)
    out["danh_doi_farm_theo_dang"] = bang_danh_doi(fm, ("subsidy_form", "farm_share", "victim_type"), B=B)
    print(f"bảng đánh đổi: {time.time() - t0:.1f} s")
    out["gon"] = bang_gon(out["danh_doi"], ("victim_type",))
    out["gon_theo_dang"] = bang_gon(out["danh_doi_theo_dang"], ("subsidy_form", "victim_type"))
    out["gon_farm"] = bang_gon(out["danh_doi_farm"], ("farm_share", "victim_type"))
    out["ty_le_sap"] = ty_le_sap(tt, ("victim_type",), B=B)
    out["ty_le_sap_farm"] = ty_le_sap(fm, ("farm_share", "victim_type"), B=B)
    qv = q_sao_vu(tt)
    out["q_sao_vu"] = qv
    out["q_sao_tomtat"] = tom_tat_q_sao(qv)
    files = []
    for ten, bang in out.items():
        f = ra / f"{ten}.csv"
        bang.to_csv(f, index=False)
        files.append(f)
    return files


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gd2", default="ket_qua/gd2")
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--nhanh", action="store_true")
    a = ap.parse_args()
    for f in main(a.gd2, 200 if a.nhanh else a.B):
        print(f)

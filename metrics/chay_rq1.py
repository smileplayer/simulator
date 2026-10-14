"""Chạy kiểm định RQ1 trên thư mục log của bộ tổ hợp, ghi bảng tóm tắt (CSV nhỏ) vào `ket_qua/rq1/`.

Lệnh: `python -m metrics.chay_rq1 [--vao ket_qua/rq1_tohop] [--ra ket_qua/rq1]`.
Ghi: `tomtat.csv` (một dòng/vụ), `kiemdinh.csv`, `bang4_lift.csv`, `bang6_gia.csv`, `bang7_drop.csv`.
Không ghi lại log; chỉ các file này được commit.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd

from metrics.report import summarize
from metrics.validate import bang_chia_nhom, validate_rq1
from scenarios.batch import doc_ket_qua


def tom_tat_thu_muc(vao: str | Path) -> pd.DataFrame:
    """Đọc mọi log trong `vao` bằng `doc_ket_qua`, trả bảng `summarize` (một dòng/vụ, thêm `vu`, `seed` và tham số kịch bản)."""
    rows = []
    for df in doc_ket_qua(vao):
        m = df.attrs["meta"]
        r = summarize(df)
        tham_so = {k: m.get(k) for k in ("L_A", "k", "c_V", "bg_band", "bg_tail", "subsidy_form")}
        rows.append({"vu": m.get("scenario_id"), "seed": m.get("seed"), **tham_so, **r})
    return pd.DataFrame(rows)


def main(vao: str, ra: str) -> None:
    """Tóm tắt, kiểm định, chia nhóm rồi ghi CSV; in bảng kiểm định ngắn."""
    t0 = time.time()
    tt = tom_tat_thu_muc(vao)
    out = Path(ra)
    out.mkdir(parents=True, exist_ok=True)
    tt.to_csv(out / "tomtat.csv", index=False, encoding="utf-8-sig")
    kd = validate_rq1(tt)
    kd.to_csv(out / "kiemdinh.csv", index=False, encoding="utf-8-sig")
    for ten, b in bang_chia_nhom(tt).items():
        b.to_csv(out / f"{ten}.csv", encoding="utf-8-sig")
    print(f"{len(tt)} vụ, {time.time() - t0:.1f} s → {out}")
    print(kd[["dau_hieu", "loai", "ty_le_mo_phong", "ty_le_bai_goc", "ket_qua"]].round(2).to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--vao", default="ket_qua/rq1_tohop")
    ap.add_argument("--ra", default="ket_qua/rq1")
    a = ap.parse_args()
    main(a.vao, a.ra)

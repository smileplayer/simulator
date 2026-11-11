"""Bốn chỉ số của kẻ tấn công ở RQ1 đo ĐỦ mọi lát xả (không cắt ở t_b): `python -m metrics.chay_rq1_du [--vao ...] [--ra ...]`.

`metrics.pnl.attacker_profit` (cột `attacker_profit_*` của `tomtat.csv`) chỉ tính lệnh xả trong [t_0, t_b]; khi giá đã
sập ≥ 10% ngay bước xả đầu (t_b = t_0) thì lát xả thứ hai bị bỏ. Script này dùng `scenarios.quet_gd2.loi_nhuan_dia_chi`
(đúng thước đo `dc_*` của RQ2/RQ3) trên từng log, ghi `loi_du_theo_luot.csv` và `loi_du.csv` (trung vị, CI 95%
bootstrap phân cụm theo vụ, số lượt dương, trung vị theo k). Đơn vị token1.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from metrics.validate import bootstrap_ci
from scenarios.batch import doc_ket_qua
from scenarios.quet_gd2 import loi_nhuan_dia_chi


def bang_luot(vao: str | Path) -> pd.DataFrame:
    """Một dòng mỗi log: vu, seed, k, dc_paper (lãi gộp cú xả), dc_ban_thang, dc_excess, ty_ban_thang = ban_thang / paper."""
    rows = []
    for df in doc_ket_qua(vao):
        m = df.attrs["meta"]
        if "pe_farmer" not in m or "Q_buoc" not in m:
            raise SystemExit(f"Log {m.get('scenario_id')} thiếu meta pe_farmer/Q_buoc (log dựng trước 22/10): phát lại bán thẳng sẽ lệch. "
                             "Dựng lại log bằng scenarios.batch, hoặc lấy số từ dòng bp = khong của ket_qua/gd2/tomtat_v4.csv.")
        r = loi_nhuan_dia_chi(df)
        rows.append(dict(vu=m.get("scenario_id"), seed=m.get("seed"), k=m.get("k"), dc_paper=r["dc_paper"],
                         dc_ban_thang=r["dc_ban_thang"], dc_excess=r["dc_excess"]))
    d = pd.DataFrame(rows)
    d["ty_ban_thang"] = d["dc_ban_thang"] / d["dc_paper"]
    return d


def tom_tat(d: pd.DataFrame) -> pd.DataFrame:
    """Bảng gộp: n lượt có cú xả, trung vị lãi gộp, trung vị tỷ lệ bán thẳng, trung vị lợi tăng thêm + CI, số lượt dương, theo k."""
    c = d.dropna(subset=["dc_excess"])
    lo, hi = bootstrap_ci(c, lambda x: float(np.median(x["dc_excess"])))
    r = dict(n=len(c), paper_tv=c["dc_paper"].median(), ty_ban_thang_tv=c["ty_ban_thang"].median(),
             excess_tv=c["dc_excess"].median(), excess_lo=lo, excess_hi=hi, n_duong=int((c["dc_excess"] > 1e-9).sum()))
    for k, g in c.groupby("k"):
        r[f"excess_tv_k{k:g}"] = g["dc_excess"].median()
    return pd.DataFrame([r])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--vao", default="ket_qua/rq1_tohop")
    ap.add_argument("--ra", default="ket_qua/rq1")
    a = ap.parse_args()
    d = bang_luot(a.vao)
    out = Path(a.ra)
    out.mkdir(parents=True, exist_ok=True)
    d.to_csv(out / "loi_du_theo_luot.csv", index=False, encoding="utf-8-sig")
    t = tom_tat(d)
    t.to_csv(out / "loi_du.csv", index=False, encoding="utf-8-sig")
    print(t.round(3).T.to_string(header=False))

"""Ngưỡng trần kiểu Định lý 6 bài gốc, tính từ bảng quét RQ2 sẵn có (không chạy lại mô phỏng).

    python -m metrics.nguong_dl6 [--vao ket_qua/gd2/tomtat_v4.csv ket_qua/gd2/tomtat_f001_v5.csv]

Định lý 6: Q* = inf{Q : Π_A^Q ≥ Π_direct}, Π_A^Q = F(Q) + D(Q) − κ(L_A). Trong bảng quét, với mỗi mức trần r = Q/Q_gốc:
- `F` = lãi vị thế tường (token1): tiền ròng của tường cộng token0 ròng của tường định giá ở giữa tick tường; gần bằng phí tường thu;
- `excess` = D − Π_direct = `dc_excess` (tiền xả trừ tiền bán thẳng phản thực);
- `G` = F + excess: phần hơn bán thẳng khi chưa trừ chi phí vốn tường. Tấn công hơn bán thẳng khi G ≥ κ.
κ không có trong mô phỏng, nên báo `kappa_hoa_von` = G / vốn tường (vốn tường = L_A·√P·(√1,0001 − 1), token1), tính trên cả thời gian
giữ tường, và ngưỡng Q*(κ)/Q = mức trần nhỏ nhất có trung vị G theo seed ≥ κ·vốn tường, cho vài mức κ. `Q_V`/Q = k là ngưỡng tham gia
của nạn nhân (Bổ đề 4) mà bài đang dùng. Ghi `ket_qua/gd2/nguong_dl6_<tên bảng>.csv` (theo mức trần) và `..._vu.csv` (theo vụ).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

KAPPA = [0.0, 0.001, 0.0025, 0.005, 0.01, 0.02, 0.05]


def them_cot(d: pd.DataFrame) -> pd.DataFrame:
    """Giữ các dòng `khong` và `capXX`, thêm r (tỷ lệ trần), F, G, vốn tường, kappa_hoa_von (đơn vị token1)."""
    d = d[d["bp"].str.startswith("cap") | (d["bp"] == "khong")].copy()
    d["r"] = np.where(d["bp"] == "khong", 1.0, pd.to_numeric(d["bp"].str[3:], errors="coerce") / 100)
    Pw = 1.0001 ** (d["wall_tick_lower"] + 0.5)
    d["von_tuong"] = d["L_A"] * np.sqrt(Pw) * (1.0001 ** 0.5 - 1)
    d["F"] = (d["dc_cash1"] - d["dc_paper"]) + (d["dc_d0"] + d["dc_x_xa"]) * Pw
    d["G"] = d["F"] + d["dc_excess"]
    d["kappa_hoa_von"] = d["G"] / d["von_tuong"]
    return d


def theo_muc_tran(d: pd.DataFrame) -> pd.DataFrame:
    """Trung vị theo (loại nạn nhân, mức trần): excess, F, G, κ hòa vốn, tỷ lệ lượt G < 0."""
    return d.groupby(["victim_type", "r"]).agg(
        n=("seed", "size"), excess=("dc_excess", "median"), F=("F", "median"), G=("G", "median"),
        kappa_hoa_von=("kappa_hoa_von", "median"), kappa_q10=("kappa_hoa_von", lambda s: s.quantile(0.1)),
        ty_le_G_am=("G", lambda s: (s < 0).mean())).reset_index()


def theo_vu(d: pd.DataFrame, kappa: list[float] = KAPPA) -> pd.DataFrame:
    """Mỗi (vụ, loại nạn nhân): Q*(κ)/Q cho từng κ (NaN nếu không mức trần nào đạt) cạnh k = Q_V/Q."""
    tv = d.groupby(["scenario_id", "victim_type", "r"]).agg(G=("G", "median"), von=("von_tuong", "median"), k=("k", "first")).reset_index()
    dong = []
    for (vu, vt), g in tv.groupby(["scenario_id", "victim_type"]):
        g = g.sort_values("r")
        r = dict(scenario_id=vu, victim_type=vt, k=float(g["k"].iloc[0]))
        for ka in kappa:
            dat = g[g["G"] >= ka * g["von"]]
            r[f"Qsao_{ka:g}"] = float(dat["r"].min()) if len(dat) else float("nan")
        dong.append(r)
    return pd.DataFrame(dong)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--vao", nargs="*", default=["ket_qua/gd2/tomtat_v4.csv", "ket_qua/gd2/tomtat_f001_v5.csv"])
    a = ap.parse_args()
    pd.set_option("display.width", 250, "display.max_columns", 40)
    for f in map(Path, a.vao):
        d = them_cot(pd.read_csv(f))
        m, v = theo_muc_tran(d), theo_vu(d)
        m.to_csv(f.parent / f"nguong_dl6_{f.stem}.csv", index=False)
        v.to_csv(f.parent / f"nguong_dl6_{f.stem}_vu.csv", index=False)
        print(f"== {f.name}: phí {d['meta_fee'].iloc[0]:g}")
        print(m.to_string(index=False, float_format=lambda x: f"{x:.4g}"))
        cot = [c for c in v.columns if c.startswith("Qsao_")]
        tt = v.groupby("victim_type")[cot].agg(lambda s: f"{s.median():.2f} ({s.isna().sum()} vụ không đạt)")
        print("Q*(κ)/Q trung vị theo vụ (k trung vị %.2f):" % v["k"].median())
        print(tt.to_string())
        om = v[v["victim_type"] == "omniscient"]
        for c in cot:
            print(f"  toàn tri, {c}: |Q*/Q − k| ≤ 0,15 ở {int(((om[c] - om['k']).abs() <= 0.15).sum())}/{len(om)} vụ")

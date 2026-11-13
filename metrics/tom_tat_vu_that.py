"""Tóm tắt kịch bản theo vụ thật (`scenarios.quet_vu_that`): mô phỏng so với thật, và mức cắt của từng biện pháp.

    python -m metrics.tom_tat_vu_that [--vao ket_qua/that/kich_ban_vu.csv]

Bảng 1 (`<tên file vào>_so_that.csv`), mỗi vụ, dòng không biện pháp: L_V/L_A và độ sập mô phỏng (trung vị theo seed) cạnh số thật
(`ket_qua/that/tham_so_vu.csv`). Bảng 2 (`<tên file vào>_bien_phap.csv`), mỗi (loại nạn nhân, biện pháp): thay đổi % của lợi tăng thêm
`dc_excess` (token1) so với không biện pháp theo cặp cùng vụ + seed; trung vị theo vụ rồi trung vị, nhỏ nhất, lớn nhất giữa các vụ,
và số vụ biện pháp cắt từ 50% trở lên. Vụ có lợi tăng thêm gốc ≤ 0 bị bỏ khỏi bảng 2.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

GOC = Path("ket_qua/that")
KHOA = ["scenario_id", "victim_type", "seed"]


def so_that(d: pd.DataFrame, ts: pd.DataFrame) -> pd.DataFrame:
    """Dòng `khong` theo (vụ, loại nạn nhân): L_V/L_A và độ sập mô phỏng cạnh thật."""
    g = d[d["bp"] == "khong"].groupby(["scenario_id", "victim_type"]).agg(
        LV_mp=("LV_chia_LA", "median"), sap_mp=("do_sap", "median"), loi_them=("dc_excess", "median"),
        thiet_hai_nn=("victim_loss_full", "median")).reset_index()
    ts = ts.assign(scenario_id="VU_" + ts["vu_id"], LV_that=1 / np.sqrt(ts["k"]) - 1)
    return g.merge(ts[["scenario_id", "k", "LV_that", "sap_400"]].rename(columns={"k": "k_that", "sap_400": "sap_that"}), on="scenario_id")


def bien_phap(d: pd.DataFrame) -> pd.DataFrame:
    """Thay đổi % của lợi tăng thêm so với không biện pháp (cặp cùng vụ + seed), gộp theo (loại nạn nhân, biện pháp)."""
    goc = d[d["bp"] == "khong"][KHOA + ["dc_excess"]].rename(columns={"dc_excess": "goc"})
    x = d[d["bp"] != "khong"].merge(goc, on=KHOA)
    x = x[x["goc"] > 1e-6].copy()
    x["doi"] = (x["dc_excess"] / x["goc"] - 1) * 100
    vu = x.groupby(["victim_type", "bp", "scenario_id"])["doi"].median().reset_index()
    return vu.groupby(["victim_type", "bp"])["doi"].agg(
        n_vu="size", trung_vi="median", nho_nhat="min", lon_nhat="max", cat_tu_50=lambda s: int((s <= -50).sum())).reset_index()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--vao", default=str(GOC / "kich_ban_vu.csv"))
    a = ap.parse_args()
    d = pd.read_csv(a.vao)
    s, b = so_that(d, pd.read_csv(GOC / "tham_so_vu.csv")), bien_phap(d)
    s.to_csv(GOC / f"{Path(a.vao).stem}_so_that.csv", index=False)
    b.to_csv(GOC / f"{Path(a.vao).stem}_bien_phap.csv", index=False)
    pd.set_option("display.width", 250, "display.max_columns", 40)
    print(s.to_string(index=False, float_format=lambda x: f"{x:.4g}"))
    print(b.to_string(index=False, float_format=lambda x: f"{x:.1f}"))

"""Kiểm tính bất biến theo quy mô: nhân mọi đại lượng tiền và thanh khoản với κ, giữ k, σ, f, bg_band.

    python -m scenarios.kiem_quy_mo [--kappa 100] [--seeds 3] [--nhanh]

Với mỗi vụ RQ1 (30 vụ) × loại nạn nhân × seed, chạy cặp (κ = 1, κ) cùng dòng ngẫu nhiên và so các đại lượng đã chia κ
(lợi tăng thêm, lãi gộp, thiệt hại nạn nhân, trợ cấp, khối lượng) cùng các tỷ số (độ sập, L_V/L_A). Ghi một dòng mỗi
cặp vào `ket_qua/rq1/quy_mo.csv` (ghi dần, chạy lại bỏ cặp đã có) và in sai lệch tương đối lớn nhất.
Đại lượng được nhân: L_A, L_bg, Q, attacker_inventory, bg_size (c_V tự giữ vì k giữ: c_V = k·f·V/L_A).
"""
from __future__ import annotations

import argparse
import csv
import warnings
from pathlib import Path

import pandas as pd

from metrics.report import summarize
from scenarios.batch import cau_hinh, to_hop_rq1
from scenarios.hieu_chinh import LV_chia_LA, do_sap
from scenarios.quet_gd2 import loi_nhuan_dia_chi
from scenarios.run import run_frame

NHAN = ("L_A", "L_bg", "Q", "attacker_inventory", "bg_size")
TIEN = ("dc_excess", "dc_paper", "victim_loss_full", "subsidy_total", "vol_tong")   # chia κ trước khi so
TY_SO = ("do_sap", "LV_chia_LA")


def mot_luot(vu: dict, victim: str, seed: int, kappa: float) -> dict:
    """Chạy một lượt với mọi đại lượng quy mô nhân `kappa`; trả các chỉ số (tiền đã chia `kappa`)."""
    cfg = cau_hinh(vu)
    for c in NHAN:
        cfg[c] = cfg[c] * kappa
    cfg["victim_type"] = victim
    df = run_frame(cfg, seed)
    m = df.attrs["meta"]
    r = {**summarize(df), **loi_nhuan_dia_chi(df)}
    r["vol_tong"] = float(df[df.kind == "swap"].amount1.abs().sum())
    r["do_sap"] = do_sap(df) if m["t_rut"] is not None else float("nan")
    r["LV_chia_LA"] = LV_chia_LA(df)
    return {**{c: r[c] / kappa for c in TIEN}, **{c: r[c] for c in TY_SO}}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--kappa", type=float, default=100.0)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--nhanh", action="store_true", help="3 vụ × 1 seed")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    warnings.filterwarnings("ignore")
    out = Path(a.out or ("ket_qua/rq1/quy_mo_nhanh.csv" if a.nhanh else "ket_qua/rq1/quy_mo.csv"))
    ds = to_hop_rq1()[:3] if a.nhanh else to_hop_rq1()
    seeds = 1 if a.nhanh else a.seeds
    da_co = set()
    if out.exists():
        da_co = {(r["vu"], r["victim_type"], int(r["seed"])) for r in csv.DictReader(out.open(encoding="utf-8"))}
    with out.open("a", encoding="utf-8", newline="") as f:
        w = None
        for vu in ds:
            for vt in ("omniscient", "adaptive"):
                for sd in range(seeds):
                    if (vu["id"], vt, sd) in da_co:
                        continue
                    a1, ak = mot_luot(vu, vt, sd, 1.0), mot_luot(vu, vt, sd, a.kappa)
                    dong = dict(vu=vu["id"], victim_type=vt, seed=sd, kappa=a.kappa,
                                **{f"{c}_1": v for c, v in a1.items()}, **{f"{c}_k": v for c, v in ak.items()})
                    if w is None:
                        w = csv.DictWriter(f, fieldnames=list(dong))
                        if not da_co:
                            w.writeheader()
                    w.writerow(dong)
                    f.flush()
    d = pd.read_csv(out)
    print(f"{len(d)} cặp → {out}")
    for c in TIEN + TY_SO:
        x, y = d[f"{c}_1"], d[f"{c}_k"]
        mau = x.abs().clip(lower=1e-9)
        lech = ((y - x).abs() / mau)[x.abs() > 1e-6]
        print(f"  {c}: lệch tương đối lớn nhất {lech.max():.2e}, trung vị {lech.median():.2e} (n = {lech.notna().sum()})")

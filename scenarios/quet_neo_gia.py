"""Quét mức biến động của giá ngoài trong pha tường (giữa hai cực "neo cứng" và "bỏ neo") trên bộ RQ1.

    python -m scenarios.quet_neo_gia [--seeds 10] [--nhanh]

`vol_prep` = độ biến động mỗi giờ của P_e trong pha tường (0 = neo cứng như bản gốc; 0,002 = như trước khi dựng tường,
tức biến thể "bỏ neo" của mục độ nhạy). Một tick rộng 0,0001 (0,01%). Mỗi (mức, vụ, seed) ghi một dòng vào
`ket_qua/rq1/neo_gia.csv` (ghi dần, chạy lại bỏ lượt đã có): L_V/L_A ngay trước khi rút tường, lợi tăng thêm
`dc_excess` (token1), độ sập. Cuối cùng in bảng gộp theo mức.
"""
from __future__ import annotations

import argparse
import csv
import time
import warnings
from pathlib import Path

import pandas as pd

from scenarios.batch import cau_hinh, to_hop_rq1
from scenarios.hieu_chinh import LV_chia_LA, do_sap
from scenarios.quet_gd2 import loi_nhuan_dia_chi
from scenarios.run import run_frame

MUC_VOL = [0.0, 0.00002, 0.00005, 0.0001, 0.0002, 0.0005, 0.001, 0.002]


def mot_luot(vu: dict, vol: float, seed: int) -> dict:
    """Một lượt RQ1 (nạn nhân toàn tri, không biện pháp) với `vol_prep` = `vol`; trả các chỉ số của lượt."""
    cfg = cau_hinh(vu)
    cfg["vol_prep"] = vol
    df = run_frame(cfg, seed)
    m = df.attrs["meta"]
    co_rut = m["t_rut"] is not None
    r = loi_nhuan_dia_chi(df)
    return dict(vol_prep=vol, vu=vu["id"], seed=seed, LV_chia_LA=LV_chia_LA(df) if co_rut else float("nan"),
                dc_excess=r["dc_excess"], do_sap=do_sap(df) if co_rut else float("nan"))


def gop(d: pd.DataFrame) -> pd.DataFrame:
    """Bảng theo mức: số lượt, phần lượt còn nạn nhân trước khi rút tường, trung vị lợi tăng thêm và độ sập."""
    g = d.groupby("vol_prep")
    return pd.DataFrame(dict(n=g.size(), con_nan_nhan=g["LV_chia_LA"].apply(lambda s: float((s > 1e-9).mean())),
                             LV_chia_LA_tv=g["LV_chia_LA"].median(), excess_tv=g["dc_excess"].median(),
                             excess_duong=g["dc_excess"].apply(lambda s: float((s > 1e-9).mean())),
                             do_sap_tv=g["do_sap"].median()))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--nhanh", action="store_true", help="3 vụ × 1 seed × 3 mức")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    warnings.filterwarnings("ignore")
    out = Path(a.out or ("ket_qua/rq1/neo_gia_nhanh.csv" if a.nhanh else "ket_qua/rq1/neo_gia.csv"))
    ds, muc, seeds = to_hop_rq1(), MUC_VOL, a.seeds
    if a.nhanh:
        ds, muc, seeds = ds[:3], [0.0, 0.0002, 0.002], 1
    da_co = set()
    if out.exists():
        da_co = {(float(r["vol_prep"]), r["vu"], int(r["seed"])) for r in csv.DictReader(out.open(encoding="utf-8"))}
    viec = [(v, vu, s) for v in muc for vu in ds for s in range(seeds) if (v, vu["id"], s) not in da_co]
    t0 = time.time()
    with out.open("a", encoding="utf-8", newline="") as f:
        w = None
        for i, (v, vu, s) in enumerate(viec):
            dong = mot_luot(vu, v, s)
            if w is None:
                w = csv.DictWriter(f, fieldnames=list(dong))
                if not da_co:
                    w.writeheader()
            w.writerow(dong)
            f.flush()
            if (i + 1) % 200 == 0:
                tb = (time.time() - t0) / (i + 1)
                print(f"{i + 1}/{len(viec)}, còn ~{tb * (len(viec) - i - 1) / 60:.1f} phút", flush=True)
    print(gop(pd.read_csv(out)).round(3).to_string())
    print(f"→ {out}")

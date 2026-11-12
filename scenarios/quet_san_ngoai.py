"""Quét chế độ giá ngoài nội sinh (cải tiến H): tường có tự giữ được giá không, và thứ hạng biện pháp có giữ không.

    python -m scenarios.quet_san_ngoai [--seeds 5] [--nhanh]

Lưới: độ sâu sàn ngoài `do_sau` ∈ {ghim (None, mô hình cũ), 1e4, 1e5, 1e6, 1e8} token1 × cỡ giao dịch nền
`bg_nhan` ∈ {1; 0,3; 0,1} (luồng tự nhiên so với sức chứa của tường) × biện pháp ∈ {khong, cap50, cap05, warn15, warn40,
dyncap} × 2 loại nạn nhân × 30 vụ RQ1 × seeds. Độ biến động riêng của sàn ngoài trong pha tường = 0 (chỉ luồng lệnh
làm giá trôi). Mỗi lượt một dòng `ket_qua/gd2/tomtat_san.csv` (ghi dần, chạy lại bỏ lượt đã có): phần giờ pha tường
giá nằm trong tick tường (`ty_trong_tuong`), khối lượng farmer, L_V/L_A, lợi tăng thêm `dc_excess` + `dc_farm_pnl`,
độ sập, trợ cấp. `--tom_tat` in bảng: theo (do_sau, bg_nhan) phần giờ giữ giá và lợi tăng thêm; % thay đổi của từng
biện pháp so với `khong` (tỷ số trung bình trên cặp cùng vụ + seed), để so thứ hạng với mô hình ghim.
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
from scenarios.quet_gd2 import BIEN_PHAP, loi_nhuan_dia_chi
from scenarios.run import run_frame

DO_SAU = [None, 1e4, 1e5, 1e6, 1e8]
BG_NHAN = [1.0, 0.3, 0.1]
BP = ["khong", "cap50", "cap05", "warn15", "warn40", "dyncap"]
VICTIM = ["omniscient", "adaptive"]
KHOA = ["do_sau", "bg_nhan", "bp", "victim_type", "vu", "seed"]


def mot_luot(vu: dict, do_sau, bg_nhan: float, bp: str, victim: str, seed: int) -> dict:
    """Một lượt; `do_sau` None = mô hình ghim cũ. Trả dict phẳng các chỉ số (token1)."""
    cfg = cau_hinh(vu)
    cfg.update(victim_type=victim, defense=BIEN_PHAP[bp], bg_size=cfg["bg_size"] * bg_nhan)
    if do_sau is not None:
        cfg["san_ngoai"] = {"do_sau": do_sau, "vol_prep": 0.0}
    df = run_frame(cfg, seed)
    m = df.attrs["meta"]
    st = df[df.kind == "step"].groupby("t").last()
    tr = m["t_rut"]
    pha = st.loc[m["t_m"]:(tr - 1 if tr is not None else None)]
    sw = df[df.kind == "swap"]
    r = loi_nhuan_dia_chi(df)
    return dict(do_sau="ghim" if do_sau is None else do_sau, bg_nhan=bg_nhan, bp=bp, victim_type=victim, vu=vu["id"],
                seed=seed, k=m["k"], ty_trong_tuong=float((pha.tick_after == m["wall_tick"]).mean()),
                vol_farmer=float(sw[sw.role == "farmer"].amount1.clip(lower=0).sum()),
                LV_chia_LA=LV_chia_LA(df) if tr is not None else float("nan"),
                loi_tang_them=r["dc_excess"] + r["dc_farm_pnl"], dc_excess=r["dc_excess"],
                do_sap=do_sap(df) if tr is not None else float("nan"),
                tro_cap=float(df[df.kind == "subsidy"].amount1.sum()))


def tom_tat(d: pd.DataFrame) -> None:
    """In hai bảng: giữ giá + lợi theo chế độ; % thay đổi theo biện pháp (so với khong, cùng chế độ, vụ, seed, victim)."""
    k = d[d.bp == "khong"]
    print(k.groupby(["victim_type", "do_sau", "bg_nhan"]).agg(
        giu_gia=("ty_trong_tuong", "median"), vol_farmer=("vol_farmer", "median"), LV_LA=("LV_chia_LA", "median"),
        loi=("loi_tang_them", "median"), sap=("do_sap", "median")).round(3).to_string())
    goc = k.set_index(["do_sau", "bg_nhan", "victim_type", "vu", "seed"])["loi_tang_them"]
    x = d.join(goc.rename("goc"), on=["do_sau", "bg_nhan", "victim_type", "vu", "seed"])
    g = x.groupby(["victim_type", "do_sau", "bg_nhan", "bp"])
    mau = g["goc"].mean()
    pct = (100 * (g["loi_tang_them"].mean() / mau.where(mau.abs() > 1.0) - 1)).unstack("bp")   # gốc ≈ 0 → NaN
    print("\n% thay đổi lợi tăng thêm so với khong (tỷ số trung bình):")
    print(pct[[b for b in BP if b in pct]].round(0).to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--nhanh", action="store_true", help="3 vụ × 1 seed × (ghim, 1e5) × bg {1; 0,1} × (khong, cap05)")
    ap.add_argument("--tom_tat", action="store_true", help="chỉ in bảng từ file đã có")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    warnings.filterwarnings("ignore")
    out = Path(a.out or ("ket_qua/gd2/tomtat_san_nhanh.csv" if a.nhanh else "ket_qua/gd2/tomtat_san.csv"))
    if not a.tom_tat:
        ds, sau, bg, bp, seeds = to_hop_rq1(), DO_SAU, BG_NHAN, BP, a.seeds
        if a.nhanh:
            ds, sau, bg, bp, seeds = ds[:3], [None, 1e5], [1.0, 0.1], ["khong", "cap05"], 1
        da_co = set()
        if out.exists():
            da_co = {tuple(r[c] for c in KHOA) for r in csv.DictReader(out.open(encoding="utf-8"))}
        viec = [(vu, s_, b_, p_, v_, sd) for s_ in sau for b_ in bg for p_ in bp for v_ in VICTIM for vu in ds
                for sd in range(seeds)
                if ("ghim" if s_ is None else str(s_), str(b_), p_, v_, vu["id"], str(sd)) not in da_co]
        t0 = time.time()
        with out.open("a", encoding="utf-8", newline="") as f:
            w = None
            for i, (vu, s_, b_, p_, v_, sd) in enumerate(viec):
                dong = mot_luot(vu, s_, b_, p_, v_, sd)
                if w is None:
                    w = csv.DictWriter(f, fieldnames=list(dong))
                    if not da_co:
                        w.writeheader()
                w.writerow(dong)
                f.flush()
                if (i + 1) % 200 == 0 or i + 1 == len(viec):
                    tb = (time.time() - t0) / (i + 1)
                    print(f"{i + 1}/{len(viec)}, {tb:.2f} s/lượt, còn ~{tb * (len(viec) - i - 1) / 60:.0f} phút", flush=True)
    tom_tat(pd.read_csv(out))
    print(f"→ {out}")

"""Quét độ nhạy vốn arbitrageur (tuần 11/11): 30 vụ RQ1 × `arb_budget` ∈ {None, 100k, 30k, 10k} token1 × 2 loại victim
× seed, không biện pháp, một nạn nhân. Cột như `scenarios.quet_nhieu_nan_nhan` (+ `arb_budget`, `arb_da_chi`).

Chạy: `python -m scenarios.quet_arb_von [--seeds 10] [--nhanh] [--out ...]` → `ket_qua/gd2/tomtat_arb_von.csv`;
chạy lại thì bỏ các lượt đã có (`arb_budget` ghi "None" khi không giới hạn).
"""
from __future__ import annotations

import argparse
import csv
import json
import time
import warnings
from pathlib import Path

from scenarios import quet_gd2
from scenarios.batch import FILE_TO_HOP
from scenarios.quet_nhieu_nan_nhan import dong_voi_cfg

VON = [None, 100_000.0, 30_000.0, 10_000.0, 3_000.0, 1_000.0]
BANG = {"khong": quet_gd2.BIEN_PHAP["khong"]}
KHOA = ["scenario_id", "arb_budget", "victim_type", "seed"]


def danh_sach_viec(seeds: int, nhanh: bool = False) -> list[tuple]:
    """Mọi lượt (vu, arb_budget, victim, seed); --nhanh: 2 vụ đầu × 2 seed."""
    ds = json.loads(FILE_TO_HOP.read_text(encoding="utf-8"))
    if nhanh:
        ds, seeds = ds[:2], 2
    return [(vu, b, vt, sd) for vu in ds for b in VON for vt in quet_gd2.LOAI_VICTIM for sd in range(seeds)]


def chay(seeds: int, out: Path, nhanh: bool = False) -> None:
    """Chạy các lượt còn thiếu, ghi nối từng dòng vào CSV (flush ngay)."""
    warnings.filterwarnings("ignore")
    out.parent.mkdir(parents=True, exist_ok=True)
    da_co, cot = set(), None
    if out.exists() and out.stat().st_size > 0:
        with out.open(encoding="utf-8", newline="") as f:
            rd = csv.DictReader(f)
            cot = rd.fieldnames
            da_co = {tuple(row[k] for k in KHOA) for row in rd}
    viec = [v for v in danh_sach_viec(seeds, nhanh) if (v[0]["id"], str(v[1]), v[2], str(v[3])) not in da_co]
    print(f"[arb_von] {len(da_co)} lượt đã có, còn {len(viec)} lượt → {out}")
    t0 = time.time()
    with out.open("a", encoding="utf-8", newline="") as f:
        w = None
        for i, (vu, b, vt, sd) in enumerate(viec):
            r = dong_voi_cfg(vu, "khong", vt, sd, {"arb_budget": b}, BANG)
            r["arb_budget"] = b
            if w is None:
                cot = cot or list(r)
                w = csv.DictWriter(f, fieldnames=cot, extrasaction="ignore")
                if f.tell() == 0:
                    w.writeheader()
            w.writerow(r)
            f.flush()
            if (i + 1) % 100 == 0 or i == len(viec) - 1:
                da = time.time() - t0
                print(f"{i + 1}/{len(viec)} · {da:.0f}s · còn ≈ {da / (i + 1) * (len(viec) - i - 1) / 60:.1f} phút")
    print(f"Xong → {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--out", default=None)
    ap.add_argument("--nhanh", action="store_true")
    a = ap.parse_args()
    mac_dinh = "ket_qua/gd2/tomtat_arb_von.csv"
    chay(a.seeds, Path(a.out or (mac_dinh.replace(".csv", "_nhanh.csv") if a.nhanh else mac_dinh)), a.nhanh)

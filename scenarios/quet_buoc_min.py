"""Kiểm độ bền theo bước thời gian: 30 vụ RQ1 chạy lại với `buoc_con` vòng mua–bán mỗi giờ, cùng Q (phí theo `MP_BIEN_THE`).

    python -m scenarios.quet_buoc_min [--seeds 2] [--vong 1,4,12] [--nhanh]

Mỗi lượt một dòng `ket_qua/gd2/tomtat_buoc_min.csv` (ghi dần, chạy lại bỏ lượt đã có): vụ × biện pháp {khong, cap50, cap05,
warn40} × loại nạn nhân × seed × số vòng. Cùng vụ + seed thì dòng ngẫu nhiên giống nhau ở mọi số vòng, nên so theo cặp được.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
import warnings
from pathlib import Path

from scenarios.batch import FILE_TO_HOP
from scenarios.quet_gd2 import BIEN_PHAP, dong_ket_qua

BP = {k: BIEN_PHAP[k] for k in ("khong", "cap50", "cap05", "warn40")}
KHOA = ["scenario_id", "bp", "victim_type", "seed", "buoc_con"]


def chay(seeds: int, vong: list[int], out: Path, nhanh: bool = False) -> None:
    """Chạy mọi lượt còn thiếu; `nhanh`: 2 vụ × 1 seed."""
    warnings.filterwarnings("ignore")
    ds = json.loads(FILE_TO_HOP.read_text(encoding="utf-8"))
    if nhanh:
        ds, seeds = ds[:2], 1
    da_co, cot = set(), None
    if out.exists() and out.stat().st_size > 0:
        with out.open(encoding="utf-8", newline="") as f:
            rd = csv.DictReader(f)
            cot, da_co = rd.fieldnames, {tuple(row[k] for k in KHOA) for row in rd}
    viec = [(vu, bp, vt, sd, n) for n in vong for vu in ds for bp in BP for vt in ("omniscient", "adaptive") for sd in range(seeds)
            if (vu["id"], bp, vt, str(sd), str(n)) not in da_co]
    print(f"{len(da_co)} lượt đã có, còn {len(viec)} lượt → {out}", flush=True)
    t0 = time.time()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8", newline="") as f:
        w = None
        for i, (vu, bp, vt, sd, n) in enumerate(viec):
            r = dong_ket_qua(dict(vu, buoc_con=n), bp, vt, sd, None, BP)
            r["buoc_con"] = n
            if w is None:
                cot = cot or list(r)
                w = csv.DictWriter(f, fieldnames=cot, extrasaction="ignore")
                if f.tell() == 0:
                    w.writeheader()
            w.writerow(r)
            f.flush()
            if (i + 1) % 100 == 0 or i == len(viec) - 1:
                da = time.time() - t0
                print(f"{i + 1}/{len(viec)} · {da:.0f}s · còn ≈ {da / (i + 1) * (len(viec) - i - 1) / 60:.1f} phút", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--vong", default="1,4,12")
    ap.add_argument("--nhanh", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    chay(a.seeds, [int(x) for x in a.vong.split(",")], Path(a.out or ("ket_qua/gd2/tomtat_buoc_min_nhanh.csv" if a.nhanh else "ket_qua/gd2/tomtat_buoc_min.csv")), a.nhanh)

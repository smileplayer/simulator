"""Sinh mọi hình RQ1 bằng một lệnh: `python -m plots.ve_rq1 [--rq1 ket_qua/rq1] [--seed 0]`.

Đọc bảng tóm tắt đã commit trong `ket_qua/rq1/` (không cần log), chạy lại kịch bản `co_so` (≈ 0,5 s) cho timeline.
Ghi PNG vào `ket_qua/rq1/hinh/`: `timeline_co_so.png`, `hop_rv.png`, `bang4_lift.png`, `bang7_drop.png`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from plots.hinh import ve_bang4, ve_bang7, ve_hop_rv, ve_timeline
from scenarios.run import nap_config, run_frame


def main(rq1: str, seed: int) -> list[Path]:
    """Vẽ 4 hình, trả danh sách đường dẫn."""
    d = Path(rq1)
    ra = d / "hinh"
    ra.mkdir(parents=True, exist_ok=True)
    tt = pd.read_csv(d / "tomtat.csv")
    b4 = pd.read_csv(d / "bang4_lift.csv", index_col=0)
    b7 = pd.read_csv(d / "bang7_drop.csv", index_col=0)
    files = [ra / "timeline_co_so.png", ra / "hop_rv.png", ra / "bang4_lift.png", ra / "bang7_drop.png"]
    ve_timeline(run_frame(nap_config("co_so"), seed), files[0], f"Một vụ tấn công mô phỏng (kịch bản co_so, seed {seed})")
    ve_hop_rv(tt, files[1])
    ve_bang4(b4, files[2])
    ve_bang7(b7, files[3])
    return files


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rq1", default="ket_qua/rq1")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    for f in main(a.rq1, a.seed):
        print(f)

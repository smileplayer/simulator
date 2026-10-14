"""Quét GĐ2 (RQ2): 30 vụ RQ1 × biện pháp × loại victim × seed; mỗi lượt ghi ngay một dòng tóm tắt.

Biện pháp: không có; hạ trần Q còn 75% / 50% / 25%; trả trễ D = 24 / 72 / 168 bước (token0, δ = 0,995/bước).
Đánh đổi (khối lượng, thanh khoản mất đi) so bằng cặp phản thực cùng vụ + seed với dòng `bp = khong`.

Chạy: `python -m scenarios.quet_gd2 [--seeds 10] [--out ket_qua/gd2/tomtat.csv] [--nhanh]`.
Chạy lại thì bỏ qua các (vụ, bp, victim, seed) đã có trong file; không lưu log thô (quá lớn).
"""
from __future__ import annotations

import argparse
import csv
import json
import time
import warnings
from pathlib import Path

from scenarios.batch import FILE_TO_HOP, cau_hinh
from scenarios.hieu_chinh import LV_chia_LA, do_sap
from scenarios.run import run_frame

BIEN_PHAP = {
    "khong": None,
    "cap75": {"name": "cap", "ty_le": 0.75},
    "cap50": {"name": "cap", "ty_le": 0.50},
    "cap25": {"name": "cap", "ty_le": 0.25},
    "delay24": {"name": "delay", "D": 24, "don_vi": "token0", "chiet_khau": 0.995},
    "delay72": {"name": "delay", "D": 72, "don_vi": "token0", "chiet_khau": 0.995},
    "delay168": {"name": "delay", "D": 168, "don_vi": "token0", "chiet_khau": 0.995},
}
LOAI_VICTIM = ["omniscient", "adaptive"]
KHOA = ["scenario_id", "bp", "victim_type", "seed"]


def dong_ket_qua(vu: dict, bp: str, victim: str, seed: int) -> dict:
    """Chạy một lượt, trả dict phẳng: khóa + tham số vụ + summarize của B + vài chỉ số của C."""
    from metrics.report import summarize
    cfg = cau_hinh(vu)
    cfg.update(defense=BIEN_PHAP[bp], victim_type=victim)
    df = run_frame(cfg, seed)
    m = df.attrs["meta"]
    sw = df[df.kind == "swap"]
    r = {"scenario_id": vu["id"], "bp": bp, "victim_type": victim, "seed": seed,
         **{k: m[k] for k in ("L_A", "k", "sigma", "Q", "Q_eff", "bg_band", "attacker_inventory", "subsidy_form")},
         "LV_chia_LA": LV_chia_LA(df), "do_sap": do_sap(df), "subsidy_pending": m["subsidy_pending"],
         "vol_farmer": sw[sw.role == "farmer"].amount1.clip(lower=0).sum(),
         "vol_tong": sw.amount1.abs().sum()}
    r.update({k: v for k, v in summarize(df).items() if k not in r})
    return r


def chay(seeds: int, out: Path, nhanh: bool = False) -> None:
    """Chạy mọi lượt còn thiếu, ghi nối vào CSV; --nhanh: 2 vụ × mọi bp × 2 victim × 1 seed để đo giờ."""
    warnings.filterwarnings("ignore")
    ds = json.loads(FILE_TO_HOP.read_text(encoding="utf-8"))
    if nhanh:
        ds, seeds = ds[:2], 1
    out.parent.mkdir(parents=True, exist_ok=True)
    da_co, cot = set(), None
    if out.exists() and out.stat().st_size > 0:
        with out.open(encoding="utf-8", newline="") as f:
            rd = csv.DictReader(f)
            cot = rd.fieldnames
            da_co = {tuple(row[k] for k in KHOA) for row in rd}
    viec = [(vu, bp, vt, s) for vu in ds for bp in BIEN_PHAP for vt in LOAI_VICTIM for s in range(seeds)
            if (vu["id"], bp, vt, str(s)) not in da_co]
    print(f"{len(da_co)} lượt đã có, còn {len(viec)} lượt")
    t0 = time.time()
    with out.open("a", encoding="utf-8", newline="") as f:
        w = None
        for i, (vu, bp, vt, s) in enumerate(viec):
            r = dong_ket_qua(vu, bp, vt, s)
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
    ap.add_argument("--out", default="ket_qua/gd2/tomtat.csv")
    ap.add_argument("--nhanh", action="store_true")
    a = ap.parse_args()
    chay(a.seeds, Path(a.out), a.nhanh)

"""Quét nhiều nạn nhân (tuần 11/11): 30 vụ RQ1 × n_victims ∈ {1, 2, 4, 8} × 2 loại victim × biện pháp × seed.

Mỗi lượt một dòng tóm tắt (cùng cột với `scenarios.quet_gd2.dong_ket_qua`, thêm `n_victims_cfg`, `victim_delay`,
`loi_them_tong` = dc_excess + dc_farm_pnl, `L_victim_tong` = tổng L nạn nhân trước khi rút tường). Chỉ số nạn nhân
(`victim_loss_full`, `victim_net`, `n_victims`) cộng mọi `victim:k` (metrics.pnl.victim_loss), phản thực bán thẳng
bỏ mọi `victim:*` (quet_gd2.phat_lai_ban_thang).

Các nạn nhân vào lần lượt cách nhau `victim_delay` bước; để mọi nạn nhân vào kịp trước khi rút tường (t_0), mặc định
`victim_delay = 30 // n_victims` (n = 1 giữ 30 như cũ; n = 8 → 3), nên nạn nhân cuối luôn vào ở t_m + 30.

Chạy: `python -m scenarios.quet_nhieu_nan_nhan [--seeds 10] [--nhanh] [--out ...]` →
`ket_qua/gd2/tomtat_nhieu_nn.csv`; chạy lại thì bỏ các lượt đã có.
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

N_NAN_NHAN = [1, 2, 4, 8]
BIEN_PHAP_NN = {k: quet_gd2.BIEN_PHAP[k] for k in ("khong", "cap50", "cap05", "warn15", "warn40", "dyncap")}
LOAI_VICTIM = quet_gd2.LOAI_VICTIM
KHOA = ["scenario_id", "n_victims_cfg", "bp", "victim_type", "seed"]


def do_tre_vao(n: int) -> int:
    """Số bước giữa hai nạn nhân liên tiếp: 30 // n (≥ 1), để nạn nhân cuối vào ở t_m + 30 (bước)."""
    return max(1, 30 // n)


def dong_voi_cfg(vu: dict, bp: str, victim: str, seed: int, extra: dict, bang: dict) -> dict:
    """Chạy một lượt như `quet_gd2.dong_ket_qua` nhưng ghi đè config bằng `extra` (n_victims, victim_delay, arb_budget…).

    Thêm cột `loi_them_tong` (token1), `L_victim_tong` (đơn vị L), `arb_da_chi` (token1 arbitrageur đã bỏ ra mua token0). Trả dict phẳng."""
    goc, goc_run, chi = quet_gd2.cau_hinh, quet_gd2.run_frame, []

    def run_ghi(cfg, sd, *a, **k):
        df = goc_run(cfg, sd, *a, **k)
        chi.append(float(df.attrs["meta"]["arb_da_chi"]))
        return df

    quet_gd2.cau_hinh = lambda v: {**goc(v), **extra}
    quet_gd2.run_frame = run_ghi
    try:
        r = quet_gd2.dong_ket_qua(vu, bp, victim, seed, None, bang)
    finally:
        quet_gd2.cau_hinh, quet_gd2.run_frame = goc, goc_run
    r["arb_da_chi"] = chi[-1]
    r["loi_them_tong"] = r["dc_excess"] + r["dc_farm_pnl"]
    r["L_victim_tong"] = r["LV_chia_LA"] * r["L_A"]
    return r


def danh_sach_viec(seeds: int, nhanh: bool = False) -> list[tuple]:
    """Mọi lượt (vu, n, bp, victim, seed); --nhanh: 2 vụ đầu × 2 seed."""
    ds = json.loads(FILE_TO_HOP.read_text(encoding="utf-8"))
    if nhanh:
        ds, seeds = ds[:2], 2
    return [(vu, n, bp, vt, sd) for vu in ds for n in N_NAN_NHAN for bp in BIEN_PHAP_NN
            for vt in LOAI_VICTIM for sd in range(seeds)]


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
    viec = [v for v in danh_sach_viec(seeds, nhanh) if (v[0]["id"], str(v[1]), v[2], v[3], str(v[4])) not in da_co]
    print(f"[nhieu_nn] {len(da_co)} lượt đã có, còn {len(viec)} lượt → {out}")
    t0 = time.time()
    with out.open("a", encoding="utf-8", newline="") as f:
        w = None
        for i, (vu, n, bp, vt, sd) in enumerate(viec):
            r = dong_voi_cfg(vu, bp, vt, sd, {"n_victims": n, "victim_delay": do_tre_vao(n)}, BIEN_PHAP_NN)
            r["n_victims_cfg"], r["victim_delay"] = n, do_tre_vao(n)
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
    mac_dinh = "ket_qua/gd2/tomtat_nhieu_nn.csv"
    chay(a.seeds, Path(a.out or (mac_dinh.replace(".csv", "_nhanh.csv") if a.nhanh else mac_dinh)), a.nhanh)

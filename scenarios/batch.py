"""Bộ tổ hợp kịch bản RQ1 (~30 vụ, đối chiếu 29 vụ của bài gốc) và bộ chạy nhiều seed ghi dần ra đĩa.

Tổ hợp = mảng trực giao L27 (6 yếu tố × 3 mức: L_A, k, σ, Q, bg_band, kho attacker; mọi cặp mức của hai yếu tố bất kỳ
xuất hiện đều 3 lần) + 3 vụ trợ cấp dạng log. `k` đặt c_V = k·f·V/L_A với V = n_farmers·Q, k ∈ [0,64; 1)
nên L_V*/L_A = 1/√k − 1 ∈ (0; 0,25] — tường chiếm ≥ 80% như 25/29 vụ bài gốc.

Chạy: `python -m scenarios.batch [--seeds 5] [--out ket_qua/rq1_tohop] [--nhanh]`.
Mỗi (vụ, seed) ghi `<id>_s<seed>.csv` (log) + `.meta.json`; chạy lại thì bỏ qua file đã có.
"""
from __future__ import annotations

import argparse
import itertools
import json
import time
from pathlib import Path

import pandas as pd

from scenarios.run import THU_MUC_CONFIG, nap_config, run_frame

MUC = {
    "L_A": [2e8, 4e8, 8e8],
    "k": [0.64, 0.80, 0.95],
    "sigma": [0.005, 0.01, 0.02],
    "Q": [12000, 24000, 48000],
    "bg_band": [0.15, 0.25, 0.40],
    "attacker_inventory": [15000, 25000, 40000],
}
FILE_TO_HOP = THU_MUC_CONFIG / "rq1_tohop.json"


def mang_L27() -> list[tuple[int, ...]]:
    """27 dòng × 6 cột mức {0,1,2}: cột = a, b, c, a+b+c, a+2b, b+2c (mod 3) — từng cặp cột độc lập tuyến
    tính trên GF(3) nên mảng trực giao độ mạnh 2."""
    return [(a, b, c, (a + b + c) % 3, (a + 2 * b) % 3, (b + 2 * c) % 3)
            for a, b, c in itertools.product(range(3), repeat=3)]


def ap_k(cfg: dict) -> dict:
    """Đổi `k` thành c_V = k·f·V/L_A (V = n_farmers·Q, token1 mỗi cửa sổ); trả config mới."""
    cfg = dict(cfg)
    k = cfg.pop("k")
    cfg["c_V"] = k * cfg["fee"] * cfg["n_farmers"] * cfg["Q"] / cfg["L_A"]
    cfg["k"] = k
    return cfg


def to_hop_rq1(muc: dict | None = None, tien_to: str = "") -> list[dict]:
    """30 vụ: {id, các tham số ghi đè lên co_so}. 27 vụ L27 trợ cấp tuyến tính + 3 vụ dạng log.
    `muc`: bảng mức (mặc định MUC); `tien_to`: thêm trước mã vụ (vd "KN_" cho vùng k nhỏ GĐ2)."""
    muc = MUC if muc is None else muc
    ten = list(muc)
    vu = []
    for i, dong in enumerate(mang_L27()):
        vu.append({"id": f"{tien_to}L27_{i:02d}", "subsidy_form": "linear",
                   **{t: muc[t][m] for t, m in zip(ten, dong)}})
    for j, m in enumerate([1, 0, 2]):                    # log ở mức giữa, thấp, cao (cùng mức mọi yếu tố)
        vu.append({"id": f"{tien_to}LOG_{j}", "subsidy_form": "log", **{t: muc[t][m] for t in ten}})
    return vu


def cau_hinh(vu: dict, goc: dict | None = None) -> dict:
    """Config đầy đủ của một vụ = co_so + ghi đè, đã đổi k → c_V."""
    cfg = dict(goc if goc is not None else nap_config("co_so"))
    cfg.update({k: v for k, v in vu.items() if k != "id"})
    cfg["scenario_id"] = vu["id"]
    return ap_k(cfg)


def chay(seeds: int, out: Path, nhanh: bool = False) -> None:
    """Chạy mọi (vụ, seed), ghi dần; bỏ qua cặp đã có file. --nhanh: 3 vụ × 1 seed để đo giờ."""
    out.mkdir(parents=True, exist_ok=True)
    ds = json.loads(FILE_TO_HOP.read_text(encoding="utf-8"))
    if nhanh:
        ds, seeds = ds[:3], 1
    viec = [(vu, s) for vu in ds for s in range(seeds)]
    t0, lam = time.time(), 0
    for i, (vu, s) in enumerate(viec):
        p = out / f"{vu['id']}_s{s}.csv"
        if p.exists():
            continue
        df = run_frame(cau_hinh(vu), s)
        df.to_csv(p, index=False)
        p.with_suffix(".meta.json").write_text(json.dumps(df.attrs["meta"], ensure_ascii=False,
                                                         default=lambda o: o.tolist()), encoding="utf-8")
        lam += 1
        if lam % 10 == 0 or i == len(viec) - 1:
            print(f"{i + 1}/{len(viec)} xong, {time.time() - t0:.0f}s")
    print(f"Xong {lam} lượt mới trong {time.time() - t0:.1f}s → {out}")


def doc_ket_qua(out: str | Path) -> list[pd.DataFrame]:
    """Đọc lại mọi log trong thư mục, gắn meta vào df.attrs["meta"] (cho metrics.validate_rq1)."""
    dfs = []
    for p in sorted(Path(out).glob("*_s*.csv")):
        df = pd.read_csv(p)
        for c in ("position_id", "tick_lower", "tick_upper"):
            df[c] = df[c].astype("Int64")
        df.attrs["meta"] = json.loads(p.with_suffix(".meta.json").read_text(encoding="utf-8"))
        dfs.append(df)
    return dfs


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--out", default="ket_qua/rq1_tohop")
    ap.add_argument("--nhanh", action="store_true")
    ap.add_argument("--tao", action="store_true", help="ghi lại scenarios/configs/rq1_tohop.json")
    a = ap.parse_args()
    if a.tao or not FILE_TO_HOP.exists():
        FILE_TO_HOP.write_text(json.dumps(to_hop_rq1(), ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"đã ghi {FILE_TO_HOP}")
    chay(a.seeds, Path(a.out), a.nhanh)

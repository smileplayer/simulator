"""Quét GĐ2 (RQ2): 30 vụ RQ1 × biện pháp × loại victim × seed; mỗi lượt ghi ngay một dòng tóm tắt.

Biện pháp: không có; hạ trần Q còn 75% / 50% / 25%; trả trễ D = 24 / 72 / 168 bước (token0, δ = 0,995/bước).
Đánh đổi (khối lượng, thanh khoản mất đi) so bằng cặp phản thực cùng vụ + seed với dòng `bp = khong`.

Chế độ `--farm` (CH-6): kẻ tấn công cũng là farmer, phần khối lượng farmer danh nghĩa s ∈ {0; 0,3; 0,6}
(`attacker_farm_share`) × {khong, delay24/72/168, claw24/72/168} (claw = delay + thu hồi khi sập ≥ 10%, chỉ owner
có vị thế LP; với s = 0 không có owner nào như vậy nên bỏ) → `ket_qua/gd2/tomtat_farm.csv`.

Chạy: `python -m scenarios.quet_gd2 [--seeds 10] [--out ket_qua/gd2/tomtat.csv] [--nhanh] [--farm]`.
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
BIEN_PHAP_FARM = {
    **{k: BIEN_PHAP[k] for k in ("khong", "delay24", "delay72", "delay168")},
    **{f"claw{D}": dict(BIEN_PHAP[f"delay{D}"], clawback=0.10) for D in (24, 72, 168)},
}
FARM_SHARE = [0.0, 0.3, 0.6]
LOAI_VICTIM = ["omniscient", "adaptive"]
KHOA = ["scenario_id", "bp", "victim_type", "seed"]
KHOA_FARM = ["scenario_id", "farm_share", "bp", "victim_type", "seed"]


def dong_ket_qua(vu: dict, bp: str, victim: str, seed: int, farm_share: float | None = None) -> dict:
    """Chạy một lượt, trả dict phẳng: khóa + tham số vụ + summarize của B + vài chỉ số của C.

    `farm_share` khác None → chế độ CH-6: thêm cột farm của kẻ tấn công (token1): `vol_farm_att` (khối lượng mua),
    `farm_share_thuc` (phần thực trong khối lượng farmer), `sub_att` (thưởng đã nhận), `chi_phi_farm_att`
    (Σ v − P_e·x của các lệnh mua, P_e ở dòng `step` cùng bước), `sub_att_treo` (thưởng của kẻ tấn công chưa
    tới hạn khi hết kịch bản, theo giá cuối), `subsidy_clawed`."""
    from metrics.report import summarize
    cfg = cau_hinh(vu)
    bang = BIEN_PHAP if farm_share is None else BIEN_PHAP_FARM
    cfg.update(defense=bang[bp], victim_type=victim, attacker_farm_share=farm_share or 0.0)
    df = run_frame(cfg, seed)
    m = df.attrs["meta"]
    sw = df[df.kind == "swap"]
    r = {"scenario_id": vu["id"], **({} if farm_share is None else {"farm_share": farm_share}),
         "bp": bp, "victim_type": victim, "seed": seed,
         **{k: m[k] for k in ("L_A", "k", "sigma", "Q", "Q_eff", "bg_band", "attacker_inventory", "subsidy_form")},
         "LV_chia_LA": LV_chia_LA(df), "do_sap": do_sap(df), "subsidy_pending": m["subsidy_pending"],
         "vol_farmer": sw[sw.role == "farmer"].amount1.clip(lower=0).sum(),
         "vol_tong": sw.amount1.abs().sum()}
    if farm_share is not None:
        p_e = df[df.kind == "step"].set_index("t").external_price
        mua = sw[(sw.owner == "attacker:0") & (sw.amount1 > 0)]
        sub = df[df.kind == "subsidy"]
        r.update(vol_farm_att=mua.amount1.sum(),
                 farm_share_thuc=mua.amount1.sum() / max(mua.amount1.sum() + r["vol_farmer"], 1e-12),
                 sub_att=sub[sub.owner == "attacker:0"].amount1.sum(),
                 chi_phi_farm_att=float((mua.amount1 + mua.amount0 * mua.t.map(p_e)).sum()),
                 sub_att_treo=m["subsidy_pending_attacker"], subsidy_clawed=m["subsidy_clawed"])
    r.update({k: v for k, v in summarize(df).items() if k not in r})
    return r


def chay(seeds: int, out: Path, nhanh: bool = False, farm: bool = False) -> None:
    """Chạy mọi lượt còn thiếu, ghi nối vào CSV; --nhanh: 2 vụ × mọi bp × 2 victim × 1 seed để đo giờ.
    `farm`: chế độ CH-6 (thêm chiều `farm_share`, bộ biện pháp `BIEN_PHAP_FARM`)."""
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
            da_co = {tuple(row[k] for k in (KHOA_FARM if farm else KHOA)) for row in rd}
    if farm:
        viec = [(vu, bp, vt, sd, fs) for vu in ds for fs in FARM_SHARE for bp in BIEN_PHAP_FARM
                for vt in LOAI_VICTIM for sd in range(seeds)
                if not (fs == 0 and bp.startswith("claw")) and (vu["id"], str(fs), bp, vt, str(sd)) not in da_co]
    else:
        viec = [(vu, bp, vt, sd, None) for vu in ds for bp in BIEN_PHAP for vt in LOAI_VICTIM
                for sd in range(seeds) if (vu["id"], bp, vt, str(sd)) not in da_co]
    print(f"{len(da_co)} lượt đã có, còn {len(viec)} lượt")
    t0 = time.time()
    with out.open("a", encoding="utf-8", newline="") as f:
        w = None
        for i, (vu, bp, vt, sd, fs) in enumerate(viec):
            r = dong_ket_qua(vu, bp, vt, sd, fs)
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
    ap.add_argument("--farm", action="store_true", help="CH-6: kẻ tấn công cũng là farmer → tomtat_farm.csv")
    a = ap.parse_args()
    out = a.out or ("ket_qua/gd2/tomtat_farm.csv" if a.farm else "ket_qua/gd2/tomtat.csv")
    chay(a.seeds, Path(out), a.nhanh, a.farm)

"""Quét GĐ3 (RQ3): phân bổ phí theo độ rộng φ(w) = min(1, (w/w₀)^α) × vụ × loại victim × seed.

Lưới φ: α = 0 (pro-rata, một dòng, w₀ = 0) và α ∈ {0,5; 1; 1,5; 2; 3} × w₀ ∈ {10, 50, 200} → 16 mức φ.
Vụ (6): L27_10, L27_16, L27_22 của bộ RQ1 (k = 0,64 / 0,95 / 0,80) và cùng ba vụ ở vùng k nhỏ (KN_: k = 0,10 /
0,45 / 0,25; các yếu tố khác giữ nguyên) — trải k hai phía ngưỡng giải tích k = 1/4 (`agents.do_rong.ty_le_von`),
độ sập sâu / vừa / nông (≈ −50% / −18% / −8% ở GĐ2), L_A 4e8 / 4e8 / 8e8.

Mọi lượt (kể cả α = 0) dùng cùng mô hình GĐ3: chi phí victim **theo vốn** `c_V_von` = c_V·ℓ(1) (ℓ(1) = L trên mỗi token1 vốn
ở dải một tick tại giá đầu, nên α = 0 trùng Lemma 4 của RQ1), victim tự chọn w* = argmax φ(w)·ℓ(w) trên lưới
{1, 2, 5, 10, 20, 50, 100, 200} (biết φ — luật công khai), dải **căn giữa** quanh tick tường. Hai LP lành mạnh vốn 1.000
token1 trong pha bình thường [0, t_m − 1): `lp:0` tự chọn w theo cùng luật, `lp:1` dải cố định 10 tick.

Cột chính: `w_victim`, `von_victim` (token1, theo giá ngay trước khi rút tường), `L_victim_tuong` (L của victim trong
tick tường), `phan_duong_sap` (phần vốn victim bị quét qua: token1 đổi thành token0 khi giá đi từ giá trước rút xuống
đáy cú xả / vốn), `vl_*` (thiệt hại victim theo `metrics.pnl.victim_loss` với tập victim theo địa chỉ thật — đúng cả
khi dải rộng), `vl_lai_tien` (giá trị nhận lại + phí − giá trị nạp theo giá lúc nạp), `dc_*` lợi nhuận kẻ tấn công
theo địa chỉ thật + phản thực phát lại (`dc_excess`), `lp{0,1}_*` (w, phí/vốn mỗi cửa sổ, tỷ lệ bước trong dải, L tại
giá TB, trượt giá TB của lệnh mua 1.000 token1), `vol_farmer`, `vol_tong`, `do_sap`.

Chạy: `python -m scenarios.quet_gd3 [--seeds 10] [--out ket_qua/gd3/tomtat.csv] [--nhanh]` (ghi dần, bỏ lượt đã có).
"""
from __future__ import annotations

import argparse
import csv
import time
import warnings
from pathlib import Path

from agents.do_rong import l_tren_von
from engine import amounts_for_liquidity, sqrt_price_at_tick
from scenarios.batch import MUC, cau_hinh, to_hop_rq1
from scenarios.hieu_chinh import LV_chia_LA, do_sap
from scenarios.quet_gd2 import K_NHO, LOAI_VICTIM, loi_nhuan_dia_chi
from scenarios.run import run_frame

NAN = float("nan")
ALPHA = [0.5, 1.0, 1.5, 2.0, 3.0]
W0 = [10, 50, 200]
LUOI_PHI = [(0.0, 0)] + [(a, w0) for a in ALPHA for w0 in W0]
VU_CHON = ["L27_10", "L27_16", "L27_22"]
LP_LANH_MANH = [{"w": "tu_chon", "von": 1000.0}, {"w": 10, "von": 1000.0}]
KHOA = ["scenario_id", "alpha", "w0", "victim_type", "seed"]


def to_hop_gd3() -> list[dict]:
    """6 vụ: VU_CHON của bộ RQ1 + cùng các vụ ở vùng k nhỏ (tiền tố KN_)."""
    rq1 = {v["id"]: v for v in to_hop_rq1()}
    kn = {v["id"]: v for v in to_hop_rq1({**MUC, "k": K_NHO}, tien_to="KN_")}
    return [rq1[i] for i in VU_CHON] + [kn["KN_" + i] for i in VU_CHON]


def cau_hinh_gd3(vu: dict, alpha: float, w0: int, victim: str) -> dict:
    """Config một lượt GĐ3: vụ + φ + victim tự chọn độ rộng, căn giữa, chi phí theo vốn + 2 LP lành mạnh."""
    cfg = cau_hinh(vu)
    z0 = sqrt_price_at_tick(0) * 1.0001 ** 0.25
    cfg.update(phi=None if alpha == 0 else {"alpha": alpha, "w0": w0}, victim_type=victim, w_victim="tu_chon",
               vi_tri_victim="giua", c_V_von=cfg["c_V"] * l_tren_von(1, z0, 0), lp_lanh_manh=LP_LANH_MANH)
    return cfg


def chi_so_victim(df) -> dict:
    """Vốn, L trong tick tường, phần vốn trên đường sập, thiệt hại (token1) của mọi `victim:*` theo địa chỉ thật."""
    from metrics.pnl import victim_loss
    from metrics.phases import phases
    m = df.attrs["meta"]
    t_rut, wt = m["t_rut"], m["wall_tick"]
    r = dict(von_victim=0.0, L_victim_tuong=0.0, phan_duong_sap=NAN, vl_loss_full=0.0, vl_E_full=0.0,
             vl_E_nonalpha=0.0, vl_fees=0.0, vl_von_nap=0.0, vl_lai_tien=0.0)
    v = df[(df.role == "victim") & df.kind.isin(["mint", "burn"])]
    if t_rut is None or v.empty:
        return r
    step = df[df.kind == "step"].set_index("t").sqrt_price_after
    z_truoc = float(step.loc[t_rut - 1])
    xa = df[(df.t >= t_rut) & (df.t < t_rut + m["dump_steps"])]
    z_day = float(min(xa.sqrt_price_after.min(), z_truoc))
    truoc = v[v.t < t_rut]
    von = quet = L_tuong = 0.0
    for pid, g in truoc.groupby("position_id"):
        L = float((g.liquidity * g.kind.map({"mint": 1.0, "burn": -1.0})).sum())
        if L <= 0:
            continue
        lo, hi = int(g.tick_lower.iloc[0]), int(g.tick_upper.iloc[0])
        za, zb = sqrt_price_at_tick(lo), sqrt_price_at_tick(hi)
        a0, a1 = amounts_for_liquidity(z_truoc, za, zb, L)
        von += a0 * z_truoc ** 2 + a1
        quet += L * max(0.0, min(zb, z_truoc) - max(za, z_day))     # token1 bị đổi khi giá quét qua
        if lo <= wt < hi:
            L_tuong += L
    r.update(von_victim=von, L_victim_tuong=L_tuong, phan_duong_sap=quet / von if von > 0 else NAN)
    # lãi theo tiền mặt (token1) ở cuối kịch bản: nhận lại (burn + phần còn kẹt + phí đã collect) theo giá cuối
    # − giá trị nạp theo giá lúc nạp; không cần mốc t_b nên có cả khi giá không sập
    z_cuoi = float(step.iloc[-1])
    mint = v[v.kind == "mint"]
    nap = float((mint.amount0 * mint.sqrt_price_after ** 2 + mint.amount1).sum())
    burn = v[v.kind == "burn"]
    nhan = float(-(burn.amount0 * z_cuoi ** 2 + burn.amount1).sum())
    for pid, g in v.groupby("position_id"):
        L = float((g.liquidity * g.kind.map({"mint": 1.0, "burn": -1.0})).sum())
        if L > 1e-9 * float(g.liquidity.max()):
            a0, a1 = amounts_for_liquidity(z_cuoi, sqrt_price_at_tick(int(g.tick_lower.iloc[0])),
                                           sqrt_price_at_tick(int(g.tick_upper.iloc[0])), L)
            nhan += a0 * z_cuoi ** 2 + a1
    col = df[(df.kind == "collect") & (df.role == "victim")]
    phi = float((col.fee1 + col.fee0 * z_cuoi ** 2).sum())
    r.update(vl_von_nap=nap, vl_fees=phi, vl_lai_tien=nhan + phi - nap)
    try:                                              # thiệt hại theo B (cần mốc t_b: giá sập ≥ 10%)
        tg = victim_loss(df, phases(df), victims=set(v.owner)).loc["TOTAL"]
        r.update(vl_loss_full=float(tg.loss_full), vl_E_full=float(tg.E_full), vl_E_nonalpha=float(tg.E_nonalpha))
    except ValueError:
        r.update(vl_loss_full=NAN, vl_E_full=NAN, vl_E_nonalpha=NAN)
    return r


def dong_ket_qua(vu: dict, alpha: float, w0: int, victim: str, seed: int) -> dict:
    """Chạy một lượt GĐ3, trả dict phẳng: khóa + tham số + chỉ số victim, kẻ tấn công, LP lành mạnh, khối lượng."""
    cfg = cau_hinh_gd3(vu, alpha, w0, victim)
    df = run_frame(cfg, seed)
    m = df.attrs["meta"]
    sw = df[df.kind == "swap"]
    r = {"scenario_id": vu["id"], "alpha": alpha, "w0": w0, "victim_type": victim, "seed": seed,
         **{k: m[k] for k in ("L_A", "k", "c_V", "c_V_von", "sigma", "Q", "bg_band", "attacker_inventory")},
         "w_victim": m["w_victim_chon"], "LV_chia_LA": LV_chia_LA(df), "t_rut": m["t_rut"],
         "do_sap": do_sap(df) if m["t_rut"] is not None else NAN,
         "vol_farmer": sw[sw.role == "farmer"].amount1.clip(lower=0).sum(), "vol_tong": sw.amount1.abs().sum()}
    r.update(chi_so_victim(df))
    r.update(loi_nhuan_dia_chi(df))
    for k, d in enumerate(m["lp_lanh_manh_kq"]):
        r.update({f"lp{k}_{c}": d[c] for c in ("w", "phi_tren_von", "trong_dai", "L_gia", "truot")})
    return r


def danh_sach_viec(seeds: int, nhanh: bool = False) -> list[tuple]:
    """Mọi lượt (vu, alpha, w0, victim, seed). --nhanh: 2 vụ (L27_10, KN_L27_10) × φ {0; (2, 50)} × 2 victim × 1 seed."""
    ds, phi = to_hop_gd3(), LUOI_PHI
    if nhanh:
        ds, phi, seeds = [ds[0], ds[3]], [(0.0, 0), (2.0, 50)], 1
    return [(vu, a, w0, vt, sd) for vu in ds for a, w0 in phi for vt in LOAI_VICTIM for sd in range(seeds)]


def chay(seeds: int, out: Path, nhanh: bool = False) -> None:
    """Chạy mọi lượt còn thiếu, ghi nối vào CSV (mỗi lượt một dòng, flush ngay)."""
    warnings.filterwarnings("ignore")
    out.parent.mkdir(parents=True, exist_ok=True)
    da_co, cot = set(), None
    if out.exists() and out.stat().st_size > 0:
        with out.open(encoding="utf-8", newline="") as f:
            rd = csv.DictReader(f)
            cot = rd.fieldnames
            da_co = {tuple(row[k] for k in KHOA) for row in rd}
    ma = lambda vu, a, w0, vt, sd: (vu["id"], str(a), str(w0), vt, str(sd))
    viec = [v for v in danh_sach_viec(seeds, nhanh) if ma(*v) not in da_co]
    print(f"[gd3] {len(da_co)} lượt đã có, còn {len(viec)} lượt → {out}")
    t0 = time.time()
    with out.open("a", encoding="utf-8", newline="") as f:
        w = None
        for i, v in enumerate(viec):
            r = dong_ket_qua(*v)
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
    out = a.out or ("ket_qua/gd3/tomtat_nhanh.csv" if a.nhanh else "ket_qua/gd3/tomtat.csv")
    chay(a.seeds, Path(out), a.nhanh)

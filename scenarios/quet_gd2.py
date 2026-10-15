"""Quét GĐ2 (RQ2): vụ × biện pháp × loại victim × seed; mỗi lượt ghi ngay một dòng tóm tắt.

Biện pháp (`BIEN_PHAP`): không có; hạ trần Q còn 75/50/25% (§7.1); trả trễ D = 24/72/168 bước (token0,
δ = 0,995/bước, §7.2); cảnh báo rủi ro `warn15/20/40` = c_V của victim × 1,5/2/4 (§7.3); trần động `dyncap`
= Q → 0,25·Q trong H = 24 bước sau khi L tick chứa giá > 3 × trung vị 24 bước bình thường (§7.4,
`defenses/tran_dong.py`). Đánh đổi so bằng cặp phản thực cùng vụ + seed với dòng `bp = khong`.

Ba chế độ (v3, 15/10 — thêm cột lợi nhuận theo **địa chỉ thật** `dc_*`, có cả khi giá không sập):
- mặc định: 30 vụ RQ1 × 16 bp (cap90/75/60/50/25/15/10/05 thêm lưới mịn) × 2 victim × seed
  → `ket_qua/gd2/tomtat_v3.csv`;
- `--farm` (CH-6): kẻ tấn công cũng farm, s ∈ {0; 0,3; 0,6} × {khong, delay24/72/168, claw24/72/168}
  (claw với s = 0 bỏ) → `ket_qua/gd2/tomtat_farm_v3.csv`;
- `--k_nho`: vùng victim lớn — 30 vụ cùng mảng L27 nhưng k ∈ {0,10; 0,25; 0,45} (L_V*/L_A = 1/√k − 1 ≈
  2,16; 1,0; 0,49), s = 0,3 cố định, bp {khong, cap50, cap25, cap10, delay72, claw72, warn15/20/40, dyncap}
  → `ket_qua/gd2/tomtat_knho_v3.csv`;
- `--luoi`: lưới σ ∈ {0,0025 … 0,04} × Q ∈ {6k … 96k} quanh co_so (giữ c_V của co_so), bp {khong, cap50}
  → `ket_qua/gd2/tomtat_luoi_v3.csv`.

Chạy: `python -m scenarios.quet_gd2 [--seeds 10] [--out ...] [--nhanh] [--farm | --k_nho | --luoi]`.
Chạy lại thì bỏ qua các lượt đã có trong file; không lưu log thô (quá lớn).
"""
from __future__ import annotations

import argparse
import csv
import json
import time
import warnings
from pathlib import Path

from scenarios.batch import FILE_TO_HOP, MUC, cau_hinh, to_hop_rq1
from scenarios.hieu_chinh import LV_chia_LA, do_sap
from scenarios.run import run_frame

NAN = float("nan")
DYNCAP = {"name": "dyncap", "ty_le": 0.25, "m": 3.0, "N": 24, "H": 24}
BIEN_PHAP = {
    "khong": None,
    **{f"cap{round(r * 100):02d}": {"name": "cap", "ty_le": r} for r in (0.90, 0.75, 0.60, 0.50, 0.25, 0.15, 0.10, 0.05)},
    "delay24": {"name": "delay", "D": 24, "don_vi": "token0", "chiet_khau": 0.995},
    "delay72": {"name": "delay", "D": 72, "don_vi": "token0", "chiet_khau": 0.995},
    "delay168": {"name": "delay", "D": 168, "don_vi": "token0", "chiet_khau": 0.995},
    "warn15": {"name": "warn", "he_so": 1.5},
    "warn20": {"name": "warn", "he_so": 2.0},
    "warn40": {"name": "warn", "he_so": 4.0},
    "dyncap": DYNCAP,
}
BIEN_PHAP_FARM = {
    **{k: BIEN_PHAP[k] for k in ("khong", "delay24", "delay72", "delay168")},
    **{f"claw{D}": dict(BIEN_PHAP[f"delay{D}"], clawback=0.10) for D in (24, 72, 168)},
}
BIEN_PHAP_KNHO = {
    **{k: BIEN_PHAP[k] for k in ("khong", "cap50", "cap25", "cap10", "delay72")},
    "claw72": BIEN_PHAP_FARM["claw72"],
    **{k: BIEN_PHAP[k] for k in ("warn15", "warn20", "warn40", "dyncap")},
}
BIEN_PHAP_LUOI = {k: BIEN_PHAP[k] for k in ("khong", "cap50")}
SIGMA_LUOI = [0.0025, 0.005, 0.01, 0.02, 0.04]
Q_LUOI = [6000, 12000, 24000, 48000, 96000]
FARM_SHARE = [0.0, 0.3, 0.6]
FARM_SHARE_KNHO = 0.3
K_NHO = [0.10, 0.25, 0.45]
LOAI_VICTIM = ["omniscient", "adaptive"]
KHOA = ["scenario_id", "bp", "victim_type", "seed"]
KHOA_FARM = ["scenario_id", "farm_share", "bp", "victim_type", "seed"]


def to_hop_k_nho() -> list[dict]:
    """30 vụ vùng k nhỏ: mảng L27 + 3 vụ log như RQ1, chỉ thay mức k bằng K_NHO; mã vụ tiền tố `KN_`."""
    return to_hop_rq1({**MUC, "k": K_NHO}, tien_to="KN_")


def phat_lai_ban_thang(df, owner: str = "attacker:0", c_A: float | None = None) -> dict:
    """Phản thực "bán thẳng kho" bằng phát lại log (token1): dựng bể ngay trước dòng burn tường đầu tiên của
    `owner` (mọi vị thế còn mở lúc đó, BỎ vị thế của `attacker:*` và `victim:*`), rồi phát lại tuần tự mọi dòng sau
    đó — mint/burn của owner khác (trừ attacker/victim), mọi swap với đúng chiều và `amount_in` của log (gồm cú xả
    của `owner`, lệnh nền, farmer, arb). Swap xả của `owner` giữ giới hạn z̄ = √(c_A/(1−f)) như tác nhân thật.

    Trả `ban_thang` = token1 `owner` nhận từ các swap xả trong bể phát lại + phần chưa bán được × c_A,
    `x_sold`, `x_left`, `hut` = số swap (không kể cú xả chạm z̄) khớp thiếu do hết thanh khoản. Không có victim
    → bể phát lại trùng bể thật → ban_thang = paper. Không có burn tường → None."""
    import math

    import numpy as np

    from engine import Pool
    meta = df.attrs["meta"]
    fee = float(meta["fee"])
    c_A = float(meta["c_A"]) if c_A is None else c_A
    ev = df[df.kind.isin(["mint", "burn", "swap"])].sort_values(["t", "seq"]).reset_index(drop=True)
    vt = ev.index[(ev.kind == "burn") & (ev.owner == owner)]
    if not len(vt) or vt[0] == 0:
        return None
    i = int(vt[0])
    bo = ev.owner.astype(str).str.startswith(("attacker:", "victim:"))
    pool = Pool(fee, float(ev.sqrt_price_after.iloc[i - 1]))
    truoc = ev.iloc[:i]
    mb = truoc[(truoc.kind != "swap") & ~bo.iloc[:i]].copy()
    mb["dL"] = np.where(mb.kind == "mint", 1.0, -1.0) * mb.liquidity.astype(float)
    ma = {}
    for pid, g in mb.groupby("position_id"):
        L = float(g.dL.sum())
        if L > 1e-12 * max(1.0, float(g.liquidity.abs().max())):
            ma[pid] = pool.mint(str(g.owner.iloc[0]), int(g.tick_lower.iloc[0]), int(g.tick_upper.iloc[0]), L)[0]
    z_dung = math.sqrt(c_A / (1 - fee)) if c_A > 0 else None
    out = x_sold = x_xin = 0.0
    hut = 0
    sau = ev.iloc[i:]
    for r, la_bo in zip(sau.itertuples(index=False), bo.iloc[i:]):
        if r.kind == "swap":
            xuong = r.amount0 > 0
            v = float(r.amount0 if xuong else r.amount1)
            if v <= 0:
                continue                                  # swap chỉ nhảy khoảng trống (lượng 0)
            la_xa = r.owner == owner and xuong
            lim = z_dung if la_xa and z_dung is not None and z_dung < pool.sqrt_price else None
            if la_xa and z_dung is not None and pool.sqrt_price <= z_dung:
                x_xin += v                                # đã dưới giá vốn: không bán
                continue
            if pool.liquidity <= 0 and not la_xa:
                hut += 1
                continue
            kq = pool.swap(str(r.owner), xuong, amount_in=v, sqrt_price_limit=lim)
            if la_xa:
                out, x_sold, x_xin = out + kq.amount_out, x_sold + kq.amount_in, x_xin + v
            elif kq.amount_in < v * (1 - 1e-9):
                hut += 1
        elif la_bo:
            continue
        elif r.kind == "mint":
            ma[r.position_id] = pool.mint(str(r.owner), int(r.tick_lower), int(r.tick_upper), float(r.liquidity))[0]
        elif r.position_id in ma:                          # burn của owner khác
            L_con = next((p.liquidity for p in pool.positions() if p.id == ma[r.position_id]), 0.0)
            if L_con > 0:
                pool.burn(ma[r.position_id], min(float(r.liquidity), L_con))
    x_left = max(x_xin - x_sold, 0.0)
    return dict(ban_thang=out + x_left * c_A, x_sold=x_sold, x_left=x_left, hut=hut)


def to_hop_luoi() -> list[dict]:
    """25 ô lưới (σ, Q), mọi yếu tố khác = co_so. Giữ **c_V của co_so** (chi phí vật lý của victim không đổi theo
    luật trợ cấp) → k = c_V·L_A/(f·n·Q) = 0,75·24.000/Q đổi theo Q (Q ≤ 18k: k ≥ 1, victim toàn tri không vào;
    Q = 24k/48k/96k: k = 0,75/0,375/0,1875)."""
    co_so = json.loads((FILE_TO_HOP.parent / "co_so.json").read_text(encoding="utf-8"))
    ds = []
    for sg in SIGMA_LUOI:
        for Q in Q_LUOI:
            k = co_so["c_V"] * co_so["L_A"] / (co_so["fee"] * co_so["n_farmers"] * Q)
            ds.append({"id": f"LUOI_s{sg}_Q{Q}", "sigma": sg, "Q": Q, "k": k})
    return ds


def loi_nhuan_dia_chi(df, owner: str = "attacker:0") -> dict:
    """Lợi nhuận của địa chỉ thật `owner` (token1, cả log, không cần suy vai, có cả khi giá không sập).

    Tách lệnh farm (mua token0, `amount1 > 0`) + dòng `subsidy` ra phần farm. Phần tấn công: `dc_cash1` = token1
    ròng (mint/burn/swap bán/collect), `dc_d0` = token0 ròng, `dc_lai_tan_cong` = cash1 + d0·c_A; `dc_x_xa`,
    `dc_paper` = token0 đã bán và token1 nhận từ các swap bán. Phản thực bán thẳng = phát lại log không tường,
    không victim (`phat_lai_ban_thang`): `dc_ban_thang`, `dc_phat_lai_hut` (số swap khớp thiếu),
    **`dc_excess` = paper − ban_thang** (chỉ số chính: lợi nhuận tăng thêm nhờ victim; = 0 khi không victim);
    phụ: `dc_lai_ban_thang` = ban_thang − x_xa·c_A, `dc_loi_them` = lai_tan_cong − lai_ban_thang (gồm cả lãi/lỗ
    vị thế tường định giá theo c_A). Farm (`metrics.pnl.farm_pnl`): `dc_farm_pnl`, `dc_farm_sub`,
    `dc_farm_cost`, `dc_farm_treo` (thưởng chưa tới hạn, không cộng); `dc_lai_tong` = lai_tan_cong + farm_pnl."""
    from metrics.pnl import farm_pnl
    meta = df.attrs["meta"]
    c_A = float(meta["c_A"])
    a = df[df.owner == owner]
    la_farm = (a.kind == "swap") & (a.amount1 > 0) & (a.amount0 < 0)
    tc = a[~la_farm & a.kind.isin(["mint", "burn", "swap", "collect"])]
    cash1 = float(-tc.amount1.sum() + tc.fee1.where(tc.kind == "collect", 0).sum())
    d0 = float(-tc.amount0.sum() + tc.fee0.where(tc.kind == "collect", 0).sum())
    ban = tc[(tc.kind == "swap") & (tc.amount0 > 0)]
    x_xa, paper = float(ban.amount0.sum()), float(-ban.amount1.sum())
    fm = farm_pnl(df, owner)
    r = dict(dc_cash1=cash1, dc_d0=d0, dc_lai_tan_cong=cash1 + d0 * c_A, dc_x_xa=x_xa, dc_paper=paper,
             dc_ban_thang=NAN, dc_phat_lai_hut=NAN, dc_lai_ban_thang=NAN, dc_excess=NAN, dc_loi_them=NAN,
             dc_farm_pnl=fm["farm_pnl"], dc_farm_sub=fm["farm_subsidy"], dc_farm_cost=fm["farm_cost"],
             dc_farm_treo=float(meta.get("subsidy_pending_attacker", 0.0) or 0.0))
    r["dc_lai_tong"] = r["dc_lai_tan_cong"] + fm["farm_pnl"]
    bt = phat_lai_ban_thang(df, owner, c_A)
    if bt is not None:
        r.update(dc_ban_thang=bt["ban_thang"], dc_phat_lai_hut=bt["hut"],
                 dc_lai_ban_thang=bt["ban_thang"] - x_xa * c_A, dc_excess=paper - bt["ban_thang"])
        r["dc_loi_them"] = r["dc_lai_tan_cong"] - r["dc_lai_ban_thang"]
    return r


def dong_ket_qua(vu: dict, bp: str, victim: str, seed: int, farm_share: float | None = None,
                 bang: dict | None = None) -> dict:
    """Chạy một lượt, trả dict phẳng: khóa + tham số vụ + summarize của B + lợi nhuận theo địa chỉ + vài chỉ số của C.

    `bang`: bảng biện pháp (mặc định BIEN_PHAP, hoặc BIEN_PHAP_FARM khi có `farm_share`).
    `farm_share` khác None → thêm cột farm của kẻ tấn công (token1): `vol_farm_att` (khối lượng mua),
    `farm_share_thuc` (phần thực trong khối lượng farmer), `sub_att` (thưởng đã nhận), `chi_phi_farm_att`
    (= `dc_farm_cost`, `metrics.pnl.farm_pnl`: P_e bước t, bước có cú xả lấy P_e(t−1)), `sub_att_treo` (thưởng của kẻ tấn công chưa
    tới hạn khi hết kịch bản, theo giá cuối), `subsidy_clawed`."""
    from metrics.report import summarize
    cfg = cau_hinh(vu)
    if bang is None:
        bang = BIEN_PHAP if farm_share is None else BIEN_PHAP_FARM
    cfg.update(defense=bang[bp], victim_type=victim, attacker_farm_share=farm_share or 0.0)
    df = run_frame(cfg, seed)
    m = df.attrs["meta"]
    sw = df[df.kind == "swap"]
    r = {"scenario_id": vu["id"], **({} if farm_share is None else {"farm_share": farm_share}),
         "bp": bp, "victim_type": victim, "seed": seed,
         **{k: m[k] for k in ("L_A", "k", "c_V", "sigma", "Q", "Q_eff", "bg_band", "attacker_inventory",
                              "subsidy_form")},
         "LV_chia_LA": LV_chia_LA(df), "do_sap": do_sap(df), "subsidy_pending": m["subsidy_pending"],
         "dyncap_t_bao_dau": m["dyncap_t_bao_dau"], "dyncap_so_buoc": m["dyncap_so_buoc"],
         "vol_farmer": sw[sw.role == "farmer"].amount1.clip(lower=0).sum(),
         "vol_tong": sw.amount1.abs().sum()}
    r.update(loi_nhuan_dia_chi(df))
    if farm_share is not None:                       # chi phí farm theo metrics.pnl.farm_pnl của B (= dc_farm_cost)
        mua = sw[(sw.owner == "attacker:0") & (sw.amount1 > 0)]
        r.update(vol_farm_att=mua.amount1.sum(),
                 farm_share_thuc=mua.amount1.sum() / max(mua.amount1.sum() + r["vol_farmer"], 1e-12),
                 sub_att=r["dc_farm_sub"], chi_phi_farm_att=r["dc_farm_cost"],
                 sub_att_treo=m["subsidy_pending_attacker"], subsidy_clawed=m["subsidy_clawed"])
    r.update({k: v for k, v in summarize(df).items() if k not in r})
    return r


def danh_sach_viec(che_do: str, seeds: int, nhanh: bool = False) -> list[tuple]:
    """Mọi lượt (vu, bp, victim, seed, farm_share, bang) của một chế độ: "chinh", "farm" hoặc "k_nho".
    --nhanh: 2 vụ đầu × 1 seed."""
    ds = (to_hop_k_nho() if che_do == "k_nho" else to_hop_luoi() if che_do == "luoi"
          else json.loads(FILE_TO_HOP.read_text(encoding="utf-8")))
    if nhanh:
        ds, seeds = ds[:2], 1
    if che_do == "farm":
        return [(vu, bp, vt, sd, fs, BIEN_PHAP_FARM) for vu in ds for fs in FARM_SHARE for bp in BIEN_PHAP_FARM
                for vt in LOAI_VICTIM for sd in range(seeds) if not (fs == 0 and bp.startswith("claw"))]
    if che_do == "k_nho":
        return [(vu, bp, vt, sd, FARM_SHARE_KNHO, BIEN_PHAP_KNHO) for vu in ds for bp in BIEN_PHAP_KNHO
                for vt in LOAI_VICTIM for sd in range(seeds)]
    if che_do == "luoi":
        return [(vu, bp, vt, sd, None, BIEN_PHAP_LUOI) for vu in ds for bp in BIEN_PHAP_LUOI
                for vt in LOAI_VICTIM for sd in range(seeds)]
    return [(vu, bp, vt, sd, None, BIEN_PHAP) for vu in ds for bp in BIEN_PHAP for vt in LOAI_VICTIM
            for sd in range(seeds)]


def chay(seeds: int, out: Path, nhanh: bool = False, farm: bool = False, k_nho: bool = False,
         luoi: bool = False) -> None:
    """Chạy mọi lượt còn thiếu, ghi nối vào CSV (mỗi lượt một dòng, flush ngay); --nhanh: 2 vụ × 1 seed để đo giờ.
    `farm`: chế độ CH-6; `k_nho`: vùng victim lớn (khóa có `farm_share`)."""
    warnings.filterwarnings("ignore")
    che_do = "farm" if farm else "k_nho" if k_nho else "luoi" if luoi else "chinh"
    khoa = KHOA if che_do in ("chinh", "luoi") else KHOA_FARM
    out.parent.mkdir(parents=True, exist_ok=True)
    da_co, cot = set(), None
    if out.exists() and out.stat().st_size > 0:
        with out.open(encoding="utf-8", newline="") as f:
            rd = csv.DictReader(f)
            cot = rd.fieldnames
            da_co = {tuple(row[k] for k in khoa) for row in rd}

    def ma(vu, bp, vt, sd, fs):
        return (vu["id"], bp, vt, str(sd)) if fs is None else (vu["id"], str(fs), bp, vt, str(sd))

    viec = [v for v in danh_sach_viec(che_do, seeds, nhanh) if ma(*v[:5]) not in da_co]
    print(f"[{che_do}] {len(da_co)} lượt đã có, còn {len(viec)} lượt → {out}")
    t0 = time.time()
    with out.open("a", encoding="utf-8", newline="") as f:
        w = None
        for i, (vu, bp, vt, sd, fs, bang) in enumerate(viec):
            r = dong_ket_qua(vu, bp, vt, sd, fs, bang)
            if w is None:
                cot = cot or list(r)
                w = csv.DictWriter(f, fieldnames=cot, extrasaction="ignore")
                if f.tell() == 0:
                    w.writeheader()
            w.writerow(r)
            f.flush()
            if (i + 1) % 200 == 0 or i == len(viec) - 1:
                da = time.time() - t0
                print(f"{i + 1}/{len(viec)} · {da:.0f}s · còn ≈ {da / (i + 1) * (len(viec) - i - 1) / 60:.1f} phút")
    print(f"Xong → {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--out", default=None)
    ap.add_argument("--nhanh", action="store_true")
    nhom = ap.add_mutually_exclusive_group()
    nhom.add_argument("--farm", action="store_true", help="CH-6: kẻ tấn công cũng là farmer")
    nhom.add_argument("--k_nho", action="store_true", help="vùng victim lớn k ∈ {0,10; 0,25; 0,45}")
    nhom.add_argument("--luoi", action="store_true", help="lưới (σ, Q) 5 × 5 quanh co_so, bp khong + cap50")
    a = ap.parse_args()
    mac_dinh = ("ket_qua/gd2/tomtat_farm_v3.csv" if a.farm else "ket_qua/gd2/tomtat_knho_v3.csv" if a.k_nho
                else "ket_qua/gd2/tomtat_luoi_v3.csv" if a.luoi else "ket_qua/gd2/tomtat_v3.csv")
    out = a.out or (mac_dinh.replace(".csv", "_nhanh.csv") if a.nhanh else mac_dinh)
    chay(a.seeds, Path(out), a.nhanh, a.farm, a.k_nho, a.luoi)

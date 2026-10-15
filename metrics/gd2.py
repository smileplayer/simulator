"""Đo lường GĐ2 (RQ2): bảng đánh đổi biện pháp × loại victim (× farm_share), tỷ lệ sập, `Q*` thực nghiệm.

Cặp phản thực = cùng `scenario_id` + `seed` + `victim_type` (+ `farm_share`), bp − `khong` (chuỗi ngẫu nhiên
đã ghép chặt, CH-8). CI 95% = bootstrap **cặp** phân cụm theo vụ (lấy lại vụ có hoàn lại, rồi cặp trong vụ),
dùng `metrics.validate._mau_bootstrap` như `bootstrap_cap`.

Quy ước CH 15/10: chỉ số chỉ đo được khi giá sập ≥ 10% (`breached`) — lợi nhuận, thiệt hại victim, thanh khoản
sau sập — so trên cặp **cả hai đều sập**; số cặp bị loại ghi ở cột `n_loai_khong_sap`. Tỷ lệ sập là chỉ số riêng.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from metrics.validate import B_MAC_DINH, SEED_BOOT, _mau_bootstrap

KHOA = ("scenario_id", "seed", "victim_type", "farm_share")
BP_GOC = "khong"

# (cột, nhóm, cần cả hai sập?, thống kê hiệu: "trung_vi" | "trung_binh", mô tả + đơn vị)
CHI_SO = [
    ("victim_loss_full", "loi_ich", True, "trung_vi", "thiệt hại victim so với ôm (token1)"),
    ("LV_chia_LA", "loi_ich", False, "trung_vi", "L victim / L tường (không đơn vị)"),
    ("attacker_profit_excess", "loi_ich", True, "trung_vi", "lợi nhuận tấn công trừ bán thẳng (token1)"),
    ("attacker_farm_pnl", "loi_ich", True, "trung_vi", "lãi farm kẻ tấn công đã nhận − chi phí (token1)"),
    ("loi_tan_cong", "loi_ich", True, "trung_vi", "tổng lợi kẻ tấn công = excess + farm_pnl (token1)"),
    ("loi_tan_cong_treo", "loi_ich", True, "trung_vi", "tổng lợi + thưởng treo chưa tới hạn (token1)"),
    ("breached", "loi_ich", False, "trung_binh", "tỷ lệ sập ≥ 10% (hiệu = điểm %/100)"),
    ("do_sap", "loi_ich", False, "trung_vi", "độ dời giá khi xả (âm = sập, tỷ lệ)"),
    ("vol_tong", "chi_phi", False, "trung_vi", "tổng khối lượng (token1)"),
    ("vol_farmer", "chi_phi", False, "trung_vi", "khối lượng farmer thật (token1)"),
    ("L_mean_before", "chi_phi", False, "trung_vi", "L_active trung bình Before (L)"),
    ("L_mean_post", "chi_phi", True, "trung_vi", "L_active trung bình Post (L)"),
    ("subsidy_total", "chi_phi", False, "trung_vi", "trợ cấp đã trả + treo (token1)"),
    ("subsidy_clawed", "chi_phi", False, "trung_vi", "trợ cấp bị thu hồi (token1)"),
]
MUC_CAP = {"khong": 1.0, "cap75": 0.75, "cap50": 0.5, "cap25": 0.25}
TOL_LOSS = 1.0          # victim loss ≤ 1 token1 coi như 0


def them_cot(df: pd.DataFrame) -> pd.DataFrame:
    """Thêm `loi_tan_cong` = excess + farm_pnl và `loi_tan_cong_treo` = + `attacker_farm_pending` (token1);
    thiếu cột farm (bảng không farm) thì farm = 0. NaN giữ nguyên khi không sập."""
    d = df.copy()
    farm = d["attacker_farm_pnl"] if "attacker_farm_pnl" in d else 0.0
    treo = d["attacker_farm_pending"] if "attacker_farm_pending" in d else 0.0
    d["loi_tan_cong"] = d["attacker_profit_excess"] + farm
    d["loi_tan_cong_treo"] = d["loi_tan_cong"] + (treo.fillna(0.0) if isinstance(treo, pd.Series) else treo)
    d["breached"] = d["breached"].astype(float)
    return d


def ghep_cap(df: pd.DataFrame, bp: str, bp_goc: str = BP_GOC, khoa=KHOA) -> pd.DataFrame:
    """Ghép mỗi dòng `bp` với dòng `bp_goc` cùng khóa; cột của bản gốc có hậu tố `_goc`."""
    k = [c for c in khoa if c in df.columns]
    a, b = df[df["bp"] == bp], df[df["bp"] == bp_goc]
    return a.merge(b.drop(columns=[c for c in b.columns if c not in k and not pd.api.types.is_numeric_dtype(b[c])]),
                   on=k, suffixes=("", "_goc"))


def _ma_tran_mau(cum: np.ndarray, B: int, seed: int) -> np.ndarray | list:
    """Chỉ số bootstrap phân cụm; cụm cùng cỡ thì xếp thành ma trận B × n (tính vector hóa)."""
    mau = _mau_bootstrap(cum, len(cum), B, seed)
    if len({len(m) for m in mau}) == 1:
        return np.vstack(mau)
    return mau


def _thong_ke(M: np.ndarray, kieu: str) -> np.ndarray:
    """Trung vị / trung bình theo hàng, bỏ NaN (NaN = cặp bị loại)."""
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return np.nanmedian(M, axis=1) if kieu == "trung_vi" else np.nanmean(M, axis=1)


def hieu_cap(P: pd.DataFrame, cot: str, can_sap: bool, kieu: str = "trung_vi", mau=None,
             muc: float = 0.95) -> dict:
    """Hiệu cặp của `cot` trên bảng ghép `P` (từ `ghep_cap`). Trả `n_cap` (dùng được), `n_loai_khong_sap`,
    `tk_goc`, `tk_bp` (thống kê từng phía), `hieu` (trung vị/trung bình của d = bp − gốc) + `hieu_lo/hi`, `pct`
    = 100·(TB bp − TB gốc)/|TB gốc| (%, tỷ số trung bình trên cùng cặp) + `pct_lo/hi`. Đơn vị theo `cot`."""
    a, b = P[cot].to_numpy(float), P[cot + "_goc"].to_numpy(float)
    ok = ~(np.isnan(a) | np.isnan(b))
    n_loai = 0
    if can_sap:
        sap = (P["breached"].to_numpy(float) > 0) & (P["breached_goc"].to_numpy(float) > 0)
        n_loai = int((~sap).sum())
        ok &= sap
    out = dict(n_cap=int(ok.sum()), n_loai_khong_sap=n_loai, n_loai_nan=int((~ok).sum()) - n_loai)
    if ok.sum() == 0:
        return out | dict(tk_goc=math.nan, tk_bp=math.nan, hieu=math.nan, hieu_lo=math.nan, hieu_hi=math.nan,
                          pct=math.nan, pct_lo=math.nan, pct_hi=math.nan)
    ham = np.median if kieu == "trung_vi" else np.mean
    d = np.where(ok, a - b, np.nan)
    an, bn = np.where(ok, a, np.nan), np.where(ok, b, np.nan)
    tb_a, tb_b = np.nanmean(an), np.nanmean(bn)
    out |= dict(tk_goc=float(ham(b[ok])), tk_bp=float(ham(a[ok])), hieu=float(ham(d[ok])),
                pct=100 * (tb_a - tb_b) / abs(tb_b) if tb_b != 0 else math.nan)
    if mau is None:
        mau = _ma_tran_mau(P["scenario_id"].to_numpy(), B_MAC_DINH, SEED_BOOT)
    if isinstance(mau, np.ndarray):
        th = _thong_ke(d[mau], kieu)
        with np.errstate(all="ignore"):
            ma, mb = np.nanmean(an[mau], axis=1), np.nanmean(bn[mau], axis=1)
    else:
        th = np.array([_thong_ke(d[i][None], kieu)[0] for i in mau])
        ma = np.array([np.nanmean(an[i]) if ok[i].any() else np.nan for i in mau])
        mb = np.array([np.nanmean(bn[i]) if ok[i].any() else np.nan for i in mau])
    with np.errstate(all="ignore"):
        pc = 100 * (ma - mb) / np.abs(mb)
    q = ((1 - muc) / 2, 1 - (1 - muc) / 2)

    def _ci(x):
        x = x[np.isfinite(x)]
        return (float(np.quantile(x, q[0])), float(np.quantile(x, q[1]))) if len(x) else (math.nan, math.nan)

    out["hieu_lo"], out["hieu_hi"] = _ci(th)
    out["pct_lo"], out["pct_hi"] = _ci(pc)
    return out


def bang_danh_doi(df: pd.DataFrame, nhom: tuple[str, ...] = ("victim_type",), chi_so=CHI_SO,
                  B: int = B_MAC_DINH, seed: int = SEED_BOOT, bp_goc: str = BP_GOC) -> pd.DataFrame:
    """Bảng dài: mỗi dòng = (nhóm..., bp, chỉ số) với hiệu cặp so với `bp_goc` + CI, % thay đổi + CI.
    `df` là bảng tóm tắt GĐ2 (đã/ chưa `them_cot`). Chỉ số thiếu cột thì bỏ qua."""
    if "loi_tan_cong" not in df:
        df = them_cot(df)
    dong = []
    nhom = [c for c in nhom if c in df.columns]
    for khoa_nhom, g in df.groupby(nhom, sort=True) if nhom else [((), df)]:
        khoa_nhom = khoa_nhom if isinstance(khoa_nhom, tuple) else (khoa_nhom,)
        for bp in sorted(set(g["bp"]) - {bp_goc}):
            P = ghep_cap(g, bp, bp_goc)
            if P.empty:
                continue
            mau = _ma_tran_mau(P["scenario_id"].to_numpy(), B, seed)
            for cot, loai, can_sap, kieu, mo_ta in chi_so:
                if cot not in P:
                    continue
                r = hieu_cap(P, cot, can_sap, kieu, mau)
                dong.append(dict(zip(nhom, khoa_nhom)) | dict(bp=bp, chi_so=cot, loai=loai, thong_ke=kieu,
                                                              chi_khi_sap=can_sap, n_vu=P["scenario_id"].nunique())
                            | r | dict(mo_ta=mo_ta))
    return pd.DataFrame(dong)


def ty_le_sap(df: pd.DataFrame, nhom: tuple[str, ...] = ("victim_type",), B: int = B_MAC_DINH,
              seed: int = SEED_BOOT) -> pd.DataFrame:
    """Tỷ lệ lượt sập ≥ 10% (`breached`) theo nhóm × bp, CI bootstrap phân cụm theo vụ (tỷ lệ 0–1)."""
    nhom = [c for c in nhom if c in df.columns] + ["bp"]
    dong = []
    for k, g in df.groupby(nhom, sort=True):
        x = g["breached"].to_numpy(float)
        mau = _mau_bootstrap(g["scenario_id"].to_numpy(), len(g), B, seed)
        tk = np.array([x[i].mean() for i in mau])
        dong.append(dict(zip(nhom, k)) | dict(n=len(g), n_sap=int(x.sum()), ty_le=float(x.mean()),
                                              ci_lo=float(np.quantile(tk, .025)), ci_hi=float(np.quantile(tk, .975))))
    return pd.DataFrame(dong)


def bang_gon(dai: pd.DataFrame, nhom: tuple[str, ...] = ("victim_type",)) -> pd.DataFrame:
    """Bảng rộng một dòng / (nhóm, bp) cho bài báo: % thay đổi [CI] của các chỉ số chính, hiệu tỷ lệ sập (điểm %)."""
    nhom = [c for c in nhom if c in dai.columns]
    cs = {"victim_loss_full": "thiet_hai_victim_%", "loi_tan_cong": "loi_tan_cong_%",
          "loi_tan_cong_treo": "loi_tan_cong_treo_%", "vol_tong": "khoi_luong_%",
          "L_mean_post": "L_post_%", "subsidy_total": "tro_cap_%"}
    dong = []
    for k, g in dai.groupby(nhom + ["bp"], sort=True):
        r = dict(zip(nhom + ["bp"], k))
        for c, ten in cs.items():
            h = g[g["chi_so"] == c]
            if len(h):
                h = h.iloc[0]
                r[ten] = f"{h.pct:+.1f} [{h.pct_lo:+.1f}; {h.pct_hi:+.1f}]"
        h = g[g["chi_so"] == "breached"]
        if len(h):
            h = h.iloc[0]
            r["sap_diem_%"] = f"{100 * h.hieu:+.1f} [{100 * h.hieu_lo:+.1f}; {100 * h.hieu_hi:+.1f}]"
        h = g[g["chi_so"] == "victim_loss_full"]
        if len(h):
            r["n_cap_ca_hai_sap"] = int(h.iloc[0].n_cap)
            r["n_loai_khong_sap"] = int(h.iloc[0].n_loai_khong_sap)
        dong.append(r)
    return pd.DataFrame(dong)


# ---------------------------------------------------------------- Q* thực nghiệm

DAC_TRUNG = ["L_A", "k", "sigma", "Q", "bg_band", "attacker_inventory", "subsidy_form"]


def _khoang(an_toan: dict[float, bool]) -> tuple[float, float, str]:
    """Từ {mức trần r: an toàn?} → khoảng (lo, hi] chứa Q*/Q và ghi chú. Q*/Q = mức trần cao nhất mà mọi mức
    ≤ nó đều an toàn (can thiệp nhẹ nhất đủ chặn); `lo` = mức đó (0 nếu mức thấp nhất vẫn không an toàn)."""
    muc = sorted(an_toan)
    lo, chu = 0.0, ""
    for r in muc:
        if an_toan[r]:
            lo = r
        else:
            break
    hi = next((r for r in muc if r > lo), math.inf)
    if lo == 0.0:
        chu = "dưới lưới (< mức thấp nhất)"
    elif hi == math.inf:
        chu = "trên lưới (an toàn cả khi không hạ trần)"
    if any(an_toan[r] for r in muc if r > lo):
        chu = (chu + "; " if chu else "") + "không đơn điệu"
    return lo, hi, chu


def q_sao_vu(df: pd.DataFrame, tol_loss: float = TOL_LOSS) -> pd.DataFrame:
    """`Q*` thực nghiệm theo vụ × loại victim từ các mức trần `MUC_CAP` (r = Q_eff/Q).

    Mỗi mức: trung vị qua seed (chỉ lượt sập) của `victim_loss_full` và `loi_tan_cong` (token1), trung vị
    `LV_chia_LA` (mọi lượt). An toàn theo victim (V): loss ≤ `tol_loss`; theo kẻ tấn công (A): lợi ≤ 0;
    gộp: V hoặc A. Khoảng `(lo, hi]` của Q*/Q cho từng tiêu chí (xem `_khoang`). Nội suy ngưỡng vào của victim
    `r_V`: theo Lemma 4, victim vào ⇔ (1 + L_V/L_A)² > 1 với (1 + L_V/L_A)² = fQ_eff·n/(c_V·L_A) ∝ r — toàn tri
    khớp đường qua gốc y = r/k̂ ⇒ r_V = k̂; thích nghi (V̂ gồm cả arb/nền) khớp y = a + b·r trên ≥ 2 mức có
    L_V > 0 ⇒ r_V = (1 − a)/b. `r_V_ly_thuyet` = k (toàn tri)."""
    if "loi_tan_cong" not in df:
        df = them_cot(df)
    d = df[df["bp"].isin(MUC_CAP)].assign(r=lambda x: x["bp"].map(MUC_CAP))
    dong = []
    for (vu, vt), g in d.groupby(["scenario_id", "victim_type"], sort=True):
        r0 = g.iloc[0]
        row = dict(scenario_id=vu, victim_type=vt) | {c: r0[c] for c in DAC_TRUNG if c in g}
        av, aa, ag, y = {}, {}, {}, {}
        for r, h in g.groupby("r"):
            s = h[h["breached"] > 0]
            loss = s["victim_loss_full"].median() if len(s) else math.nan
            loi = s["loi_tan_cong"].median() if len(s) else math.nan
            lv = h["LV_chia_LA"].median()
            tag = f"{int(round(r * 100))}"
            row |= {f"loss_{tag}": loss, f"loi_{tag}": loi, f"LV_{tag}": lv, f"n_sap_{tag}": len(s)}
            av[r] = bool(loss <= tol_loss) if not math.isnan(loss) else True     # không sập: không thiệt hại
            aa[r] = bool(loi <= 0) if not math.isnan(loi) else True
            ag[r] = av[r] or aa[r]
            y[r] = (1 + lv) ** 2
        for ten, at in (("V", av), ("A", aa), ("gop", ag)):
            lo, hi, chu = _khoang(at)
            row |= {f"qs_{ten}_lo": lo, f"qs_{ten}_hi": hi, f"ghi_chu_{ten}": chu}
        rr = np.array([r for r in y if y[r] > 1 + 1e-9])
        yy = np.array([y[r] for r in rr])
        r_v = math.nan
        if vt == "omniscient" and len(rr):
            r_v = float((rr * rr).sum() / (rr * yy).sum())          # y = r / k̂, bình phương tối thiểu qua gốc
        elif len(rr) >= 2:
            b, a = np.polyfit(rr, yy, 1)
            r_v = float((1 - a) / b) if b > 0 else math.nan
        k_ = float(r0["k"])
        row |= dict(r_V=r_v, r_V_ly_thuyet=k_ if vt == "omniscient" else math.nan,
                    k_trong_khoang_V=bool(row["qs_V_lo"] < k_ <= row["qs_V_hi"]),
                    r_V_ngoai_suy=bool(r_v < min(MUC_CAP.values())) if not math.isnan(r_v) else False,
                    don_dieu_loi=bool(np.all(np.diff([row.get(f"loi_{t}", np.nan) for t in (25, 50, 75, 100)]) >= -1e-6)))
        dong.append(row)
    return pd.DataFrame(dong)


def tom_tat_q_sao(qv: pd.DataFrame) -> pd.DataFrame:
    """Phân phối khoảng Q*/Q theo loại victim × tiêu chí (V, A, gộp): số vụ rơi vào mỗi khoảng `(lo, hi]`;
    thêm dòng tiêu chí `r_V` (ngưỡng vào nội suy): trung vị, số vụ r_V ≤ 0 (hạ trần không chặn được victim),
    số vụ k nằm trong khoảng Q*_V (đối chiếu Lemma 4: victim toàn tri vào ⇔ Q_eff/Q > k)."""
    dong = []
    for vt, g in qv.groupby("victim_type"):
        r = g["r_V"]
        dong.append(dict(victim_type=vt, tieu_chi="r_V", khoang=f"trung vị {r.median():.2f}", so_vu=int(r.notna().sum()),
                         vu=f"r_V<=0: {int((r <= 0).sum())}; k trong khoảng Q*_V: {int(g['k_trong_khoang_V'].sum())}"
                            f"/{len(g)}; lợi kẻ tấn công đơn điệu theo trần: {int(g['don_dieu_loi'].sum())}/{len(g)}"))
    for vt, g in qv.groupby("victim_type"):
        for ten in ("V", "A", "gop"):
            for (lo, hi), h in g.groupby([f"qs_{ten}_lo", f"qs_{ten}_hi"]):
                dong.append(dict(victim_type=vt, tieu_chi=ten, khoang=f"({lo:g}; {hi:g}]", so_vu=len(h),
                                 vu=",".join(h["scenario_id"])))
    return pd.DataFrame(dong)

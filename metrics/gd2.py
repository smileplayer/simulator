"""Đo lường GĐ2 (RQ2): bảng đánh đổi biện pháp × loại victim (× farm_share), tỷ lệ sập, `Q*` thực nghiệm.

Cặp phản thực = cùng `scenario_id` + `seed` + `victim_type` (+ `farm_share`), bp − `khong` (chuỗi ngẫu nhiên
đã ghép chặt, CH-8). CI 95% = bootstrap **cặp** phân cụm theo vụ (lấy lại vụ có hoàn lại, rồi cặp trong vụ),
dùng `metrics.validate._mau_bootstrap` như `bootstrap_cap`.

Quy ước CH 15/10: chỉ số chỉ đo được khi giá sập ≥ 10% (`breached`) — thiệt hại victim, thanh khoản sau sập,
lợi nhuận suy vai bản v2 — so trên cặp **cả hai đều sập**; số cặp bị loại ghi ở cột `n_loai_khong_sap`. Tỷ lệ sập
là chỉ số riêng. Bản v3 có lợi nhuận theo địa chỉ thật `dc_*` (đo được cả khi không sập) → chỉ số lợi kẻ tấn công
chính `loi_tang_them` = `dc_excess` + `dc_farm_pnl` so trên mọi cặp.
"""
from __future__ import annotations

import math
import warnings

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
# v3: lợi kẻ tấn công theo địa chỉ thật (có cả khi không sập) thay các chỉ số suy vai
CHI_SO_V3 = [c for c in CHI_SO if c[0] not in ("attacker_profit_excess", "attacker_farm_pnl", "loi_tan_cong",
                                              "loi_tan_cong_treo")] + [
    ("dc_excess", "loi_ich", False, "trung_vi", "lợi nhuận tăng thêm so với phát lại không victim (token1)"),
    ("dc_farm_pnl", "loi_ich", False, "trung_vi", "lãi farm kẻ tấn công (token1)"),
    ("loi_tang_them", "loi_ich", False, "trung_vi", "lợi tăng thêm của kẻ tấn công = dc_excess + farm (token1)"),
    ("loi_tang_them_treo", "loi_ich", False, "trung_vi", "lợi tăng thêm + thưởng treo (token1)"),
    ("dc_lai_tong", "loi_ich", False, "trung_vi", "lãi tổng theo địa chỉ, gồm bán kho theo c_A (token1)"),
]
MUC_CAP = {"khong": 1.0, "cap90": 0.9, "cap75": 0.75, "cap60": 0.6, "cap50": 0.5, "cap25": 0.25, "cap15": 0.15,
           "cap10": 0.10, "cap05": 0.05}
TOL_LV = 1e-3           # L_V/L_A ≤ 0,001 coi như victim không vào
TOL_LOSS = 1.0          # victim loss ≤ 1 token1 coi như 0


def them_cot(df: pd.DataFrame) -> pd.DataFrame:
    """Thêm `loi_tan_cong` = excess + farm_pnl và `loi_tan_cong_treo` = + `attacker_farm_pending` (token1, suy vai,
    NaN khi không sập; thiếu cột farm thì farm = 0). Có cột v3 `dc_*` → thêm `loi_tang_them` = dc_excess +
    dc_farm_pnl và `loi_tang_them_treo` = + dc_farm_treo (token1, theo địa chỉ thật, có cả khi không sập)."""
    d = df.copy()
    farm = d["attacker_farm_pnl"] if "attacker_farm_pnl" in d else 0.0
    treo = d["attacker_farm_pending"] if "attacker_farm_pending" in d else 0.0
    if "dc_excess" in d:
        d["loi_tang_them"] = d["dc_excess"] + d["dc_farm_pnl"]
        d["loi_tang_them_treo"] = d["loi_tang_them"] + d["dc_farm_treo"].fillna(0.0)
    if "attacker_profit_excess" in d:
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
        with np.errstate(all="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
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


def bang_danh_doi(df: pd.DataFrame, nhom: tuple[str, ...] = ("victim_type",), chi_so=None,
                  B: int = B_MAC_DINH, seed: int = SEED_BOOT, bp_goc: str = BP_GOC) -> pd.DataFrame:
    """Bảng dài: mỗi dòng = (nhóm..., bp, chỉ số) với hiệu cặp so với `bp_goc` + CI, % thay đổi + CI.
    `df` là bảng tóm tắt GĐ2 (đã/ chưa `them_cot`). Chỉ số thiếu cột thì bỏ qua. `chi_so` = None → `CHI_SO_V3`
    nếu có cột `dc_excess`, không thì `CHI_SO`."""
    if "loi_tan_cong" not in df and "attacker_profit_excess" in df:
        df = them_cot(df)
    if chi_so is None:
        chi_so = CHI_SO_V3 if "dc_excess" in df else CHI_SO
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
          "loi_tan_cong_treo": "loi_tan_cong_treo_%", "loi_tang_them": "loi_tang_them_%",
          "loi_tang_them_treo": "loi_tang_them_treo_%", "vol_tong": "khoi_luong_%",
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


def q_sao_vu(df: pd.DataFrame, tol_loss: float = TOL_LOSS, tol_lv: float = TOL_LV) -> pd.DataFrame:
    """`Q*` thực nghiệm theo vụ × loại victim từ các mức trần có trong dữ liệu (`MUC_CAP`, r = Q_eff/Q).

    Mỗi mức: trung vị qua seed của `LV_chia_LA`, `victim_loss_full` (chỉ lượt sập) và lợi **tấn công** (token1;
    v3: `dc_excess` mọi lượt — không gồm lãi farm vì Theorem 6 so tấn công với bán thẳng, lãi farm có cả khi
    không tấn công; v2: `loi_tan_cong` lượt sập). An toàn theo victim (V): victim không vào
    (L_V/L_A ≤ `tol_lv`) hoặc thiệt hại ≤ `tol_loss`; theo kẻ tấn công (A): lợi ≤ 0; gộp: V hoặc A. Khoảng
    `(lo, hi]` của Q*/Q cho từng tiêu chí (xem `_khoang`). Nội suy ngưỡng vào `r_V`: Lemma 4 cho
    (1 + L_V/L_A)² = f·V̂/(c_V·L_A) = (V̂/(n·Q))/k — toàn tri V̂ = n·Q_eff ⇒ đường qua gốc y = r/k̂, r_V = k̂;
    thích nghi khớp y = a + b·r trên các mức có L_V > 0 ⇒ r_V = (1 − a)/b (≤ 0: hạ trần không đuổi được).
    `Vhat_{tag}` = k·(1 + L_V/L_A)² = V̂/(n·Q) ngầm định từ L_V của victim (đơn vị: phần của trần gốc).
    Có `farm_share` s → k hiệu dụng = k·(1 − s) (victim toàn tri tính cả khối lượng farm của kẻ tấn công)."""
    if "loi_tan_cong" not in df:
        df = them_cot(df)
    v3 = "loi_tang_them" in df
    d = df[df["bp"].isin(MUC_CAP)].assign(r=lambda x: x["bp"].map(MUC_CAP))
    dong = []
    for (vu, vt), g in d.groupby(["scenario_id", "victim_type"], sort=True):
        r0 = g.iloc[0]
        # victim toàn tri tính V gồm farm của kẻ tấn công: V = (n + m)·Q_eff, n/(n + m) = 1 − farm_share
        k_ = float(r0["k"]) * (1 - float(r0["farm_share"]) if "farm_share" in g else 1.0)
        row = dict(scenario_id=vu, victim_type=vt, k_hieu_dung=k_) | {c: r0[c] for c in DAC_TRUNG if c in g}
        av, aa, ag, y, lois = {}, {}, {}, {}, {}
        for r, h in g.groupby("r"):
            s = h[h["breached"] > 0]
            loss = s["victim_loss_full"].median() if len(s) else math.nan
            loi = h["dc_excess"].median() if v3 else (s["loi_tan_cong"].median() if len(s) else math.nan)
            lv = h["LV_chia_LA"].median()
            tag = f"{int(round(r * 100))}"
            row |= {f"loss_{tag}": loss, f"loi_{tag}": loi, f"LV_{tag}": lv, f"n_sap_{tag}": len(s),
                    f"Vhat_{tag}": k_ * (1 + lv) ** 2 if lv > tol_lv else math.nan}
            av[r] = bool(lv <= tol_lv or (not math.isnan(loss) and loss <= tol_loss) or len(s) == 0)
            aa[r] = bool(loi <= 0) if not math.isnan(loi) else True
            ag[r] = av[r] or aa[r]
            y[r], lois[r] = (1 + lv) ** 2, loi
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
        r_min = min(y)
        mang = [lois[r] for r in sorted(lois)]
        row |= dict(r_V=r_v, r_V_ly_thuyet=k_ if vt == "omniscient" else math.nan,
                    k_trong_khoang_V=bool(row["qs_V_lo"] < k_ <= row["qs_V_hi"]),
                    r_V_ngoai_suy=bool(r_v < r_min) if not math.isnan(r_v) else False,
                    r_thap_nhat=r_min, victim_con_o_muc_thap_nhat=not av[r_min],
                    # Theorem 6: Π_A không giảm theo Q — cho phép nhiễu 5% mức không hạ trần + 1 token1
                    don_dieu_loi=bool(np.all(np.diff(mang) >= -(0.05 * abs(mang[-1]) + 1.0))))
        dong.append(row)
    return pd.DataFrame(dong)


def tom_tat_q_sao(qv: pd.DataFrame) -> pd.DataFrame:
    """Phân phối khoảng Q*/Q theo loại victim × tiêu chí (V, A, gộp): số vụ rơi vào mỗi khoảng `(lo, hi]`;
    thêm dòng tiêu chí `r_V` (ngưỡng vào nội suy): trung vị, số vụ r_V ≤ 0 (hạ trần không chặn được victim),
    số vụ k nằm trong khoảng Q*_V (đối chiếu Lemma 4: victim toàn tri vào ⇔ Q_eff/Q > k)."""
    dong = []
    for vt, g in qv.groupby("victim_type"):
        r = g["r_V"]
        if "victim_con_o_muc_thap_nhat" in g:
            dong.append(dict(victim_type=vt, tieu_chi="con_o_muc_thap_nhat", khoang=f"r = {g['r_thap_nhat'].min():g}",
                             so_vu=int(g["victim_con_o_muc_thap_nhat"].sum()),
                             vu=",".join(g.loc[g["victim_con_o_muc_thap_nhat"], "scenario_id"])))
        dong.append(dict(victim_type=vt, tieu_chi="r_V", khoang=f"trung vị {r.median():.2f}", so_vu=int(r.notna().sum()),
                         vu=f"r_V<=0: {int((r <= 0).sum())}; k trong khoảng Q*_V: {int(g['k_trong_khoang_V'].sum())}"
                            f"/{len(g)}; lợi kẻ tấn công đơn điệu theo trần: {int(g['don_dieu_loi'].sum())}/{len(g)}"))
    for vt, g in qv.groupby("victim_type"):
        for ten in ("V", "A", "gop"):
            for (lo, hi), h in g.groupby([f"qs_{ten}_lo", f"qs_{ten}_hi"]):
                dong.append(dict(victim_type=vt, tieu_chi=ten, khoang=f"({lo:g}; {hi:g}]", so_vu=len(h),
                                 vu=",".join(h["scenario_id"])))
    return pd.DataFrame(dong)


# ---------------------------------------------------------------- bản đồ ba vùng (σ, Q)

def kiem_gia_dinh(df: pd.DataFrame) -> dict:
    """Kiểm hai giả định của Theorem 3/6 trên một log (cần `df.attrs["meta"]`), trong pha Prep [t_m, t_rut).

    `lap_day` = trung vị khối lượng farmer mỗi bước / (n_farmers·Q_eff/subsidy_window) — Giả định 1 (trần ràng
    buộc) đúng khi ≈ 1; `ra_tick` = tỷ lệ lệnh farmer làm giá rời tick tường — Giả định 2 (mọi giao dịch được
    trợ cấp nằm trong một tick) đúng khi ≈ 0; `tick_xa_nhat` = số tick giá vượt khỏi tường lớn nhất."""
    m = df.attrs["meta"]
    t0, t1 = int(m["t_m"]), int(m.get("t_rut") or m["t_0"])
    mint = df[(df["kind"] == "mint") & (df["owner"] == "attacker:0")]
    if mint.empty:
        return dict(lap_day=math.nan, ra_tick=math.nan, tick_xa_nhat=math.nan)
    lo, hi = int(mint["tick_lower"].iloc[0]), int(mint["tick_upper"].iloc[0])
    sw = df[(df["kind"] == "swap") & df["owner"].astype(str).str.startswith("farmer") & (df["t"] >= t0) & (df["t"] < t1)]
    tran = float(m["n_farmers"]) * float(m["Q_eff"]) / float(m["subsidy_window"])
    v = sw.groupby("t")["amount1"].sum().reindex(range(t0, t1), fill_value=0.0)
    ngoai = (sw["tick_after"] >= hi) | (sw["tick_after"] < lo)
    xa = np.maximum(sw["tick_after"] - (hi - 1), lo - sw["tick_after"]).clip(lower=0)
    return dict(lap_day=float(v.median() / tran), ra_tick=float(ngoai.mean()) if len(sw) else 0.0,
                tick_xa_nhat=float(xa.max()) if len(sw) else 0.0)


def ba_vung(luoi: pd.DataFrame, gia_dinh: pd.DataFrame | None = None, nguong_kl: float = 0.5,
            tol_lv: float = TOL_LV, nguong_lap_day: float = 0.8, nguong_ra_tick: float = 0.05) -> pd.DataFrame:
    """Bản đồ ba vùng thiết kế trên lưới (σ, Q) (`tomtat_luoi_v4.csv`), mỗi ô = (victim_type, bp, σ, Q):
    trung vị qua seed của `vol_farmer` (token1), `LV_chia_LA`, `loi_tang_them` (token1), thiệt hại victim.

    Vùng thực nghiệm: (i) `khong_KL` — khối lượng farmer < `nguong_kl` × lớn nhất theo σ cùng Q (trợ cấp không
    tạo khối lượng); (ii) `an_toan` — có khối lượng, victim không vào hoặc lợi tăng thêm ≤ 0; (iii) `co_lai`.
    Vùng lý thuyết: (i) σ ≤ σ₀ = f (Theorem 1, P_e = P₀); (ii) k_eff = k/r ≥ 1 (Lemma 4: victim toàn tri không
    vào ⇔ Q_eff ≤ c_V·L_A/(f·n)); (iii) còn lại. `gia_dinh` (từ `kiem_gia_dinh`, cột sigma, Q, bp, victim_type)
    → thêm `lap_day`, `ra_tick`, cờ `vp_GD1` (lap_day < `nguong_lap_day`), `vp_GD2` (ra_tick > `nguong_ra_tick`)
    và `ngoai_gia_dinh` (vùng iv: vi phạm một trong hai)."""
    d = them_cot(luoi) if "loi_tang_them" not in luoi else luoi
    d = d.assign(r=d["bp"].map(MUC_CAP))
    k = ["victim_type", "bp", "sigma", "Q"]
    g = d.groupby(k)
    out = pd.DataFrame(dict(vol_farmer=g["vol_farmer"].median(), LV=g["LV_chia_LA"].median(),
                            loi=g["loi_tang_them"].median(), dc_excess=g["dc_excess"].median(),
                            loss=g["victim_loss_full"].median(), ty_le_sap=g["breached"].mean(),
                            k=g["k"].first(), r=g["r"].first(), f=g["meta_fee"].first() if "meta_fee" in d else 0.0025,
                            n=g.size())).reset_index()
    vmax = out.groupby(["victim_type", "bp", "Q"])["vol_farmer"].transform("max")
    kl = out["vol_farmer"] >= nguong_kl * vmax
    an = (out["LV"] <= tol_lv) | (out["loi"] <= 0)
    out["vung"] = np.where(~kl, "i_khong_KL", np.where(an, "ii_an_toan", "iii_co_lai"))
    out["k_eff"] = out["k"] / out["r"]
    out["vung_ly_thuyet"] = np.where(out["sigma"] <= out["f"], "i_khong_KL",
                                     np.where(out["k_eff"] >= 1, "ii_an_toan", "iii_co_lai"))
    if gia_dinh is not None:
        gd = gia_dinh.groupby(k)[["lap_day", "ra_tick", "tick_xa_nhat"]].median().reset_index()
        out = out.merge(gd, on=k, how="left")
        out["vp_GD1"] = out["lap_day"] < nguong_lap_day
        out["vp_GD2"] = out["ra_tick"] > nguong_ra_tick
        out["ngoai_gia_dinh"] = out["vp_GD1"] | out["vp_GD2"]
    out["khop_ly_thuyet"] = out["vung"] == out["vung_ly_thuyet"]
    return out


# ---------------------------------------------------------------- kiểm đơn điệu theo trần (Theorem 6)

def kiem_don_dieu(df: pd.DataFrame, cot: str = "loi_tang_them", B: int = B_MAC_DINH, seed: int = SEED_BOOT,
                  nguong: float = 50.0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Theorem 6: Π_A không giảm theo Q ⇒ hạ trần một mức (r_cao → r_thap) không được làm `cot` tăng.

    Ghép cặp cùng vụ + seed + victim giữa hai mức trần liền kề có trong dữ liệu, d = cot(r_thap) − cot(r_cao)
    (token1). Trả (`gop`, `vu`): `gop` — mỗi victim × bước hạ: trung bình và trung vị d + CI 95% bootstrap phân
    cụm theo vụ, số vụ tăng có ý nghĩa; `vu` — mỗi vụ × victim × bước: TB d qua seed + CI bootstrap theo seed,
    `tang_co_y_nghia` = TB > `nguong` và ci_lo > 0."""
    if cot not in df:
        df = them_cot(df)
    muc = sorted((r, b) for b, r in MUC_CAP.items() if b in set(df["bp"]))
    rng = np.random.default_rng(seed)
    gop, vu = [], []
    for vt, g in df.groupby("victim_type"):
        for (r_lo, b_lo), (r_hi, b_hi) in zip(muc[:-1], muc[1:]):
            P = ghep_cap(g, b_lo, b_hi)
            if P.empty:
                continue
            d = (P[cot] - P[cot + "_goc"]).to_numpy(float)
            mau = _ma_tran_mau(P["scenario_id"].to_numpy(), B, seed)
            tb = np.array([d[i].mean() for i in mau]) if isinstance(mau, list) else d[mau].mean(axis=1)
            tv = np.array([np.median(d[i]) for i in mau]) if isinstance(mau, list) else np.median(d[mau], axis=1)
            dong_vu = []
            for v, h in P.assign(d=d).groupby("scenario_id"):
                x = h["d"].to_numpy()
                bs = x[rng.integers(0, len(x), (B, len(x)))].mean(axis=1)
                lo, hi = np.quantile(bs, [0.025, 0.975])
                dong_vu.append(dict(victim_type=vt, buoc=f"{b_hi}→{b_lo}", scenario_id=v, Q=h["Q"].iloc[0],
                                    sigma=h["sigma"].iloc[0], L_A=h["L_A"].iloc[0], k=h["k"].iloc[0],
                                    goc=h[cot + "_goc"].mean(), tb_d=x.mean(), ci_lo=lo, ci_hi=hi,
                                    tang_co_y_nghia=bool(x.mean() > nguong and lo > 0)))
            vu += dong_vu
            gop.append(dict(victim_type=vt, buoc=f"{b_hi}→{b_lo}", r_cao=r_hi, r_thap=r_lo, n_cap=len(d),
                            tb_d=d.mean(), tb_lo=np.quantile(tb, .025), tb_hi=np.quantile(tb, .975),
                            tv_d=float(np.median(d)), tv_lo=np.quantile(tv, .025), tv_hi=np.quantile(tv, .975),
                            so_vu_tang_y_nghia=sum(r["tang_co_y_nghia"] for r in dong_vu), so_vu=len(dong_vu)))
    return pd.DataFrame(gop), pd.DataFrame(vu)

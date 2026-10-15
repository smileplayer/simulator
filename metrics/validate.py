"""Bộ kiểm định RQ1 theo **phân phối** qua các vụ, đặt cạnh số đếm của bài gốc (§6, Phụ lục C, n = 29).

- `validate_rq1`: mỗi tiêu chí = tỷ lệ vụ mô phỏng thỏa một phát biểu của bài gốc, so với tỷ lệ bài gốc;
  Đạt khi tỷ lệ mô phỏng ≥ `ty_le_dat` (mặc định 0,5 — mọi phát biểu của bài gốc đều là đa số), riêng
  "có vụ Attack > 5×" chỉ cần > 0. Không còn tiêu chuẩn "Prep 1–1,5×" (Đức bỏ 14/10): Prep xem ở Bảng 4.
- `bang_chia_nhom`: bảng chia nhóm như Bảng 4 (volume lift), Bảng 6 (độ dời giá), Bảng 7 (độ tụt tại `t_b`).
- `bootstrap_ci`: khoảng tin cậy bootstrap **phân cụm** (mục 5.5: lấy lại vụ có hoàn lại, trong mỗi vụ lấy lại seed);
  `bootstrap_cap`: bootstrap **cặp** cho GĐ2 (hiệu biện pháp − `khong` cùng vụ + seed + loại victim [+ farm_share]).
Volume lift chính trên `vol_total`, phụ trên `vol_trade`. Độ dời giá chính = VWAP bài gốc, phụ = mốc trước burn.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from metrics.report import summarize_many

INF = math.inf
N_BAI_GOC = 29

# Bảng 4 bài gốc: số vụ theo nhóm volume lift
NHOM_LIFT = [("<1×", -INF, 1.0), ("1–1.5×", 1.0, 1.5), ("1.5–2×", 1.5, 2.0), ("2–5×", 2.0, 5.0), (">5×", 5.0, INF)]
BAI_GOC_LIFT = {"Prep": [9, 11, 4, 2, 3], "Attack": [12, 9, 3, 1, 4], "Post": [23, 1, 1, 2, 2]}
# Bảng 7: độ tụt thanh khoản tick tường tại t_b
NHOM_DROP = [("0–20%", -INF, 0.2), ("20–40%", 0.2, 0.4), ("40–60%", 0.4, 0.6), ("60–80%", 0.6, 0.8),
             ("80–99%", 0.8, 1 - 1e-9), ("100%", 1 - 1e-9, INF)]
BAI_GOC_DROP = [0, 0, 2, 2, 7, 18]
# Bảng 6: độ dời giá
NHOM_GIA = [("<−50%", -INF, -0.5), ("−50% đến −20%", -0.5, -0.2), ("−20% đến −10%", -0.2, -0.1),
            ("−10% đến 0%", -0.1, 0.0), ("0% đến 10%", 0.0, 0.1), ("10% đến 20%", 0.1, 0.2),
            ("20% đến 50%", 0.2, 0.5), (">50%", 0.5, INF)]
BAI_GOC_GIA = {"before": [1, 0, 1, 7, 16, 2, 2, 0], "attack": [0, 10, 10, 8, 1, 0, 0, 0]}


B_MAC_DINH = 2000
SEED_BOOT = 20261014


def _mau_bootstrap(cum: np.ndarray | None, n: int, B: int, seed: int,
                   cheo: np.ndarray | None = None) -> list[np.ndarray]:
    """B mảng chỉ số dòng lấy lại mẫu. Mặc định hai tầng lồng nhau: chọn cụm có hoàn lại, rồi trong mỗi cụm chọn
    dòng có hoàn lại. `cheo` khác None → bootstrap **chéo** (pigeonhole, Owen 2007): chọn độc lập cụm và mức của
    `cheo` (ví dụ seed dùng chung mọi vụ), lấy mọi dòng (cụm, mức) của hai tập đã chọn. `cum` = None → bootstrap thường."""
    rng = np.random.default_rng(seed)
    if cum is None:
        return [rng.integers(0, n, n) for _ in range(B)]
    if cheo is not None:
        cu, ci = np.unique(cum, return_inverse=True)
        su, si = np.unique(cheo, return_inverse=True)
        bang = np.full((len(cu), len(su)), -1)
        bang[ci, si] = np.arange(n)
        out = []
        for _ in range(B):
            m = bang[np.ix_(rng.integers(0, len(cu), len(cu)), rng.integers(0, len(su), len(su)))].ravel()
            out.append(m[m >= 0])
        return out
    nhom = [np.flatnonzero(cum == c) for c in pd.unique(cum)]
    out = []
    for _ in range(B):
        chon = rng.integers(0, len(nhom), len(nhom))
        out.append(np.concatenate([g[rng.integers(0, len(g), len(g))] for g in (nhom[i] for i in chon)]))
    return out


def bootstrap_ci(df: pd.DataFrame, ham, B: int = B_MAC_DINH, cum: str | None = "vu", muc: float = 0.95,
                 seed: int = SEED_BOOT, cot: str | None = None, mau: list[np.ndarray] | None = None,
                 cheo: str | None = None) -> tuple[float, float]:
    """CI bách phân vị mức `muc` của thống kê `ham` bằng bootstrap phân cụm theo cột `cum` (mặc định `vu`;
    không có cột đó → bootstrap thường theo dòng). `ham` nhận DataFrame đã lấy lại mẫu, hoặc mảng numpy của
    cột `cot` nếu cho `cot` (nhanh hơn). `mau` = chỉ số lấy sẵn (dùng chung cho nhiều chỉ số). Seed cố định.
    `cheo` = tên cột (ví dụ `seed`) → bootstrap chéo vụ × seed thay cho lồng nhau (xem `_mau_bootstrap`)."""
    cum_arr = df[cum].to_numpy() if (cum is not None and cum in df.columns) else None
    if mau is None:
        cheo_arr = df[cheo].to_numpy() if (cheo is not None and cheo in df.columns and cum_arr is not None) else None
        mau = _mau_bootstrap(cum_arr, len(df), B, seed, cheo_arr)
    x = df[cot].to_numpy() if cot is not None else None
    tk = np.array([ham(x[i]) if x is not None else ham(df.iloc[i]) for i in mau], dtype=float)
    tk = tk[~np.isnan(tk)]
    if len(tk) == 0:
        return math.nan, math.nan
    a = (1 - muc) / 2
    return float(np.quantile(tk, a)), float(np.quantile(tk, 1 - a))


def bootstrap_cap(df: pd.DataFrame, cot: str, bp: str, bp_goc: str = "khong", ham=np.mean,
                  khoa: tuple[str, ...] = ("scenario_id", "seed", "victim_type", "farm_share"),
                  cum: str = "scenario_id", B: int = B_MAC_DINH, muc: float = 0.95, seed: int = SEED_BOOT) -> dict:
    """Bootstrap **cặp** GĐ2: hiệu d = `cot`(bp) − `cot`(bp_goc) ghép theo `khoa` (cột nào có mới dùng), rồi
    lấy lại vụ (`cum`) có hoàn lại và seed trong vụ. Trả `hieu` = ham(d), `ci_lo`, `ci_hi`, `n_cap`, `n_vu`.
    Đơn vị theo `cot` (ví dụ token1 cho lợi nhuận, trợ cấp)."""
    k = [c for c in khoa if c in df.columns]
    a = df[df["bp"] == bp][k + [cot]]
    b = df[df["bp"] == bp_goc][k + [cot]]
    g = a.merge(b, on=k, suffixes=("", "_goc")).dropna(subset=[cot, cot + "_goc"])
    g = g.assign(d=g[cot] - g[cot + "_goc"])
    if g.empty:
        return dict(hieu=math.nan, ci_lo=math.nan, ci_hi=math.nan, n_cap=0, n_vu=0)
    lo, hi = bootstrap_ci(g, ham, B=B, cum=cum, muc=muc, seed=seed, cot="d")
    return dict(hieu=float(ham(g["d"].to_numpy())), ci_lo=lo, ci_hi=hi, n_cap=len(g),
                n_vu=int(g[cum].nunique()) if cum in g else len(g))


def _dem(s: pd.Series, nhom: list) -> list[int]:
    """Số phần tử của `s` rơi vào từng nhóm [a, b)."""
    s = pd.to_numeric(s, errors="coerce").dropna()
    return [int(((s >= a) & (s < b)).sum()) for _, a, b in nhom]


def _bang(cot: dict[str, pd.Series], bai_goc: dict[str, list[int]], nhom: list) -> pd.DataFrame:
    """Bảng nhóm: với mỗi chỉ số `k` có cột `k_mo_phong`, `k_mo_phong_%`, `k_bai_goc`, `k_bai_goc_%`."""
    out = pd.DataFrame(index=[n for n, _, _ in nhom])
    out.index.name = "nhom"
    for k, s in cot.items():
        d = _dem(s, nhom)
        tong = max(sum(d), 1)
        out[f"{k}_mo_phong"] = d
        out[f"{k}_mo_phong_%"] = [100 * x / tong for x in d]
        if k in bai_goc:
            out[f"{k}_bai_goc"] = bai_goc[k]
            out[f"{k}_bai_goc_%"] = [100 * x / N_BAI_GOC for x in bai_goc[k]]
    return out


def bang_chia_nhom(tom_tat: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Ba bảng chia nhóm từ bảng `summarize_many`: `bang4_lift` (chính `vol_total` + phụ `vol_trade`),
    `bang6_gia` (chính VWAP + phụ trước burn), `bang7_drop`. Số đếm bài gốc đặt cạnh (n = 29)."""
    b4 = _bang({"Prep": tom_tat["lift_Prep"], "Attack": tom_tat["lift_Attack"], "Post": tom_tat["lift_Post"],
                "Prep_trade": tom_tat["lift_trade_Prep"], "Attack_trade": tom_tat["lift_trade_Attack"],
                "Post_trade": tom_tat["lift_trade_Post"]}, BAI_GOC_LIFT, NHOM_LIFT)
    b6 = _bang({"before": tom_tat["before_price_change"], "attack": tom_tat["attack_price_change"],
                "attack_preburn": tom_tat["attack_price_change_preburn"]}, BAI_GOC_GIA, NHOM_GIA)
    b7 = _bang({"drop": tom_tat["L_drop_at_tb"]}, {"drop": BAI_GOC_DROP}, NHOM_DROP)
    return dict(bang4_lift=b4, bang6_gia=b6, bang7_drop=b7)


def _tieu_chi() -> list[tuple]:
    """(dấu hiệu, loại, phát biểu, cột, điều kiện từng vụ, số vụ bài gốc thỏa hoặc None, kiểu ngưỡng)."""
    return [
        ("Có cú sập ≥ 10%", "chính", "vụ có t_b (giá ≤ 90% tick tường)", "breached", lambda x: bool(x), 29, "da_so"),
        ("Chuẩn bị theo ngày", "chính", "Δbuild ≥ 1 ngày", "delta_build", lambda x: x >= 24, 16, "da_so"),
        ("Thu hoạch theo giờ", "chính", "Δextract < 24 giờ", "delta_extract", lambda x: x < 24, 18, "da_so"),
        ("Khối lượng Attack trên nền", "chính", "lift_Attack ≥ 1×", "lift_Attack", lambda x: x >= 1, 17, "da_so"),
        ("Khối lượng Attack bùng", "chính", "có vụ lift_Attack > 5×", "lift_Attack", lambda x: x > 5, 4, "co_vu"),
        ("Khối lượng Post dưới nền", "chính", "lift_Post < 1×", "lift_Post", lambda x: x < 1, 23, "da_so"),
        ("Khối lượng Post dưới nền", "phụ", "lift_trade_Post < 1× (bỏ arb)", "lift_trade_Post",
         lambda x: x < 1, None, "da_so"),
        ("Biến động Prep thấp hơn Attack", "chính", "RV_Prep < RV_Attack", "rv_atk_prep", lambda x: x > 1, None, "da_so"),
        ("Biến động Post cao nhất", "chính", "RV_Post ≥ max(RV_Prep, RV_Attack)", "rv_post_max",
         lambda x: x >= 1, None, "da_so"),
        ("Giá ghim quanh t_m", "chính", "|before_price_change| < 10%", "before_price_change",
         lambda x: abs(x) < 0.10, 23, "da_so"),
        ("Giá sập sau rút", "chính", "attack_price_change < −10% (VWAP, bài gốc)", "attack_price_change",
         lambda x: x < -0.10, 20, "da_so"),
        ("Giá sập sau rút", "phụ", "như trên, mốc = giá trước burn tường", "attack_price_change_preburn",
         lambda x: x < -0.10, None, "da_so"),
        ("Tường cạn tại t_b", "chính", "drop_at_tb ≥ 80%", "L_drop_at_tb", lambda x: x >= 0.8, 25, "da_so"),
    ]


def validate_rq1(dfs: list[pd.DataFrame] | pd.DataFrame, ty_le_dat: float = 0.5, B: int = B_MAC_DINH,
                 seed: int = SEED_BOOT) -> pd.DataFrame:
    """Bảng kiểm định RQ1 theo phân phối. Nhận danh sách log hoặc bảng `summarize_many` (cột `vu` nếu có → bootstrap
    phân cụm theo vụ, mục 5.5).

    Cột: `dau_hieu`, `loai`, `phat_bieu`, `so_vu`, `ty_le_mo_phong`, `ci_lo`, `ci_hi` (CI 95% của tỷ lệ,
    bootstrap lồng vụ → seed như mục 5.5), `ci_lo_cheo`, `ci_hi_cheo` (bootstrap chéo vụ × seed: seed của bộ
    tổ hợp dùng chung mọi vụ nên là yếu tố chéo; có khi bảng có cả `vu` và `seed`), `ty_le_bai_goc` (x/29),
    `trung_vi`, `tv_ci_lo`, `tv_ci_hi` (CI 95% của trung vị, lồng nhau), `ket_qua`. `B` = 0 → bỏ bootstrap.
    """
    bang = dfs if isinstance(dfs, pd.DataFrame) and "breached" in dfs.columns else summarize_many(list(dfs))
    bang = bang.copy().reset_index(drop=True)
    bang["rv_atk_prep"] = bang["RV_Attack"] / bang["RV_Prep"].replace(0, np.nan)
    bang["rv_post_max"] = bang["RV_Post"] / bang[["RV_Prep", "RV_Attack"]].max(axis=1).replace(0, np.nan)
    cum = bang["vu"].to_numpy() if "vu" in bang.columns else None
    mau = _mau_bootstrap(cum, len(bang), B, seed) if B > 0 else None
    mau_cheo = (_mau_bootstrap(cum, len(bang), B, seed, bang["seed"].to_numpy())
                if (B > 0 and cum is not None and "seed" in bang.columns) else None)
    rows = []
    for ten, loai, phat_bieu, cot, dk, n_goc, kieu in _tieu_chi():
        s = bang[cot].astype(float) if cot == "breached" else pd.to_numeric(bang[cot], errors="coerce")
        hop_le = s.notna()
        r = dict(dau_hieu=ten, loai=loai, phat_bieu=phat_bieu, so_vu=int(hop_le.sum()),
                 ty_le_mo_phong=math.nan, ci_lo=math.nan, ci_hi=math.nan, ci_lo_cheo=math.nan,
                 ci_hi_cheo=math.nan, ty_le_bai_goc=math.nan if n_goc is None else n_goc / N_BAI_GOC,
                 trung_vi=math.nan, tv_ci_lo=math.nan, tv_ci_hi=math.nan, ket_qua="Chưa đo")
        if hop_le.any():
            thoa = np.where(hop_le, s.map(lambda x: float(dk(x)) if not pd.isna(x) else np.nan), np.nan)
            gia_tri = s.to_numpy(dtype=float)
            p = float(np.nanmean(thoa))
            dat = p > 0 if kieu == "co_vu" else p >= ty_le_dat
            r.update(ty_le_mo_phong=p, trung_vi=float(np.nanmedian(gia_tri)), ket_qua="Đạt" if dat else "Không đạt")
            if mau is not None:
                tam = pd.DataFrame({"thoa": thoa, "x": gia_tri, "vu": cum if cum is not None else np.arange(len(s))})
                _tb = lambda a: float(np.nanmean(a)) if np.isfinite(a).any() else np.nan
                _tv = lambda a: float(np.nanmedian(a)) if np.isfinite(a).any() else np.nan
                r["ci_lo"], r["ci_hi"] = bootstrap_ci(tam, _tb, cot="thoa", mau=mau)
                r["tv_ci_lo"], r["tv_ci_hi"] = bootstrap_ci(tam, _tv, cot="x", mau=mau)
                if mau_cheo is not None:
                    r["ci_lo_cheo"], r["ci_hi_cheo"] = bootstrap_ci(tam, _tb, cot="thoa", mau=mau_cheo)
        rows.append(r)
    rows.append(dict(dau_hieu="Victim toàn tri khớp lý thuyết", loai="chính",
                     phat_bieu="L_V*/L_A ≈ 1 tại L_A = fQ/(4c_V) (kiểm ở tests/agents của C)", so_vu=0,
                     ty_le_mo_phong=math.nan, ci_lo=math.nan, ci_hi=math.nan, ci_lo_cheo=math.nan,
                     ci_hi_cheo=math.nan, ty_le_bai_goc=math.nan,
                     trung_vi=math.nan, tv_ci_lo=math.nan, tv_ci_hi=math.nan, ket_qua="Chưa đo"))
    out = pd.DataFrame(rows)
    out.attrs["n_vu"] = len(bang)
    out.attrs["n_cum"] = int(pd.Series(cum).nunique()) if cum is not None else len(bang)
    return out

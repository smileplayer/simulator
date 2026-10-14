"""Bộ kiểm định RQ1 theo **phân phối** qua các vụ, đặt cạnh số đếm của bài gốc (§6, Phụ lục C, n = 29).

- `validate_rq1`: mỗi tiêu chí = tỷ lệ vụ mô phỏng thỏa một phát biểu của bài gốc, so với tỷ lệ bài gốc;
  Đạt khi tỷ lệ mô phỏng ≥ `ty_le_dat` (mặc định 0,5 — mọi phát biểu của bài gốc đều là đa số), riêng
  "có vụ Attack > 5×" chỉ cần > 0. Không còn tiêu chuẩn "Prep 1–1,5×" (Đức bỏ 14/10): Prep xem ở Bảng 4.
- `bang_chia_nhom`: bảng chia nhóm như Bảng 4 (volume lift), Bảng 6 (độ dời giá), Bảng 7 (độ tụt tại `t_b`).
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


def validate_rq1(dfs: list[pd.DataFrame] | pd.DataFrame, ty_le_dat: float = 0.5) -> pd.DataFrame:
    """Bảng kiểm định RQ1 theo phân phối. Nhận danh sách log hoặc bảng `summarize_many`.

    Cột: `dau_hieu`, `loai`, `phat_bieu`, `so_vu`, `ty_le_mo_phong`, `ty_le_bai_goc` (x/29), `trung_vi`, `ket_qua`.
    """
    bang = dfs if isinstance(dfs, pd.DataFrame) and "breached" in dfs.columns else summarize_many(list(dfs))
    bang = bang.copy()
    bang["rv_atk_prep"] = bang["RV_Attack"] / bang["RV_Prep"].replace(0, np.nan)
    bang["rv_post_max"] = bang["RV_Post"] / bang[["RV_Prep", "RV_Attack"]].max(axis=1).replace(0, np.nan)
    rows = []
    for ten, loai, phat_bieu, cot, dk, n_goc, kieu in _tieu_chi():
        s = bang[cot].astype(float) if cot == "breached" else pd.to_numeric(bang[cot], errors="coerce").dropna()
        r = dict(dau_hieu=ten, loai=loai, phat_bieu=phat_bieu, so_vu=len(s),
                 ty_le_mo_phong=math.nan, ty_le_bai_goc=math.nan if n_goc is None else n_goc / N_BAI_GOC,
                 trung_vi=math.nan, ket_qua="Chưa đo")
        if len(s):
            p = float(s.map(dk).mean())
            dat = p > 0 if kieu == "co_vu" else p >= ty_le_dat
            r.update(ty_le_mo_phong=p, trung_vi=float(s.median()), ket_qua="Đạt" if dat else "Không đạt")
        rows.append(r)
    rows.append(dict(dau_hieu="Victim toàn tri khớp lý thuyết", loai="chính",
                     phat_bieu="L_V*/L_A ≈ 1 tại L_A = fQ/(4c_V) (kiểm ở tests/agents của C)", so_vu=0,
                     ty_le_mo_phong=math.nan, ty_le_bai_goc=math.nan, trung_vi=math.nan, ket_qua="Chưa đo"))
    out = pd.DataFrame(rows)
    out.attrs["n_vu"] = len(bang)
    return out

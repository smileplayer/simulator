"""Bộ kiểm định RQ1: simulator có tái lập các dấu hiệu thực nghiệm của bài gốc không (mục 6 kế hoạch simulator).

Mỗi tiêu chí so **trung vị qua các vụ** với ngưỡng, kèm tỷ lệ vụ tự đạt. Ngưỡng lấy từ §6 bài gốc
(29 vụ): xây tường > 3 ngày ở 12/29 vụ, thu hoạch < 24h ở 18/29, lift Prep chủ yếu 1–1,5×, Attack phân tán
(có vụ > 5×), Post dưới nền, RV thấp nhất ở Prep và cao nhất ở Post, độ dời giá quanh `t_m` trong 0–10% ở 16/29,
sau rút < −10% ở 20/29, tường cạn ≥ 80% tại `t_b` ở 25/29. Volume lift chính trên `vol_total`, phụ trên `vol_trade`.
"""
from __future__ import annotations

import math
from typing import Callable

import pandas as pd

from metrics.report import summarize_many

NGUONG = dict(build_min=24, extract_max=24, prep_lo=1.0, prep_hi=1.5, attack_spike=5.0,
              post_max=1.0, pin_max=0.10, crash_max=-0.10, drop_min=0.80)


def _tieu_chi(n: dict) -> list[tuple]:
    """Danh sách (dấu hiệu, loại, mô tả ngưỡng, cột, hàm gộp, điều kiện trên giá trị gộp, điều kiện từng vụ)."""
    med = lambda s: float(s.median())
    return [
        ("Có cú sập ≥ 10%", "chính", "mọi vụ breached", "breached", lambda s: float(s.mean()),
         lambda v: v == 1.0, lambda x: bool(x)),
        ("Chuẩn bị theo ngày", "chính", f"trung vị Δbuild ≥ {n['build_min']} giờ", "delta_build", med,
         lambda v: v >= n["build_min"], lambda x: x >= n["build_min"]),
        ("Thu hoạch theo giờ", "chính", f"trung vị Δextract < {n['extract_max']} giờ", "delta_extract", med,
         lambda v: v < n["extract_max"], lambda x: x < n["extract_max"]),
        ("Khối lượng Prep vừa phải", "chính", f"trung vị lift_Prep ∈ [{n['prep_lo']}, {n['prep_hi']}]", "lift_Prep",
         med, lambda v: n["prep_lo"] <= v <= n["prep_hi"], lambda x: n["prep_lo"] <= x <= n["prep_hi"]),
        ("Khối lượng Prep vừa phải", "phụ", "như trên, trên vol_trade", "lift_trade_Prep",
         med, lambda v: n["prep_lo"] <= v <= n["prep_hi"], lambda x: n["prep_lo"] <= x <= n["prep_hi"]),
        ("Khối lượng Attack bùng", "chính", f"có vụ lift_Attack > {n['attack_spike']}×", "lift_Attack",
         lambda s: float(s.max()), lambda v: v > n["attack_spike"], lambda x: x > n["attack_spike"]),
        ("Khối lượng Post dưới nền", "chính", f"trung vị lift_Post < {n['post_max']}", "lift_Post", med,
         lambda v: v < n["post_max"], lambda x: x < n["post_max"]),
        ("Khối lượng Post dưới nền", "phụ", "như trên, trên vol_trade", "lift_trade_Post", med,
         lambda v: v < n["post_max"], lambda x: x < n["post_max"]),
        ("Biến động Prep thấp hơn Attack", "chính", "trung vị RV_Attack / RV_Prep > 1", "rv_atk_prep", med,
         lambda v: v > 1, lambda x: x > 1),
        ("Biến động Post cao nhất", "chính", "trung vị RV_Post / max(RV_Prep, RV_Attack) ≥ 1", "rv_post_max", med,
         lambda v: v >= 1, lambda x: x >= 1),
        ("Giá ghim quanh t_m", "chính", f"trung vị |before_price_change| < {n['pin_max']:.0%}", "abs_before",
         med, lambda v: v < n["pin_max"], lambda x: x < n["pin_max"]),
        ("Giá sập sau rút", "chính", f"trung vị attack_price_change ≤ {n['crash_max']:.0%}", "attack_price_change",
         med, lambda v: v <= n["crash_max"], lambda x: x <= n["crash_max"]),
        ("Tường cạn tại t_b", "chính", f"trung vị drop_at_tb ≥ {n['drop_min']:.0%}", "L_drop_at_tb", med,
         lambda v: v >= n["drop_min"], lambda x: x >= n["drop_min"]),
    ]


def validate_rq1(dfs: list[pd.DataFrame] | pd.DataFrame, nguong: dict | None = None) -> pd.DataFrame:
    """Bảng Đạt / Không đạt cho RQ1. Nhận danh sách log (DataFrame sự kiện) hoặc bảng `summarize_many` có sẵn.

    Cột: `dau_hieu`, `loai` (chính/phụ), `tieu_chuan`, `gia_tri` (giá trị gộp), `ty_le_vu` (tỷ lệ vụ tự đạt),
    `ket_qua` ∈ {Đạt, Không đạt, Chưa đo}.
    """
    n = {**NGUONG, **(nguong or {})}
    bang = dfs if isinstance(dfs, pd.DataFrame) and "breached" in dfs.columns else summarize_many(list(dfs))
    bang = bang.copy()
    bang["rv_atk_prep"] = bang["RV_Attack"] / bang["RV_Prep"]
    bang["rv_post_max"] = bang["RV_Post"] / bang[["RV_Prep", "RV_Attack"]].max(axis=1)
    bang["abs_before"] = bang["before_price_change"].abs()
    rows = []
    for ten, loai, mo_ta, cot, gop, dat, dat_vu in _tieu_chi(n):
        s = pd.to_numeric(bang[cot], errors="coerce").dropna() if cot != "breached" else bang[cot].astype(float)
        if s.empty:
            rows.append(dict(dau_hieu=ten, loai=loai, tieu_chuan=mo_ta, gia_tri=math.nan, ty_le_vu=math.nan,
                             ket_qua="Chưa đo"))
            continue
        v = gop(s)
        rows.append(dict(dau_hieu=ten, loai=loai, tieu_chuan=mo_ta, gia_tri=v,
                         ty_le_vu=float(s.map(dat_vu).mean()), ket_qua="Đạt" if dat(v) else "Không đạt"))
    rows.append(dict(dau_hieu="Victim toàn tri khớp lý thuyết", loai="chính",
                     tieu_chuan="L_V*/L_A ≈ 1 tại L_A = fQ/(4c_V) (kiểm ở tests/agents của C)",
                     gia_tri=math.nan, ty_le_vu=math.nan, ket_qua="Chưa đo"))
    out = pd.DataFrame(rows)
    out.attrs["n_vu"] = len(bang)
    return out

"""Chuỗi thời gian theo bước (1 bước = 1 giờ) dựng từ log sự kiện INTERFACE mục 4.

Chỉ đọc DataFrame log, không gọi engine. Mọi giá tính bằng token1/token0, khối lượng bằng token1.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

VAI_KHOI_LUONG = ("bg", "farmer", "victim", "attacker", "arb")


def step_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Ảnh chụp cuối mỗi bước từ dòng `step`: cột `price`, `tick`, `L_active`, `p_ext`; chỉ số = `t`."""
    s = df[df["kind"] == "step"].sort_values(["t", "seq"]).groupby("t").last()
    out = pd.DataFrame({
        "price": s["sqrt_price_after"].astype(float) ** 2,
        "tick": s["tick_after"].astype(int),
        "L_active": s["liquidity_active_after"].astype(float),
        "p_ext": s["external_price"].astype(float),
    })
    out.index.name = "t"
    return out


def swap_volume(df: pd.DataFrame) -> pd.DataFrame:
    """Khối lượng swap mỗi bước theo `role`, tính bằng |amount1| (token1, chiều vào đã gồm phí).

    Cột: `vol_<role>` cho từng vai trong VAI_KHOI_LUONG (thiếu thì 0) và vai lạ nếu có; chỉ số = `t`.
    """
    sw = df[df["kind"] == "swap"]
    bang = (sw.assign(v=sw["amount1"].abs())
              .pivot_table(index="t", columns="role", values="v", aggfunc="sum", fill_value=0.0))
    for r in VAI_KHOI_LUONG:
        if r not in bang.columns:
            bang[r] = 0.0
    thu_tu = list(VAI_KHOI_LUONG) + sorted(c for c in bang.columns if c not in VAI_KHOI_LUONG)
    bang = bang[thu_tu].add_prefix("vol_")
    bang.columns.name = None
    bang.index.name = "t"
    return bang


def build_timeseries(df: pd.DataFrame, vol_window: int = 24) -> pd.DataFrame:
    """Bảng chuỗi thời gian một vụ, mỗi dòng một bước `t` (giờ).

    Cột: `price`, `tick`, `L_active`, `p_ext`, `vol_<role>`, `vol_total` (mọi swap),
    `vol_trade` (bỏ `arb`), `n_swap`, `ret` (log-return giá bể mỗi bước),
    `abs_ret`, `rv` (độ lệch chuẩn `ret` trượt `vol_window` bước).
    """
    ts = step_frame(df)
    vol = swap_volume(df).reindex(ts.index, fill_value=0.0)
    ts = ts.join(vol)
    cot_vol = [c for c in vol.columns]
    ts["vol_total"] = ts[cot_vol].sum(axis=1)
    ts["vol_trade"] = ts["vol_total"] - ts["vol_arb"]
    n = df[df["kind"] == "swap"].groupby("t").size()
    ts["n_swap"] = n.reindex(ts.index, fill_value=0).astype(int)
    ts["ret"] = np.log(ts["price"]).diff()
    ts["abs_ret"] = ts["ret"].abs()
    ts["rv"] = ts["ret"].rolling(vol_window, min_periods=2).std()
    return ts

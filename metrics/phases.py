"""Mốc thời gian và pha của một vụ tấn công, theo §6.1–6.2 bài gốc (Lu et al., USENIX Sec 2026).

Định nghĩa (đơn vị: bước = giờ; `seq` cho thứ tự trong giờ):
- tường = khoảng một tick có thanh khoản một-tick đạt đỉnh lớn nhất (cộng mọi owner, không cần biết vai);
- `t_m`: mint đầu tiên vào khoảng tường;
- `t_50`: lần đầu thanh khoản tường ≥ 50% đỉnh; `t_peak`: lần đầu chạm đỉnh;
- `t_0`: lần đầu sau đỉnh tụt dưới 95% đỉnh (§6.1.1); `t_0_burn`: burn lớn nhất trên khoảng tường (§5, đối chiếu);
- `t_oot`: swap đầu tiên từ `t_0` đưa giá ra dưới tick tường;
- `t_b`: bước đầu tiên từ `t_0` có giá bể ≤ 90% giá biên dưới tick tường.
Pha (W = 24): Before `[t_m−W, t_m)`, Prep `[t_m, t_0)`, Attack `[t_0, t_b]`, Post `(t_b, t_b+W]`.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

CO_SO = 1.0001
PHA = ("Before", "Prep", "Attack", "Post")


def wall_liquidity(df: pd.DataFrame, width: int = 1) -> pd.DataFrame:
    """Phát lại mint/burn, trả thanh khoản cộng dồn theo sự kiện của từng khoảng rộng `width` tick.

    Cột: `t`, `seq`, `tick_lower`, `tick_upper`, `dL` (+mint/−burn), `L_wall` (cộng dồn, đơn vị L).
    """
    mb = df[df["kind"].isin(["mint", "burn"])].copy()
    mb = mb[(mb["tick_upper"] - mb["tick_lower"]) == width].sort_values(["t", "seq"])
    mb["dL"] = np.where(mb["kind"] == "mint", 1.0, -1.0) * mb["liquidity"].astype(float)
    mb["L_wall"] = mb.groupby("tick_lower")["dL"].cumsum()
    return mb[["t", "seq", "tick_lower", "tick_upper", "dL", "L_wall"]].reset_index(drop=True)


def _gia_ky(df: pd.DataFrame) -> pd.Series:
    """Giá bể cuối mỗi bước (token1/token0), lấy từ dòng `step`."""
    s = df[df["kind"] == "step"].sort_values(["t", "seq"]).groupby("t").last()
    return s["sqrt_price_after"].astype(float) ** 2


def phases(df: pd.DataFrame, width: int = 1, W: int = 24, breach: float = 0.10,
           wall: tuple[int, int] | None = None) -> dict:
    """Tìm mốc `t_m, t_50, t_peak, t_0, t_oot, t_b` (bước) và cửa sổ bốn pha.

    `wall` = (tick_lower, tick_upper) nếu muốn chỉ định tường; mặc định tự dò theo đỉnh thanh khoản.
    Không có cú sập ≥ `breach` thì `t_b`, `t_oot` = None và `breached` = False.
    """
    wl = wall_liquidity(df, width)
    if wl.empty:
        raise ValueError(f"log không có mint/burn nào rộng {width} tick")
    if wall is None:
        lo = int(wl.groupby("tick_lower")["L_wall"].max().idxmax())
    else:
        lo = int(wall[0])
    hi = lo + width
    e = wl[wl["tick_lower"] == lo].reset_index(drop=True)
    peak = float(e["L_wall"].max())

    t_m = int(e["t"].iloc[0])
    i_peak = int(e["L_wall"].idxmax())                       # idxmax = lần đầu chạm đỉnh
    t_peak = int(e.loc[i_peak, "t"])
    t_50 = int(e.loc[(e["L_wall"] >= 0.5 * peak).idxmax(), "t"])
    sau = e.loc[i_peak + 1:]
    tut = sau[sau["L_wall"] < 0.95 * peak]
    t_0 = int(tut["t"].iloc[0]) if len(tut) else None
    burns = e[e["dL"] < 0]
    t_0_burn = int(burns.loc[burns["dL"].idxmin(), "t"]) if len(burns) else None

    t_oot = seq_oot = t_b = None
    if t_0 is not None:
        sw = df[(df["kind"] == "swap") & (df["t"] >= t_0)].sort_values(["t", "seq"])
        ra = sw[sw["tick_after"] < lo]
        if len(ra):
            t_oot, seq_oot = int(ra["t"].iloc[0]), int(ra["seq"].iloc[0])
        gia = _gia_ky(df)
        nguong = (1 - breach) * CO_SO ** lo
        sap = gia[(gia.index >= t_0) & (gia <= nguong)]
        if len(sap):
            t_b = int(sap.index[0])

    out = dict(
        wall_tick_lower=lo, wall_tick_upper=hi, peak_liquidity=peak,
        t_m=t_m, t_50=t_50, t_peak=t_peak, t_0=t_0, t_0_burn=t_0_burn,
        t_oot=t_oot, seq_oot=seq_oot, t_b=t_b, breached=t_b is not None, W=W,
        delta_build=None if t_0 is None else t_0 - t_m,
        delta_extract=None if t_b is None else t_b - t_0,
        delta_oot=None if (t_b is None or t_oot is None) else t_b - t_oot,
    )
    out["windows"] = phase_windows(out)
    return out


def phase_windows(ph: dict) -> dict[str, tuple[int, int] | None]:
    """Cửa sổ mỗi pha dạng (đầu, cuối) **bao gồm cả hai đầu**, theo bước; pha không xác định → None."""
    t_m, t_0, t_b, W = ph["t_m"], ph["t_0"], ph["t_b"], ph["W"]
    win: dict[str, tuple[int, int] | None] = {"Before": (max(0, t_m - W), t_m - 1) if t_m > 0 else None}
    win["Prep"] = (t_m, t_0 - 1) if t_0 is not None else None
    win["Attack"] = (t_0, t_b) if t_b is not None else None
    win["Post"] = (t_b + 1, t_b + W) if t_b is not None else None
    return win


def label_phases(ts: pd.DataFrame, ph: dict) -> pd.Series:
    """Gắn nhãn pha cho mỗi bước của bảng chỉ số theo `t` (ví dụ `build_timeseries`); ngoài pha → NaN."""
    nhan = pd.Series(np.nan, index=ts.index, dtype=object, name="phase")
    for ten, w in ph["windows"].items():
        if w is not None:
            nhan[(ts.index >= w[0]) & (ts.index <= w[1])] = ten
    return nhan

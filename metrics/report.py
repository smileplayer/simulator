"""Gom mọi chỉ số của một vụ thành một dòng, và hai chỉ số dẫn xuất (mục 5 kế hoạch simulator).

Đơn vị: tiền token1; thanh khoản `L` (đơn vị L của v3); thời gian bước (giờ).
"""
from __future__ import annotations

import math

import pandas as pd

from metrics.indicators import phase_stats, pool_liquidity, price_changes, subsidy_cost
from metrics.phases import PHA, phases
from metrics.pnl import attacker_profit, identify_roles, victim_loss

NAN = float("nan")


def _chia(a: float, b: float) -> float:
    """a/b, trả NaN khi b ≤ 0 hoặc thiếu số."""
    return a / b if (b is not None and b > 0 and not math.isnan(b)) else NAN


def derived(df: pd.DataFrame, ph: dict | None = None, end: str = "t_b",
            alpha_cost: float | None = None) -> dict:
    """Hiệu quả chi tiêu và tỷ lệ rò rỉ.

    - `eff_L` = L_active trung bình pha Post / tổng trợ cấp (L trên mỗi token1): thanh khoản còn lại mua được bằng trợ cấp;
    - `eff_gain` = (L_active Post − L_active Before) / tổng trợ cấp: phần thanh khoản tăng thêm thật; ≤ 0 → trợ cấp mất trắng;
    - `leak_paper`, `leak_full` = lợi nhuận kẻ tấn công (bản bài gốc / bản đầy đủ) / tổng trợ cấp;
    - `leak_excess` = lợi nhuận tăng thêm so với bán thẳng (Theorem 6) / tổng trợ cấp.
    Tổng trợ cấp = đã trả + còn treo (`subsidy_cost`).
    """
    ph = ph or phases(df)
    S = subsidy_cost(df)["total"]
    out = dict(subsidy_total=S, eff_L=NAN, eff_gain=NAN, leak_paper=NAN, leak_full=NAN, leak_excess=NAN)
    if not ph["breached"]:
        return out
    pl = pool_liquidity(df, ph)
    out["eff_L"] = _chia(pl["mean_post"], S)
    out["eff_gain"] = _chia(pl["mean_post"] - pl["mean_before"], S)
    ap = attacker_profit(df, ph, end=end, alpha_cost=alpha_cost)
    if len(ap):
        out["leak_paper"] = _chia(float(ap.loc["TOTAL", "paper"]), S)
        out["leak_full"] = _chia(float(ap.loc["TOTAL", "full"]), S)
        out["leak_excess"] = _chia(float(ap.loc["TOTAL", "excess"]), S)
    return out


def summarize(df: pd.DataFrame, end: str = "t_b", alpha_cost: float | None = None) -> dict:
    """Một dict phẳng mọi chỉ số của một vụ: mốc, khoảng thời gian, lift/RV theo pha, độ dời giá,
    thanh khoản, trợ cấp, thiệt hại nạn nhân, lợi nhuận kẻ tấn công, chỉ số dẫn xuất. Vụ không sập → NaN phần sau t_0."""
    ph = phases(df)
    r: dict = {k: ph[k] for k in ("wall_tick_lower", "peak_liquidity", "t_m", "t_50", "t_peak", "t_0",
                                  "t_0_burn", "t_oot", "t_b", "breached", "delta_build", "delta_extract",
                                  "delta_oot")}
    bang = phase_stats(df, ph)
    for ten in PHA:
        for c in ("lift", "lift_trade", "RV", "RV_price", "vol_mean"):
            r[f"{c}_{ten}"] = float(bang.loc[ten, c])
    r.update(price_changes(df, ph))
    sc = subsidy_cost(df)
    r.update(subsidy_total=sc["total"], subsidy_paid=sc["paid"], subsidy_pending=sc["pending"],
             subsidy_clawed=sc["clawed"], subsidy_to_attacker=sc["to_attacker"])
    pl = pool_liquidity(df, ph)
    r.update({f"L_{k}": pl[k] for k in ("mean_before", "mean_post", "ratio_post_before", "drop_at_tb")})
    for k in ("victim_loss_full", "victim_loss_nonalpha", "n_victims", "n_victims_loss",
              "attacker_profit_paper", "attacker_net_cash1", "attacker_profit_full", "main_attacker",
              "attacker_ban_thang", "attacker_profit_excess", "attacker_x_dump", "attacker_farm_volume",
              "attacker_farm_cost", "attacker_farm_subsidy", "attacker_farm_pnl", "attacker_farm_pending"):
        r[k] = NAN
    if ph["breached"]:
        vl = victim_loss(df, ph, end=end)
        if len(vl):
            v = vl.drop(index="TOTAL")
            r.update(victim_loss_full=float(v["loss_full"].sum()),
                     victim_loss_nonalpha=float(v["loss_nonalpha"].sum()),
                     n_victims=len(v), n_victims_loss=int((v["loss_full"] > 0).sum()))
        else:
            r.update(victim_loss_full=0.0, victim_loss_nonalpha=0.0, n_victims=0, n_victims_loss=0)
        r["main_attacker"] = identify_roles(df, ph, end)["main_attacker"]
        ap = attacker_profit(df, ph, end=end, alpha_cost=alpha_cost)
        if len(ap):
            r.update(attacker_profit_paper=float(ap.loc["TOTAL", "paper"]),
                     attacker_net_cash1=float(ap.loc["TOTAL", "net_cash1"]),
                     attacker_profit_full=float(ap.loc["TOTAL", "full"]),
                     attacker_ban_thang=float(ap.loc["TOTAL", "ban_thang"]),
                     attacker_profit_excess=float(ap.loc["TOTAL", "excess"]),
                     attacker_x_dump=float(ap.loc["TOTAL", "x_dump"]),
                     **{f"attacker_{k}": float(ap.loc["TOTAL", k]) for k in
                        ("farm_volume", "farm_cost", "farm_subsidy", "farm_pnl", "farm_pending")})
    r.update({k: v for k, v in derived(df, ph, end, alpha_cost).items() if k != "subsidy_total"})
    meta = df.attrs.get("meta", {})
    r = {**{f"meta_{k}": meta[k] for k in ("seed", "sigma", "Q", "fee") if k in meta}, **r}
    return r


def summarize_many(dfs: list[pd.DataFrame], **kw) -> pd.DataFrame:
    """Bảng nhiều vụ: mỗi log một dòng `summarize` (dùng cho kiểm định RQ1 và bản đồ nhiệt `(σ, Q)`)."""
    return pd.DataFrame([summarize(d, **kw) for d in dfs])

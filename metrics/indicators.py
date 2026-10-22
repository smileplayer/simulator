"""Chỉ số thị trường theo pha (§6.2 bài gốc), chi phí trợ cấp và thanh khoản bể.

Quy ước khối lượng (Đức chốt 14/10/2026): **volume lift chính tính trên `vol_total`** (mọi swap, gồm
`arb`, khớp cách bài gốc đếm mọi dòng non-alpha on-chain); `vol_trade` (bỏ `arb`) chỉ là chỉ số phụ.
Tiền tính bằng token1, thời gian bằng bước (giờ).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from metrics.phases import PHA, wall_liquidity
from metrics.timeseries import build_timeseries, step_frame

LN_CO_SO = math.log(1.0001)


def subsidy_cost(df: pd.DataFrame, attackers: set[str] | None = None) -> dict:
    """Chi phí trợ cấp của nền tảng (token1) từ dòng `subsidy` + khoản trả trễ chưa tới hạn trong meta (CH-2).

    `paid` = Σ dòng `subsidy`; `pending` = `meta["subsidy_pending"]` (đã chốt, chưa tới hạn khi hết kịch bản —
    vẫn là nghĩa vụ của nền tảng); `total` = paid + pending (chỉ số chính); `clawed` = `meta["subsidy_clawed"]`
    (đã hủy nhờ clawback, báo riêng, **không** cộng). `by_owner`: Series đã trả theo owner. `to_attacker` = phần
    trả + treo của owner trong `attackers` (mặc định owner có vai `attacker`), `pending_attacker` từ meta;
    `to_farmers` = total − to_attacker.
    """
    meta = df.attrs.get("meta", {}) or {}
    sb = df[df["kind"] == "subsidy"]
    by_owner = sb.groupby("owner")["amount1"].sum()
    if attackers is None:
        attackers = {o for o in by_owner.index if str(o).split(":")[0] == "attacker"}
    paid = float(sb["amount1"].sum())
    pending = float(meta.get("subsidy_pending", 0.0) or 0.0)
    pend_att = float(meta.get("subsidy_pending_attacker", 0.0) or 0.0)
    to_att = float(by_owner[by_owner.index.isin(attackers)].sum()) + pend_att
    return dict(total=paid + pending, paid=paid, pending=pending, pending_attacker=pend_att,
                clawed=float(meta.get("subsidy_clawed", 0.0) or 0.0), to_attacker=to_att,
                to_farmers=paid + pending - to_att, by_owner=by_owner)


def _trung_binh(s: pd.Series, w: tuple[int, int] | None) -> float:
    """Trung bình của chuỗi theo bước trong cửa sổ (đầu, cuối) bao gồm hai đầu; không có → NaN."""
    if w is None:
        return float("nan")
    x = s[(s.index >= w[0]) & (s.index <= w[1])]
    return float(x.mean()) if len(x) else float("nan")


def pool_liquidity(df: pd.DataFrame, ph: dict) -> dict:
    """Thanh khoản bể: chuỗi `L_active` theo bước; trung bình Before vs `(t_b, t_b+W]`; độ cạn tường tại `t_b`.

    `drop_at_tb` = (L_max − L(t_b)) / L_max với L = thanh khoản một-tick trên tick tường (§6.2.4).
    """
    L = step_frame(df)["L_active"]
    w = ph["windows"]
    mean_before = _trung_binh(L, w["Before"])
    mean_post = _trung_binh(L, w["Post"])
    out = dict(series=L, mean_before=mean_before, mean_post=mean_post,
               ratio_post_before=mean_post / mean_before if mean_before > 0 else float("nan"),
               L_max=float("nan"), L_at_tb=float("nan"), drop_at_tb=float("nan"))
    if ph["t_b"] is not None:
        e = wall_liquidity(df)
        e = e[(e["tick_lower"] == ph["wall_tick_lower"]) & (e["t"] <= ph["t_b"])]
        L_max = float(e.loc[e["t"] >= ph["t_m"], "L_wall"].max())
        L_tb = max(float(e["L_wall"].iloc[-1]), 0.0)
        out.update(L_max=L_max, L_at_tb=L_tb, drop_at_tb=(L_max - L_tb) / L_max)
    return out


def liquidity_excluding(df: pd.DataFrame, ph: dict, bo_vai: tuple[str, ...] = ("attacker", "victim")) -> dict:
    """Thanh khoản đang hoạt động không tính vị thế của các vai `bo_vai` (CH-9, 20/10): `mean_before`, `mean_post` (L).

    Dựng lại từ dòng mint/burn: cuối mỗi bước t, cộng L ròng của mọi vị thế có `tick_lower ≤ tick(t) < tick_upper`
    mà chủ không thuộc `bo_vai` (vai = tiền tố owner trước dấu `:`). `bo_vai = ()` → trùng `L_active` của engine.
    Lý do: `L_active` Post gồm cả vị thế nạn nhân còn nằm trong dải, nên biện pháp đuổi nạn nhân bị đo thành "mất thanh khoản".
    """
    w = ph["windows"]
    s = step_frame(df)
    buoc = [t for k in ("Before", "Post") if w.get(k) is not None for t in range(w[k][0], w[k][1] + 1) if t in s.index]
    out = dict(mean_before=float("nan"), mean_post=float("nan"))
    if not buoc:
        return out
    lp = df[df["kind"].isin(["mint", "burn"])].sort_values(["t", "seq"])
    vai = lp["owner"].astype(str).str.split(":").str[0]
    lp = lp[~vai.isin(bo_vai)]
    dL = np.where(lp["kind"] == "mint", 1.0, -1.0) * lp["liquidity"].astype(float)
    lp = lp.assign(dL=dL)
    L = {}
    for t in sorted(set(buoc)):
        a = lp[lp["t"] <= t]
        tick = int(s.loc[t, "tick"])
        g = a[(a["tick_lower"] <= tick) & (a["tick_upper"] > tick)]
        L[t] = max(float(g["dL"].sum()), 0.0)
    Ls = pd.Series(L)
    out["mean_before"] = _trung_binh(Ls, w["Before"])
    out["mean_post"] = _trung_binh(Ls, w["Post"])
    return out


def vwap(df: pd.DataFrame) -> pd.Series:
    """VWAP theo giờ (token1/token0): Σp_i·v_i / Σv_i, p_i = |amount1|/|amount0| của swap, v_i = |amount1|.

    Giờ không có swap lấy giá bể cuối bước.
    """
    sw = df[(df["kind"] == "swap") & (df["amount0"].abs() > 0)]
    v = sw["amount1"].abs()
    p = v / sw["amount0"].abs()
    tu = (p * v).groupby(sw["t"]).sum()
    mau = v.groupby(sw["t"]).sum()
    P = step_frame(df)["price"].copy()
    vw = (tu / mau).reindex(P.index)
    return vw.fillna(P).rename("vwap")


def _gia_truoc_burn(df: pd.DataFrame, ph: dict) -> float:
    """Giá bể (token1/token0) ngay trước dòng `burn` đầu tiên trên khoảng tường từ `t_0`; không có → NaN."""
    lo, hi = ph["wall_tick_lower"], ph["wall_tick_upper"]
    ev = df.sort_values(["t", "seq"]).reset_index(drop=True)
    b = ev.index[(ev["kind"] == "burn") & (ev["t"] >= ph["t_0"]) & (ev["tick_lower"] == lo)
                 & (ev["tick_upper"] == hi)]
    if len(b) == 0 or b[0] == 0:
        return float("nan")
    return float(ev.loc[b[0] - 1, "sqrt_price_after"]) ** 2


def price_changes(df: pd.DataFrame, ph: dict) -> dict:
    """Độ dời giá (§6.2.3). Chính (bài gốc, VWAP theo giờ): `before_price_change` = (P(t_m) − P(t_m−1))/P(t_m),
    `attack_price_change` = (P̄(t_b) − P(t_0))/P(t_0) với P̄(t_b) = trung bình VWAP giờ t_b và t_b+1.
    Phụ (đề nghị của C): `attack_price_change_preburn` — cùng tử số, mốc là giá bể ngay trước burn tường đầu tiên
    (VWAP giờ t_0 đã gồm cú xả nên ước thấp độ sập)."""
    P = vwap(df)
    t_m, t_0, t_b = ph["t_m"], ph["t_0"], ph["t_b"]
    before = (P[t_m] - P[t_m - 1]) / P[t_m] if t_m - 1 in P.index else float("nan")
    attack = preburn = float("nan")
    if t_b is not None:
        P_b = (P[t_b] + P.get(t_b + 1, P[t_b])) / 2
        attack = (P_b - P[t_0]) / P[t_0]
        p0 = _gia_truoc_burn(df, ph)
        preburn = (P_b - p0) / p0
    return dict(before_price_change=float(before), attack_price_change=float(attack),
                attack_price_change_preburn=float(preburn))


def _rv_theo_pha(df: pd.DataFrame, ph: dict) -> pd.DataFrame:
    """RV mỗi pha = √Σr_i² qua các swap liên tiếp: `RV` dùng r = ln(1.0001)·Δtick (như bài gốc),
    `RV_price` dùng r = 2·Δln√P (mịn hơn, thấy cả dao động trong tick)."""
    sw = df[df["kind"] == "swap"].sort_values(["t", "seq"])
    r_tick = LN_CO_SO * sw["tick_after"].astype(float).diff()
    r_gia = 2 * np.log(sw["sqrt_price_after"].astype(float)).diff()
    rows = {}
    for ten in PHA:
        w = ph["windows"][ten]
        if w is None:
            rows[ten] = dict(RV=np.nan, RV_price=np.nan)
            continue
        m = (sw["t"] >= w[0]) & (sw["t"] <= w[1])
        rows[ten] = dict(RV=float(np.sqrt(np.nansum(r_tick[m] ** 2))),
                         RV_price=float(np.sqrt(np.nansum(r_gia[m] ** 2))))
    return pd.DataFrame.from_dict(rows, orient="index")


def phase_stats(df: pd.DataFrame, ph: dict, eps: float = 1e-9) -> pd.DataFrame:
    """Bảng theo pha (Before/Prep/Attack/Post): số giờ, khối lượng trung bình/giờ, **`lift`** (chính,
    = μ_s/max(μ_Before, eps) trên `vol_total`), `lift_trade` (phụ, trên `vol_trade`), `RV`, `RV_price`."""
    ts = build_timeseries(df)
    w = ph["windows"]
    mu0 = _trung_binh(ts["vol_total"], w["Before"])
    mu0_tr = _trung_binh(ts["vol_trade"], w["Before"])
    rows = {}
    for ten in PHA:
        mu = _trung_binh(ts["vol_total"], w[ten])
        mu_tr = _trung_binh(ts["vol_trade"], w[ten])
        rows[ten] = dict(
            hours=0 if w[ten] is None else int(((ts.index >= w[ten][0]) & (ts.index <= w[ten][1])).sum()),
            vol_mean=mu, lift=mu / max(mu0, eps),
            vol_trade_mean=mu_tr, lift_trade=mu_tr / max(mu0_tr, eps))
    return pd.DataFrame.from_dict(rows, orient="index").join(_rv_theo_pha(df, ph))

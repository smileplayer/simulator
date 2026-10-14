"""Vai trò, thiệt hại nạn nhân và lợi nhuận kẻ tấn công (§5 bài gốc + mục 5 kế hoạch simulator).

Theo bài gốc, vai trò suy ra từ hành vi on-chain, **không** dùng nhãn `role` của log:
- victim: còn thanh khoản > 0 trên tick tường tại `t_end`;
- wall provider: vừa mint vừa burn trên tick tường trong `[t_m, t_end]`;
- pressure trader: có ít nhất một swap chiều sập (bán token0 lấy token1) trong `[t_0, t_end]`;
- attacker = wall provider ∩ pressure trader; main attacker = thị phần tường lớn nhất ngay trước `t_0`.
`t_end` ∈ {`t_b` (mặc định), `t_oot`}. Mốc theo bước (giờ): sự kiện ở bước `t_end` được tính là "trước".
Tiền tính bằng token1; token0 (alpha) còn lại định giá bằng VWAP các swap trong `[t_b, t_b+1]`.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from metrics.indicators import vwap

CO_SO = 1.0001


def _t_end(ph: dict, end: str) -> int:
    """Bước kết thúc cửa sổ sập: `ph["t_b"]` hoặc `ph["t_oot"]`."""
    t = ph["t_b"] if end == "t_b" else ph["t_oot"]
    if t is None:
        raise ValueError(f"vụ không có {end} (giá không sập đủ ngưỡng)")
    return int(t)


def _lp_tuong(df: pd.DataFrame, ph: dict) -> pd.DataFrame:
    """Các dòng mint/burn trên đúng khoảng tường, sắp theo (t, seq), thêm `dL` (+mint/−burn)."""
    lo, hi = ph["wall_tick_lower"], ph["wall_tick_upper"]
    mb = df[df["kind"].isin(["mint", "burn"]) & (df["tick_lower"] == lo) & (df["tick_upper"] == hi)]
    mb = mb.sort_values(["t", "seq"]).copy()
    mb["dL"] = np.where(mb["kind"] == "mint", 1.0, -1.0) * mb["liquidity"].astype(float)
    return mb


def _swap_sap(df: pd.DataFrame, t_a: int, t_b: int) -> pd.DataFrame:
    """Swap chiều sập (token0 vào bể, token1 ra) trong `[t_a, t_b]`."""
    sw = df[(df["kind"] == "swap") & (df["t"] >= t_a) & (df["t"] <= t_b)]
    return sw[(sw["amount0"] > 0) & (sw["amount1"] < 0)]


def identify_roles(df: pd.DataFrame, ph: dict, end: str = "t_b") -> dict:
    """Suy vai trò như bài gốc. Trả dict tập owner: `victims`, `wall_providers`, `pressure_traders`,
    `attackers`, và `main_attacker` (str hoặc None), `wall_share` (Series thị phần tường trước `t_0`)."""
    te = _t_end(ph, end)
    mb = _lp_tuong(df, ph)
    L_cuoi = mb[mb["t"] <= te].groupby("owner")["dL"].sum()
    victims = set(L_cuoi[L_cuoi > 1e-9 * max(1.0, L_cuoi.abs().max())].index)
    trong = mb[(mb["t"] >= ph["t_m"]) & (mb["t"] <= te)]
    wall_prov = set(trong.loc[trong["kind"] == "mint", "owner"]) & set(trong.loc[trong["kind"] == "burn", "owner"])
    pressure = set(_swap_sap(df, ph["t_0"], te)["owner"])
    attackers = wall_prov & pressure
    L_truoc = mb[mb["t"] < ph["t_0"]].groupby("owner")["dL"].sum().clip(lower=0)
    share = L_truoc / L_truoc.sum() if L_truoc.sum() > 0 else L_truoc
    ung_vien = share[share.index.isin(attackers)]
    main = str(ung_vien.idxmax()) if len(ung_vien) else None
    return dict(victims=victims, wall_providers=wall_prov, pressure_traders=pressure,
                attackers=attackers, main_attacker=main, wall_share=share.sort_values(ascending=False))


def _luong_vi_the(L: float, lo: int, hi: int, z: float) -> tuple[float, float]:
    """(token0, token1) của thanh khoản L trên [lo, hi) tại √P = z."""
    za, zb = CO_SO ** (lo / 2), CO_SO ** (hi / 2)
    zc = min(max(z, za), zb)
    return L * (1 / zc - 1 / zb), L * (zc - za)


def victim_loss(df: pd.DataFrame, ph: dict, end: str = "t_b", victims: set[str] | None = None) -> pd.DataFrame:
    """Thiệt hại từng victim (token1) + dòng `TOTAL`. `victims` = None → suy như bài gốc.

    Cột: nạp `x_dep, y_dep`; nhận lại `x_back, y_back` (burn tới `t_end` + phần còn kẹt theo giá cuối `t_end`);
    `p_alpha` (VWAP [t_b, t_b+1]); `E_nonalpha` = y_dep − y_back − p_alpha·x_back (bài gốc, chỉ đếm non-alpha);
    `E_full` = (y_dep + p_alpha·x_dep) − (y_back + p_alpha·x_back) (kế hoạch, so với "ôm" định giá tại t_b);
    `loss_nonalpha`, `loss_full` = max{0, E}; `fees` = phí đã collect (token1, token0 theo p_alpha) — tách riêng, không trừ.
    """
    te = _t_end(ph, end)
    if victims is None:
        victims = identify_roles(df, ph, end)["victims"]
    P = vwap(df)
    t_b = _t_end(ph, "t_b")
    p_alpha = float((P[t_b] + P.get(t_b + 1, P[t_b])) / 2)
    s = df[df["kind"] == "step"].sort_values(["t", "seq"]).groupby("t").last()
    z_end = float(s.loc[te, "sqrt_price_after"])

    lp = df[df["kind"].isin(["mint", "burn"]) & (df["t"] <= te) & df["owner"].isin(victims)].sort_values(["t", "seq"])
    col = df[(df["kind"] == "collect") & (df["t"] <= te) & df["owner"].isin(victims)]
    rows = {}
    for u in sorted(victims):
        a = lp[lp["owner"] == u]
        m, b = a[a["kind"] == "mint"], a[a["kind"] == "burn"]
        x_dep, y_dep = float(m["amount0"].sum()), float(m["amount1"].sum())
        x_back, y_back = float(-b["amount0"].sum()), float(-b["amount1"].sum())
        for pid, g in a.groupby("position_id"):                       # phần còn kẹt trong vị thế
            L = float((np.where(g["kind"] == "mint", 1.0, -1.0) * g["liquidity"]).sum())
            if L > 0:
                x, y = _luong_vi_the(L, int(g["tick_lower"].iloc[0]), int(g["tick_upper"].iloc[0]), z_end)
                x_back, y_back = x_back + x, y_back + y
        c = col[col["owner"] == u]
        fees = float(c["fee1"].sum() + p_alpha * c["fee0"].sum())
        E_na = y_dep - y_back - p_alpha * x_back
        E_full = (y_dep + p_alpha * x_dep) - (y_back + p_alpha * x_back)
        rows[u] = dict(x_dep=x_dep, y_dep=y_dep, x_back=x_back, y_back=y_back, p_alpha=p_alpha,
                       E_nonalpha=E_na, E_full=E_full, loss_nonalpha=max(0.0, E_na),
                       loss_full=max(0.0, E_full), fees=fees)
    out = pd.DataFrame.from_dict(rows, orient="index")
    if len(out):
        tong = out.drop(columns="p_alpha").sum()
        tong["p_alpha"] = p_alpha
        out.loc["TOTAL"] = tong
    return out


def attacker_profit(df: pd.DataFrame, ph: dict, end: str = "t_b", attackers: set[str] | None = None,
                    alpha_cost: float | None = None) -> pd.DataFrame:
    """Lợi nhuận kẻ tấn công (token1), đo từ dòng tiền, **độc lập** với thiệt hại nạn nhân. Một dòng/attacker + `TOTAL`.

    `paper` = Σ token1 nhận từ swap chiều sập trong `[t_0, t_end]` (đúng §5 bài gốc).
    `net_cash1` = dòng token1 ròng về attacker trong `[t_m, t_end]` (mint/burn/swap/collect/subsidy).
    `full` = net_cash1 + Δtoken0 × `alpha_cost` (mặc định giá bể cuối bước `t_0 − 1`, tức giá vốn cơ hội của alpha).
    """
    te = _t_end(ph, end)
    if attackers is None:
        attackers = identify_roles(df, ph, end)["attackers"]
    if alpha_cost is None:
        s = df[df["kind"] == "step"].groupby("t")["sqrt_price_after"].last()
        alpha_cost = float(s[ph["t_0"] - 1] ** 2)
    sap = _swap_sap(df, ph["t_0"], te)
    cua_so = df[(df["t"] >= ph["t_m"]) & (df["t"] <= te)]
    rows = {}
    for u in sorted(attackers):
        a = cua_so[cua_so["owner"] == u]
        sub = a["kind"] == "subsidy"
        cash1 = float(-a.loc[~sub, "amount1"].sum() + a["fee1"].where(a["kind"] == "collect", 0).sum()
                      + a.loc[sub, "amount1"].sum())
        d0 = float(-a["amount0"].sum() + a["fee0"].where(a["kind"] == "collect", 0).sum())
        paper = float(-sap.loc[sap["owner"] == u, "amount1"].sum())
        rows[u] = dict(paper=paper, net_cash1=cash1, delta_token0=d0, alpha_cost=alpha_cost,
                       full=cash1 + d0 * alpha_cost)
    out = pd.DataFrame.from_dict(rows, orient="index")
    if len(out):
        tong = out.drop(columns="alpha_cost").sum()
        tong["alpha_cost"] = alpha_cost
        out.loc["TOTAL"] = tong
    return out

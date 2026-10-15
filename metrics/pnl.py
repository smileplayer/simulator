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


def _gia_ngoai(df: pd.DataFrame) -> pd.Series:
    """P_e theo bước (token1/token0) từ dòng `step`; thiếu thì lấy giá bể cuối bước."""
    s = df[df["kind"] == "step"].sort_values(["t", "seq"]).groupby("t").last()
    pe = s["external_price"].astype(float) if "external_price" in s else pd.Series(np.nan, index=s.index)
    return pe.fillna(s["sqrt_price_after"].astype(float) ** 2)


def farm_pnl(df: pd.DataFrame, owner: str) -> dict:
    """Lãi săn trợ cấp của `owner` trên cả log (token1): lệnh mua (`amount1 > 0`, token1 vào bể) = lệnh farm.

    `farm_volume` = Σ v (token1 vào, gồm phí); `farm_cost` = Σ (v − P_e·x) với x = token0 nhận, P_e = giá ngoài
    farmer thấy khi giao dịch (dòng `step` bước t; bước có cú xả của chính owner thì lấy P_e(t−1) vì bộ chạy
    neo lại P_e theo giá bể sau cú xả); `farm_subsidy` = Σ dòng `subsidy` đã trả; `farm_pnl` = subsidy − cost.
    Khoản treo/đã hủy không có dòng log — xem `subsidy_cost`.
    """
    a = df[df["owner"] == owner]
    mua = a[(a["kind"] == "swap") & (a["amount1"] > 0) & (a["amount0"] < 0)]
    ban_t = set(a.loc[(a["kind"] == "swap") & (a["amount0"] > 0), "t"].astype(int))
    pe = _gia_ngoai(df)
    gia = [float(pe.get(t - 1, pe[t])) if t in ban_t else float(pe[t]) for t in mua["t"].astype(int)]
    v, x = mua["amount1"].astype(float), -mua["amount0"].astype(float)
    cost = float((v - np.asarray(gia) * x).sum()) if len(mua) else 0.0
    sub = float(a.loc[a["kind"] == "subsidy", "amount1"].sum())
    return dict(farm_volume=float(v.sum()), farm_token0=float(x.sum()), farm_cost=cost,
                farm_subsidy=sub, farm_pnl=sub - cost)


def _truoc_burn_tuong(df: pd.DataFrame, ph: dict) -> int | None:
    """Chỉ số (trong log sắp theo t, seq) của dòng burn tường đầu tiên từ `t_0`; không có → None."""
    lo, hi = ph["wall_tick_lower"], ph["wall_tick_upper"]
    ev = df.sort_values(["t", "seq"]).reset_index(drop=True)
    b = ev.index[(ev["kind"] == "burn") & (ev["t"] >= ph["t_0"]) & (ev["tick_lower"] == lo) & (ev["tick_upper"] == hi)]
    return int(b[0]) if len(b) else None


def ban_thang(df: pd.DataFrame, ph: dict, x_ban: float, bo_owner: set[str] | frozenset = frozenset(),
              alpha_cost: float | None = None, fee: float | None = None) -> dict:
    """Phản thực Theorem 6: bán thẳng `x_ban` token0 vào bể **không tường, không victim** ngay trước lần burn
    tường đầu tiên (token1).

    Tái dựng từ log mọi vị thế còn mở tại thời điểm đó, bỏ vị thế trên đúng khoảng tường (tường + victim) và mọi
    vị thế của `bo_owner`; dựng `engine.Pool` cùng giá, `quote_swap` bán `x_ban` (gồm phí) với giới hạn
    z̄ = √(c_A/(1−f)) nếu biết `alpha_cost`. Trả `out` (token1 nhận), `x_sold`, `x_left`, `value`
    = out + x_left·alpha_cost (phần không bán được giữ lại theo giá vốn), `L_nen` = L_active tái dựng, `P_truoc`.
    """
    from engine import Pool                                    # chỉ dùng để tính bán thẳng, không đổi log
    meta = df.attrs.get("meta", {})
    if fee is None:
        fee = meta.get("fee")
    if fee is None:
        sw = df[(df["kind"] == "swap") & (df["amount0"] > 0)]
        fee = float((sw["fee0"] / sw["amount0"]).median())
    i = _truoc_burn_tuong(df, ph)
    if i is None or i == 0 or x_ban <= 0:
        return dict(out=0.0, x_sold=0.0, x_left=float(max(x_ban, 0.0)), value=float("nan"), L_nen=float("nan"),
                    P_truoc=float("nan"))
    ev = df.sort_values(["t", "seq"]).reset_index(drop=True).iloc[:i]
    z = float(ev["sqrt_price_after"].iloc[-1])
    lo, hi = ph["wall_tick_lower"], ph["wall_tick_upper"]
    mb = ev[ev["kind"].isin(["mint", "burn"])].copy()
    mb["dL"] = np.where(mb["kind"] == "mint", 1.0, -1.0) * mb["liquidity"].astype(float)
    pool = Pool(float(fee), z)
    for pid, g in mb.groupby("position_id"):
        L = float(g["dL"].sum())
        a, b, u = int(g["tick_lower"].iloc[0]), int(g["tick_upper"].iloc[0]), str(g["owner"].iloc[0])
        if L <= 1e-12 * max(1.0, float(g["liquidity"].abs().max())) or (a == lo and b == hi) or u in bo_owner:
            continue
        pool.mint(u, a, b, L)
    lim = None
    if alpha_cost is not None and alpha_cost > 0:
        lim = math.sqrt(alpha_cost / (1 - fee))
        if lim >= z:                                           # đã dưới giá vốn: không bán
            return dict(out=0.0, x_sold=0.0, x_left=float(x_ban), value=float(x_ban * alpha_cost),
                        L_nen=float(pool.liquidity), P_truoc=z * z)
    r = pool.quote_swap(True, amount_in=float(x_ban), sqrt_price_limit=lim)
    x_left = max(float(x_ban) - r.amount_in, 0.0)
    val = r.amount_out + x_left * (alpha_cost or 0.0)
    return dict(out=float(r.amount_out), x_sold=float(r.amount_in), x_left=x_left, value=float(val),
                L_nen=float(pool.liquidity), P_truoc=z * z)


def attacker_profit(df: pd.DataFrame, ph: dict, end: str = "t_b", attackers: set[str] | None = None,
                    alpha_cost: float | None = None, victims: set[str] | None = None) -> pd.DataFrame:
    """Lợi nhuận kẻ tấn công (token1), đo từ dòng tiền, **độc lập** với thiệt hại nạn nhân. Một dòng/attacker + `TOTAL`.

    Phần tấn công (bỏ lệnh farm = lệnh mua token0 và dòng `subsidy`, xem `farm_pnl`):
    `paper` = Σ token1 nhận từ swap chiều sập trong `[t_0, t_end]` (đúng §5 bài gốc); `x_dump` = token0 đã bán;
    `net_cash1` = dòng token1 ròng của phần tấn công trong `[t_m, t_end]` (mint/burn/swap bán/collect);
    `delta_token0` = token0 ròng của phần tấn công; `full` = net_cash1 + Δtoken0 × `alpha_cost` + `farm_pnl`
    (`alpha_cost` mặc định `c_A` trong meta; không có thì giá bể cuối bước `t_0 − 1`).
    Bán thẳng (Theorem 6, `ban_thang`): `ban_thang` = giá trị khi bán cùng `x_dump` vào bể bỏ tường + victim;
    `excess` = paper − ban_thang = lợi nhuận **tăng thêm** nhờ tấn công.
    Farm (CH-6): `farm_volume`, `farm_cost`, `farm_subsidy`, `farm_pnl` trên cả log; `farm_pending` =
    `meta["subsidy_pending_attacker"]` (gán cho `attacker:0`, không cộng vào `full`).
    """
    te = _t_end(ph, end)
    if attackers is None or victims is None:
        vai = identify_roles(df, ph, end)
        attackers = vai["attackers"] if attackers is None else attackers
        victims = vai["victims"] if victims is None else victims
    meta = df.attrs.get("meta", {})
    if alpha_cost is None:
        alpha_cost = meta.get("c_A")
    if alpha_cost is None:
        s = df[df["kind"] == "step"].groupby("t")["sqrt_price_after"].last()
        alpha_cost = float(s[ph["t_0"] - 1] ** 2)
    sap = _swap_sap(df, ph["t_0"], te)
    cua_so = df[(df["t"] >= ph["t_m"]) & (df["t"] <= te)]
    farm_lenh = (cua_so["kind"] == "swap") & (cua_so["amount1"] > 0) & (cua_so["amount0"] < 0)
    cua_so = cua_so[~farm_lenh & (cua_so["kind"] != "subsidy")]
    rows = {}
    for u in sorted(attackers):
        a = cua_so[cua_so["owner"] == u]
        cash1 = float(-a["amount1"].sum() + a["fee1"].where(a["kind"] == "collect", 0).sum())
        d0 = float(-a["amount0"].sum() + a["fee0"].where(a["kind"] == "collect", 0).sum())
        s_u = sap[sap["owner"] == u]
        paper, x_dump = float(-s_u["amount1"].sum()), float(s_u["amount0"].sum())
        bt = ban_thang(df, ph, x_dump, bo_owner=set(attackers) | set(victims), alpha_cost=alpha_cost)
        fm = farm_pnl(df, u)
        rows[u] = dict(paper=paper, x_dump=x_dump, ban_thang=bt["value"], ban_thang_x_sold=bt["x_sold"],
                       excess=paper - bt["value"], net_cash1=cash1, delta_token0=d0, alpha_cost=alpha_cost,
                       **fm, farm_pending=float(meta.get("subsidy_pending_attacker", 0.0) or 0.0)
                       if u == "attacker:0" else 0.0,
                       full=cash1 + d0 * alpha_cost + fm["farm_pnl"])
    out = pd.DataFrame.from_dict(rows, orient="index")
    if len(out):
        tong = out.drop(columns="alpha_cost").sum()
        tong["alpha_cost"] = alpha_cost
        out.loc["TOTAL"] = tong
    return out

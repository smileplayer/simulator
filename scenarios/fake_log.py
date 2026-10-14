"""Log giả đúng định dạng INTERFACE mục 4, để vai B viết `metrics/` trước khi có engine thật.

Kịch bản (1 bước = 1 giờ): nền 48 bước → dựng tường một tick (t_m) → farmer chỉ mua
(arb bán ngược lại), victim mint dần vào tick tường → rút tường (t_0) → xả xuyên nhiều tick → post.
Số liệu chỉ cần hợp lý về hình dạng, không theo mô hình cân bằng của bài gốc.

Giá/tick/L_active trong log được tính bằng một bể giả cross-tick đơn giản (`_BeGia`), không
dùng `engine/` của vai A.

Chạy: `python -m scenarios.fake_log [seed] [duong_dan.csv]`.
"""
from __future__ import annotations

import math
import sys

import numpy as np
import pandas as pd

COT = [
    "t", "seq", "kind", "owner", "role", "position_id", "tick_lower", "tick_upper", "liquidity",
    "amount0", "amount1", "fee0", "fee1", "sqrt_price_after", "tick_after",
    "liquidity_active_after", "external_price",
]

CO_SO = 1.0001


def _z_tai_tick(i: int) -> float:
    """√P tại biên dưới của tick i."""
    return CO_SO ** (i / 2)


def _tick_cua_z(z: float) -> int:
    """Tick chứa giá √P = z."""
    return math.floor(math.log(z * z) / math.log(CO_SO) + 1e-9)


class _BeGia:
    """Bể CLMM tối giản: swap đi từng tick, phí chia pro-rata cho vị thế đang hoạt động."""

    def __init__(self, fee: float, z: float):
        self.fee = fee
        self.z = z
        self.tick = _tick_cua_z(z)
        self.vi_the: dict[int, dict] = {}
        self._id = 0
        self.t = 0
        self.seq = 0
        self.dong: list[dict] = []

    # ---- tiện ích ----
    def L_tai(self, i: int) -> float:
        """Thanh khoản hoạt động khi giá ở tick i."""
        return sum(p["L"] for p in self.vi_the.values() if p["lo"] <= i < p["hi"])

    def _luong(self, p: dict, L: float) -> tuple[float, float]:
        """(token0, token1) ứng với thanh khoản L của vị thế p tại giá hiện tại."""
        za, zb = _z_tai_tick(p["lo"]), _z_tai_tick(p["hi"])
        z = min(max(self.z, za), zb)
        return L * (1 / z - 1 / zb), L * (z - za)

    def _ghi(self, **kw) -> None:
        dong = dict.fromkeys(COT, np.nan)
        dong.update(amount0=0.0, amount1=0.0, fee0=0.0, fee1=0.0)
        dong.update(kw)
        dong["t"], dong["seq"] = self.t, self.seq
        dong["role"] = dong["owner"].split(":")[0]
        dong["sqrt_price_after"] = self.z
        dong["tick_after"] = self.tick
        dong["liquidity_active_after"] = self.L_tai(self.tick)
        self.dong.append(dong)
        self.seq += 1

    def sang_buoc(self, t: int) -> None:
        self.t, self.seq = t, 0

    # ---- thao tác ----
    def mint(self, owner: str, lo: int, hi: int, L: float) -> int:
        self._id += 1
        p = dict(owner=owner, lo=lo, hi=hi, L=L, phi0=0.0, phi1=0.0)
        self.vi_the[self._id] = p
        a0, a1 = self._luong(p, L)
        self._ghi(kind="mint", owner=owner, position_id=self._id, tick_lower=lo, tick_upper=hi,
                  liquidity=L, amount0=a0, amount1=a1)
        return self._id

    def burn(self, pid: int) -> None:
        p = self.vi_the[pid]
        a0, a1 = self._luong(p, p["L"])
        L = p["L"]
        p["L"] = 0.0
        self._ghi(kind="burn", owner=p["owner"], position_id=pid, tick_lower=p["lo"],
                  tick_upper=p["hi"], liquidity=L, amount0=-a0, amount1=-a1)

    def collect(self, pid: int) -> None:
        p = self.vi_the[pid]
        self._ghi(kind="collect", owner=p["owner"], position_id=pid, fee0=p["phi0"], fee1=p["phi1"])
        p["phi0"] = p["phi1"] = 0.0

    def swap(self, owner: str, zero_for_one: bool, amount_in: float | None = None,
             z_limit: float | None = None) -> None:
        """Swap cross-tick; dừng khi hết amount_in (đã gồm phí), chạm z_limit, hoặc hết thanh khoản."""
        con = math.inf if amount_in is None else amount_in
        vao = ra = phi = 0.0
        for _ in range(100_000):
            if con <= 1e-12:
                break
            if z_limit is not None and ((zero_for_one and self.z <= z_limit) or
                                        (not zero_for_one and self.z >= z_limit)):
                break
            L = self.L_tai(self.tick)
            if L <= 0:
                break
            if zero_for_one:
                z_bien = _z_tai_tick(self.tick)
                z_dich = z_bien if z_limit is None else max(z_bien, z_limit)
                can = L * (1 / z_dich - 1 / self.z) / (1 - self.fee)
            else:
                z_bien = _z_tai_tick(self.tick + 1)
                z_dich = z_bien if z_limit is None else min(z_bien, z_limit)
                can = L * (z_dich - self.z) / (1 - self.fee)
            dung = min(can, con)
            rong = dung * (1 - self.fee)
            if dung < can:
                z_moi = 1 / (1 / self.z + rong / L) if zero_for_one else self.z + rong / L
            else:
                z_moi = z_dich
            ra += L * (self.z - z_moi) if zero_for_one else L * (1 / self.z - 1 / z_moi)
            f = dung * self.fee
            for p in self.vi_the.values():
                if p["L"] > 0 and p["lo"] <= self.tick < p["hi"]:
                    p["phi0" if zero_for_one else "phi1"] += f * p["L"] / L
            vao, phi, con = vao + dung, phi + f, con - dung
            self.z = z_moi
            if dung >= can and z_moi == z_bien:          # chạm biên → sang tick kế
                self.tick += -1 if zero_for_one else 1
        if zero_for_one:
            self._ghi(kind="swap", owner=owner, amount0=vao, amount1=-ra, fee0=phi)
        else:
            self._ghi(kind="swap", owner=owner, amount0=-ra, amount1=vao, fee1=phi)

    def step(self, p_e: float) -> None:
        self._ghi(kind="step", owner="platform", external_price=p_e)


def make_fake_log(seed: int = 0) -> pd.DataFrame:
    """Sinh một vụ tấn công giả, trả DataFrame đúng cột INTERFACE mục 4 (tiền tính bằng token1).

    Mốc đúng của kịch bản để trong `df.attrs["meta"]` (t_m, t_0, wall_tick, …) cho B đối chiếu.
    """
    rng = np.random.default_rng(seed)
    fee, sigma, Q, cua_so = 0.0025, 0.02, 25_000.0, 24
    t_m, t_dinh, t_0, so_buoc = 48, 72, 144, 192
    P0 = 0.5
    be = _BeGia(fee, math.sqrt(P0))

    L_A = 5.0e8
    tuong: list[int] = []
    victim: dict[str, int] = {}
    n_victim, n_farmer = 3, 3
    t_victim = sorted(int(x) for x in rng.integers(t_m + 10, t_0 - 20, size=n_victim))
    L_victim = rng.uniform(0.2, 0.5, size=n_victim) * L_A
    v_cua_so = {f"farmer:{k}": 0.0 for k in range(n_farmer)}
    p_e = P0
    wall_tick = None

    for t in range(so_buoc):
        be.sang_buoc(t)
        if t == 0:                                       # thanh khoản nền rộng (LP thụ động)
            be.mint("bg:1", be.tick - 20_000, be.tick + 20_000, 1.0e6)
        pha = "nen" if t < t_m else "prep" if t < t_0 else "attack" if t <= t_0 + 1 else "post"

        if t == t_m:                                     # tường dựng ở tick hiện tại
            wall_tick = be.tick

        # giá ngoài
        if pha == "nen":
            p_e *= math.exp(rng.normal(0, 0.002))
        elif pha == "prep":
            p_e = (_z_tai_tick(wall_tick) * 0.5 + _z_tai_tick(wall_tick + 1) * 0.5) ** 2
        elif pha == "post":
            p_e *= math.exp(rng.normal(0, 0.015))

        # giao dịch nền
        so_lenh, co = {"nen": (4, 800), "prep": (2, 800), "attack": (1, 600), "post": (2, 450)}[pha]
        for k in range(so_lenh):
            mua = bool(rng.random() < 0.5)
            v = co * rng.lognormal(0, 0.4)
            be.swap("bg:0", zero_for_one=not mua, amount_in=v if mua else v / (be.z ** 2))

        # attacker dựng tường (hai đợt)
        if t == t_m:
            tuong.append(be.mint("attacker:0", wall_tick, wall_tick + 1, 0.6 * L_A))
        if t == t_dinh:
            tuong.append(be.mint("attacker:0", wall_tick, wall_tick + 1, 0.4 * L_A))

        # farmer chỉ mua (arb bán ngược lại cuối bước)
        if pha == "prep":
            for ten in v_cua_so:
                v = 600 * rng.lognormal(0, 0.3)
                be.swap(ten, zero_for_one=False, amount_in=v)
                v_cua_so[ten] += v

        # victim mint vào tick tường
        for k, tv in enumerate(t_victim):
            if t == tv:
                victim[f"victim:{k}"] = be.mint(f"victim:{k}", wall_tick, wall_tick + 1, L_victim[k])

        # attacker rút tường rồi xả
        if t == t_0:
            for pid in tuong:
                be.burn(pid)
                be.collect(pid)
        if pha == "attack":
            for _ in range(3 if t == t_0 else 2):
                be.swap("attacker:0", zero_for_one=True, amount_in=rng.uniform(40_000, 70_000))
            p_e = be.z ** 2

        # một victim rút muộn
        if t == so_buoc - 12 and "victim:2" in victim:
            be.burn(victim["victim:2"])
            be.collect(victim["victim:2"])

        # arbitrageur kéo giá về P_e (tắt trong pha attack)
        if pha != "attack":
            z_e = math.sqrt(p_e)
            if abs(z_e / be.z - 1) > 1e-9:
                be.swap("arb:0", zero_for_one=z_e < be.z, z_limit=z_e)

        # trợ cấp cuối cửa sổ
        if (t + 1) % cua_so == 0 and any(v > 0 for v in v_cua_so.values()):
            for ten, v in v_cua_so.items():
                if v > 0:
                    be._ghi(kind="subsidy", owner=ten, amount1=sigma * min(v, Q))
                v_cua_so[ten] = 0.0

        be.step(p_e)

    df = pd.DataFrame(be.dong, columns=COT)
    for c in ("position_id", "tick_lower", "tick_upper"):
        df[c] = df[c].astype("Int64")
    df["tick_after"] = df["tick_after"].astype(int)
    df.attrs["meta"] = dict(seed=seed, fee=fee, sigma=sigma, Q=Q, subsidy_window=cua_so,
                            t_m=t_m, t_peak_wall=t_dinh, t_0=t_0, steps=so_buoc,
                            wall_tick=wall_tick, L_A=L_A, victim_mint_t=t_victim, P0=P0)
    return df


if __name__ == "__main__":
    s = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    df = make_fake_log(s)
    if len(sys.argv) > 2:
        df.to_csv(sys.argv[2], index=False)
    print(df.groupby(["kind", "role"]).size().to_string())
    print(df.attrs["meta"])

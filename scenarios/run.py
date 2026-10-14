"""Bộ chạy kịch bản (INTERFACE mục 3): ghép bể engine thật + giao dịch nền + farmer + victim + attacker + arb.

Thứ tự trong mỗi bước t: đặt pool.t → giao dịch nền bg:0 → farmer → victim → attacker → arb:0 (tắt khi
attacker đang xả) → trả trợ cấp cuối cửa sổ → dòng `step`. Bước cuối: collect phí cho mọi vị thế LP.

Chạy: `python -m scenarios.run scenarios/configs/co_so.json [seed] [duong_dan.csv]`.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from agents.arb import Arbitrageur
from agents.attacker import Attacker
from agents.farmer import Farmer, thuong_log, thuong_tuyen_tinh
from agents.victim import VictimThichNghi, VictimToanTri
from engine import MAX_TICK, MIN_TICK, EventLog, Pool, sqrt_price_at_tick, tick_at_sqrt_price

THU_MUC_CONFIG = Path(__file__).parent / "configs"


class ThiTruongKichBan:
    """Giá ngoài P_e(t) (token1/token0): bước ngẫu nhiên log-chuẩn với độ biến động đổi được theo pha.

    Bộ chạy `neo` giá vào một mức (giữa tick tường khi Prep, giá bể khi xả) và đổi `vol` khi sang pha.
    """

    def __init__(self, P0: float, vol: float, rng: np.random.Generator):
        self.duong = [P0]
        self.vol = vol
        self.rng = rng

    def external_price(self, t: int) -> float:
        """P_e tại bước t; sinh thêm đường giá nếu chưa có."""
        while len(self.duong) <= t:
            self.duong.append(self.duong[-1] * math.exp(self.rng.normal(0.0, self.vol)))
        return self.duong[t]

    def neo(self, t: int, gia: float) -> None:
        """Đặt P_e(t) = gia, bỏ phần đường giá đã sinh sau t."""
        self.external_price(t)
        del self.duong[t:]
        self.duong.append(gia)


def nap_config(ten: str | Path) -> dict:
    """Đọc config JSON; nhận đường dẫn hoặc tên file trong scenarios/configs/."""
    p = Path(ten)
    if not p.exists():
        p = THU_MUC_CONFIG / (p.name if p.suffix else p.name + ".json")
    return json.loads(p.read_text(encoding="utf-8"))


def dai_nen(P0: float, band: float, n: int) -> list[tuple[int, int]]:
    """n khoảng lồng nhau quanh P0: khoảng k phủ giá [P0·(1−band·k/n), P0·(1+band·k/n)] (tick).

    Mỗi khoảng nhận L_bg/n nên mật độ thanh khoản cao nhất ở giữa, bằng 0 ngoài ±band.
    """
    ds = []
    for k in range(1, n + 1):
        r = band * k / n
        lo = tick_at_sqrt_price(math.sqrt(P0 * (1 - r)))
        hi = tick_at_sqrt_price(math.sqrt(P0 * (1 + r))) + 1
        ds.append((lo, hi))
    return ds


def _tao_thuong(cfg: dict):
    if cfg["subsidy_form"] == "linear":
        return thuong_tuyen_tinh(cfg["sigma"], cfg["Q"]), cfg["Q"]
    if cfg["subsidy_form"] == "log":
        return thuong_log(cfg["sigma"], cfg["Q"]), None
    raise ValueError(f"subsidy_form lạ: {cfg['subsidy_form']}")


def run(config: dict, seed: int) -> EventLog:
    """Chạy một kịch bản từ đầu tới cuối, trả EventLog; `log.meta` chứa tham số + mốc thật (t_m, t_rut, c_A…)."""
    cfg = config
    if cfg.get("defense"):
        raise NotImplementedError("biện pháp phòng thủ chưa cài (GĐ2)")
    loai_victim = cfg.get("victim_type", "omniscient")
    if loai_victim not in ("omniscient", "adaptive"):
        raise ValueError(f"victim_type lạ: {loai_victim}")
    rng = np.random.default_rng(seed)
    W, T, fee = cfg["subsidy_window"], cfg["steps"], cfg["fee"]

    z0 = sqrt_price_at_tick(0) * 1.0001 ** 0.25          # giữa tick 0
    pool = Pool(fee, z0)
    tt = ThiTruongKichBan(z0 ** 2, cfg["vol_pre"], rng)

    pool.t = 0
    if cfg.get("bg_band") is not None:                    # nền hữu hạn: vài vị thế lồng nhau trong ±bg_band
        n_bg = cfg.get("bg_n", 5)
        for k, (lo, hi) in enumerate(dai_nen(z0 ** 2, cfg["bg_band"], n_bg)):
            pool.mint(f"bg:{k + 1}", lo, hi, cfg["L_bg"] / n_bg)
        if cfg.get("bg_tail", 0) > 0:                     # đuôi mỏng toàn dải: giá xả không kẹt ở mép dải
            pool.mint(f"bg:{n_bg + 1}", MIN_TICK, MAX_TICK, cfg["bg_tail"] * cfg["L_bg"])
    else:                                                 # nền phủ đều ±bg_range tick (cách cũ)
        pool.mint("bg:1", -cfg["bg_range"], cfg["bg_range"], cfg["L_bg"])

    thuong, Q_tran = _tao_thuong(cfg)
    v_buoc = cfg["Q"] / W                                 # farmer rải đều trần qua cửa sổ
    farmers = [Farmer(f"farmer:{k}", thuong, Q_tran, window=W, v_tran=v_buoc)
               for k in range(cfg["n_farmers"])]
    V_ky_vong = cfg["n_farmers"] * cfg["Q"]               # victim toàn tri: khối lượng mỗi cửa sổ

    def tao_victim(k: int):
        chung = dict(c_V=cfg["c_V"], w=cfg.get("w_victim", 1), t_vao=cfg["t_m"] + cfg["victim_delay"] * (k + 1))
        if loai_victim == "adaptive":                     # chỉ thấy phí quá khứ của bể
            return VictimThichNghi(f"victim:{k}", window=W, H=cfg.get("victim_H", 24), **chung)
        return VictimToanTri(f"victim:{k}", V=V_ky_vong, **chung)

    victims = [tao_victim(k) for k in range(cfg["n_victims"])]
    lich = [(int(t), float(r)) for t, r in cfg.get("wall_schedule", [[cfg["t_m"], 1.0]])]
    att = Attacker("attacker:0", L_A=cfg["L_A"], t_m=cfg["t_m"], kho_token0=cfg["attacker_inventory"],
                   c_A=cfg["c_A"], w=cfg.get("w_attacker", 1), dung_tuong=lich, t_0=cfg.get("t_0"),
                   nguong_victim=cfg.get("withdraw_victim_ratio"), so_buoc_xa=cfg["dump_steps"])
    arb = Arbitrageur()

    for t in range(T):
        pool.t = t
        # giao dịch nền: số lệnh Poisson, cỡ log-chuẩn (token1), mua/bán đều
        for _ in range(rng.poisson(cfg["bg_rate"])):
            v = cfg["bg_size"] * rng.lognormal(0.0, 0.5)
            if pool.liquidity <= 0:                           # bể cạn ở giá này → trader nền không vào
                continue
            if rng.random() < 0.5:
                pool.swap("bg:0", zero_for_one=False, amount_in=v)
            else:
                pool.swap("bg:0", zero_for_one=True, amount_in=v / pool.sqrt_price ** 2)
        for a in farmers:
            a.act(t, pool, tt)
        for a in victims:
            a.act(t, pool, tt)
        da_co_tuong = att.tick_lower is not None
        att.act(t, pool, tt)
        if not da_co_tuong and att.tick_lower is not None:   # vừa dựng tường → P_e neo giữa tick tường
            tt.neo(t, (sqrt_price_at_tick(att.tick_lower) * 1.0001 ** 0.25) ** 2)
            tt.vol = cfg.get("vol_prep", 0.0)
        if att.dang_xa(t):                                    # đang xả: giá ngoài đi theo bể, arb nghỉ
            tt.neo(t, pool.sqrt_price ** 2)
            tt.vol = cfg["vol_post"]
        else:
            arb.act(t, pool, tt)
        if (t + 1) % W == 0:
            for a in farmers:
                if a.v_cua_so > 0:
                    pool.log.append(t, "subsidy", a.owner, amount1=a.thuong(a.v_cua_so),
                                    sqrt_price_after=pool.sqrt_price, tick_after=pool.tick,
                                    liquidity_active_after=pool.liquidity)
        if t == T - 1:                                        # thu phí còn treo để phí hiện trong log
            for pid in sorted({int(i) for i in pool.log.to_frame()["position_id"].dropna()}):
                if any(x > 0 for x in pool.fees_owed(pid)):
                    pool.collect(pid)
        pool.log.append(t, "step", "platform", external_price=tt.external_price(t),
                        sqrt_price_after=pool.sqrt_price, tick_after=pool.tick,
                        liquidity_active_after=pool.liquidity)

    pool.log.meta = dict(cfg, seed=seed, t_rut=att.t_rut, wall_tick=att.tick_lower,
                         attacker_inventory_left=att.kho, P0=z0 ** 2)
    return pool.log


def run_frame(config: dict, seed: int) -> pd.DataFrame:
    """Như run nhưng trả DataFrame, meta để ở `df.attrs["meta"]` (cùng chỗ với log giả)."""
    log = run(config, seed)
    df = log.to_frame()
    df.attrs["meta"] = log.meta
    return df


if __name__ == "__main__":
    cfg = nap_config(sys.argv[1] if len(sys.argv) > 1 else "co_so")
    s = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    df = run_frame(cfg, s)
    if len(sys.argv) > 3:
        df.to_csv(sys.argv[3], index=False)
    print(df.groupby(["kind", "role"]).size().to_string())
    print({k: df.attrs["meta"][k] for k in ("t_m", "t_rut", "wall_tick", "attacker_inventory_left")})

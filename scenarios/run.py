"""Bộ chạy kịch bản (INTERFACE mục 3): ghép bể engine thật + giao dịch nền + farmer + victim + attacker + arb.

Thứ tự trong mỗi bước t: đặt pool.t → giao dịch nền bg:0 → farmer (+ farmer của kẻ tấn công) → victim → attacker → arb:0 (tắt khi
attacker đang xả) → chốt trợ cấp cuối cửa sổ → thu hồi (clawback) → trả khoản tới hạn → dòng `step`. Bước cuối: collect phí cho mọi vị thế LP.

Chạy: `python -m scenarios.run scenarios/configs/co_so.json [seed] [duong_dan.csv]`.
"""
from __future__ import annotations

import json
import math
import sys
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

from agents.arb import Arbitrageur
from agents.attacker import Attacker
from agents.farmer import Farmer, thuong_log, thuong_tuyen_tinh
from agents.victim import VictimThichNghi, VictimToanTri
from defenses.thuong import LichTraThuong, Q_hieu_luc, ten_bien_phap
from engine import MAX_TICK, MIN_TICK, EventLog, Pool, sqrt_price_at_tick, tick_at_sqrt_price

THU_MUC_CONFIG = Path(__file__).parent / "configs"


class ThiTruongKichBan:
    """Giá ngoài P_e(t) (token1/token0): bước ngẫu nhiên log-chuẩn với độ biến động đổi được theo pha.

    Bộ chạy `neo` giá vào một mức (giữa tick tường khi Prep, giá bể khi xả) và đổi `vol` khi sang pha.
    Cú sốc chuẩn hóa `soc[t]` rút theo chỉ số bước (mỗi bước đúng một số, dòng riêng), nên không phụ thuộc lúc neo
    hay trạng thái bể: P_e(t) = P_e(t−1)·exp(vol·soc[t]).
    """

    def __init__(self, P0: float, vol: float, rng: np.random.Generator):
        self.duong = [P0]
        self.vol = vol
        self.rng = rng
        self.soc: list[float] = [0.0]                   # soc[0] không dùng

    def _soc(self, t: int) -> float:
        while len(self.soc) <= t:
            self.soc.append(float(self.rng.standard_normal()))
        return self.soc[t]

    def external_price(self, t: int) -> float:
        """P_e tại bước t; sinh thêm đường giá nếu chưa có."""
        while len(self.duong) <= t:
            k = len(self.duong)
            self.duong.append(self.duong[-1] * math.exp(self.vol * self._soc(k)))
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


def _tao_thuong(cfg: dict, Q: float):
    if cfg["subsidy_form"] == "linear":
        return thuong_tuyen_tinh(cfg["sigma"], Q), Q
    if cfg["subsidy_form"] == "log":
        return thuong_log(cfg["sigma"], Q), None
    raise ValueError(f"subsidy_form lạ: {cfg['subsidy_form']}")


def tao_dong_ngau_nhien(cfg: dict, seed: int) -> dict[str, np.random.Generator]:
    """Các dòng ngẫu nhiên tách theo nguồn: {"nen": giao dịch nền, "gia": đường giá ngoài}.

    Gốc `SeedSequence([seed, crc32(scenario_id)])` (không có `scenario_id`, như co_so: `SeedSequence(seed)`), tách bằng
    `spawn`. Chỉ phụ thuộc (vụ, seed) — không phụ thuộc biện pháp, loại victim, farm_share — và mỗi nguồn rút số theo
    bước bất kể trạng thái bể, nên cặp phản thực GĐ2 dùng chung đúng từng số ngẫu nhiên. Tác nhân không có ngẫu nhiên."""
    ma = cfg.get("scenario_id")
    goc = np.random.SeedSequence(seed if ma is None else [seed, zlib.crc32(str(ma).encode("utf-8"))])
    nen, gia = (np.random.default_rng(s) for s in goc.spawn(2))
    return {"nen": nen, "gia": gia}


def run(config: dict, seed: int, ghi: dict | None = None) -> EventLog:
    """Chạy một kịch bản từ đầu tới cuối, trả EventLog; `log.meta` chứa tham số + mốc thật (t_m, t_rut, c_A…).
    `ghi` (dict, tùy chọn, cho test): nhận "nen" = [(t, cỡ token1, số chiều)] mỗi bước và "soc" = cú sốc giá ngoài."""
    cfg = config
    defense = cfg.get("defense")
    ten_bien_phap(defense)                                # báo lỗi nếu biện pháp chưa cài
    loai_victim = cfg.get("victim_type", "omniscient")
    if loai_victim not in ("omniscient", "adaptive"):
        raise ValueError(f"victim_type lạ: {loai_victim}")
    dong = tao_dong_ngau_nhien(cfg, seed)
    rng_nen = dong["nen"]
    W, T, fee = cfg["subsidy_window"], cfg["steps"], cfg["fee"]

    z0 = sqrt_price_at_tick(0) * 1.0001 ** 0.25          # giữa tick 0
    pool = Pool(fee, z0)
    tt = ThiTruongKichBan(z0 ** 2, cfg["vol_pre"], dong["gia"])

    pool.t = 0
    if cfg.get("bg_band") is not None:                    # nền hữu hạn: vài vị thế lồng nhau trong ±bg_band
        n_bg = cfg.get("bg_n", 5)
        for k, (lo, hi) in enumerate(dai_nen(z0 ** 2, cfg["bg_band"], n_bg)):
            pool.mint(f"bg:{k + 1}", lo, hi, cfg["L_bg"] / n_bg)
        if cfg.get("bg_tail", 0) > 0:                     # đuôi mỏng toàn dải: giá xả không kẹt ở mép dải
            pool.mint(f"bg:{n_bg + 1}", MIN_TICK, MAX_TICK, cfg["bg_tail"] * cfg["L_bg"])
    else:                                                 # nền phủ đều ±bg_range tick (cách cũ)
        pool.mint("bg:1", -cfg["bg_range"], cfg["bg_range"], cfg["L_bg"])

    Q_eff = Q_hieu_luc(cfg["Q"], defense)                 # hạ trần (nếu có)
    lich_tra = LichTraThuong.tu_defense(defense)          # trả trễ (nếu có); mặc định trả ngay
    thuong, Q_tran = _tao_thuong(cfg, Q_eff)              # luật nền tảng trả
    he_so = lich_tra.he_so_cam_nhan
    thuong_farmer = (lambda v: he_so * thuong(v)) if he_so != 1.0 else thuong   # farmer chiết khấu δ^D
    v_buoc = Q_eff / W                                    # farmer rải đều trần qua cửa sổ
    farmers = [Farmer(f"farmer:{k}", thuong_farmer, Q_tran, window=W, v_tran=v_buoc)
               for k in range(cfg["n_farmers"])]
    # kẻ tấn công cũng săn trợ cấp (CH-6 (b)): m tài khoản ảo, phần khối lượng farmer của kẻ tấn công = s khi
    # mọi tài khoản chạm trần; gộp thành một tác nhân owner = attacker, thưởng m·thưởng(v/m) (đúng cả dạng log)
    s_att = cfg.get("attacker_farm_share", 0.0)
    if not 0.0 <= s_att < 1.0:
        raise ValueError("attacker_farm_share phải trong [0, 1)")
    m_att = s_att / (1 - s_att) * cfg["n_farmers"]
    V_ky_vong = (cfg["n_farmers"] + m_att) * Q_eff        # victim toàn tri: biết luật (kể cả trần mới)

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
    if m_att > 0:
        thuong_att = lambda v: m_att * thuong(v / m_att)
        thuong_att_cam = (lambda v: he_so * thuong_att(v)) if he_so != 1.0 else thuong_att
        farm_att = Farmer(att.owner, thuong_att_cam, None if Q_tran is None else m_att * Q_tran, window=W,
                          v_tran=m_att * v_buoc)
        san_tro_cap = farmers + [farm_att]
    else:
        thuong_att, san_tro_cap = None, farmers

    doc_log = 0                                           # chỉ số dòng log đã quét để tìm mint/burn trong bước
    for t in range(T):
        pool.t = t
        if t % W == 0:                                        # giá đầu cửa sổ tích lũy (tham chiếu của clawback)
            gia_dau_cua_so = pool.sqrt_price ** 2
        # giao dịch nền: số lệnh Poisson, cỡ log-chuẩn (token1), mua/bán đều — rút đủ cả bước trước khi khớp
        n_lenh = rng_nen.poisson(cfg["bg_rate"])
        co = cfg["bg_size"] * rng_nen.lognormal(0.0, 0.5, n_lenh)
        chieu = rng_nen.random(n_lenh)
        if ghi is not None:
            ghi.setdefault("nen", []).append((t, co, chieu))
        for v, u in zip(co, chieu):
            if pool.liquidity <= 0:                           # bể cạn ở giá này → trader nền bỏ lệnh (số đã rút)
                continue
            if u < 0.5:
                pool.swap("bg:0", zero_for_one=False, amount_in=v)
            else:
                pool.swap("bg:0", zero_for_one=True, amount_in=v / pool.sqrt_price ** 2)
        for a in san_tro_cap:
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
        if (t + 1) % W == 0:                                  # chốt thưởng cuối cửa sổ
            for a in san_tro_cap:
                if a.v_cua_so > 0:
                    ham = thuong_att if a.owner == att.owner else thuong
                    lich_tra.chot(t, a.owner, ham(a.v_cua_so), pool.sqrt_price ** 2,
                                  gia_tham_chieu=gia_dau_cua_so)
        # clawback (nếu có): owner có vị thế LP trong bước t = đang giữ vị thế cuối bước hoặc có mint/burn trong
        # bước (bắt được kẻ tấn công rút tường ngay bước này); lịch trả nhớ lịch sử theo địa chỉ
        chu_lp = {p.owner for p in pool.positions()}
        rows = pool.log.rows
        chu_lp.update(r["owner"] for r in rows[doc_log:] if r["kind"] in ("mint", "burn"))
        doc_log = len(rows)
        lich_tra.thu_hoi(pool.sqrt_price ** 2, chu_lp, t)
        for owner, gia_tri in lich_tra.den_han(t, pool.sqrt_price ** 2):   # trả khoản tới hạn
            pool.log.append(t, "subsidy", owner, amount1=gia_tri, sqrt_price_after=pool.sqrt_price,
                            tick_after=pool.tick, liquidity_active_after=pool.liquidity)
        if t == T - 1:                                        # thu phí còn treo để phí hiện trong log
            for pid in sorted({int(i) for i in pool.log.to_frame()["position_id"].dropna()}):
                if any(x > 0 for x in pool.fees_owed(pid)):
                    pool.collect(pid)
        pool.log.append(t, "step", "platform", external_price=tt.external_price(t),
                        sqrt_price_after=pool.sqrt_price, tick_after=pool.tick,
                        liquidity_active_after=pool.liquidity)

    if ghi is not None:
        tt.external_price(T - 1)
        ghi["soc"] = list(tt.soc)
    P_cuoi = pool.sqrt_price ** 2
    pool.log.meta = dict(cfg, seed=seed, Q_eff=Q_eff, subsidy_pending=lich_tra.con_treo(P_cuoi),
                         subsidy_pending_attacker=lich_tra.con_treo(P_cuoi, att.owner),
                         subsidy_clawed=lich_tra.da_thu_hoi, attacker_farm_accounts=m_att, t_rut=att.t_rut,
                         wall_tick=att.tick_lower, attacker_inventory_left=att.kho, P0=z0 ** 2)
    return pool.log


def run_frame(config: dict, seed: int, ghi: dict | None = None) -> pd.DataFrame:
    """Như run nhưng trả DataFrame, meta để ở `df.attrs["meta"]` (cùng chỗ với log giả)."""
    log = run(config, seed, ghi)
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

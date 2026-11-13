"""Đo phân phối từ log thật: lịch tấn công của 29 vụ và luồng giao dịch nền (vụ + bể đối chứng không trợ cấp).

    python -m metrics.phan_phoi_that [--nhanh] [--ra ket_qua/that/phan_phoi]

Chỉ đọc `ket_qua/that/` (không gọi mạng); ghi `lich_tan_cong.csv`, `luong_nen.csv`, `tom_tat.csv` vào `--ra`.
Đây là bước ĐO: chưa nối vào simulator. Cột `gia_tri_mo_phong` của `tom_tat.csv` là số simulator đang đặt để so sánh.

Lịch tấn công (một dòng mỗi vụ). "Tường" = chuỗi thanh khoản ròng L (đơn vị L thô) của mọi vị thế HẸP chứa tick tường
(`tick_lower <= tick_tuong < tick_upper`, độ rộng <= `NGUONG_BOI` × tickSpacing; tickSpacing suy từ ước chung lớn nhất của
mọi mốc tick trong log; ngưỡng mặc định 3), cộng dồn +L khi mint, -L khi burn, từ đầu đoạn tải (72 giờ trước t_m). Mint
trước đoạn tải không thấy được: nếu L ròng âm trước t_m thì cộng bù để chuỗi không âm (cột `bu_L0`). Đỉnh = L lớn nhất trong
[t_m, t_b]. Dựng = từ mint hẹp đầu tiên sau t_m tới lúc L đạt 95% đỉnh; giữ = từ đó tới lần đầu L < 95% đỉnh; rút = từ lần
rút đầu tới lúc L < 20% đỉnh (NaN nếu không xuống tới trước t_b). "Lần nạp" / "lát rút" chỉ đếm sự kiện có L >= 2% đỉnh
(`NGUONG_LAT`) để bỏ qua các mint/burn vụn.
HẠN CHẾ QUAN TRỌNG: owner của Mint/Burn là hợp đồng quản lý vị thế, không phải ví thật, nên không tách được kẻ tấn công
khỏi nạn nhân: "tường" ở đây là TOÀN BỘ thanh khoản hẹp tại tick tường (gồm cả nạn nhân và LP hẹp khác).

Luồng nền: swap trong log chỉ là MẪU, cửa sổ `MAU_DAI` = 40 block mỗi `MAU_MOI` = 4.800 block (≈ 30 giây mỗi giờ), nên
hệ số lấy mẫu = 4.800 / 40 = 120 và cường độ swap/giờ = số swap trong mẫu × 120 / số giờ của pha (giờ = block / 4.800).
Kích thước: (a) |amount1| / 1e18, coi token1 là token định giá và 18 chữ số thập phân (giả định, không có siêu dữ liệu token
trong log); (b) kích thước chuẩn hóa không thứ nguyên |amount1| / (L_hoạt_động × √P) với √P = sqrt_price_x96 / 2^96, tức so với
độ sâu ảo token1 tại chỗ (L, √P lấy sau swap), không phụ thuộc số thập phân. Chiều mua token0 = amount0 < 0 (bể trả token0).
"""
from __future__ import annotations

import argparse
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

from metrics.danh_gia_vu_that import doan_doi_chung_co_du_lieu, thu_muc_cho_vu
from metrics.phat_hien_that import gio_block
from scenarios.tai_vu_that import BANG_DOI_CHUNG, BANG_VU, GOC, doc_bang_vu, doc_doi_chung, ke_hoach

NGUONG_BOI = 3          # tường = vị thế có độ rộng <= NGUONG_BOI × tickSpacing
NGUONG_LAT = 0.02       # lần nạp / lát rút chỉ tính khi L của sự kiện >= NGUONG_LAT × đỉnh
MAU_MOI, MAU_DAI = 4800, 40      # block: chu kỳ lấy mẫu swap và độ dài cửa sổ mẫu
HE_SO_MAU = MAU_MOI / MAU_DAI    # = 120
BLOCK_GIO = 4800                 # block mỗi giờ (BSC, 0,75 giây/block)
PHAN_VI = (10, 25, 50, 75, 90, 99)
RA = GOC / "phan_phoi"


# ---------- đọc dữ liệu ----------
def doc_su_kien(ra: Path) -> pd.DataFrame:
    """Đọc su_kien.csv (Mint/Burn/Collect), bỏ dòng trùng, thêm cột L (float, đơn vị L thô); sắp theo (block, tx_index, log_index)."""
    ev = pd.read_csv(ra / "su_kien.csv", dtype=str)
    for c in ("block", "tx_index", "log_index", "tick_lower", "tick_upper"):
        ev[c] = pd.to_numeric(ev[c], errors="coerce")
    ev = ev.drop_duplicates(subset=["block", "tx_index", "log_index", "kind"])
    ev["L"] = pd.to_numeric(ev["liquidity"], errors="coerce").astype(float)
    return ev.sort_values(["block", "tx_index", "log_index"], kind="stable").reset_index(drop=True)


def doc_swap(ra: Path) -> pd.DataFrame:
    """Đọc swap.csv (mẫu), bỏ trùng; cột: block, a0, a1 (amount0/1 thô, float), L (thanh khoản hoạt động sau swap), sqrtP (= sqrt_price_x96/2^96)."""
    s = pd.read_csv(ra / "swap.csv", dtype=str)
    s["block"] = pd.to_numeric(s["block"], errors="coerce")
    s = s.drop_duplicates(subset=[c for c in ("block", "tx_index", "log_index") if c in s.columns])
    kq = pd.DataFrame(dict(block=s["block"].astype(float),
                           a0=pd.to_numeric(s["amount0"], errors="coerce").astype(float),
                           a1=pd.to_numeric(s["amount1"], errors="coerce").astype(float),
                           L=pd.to_numeric(s["liquidity_active"], errors="coerce").astype(float),
                           sqrtP=pd.to_numeric(s["sqrt_price_x96"], errors="coerce").astype(float) / 2.0 ** 96))
    return kq.dropna(subset=["block"]).sort_values("block", kind="stable").reset_index(drop=True)


def tick_spacing(ev: pd.DataFrame) -> int:
    """tickSpacing suy ra (tick) = ước chung lớn nhất của |mọi mốc tick| trong log; 1 nếu không suy được."""
    t = pd.concat([ev["tick_lower"], ev["tick_upper"]]).dropna().astype(int).abs().to_numpy()
    t = t[t > 0]
    return int(np.gcd.reduce(t)) if len(t) else 1


# ---------- lịch tấn công ----------
def _nan_lich() -> dict:
    return dict(do_rong_tick=math.nan, do_rong_bang=math.nan, do_rong_boi=math.nan, L_dinh=math.nan, so_lan_nap=math.nan,
                ty_trong_nap="", ty_trong_lan_dau=math.nan, ty_trong_lan_max=math.nan, thoi_gian_dung_gio=math.nan,
                thoi_gian_giu_gio=math.nan, so_lat_rut=math.nan, thoi_gian_rut_gio=math.nan,
                khoang_rut_tb_gio=math.nan, ty_so_nen=math.nan, tm_den_dinh_gio=math.nan, dinh_den_tb_gio=math.nan)


def lich_tan_cong(ev: pd.DataFrame, moc: pd.DataFrame, tick_tuong: int, t_m: int, t_b: int,
                  nen_L: float = math.nan, nguong_boi: int = NGUONG_BOI, nguong_lat: float = NGUONG_LAT) -> dict:
    """Lịch dựng–giữ–rút của tường tại `tick_tuong` (tick) từ sự kiện `ev` (cột kind, block, tick_lower, tick_upper, L), mốc `moc`
    (block, ts) để đổi block → giờ; `t_m`, `t_b` là block; `nen_L` = L hoạt động trung vị 24 giờ trước t_m (L thô). Trả dict
    (xem `_nan_lich`; thời gian tính bằng giờ, `ty_so_nen` = L_dinh / nen_L); đại lượng không đo được là NaN."""
    kq = _nan_lich()
    ts = tick_spacing(ev)
    e = ev[ev["kind"].isin(["mint", "burn"]) & (ev["L"] > 0)]
    e = e[(e["tick_lower"] <= tick_tuong) & (e["tick_upper"] > tick_tuong)]
    e = e[(e["tick_upper"] - e["tick_lower"]) <= nguong_boi * ts]
    kq["ts"], kq["so_su_kien_hep"] = ts, int(len(e))
    if e.empty:
        return kq
    dL = np.where(e["kind"].to_numpy() == "mint", 1.0, -1.0) * e["L"].to_numpy()
    blk = e["block"].to_numpy(float)
    cum = np.cumsum(dL)
    truoc = blk < t_m
    bu = max(0.0, -float(cum[truoc].min())) if truoc.any() else 0.0
    cum = np.maximum(cum + bu, 0.0)
    kq["bu_L0"] = bu
    g = gio_block(blk, moc)
    g_b = float(gio_block([t_b], moc)[0])
    tr = (blk >= t_m) & (blk <= t_b)
    if not tr.any():
        return kq
    idx = np.flatnonzero(tr)
    ipk = idx[int(np.argmax(cum[idx]))]
    dinh = float(cum[ipk])
    kq["L_dinh"] = dinh
    kq["tm_den_dinh_gio"] = float(g[ipk] - gio_block([t_m], moc)[0])     # mốc bền hơn 95%: đỉnh tính từ t_m
    kq["dinh_den_tb_gio"] = float(g_b - g[ipk])
    if dinh <= 0:
        return kq
    kq["ty_so_nen"] = dinh / nen_L if nen_L and nen_L > 0 else math.nan
    i95 = idx[int(np.argmax(cum[idx] >= 0.95 * dinh))]
    mint_dau = idx[e["kind"].to_numpy()[idx] == "mint"]
    if len(mint_dau) == 0:
        return kq
    kq["thoi_gian_dung_gio"] = float(g[i95] - g[mint_dau[0]])
    # lần nạp dựng tường: mint đáng kể từ mint đầu tới lúc đạt 95% đỉnh
    kind = e["kind"].to_numpy()
    seg = np.arange(mint_dau[0], i95 + 1)
    nap = seg[(kind[seg] == "mint") & (e["L"].to_numpy()[seg] >= nguong_lat * dinh)]
    if len(nap):
        Ln = e["L"].to_numpy()[nap]
        tt = Ln / Ln.sum()
        kq["so_lan_nap"] = int(len(nap))
        kq["ty_trong_nap"] = ";".join(f"{x:.3f}" for x in tt)
        kq["ty_trong_lan_dau"], kq["ty_trong_lan_max"] = float(tt[0]), float(tt.max())
        w = (e["tick_upper"] - e["tick_lower"]).to_numpy(float)[nap]
        kq["do_rong_tick"] = float(w[np.argsort(w)][np.searchsorted(np.cumsum(Ln[np.argsort(w)]) / Ln.sum(), 0.5)])
        kq["do_rong_boi"] = kq["do_rong_tick"] / ts
    # giữ và rút
    sau = idx[idx > i95]
    xuong = sau[cum[sau] < 0.95 * dinh]
    if len(xuong):
        ir = xuong[0]
        kq["thoi_gian_giu_gio"] = float(g[ir] - g[i95])
        kq["khoang_rut_tb_gio"] = float(g_b - g[ir])
        kq["gio_rut_dau_block"] = float(blk[ir])
        d20 = idx[(idx >= ir) & (cum[idx] < 0.2 * dinh)]
        khoang = np.arange(ir, (d20[0] if len(d20) else idx[-1]) + 1)
        khoang = khoang[(kind[khoang] == "burn") & (e["L"].to_numpy()[khoang] >= nguong_lat * dinh)]
        kq["so_lat_rut"] = int(len(khoang))
        if len(d20):
            kq["thoi_gian_rut_gio"] = float(g[d20[0]] - g[ir])
    return kq


def nen_L_24h(swap: pd.DataFrame, moc: pd.DataFrame, t_m: int) -> float:
    """Thanh khoản hoạt động trung vị (L thô) của các swap mẫu trong 24 giờ trước block `t_m`; NaN nếu không có mẫu."""
    g = gio_block(swap["block"].to_numpy(), moc)
    g_m = float(gio_block([t_m], moc)[0])
    L = swap["L"].to_numpy()[(g >= g_m - 24) & (g < g_m)]
    L = L[np.isfinite(L) & (L > 0)]
    return float(np.median(L)) if len(L) else math.nan


# ---------- luồng nền ----------
def _cdf_chuan(z: np.ndarray) -> np.ndarray:
    from math import erf, sqrt
    return 0.5 * (1.0 + np.array([erf(x / sqrt(2.0)) for x in z]))


def ks_log(x: np.ndarray) -> dict:
    """Khớp ba dạng trên y = ln x và thống kê Kolmogorov–Smirnov D (tự tính): log-chuẩn (mu, sigma bằng mô-men), log-Laplace
    (vị trí = trung vị, b = trung bình |y − trung vị|), log-logistic (vị trí = trung vị, thang = IQR/(2 ln 3)). Cần >= 30 điểm dương."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x) & (x > 0)]
    kq = dict(n_ks=len(x), mu=math.nan, sigma=math.nan, ks_lognormal=math.nan, ks_loglaplace=math.nan,
              ks_loglogistic=math.nan, ks_p_lognormal=math.nan, hop_nhat="")
    if len(x) < 30:
        return kq
    y = np.sort(np.log(x))
    n = len(y)
    mu, sg = float(y.mean()), float(y.std(ddof=0))
    kq["mu"], kq["sigma"] = mu, sg
    emp_hi, emp_lo = np.arange(1, n + 1) / n, np.arange(0, n) / n

    def D(F):
        return float(max(np.max(emp_hi - F), np.max(F - emp_lo)))

    kq["ks_lognormal"] = D(_cdf_chuan((y - mu) / sg)) if sg > 0 else math.nan
    med = float(np.median(y))
    b = float(np.mean(np.abs(y - med)))
    z = (y - med) / b if b > 0 else np.zeros(n)
    kq["ks_loglaplace"] = D(np.where(z < 0, 0.5 * np.exp(z), 1 - 0.5 * np.exp(-z)))
    s = float(np.subtract(*np.percentile(y, [75, 25])) / (2 * math.log(3)))
    kq["ks_loglogistic"] = D(1.0 / (1.0 + np.exp(-(y - med) / s))) if s > 0 else math.nan
    # p-giá trị tiệm cận Kolmogorov (tham số khớp từ mẫu nên p này thiên cao; dùng D làm chính)
    d = kq["ks_lognormal"]
    t = math.sqrt(n) * d
    kq["ks_p_lognormal"] = float(min(1.0, 2 * sum((-1) ** (k - 1) * math.exp(-2 * k * k * t * t) for k in range(1, 60))))
    ds = {"lognormal": kq["ks_lognormal"], "loglaplace": kq["ks_loglaplace"], "loglogistic": kq["ks_loglogistic"]}
    kq["hop_nhat"] = min((k for k in ds if ds[k] == ds[k]), key=lambda k: ds[k], default="")
    return kq


def phan_vi(x: np.ndarray, tien_to: str) -> dict:
    """Phân vị 10/25/50/75/90/99 của `x` (bỏ NaN/không dương); khóa `<tien_to>_p<k>`; NaN nếu rỗng."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x) & (x > 0)]
    return {f"{tien_to}_p{p}": (float(np.percentile(x, p)) if len(x) else math.nan) for p in PHAN_VI}


def do_luong_nen(sw: pd.DataFrame, b_dau: float, b_cuoi: float) -> dict:
    """Thống kê luồng nền trong khoảng block [b_dau, b_cuoi) từ swap mẫu `sw` (cột block, a0, a1, L, sqrtP): số swap trong mẫu,
    số giờ, cường độ (swap/giờ = n × 120 / giờ), tỷ lệ mua token0 (theo số lệnh, theo khối lượng token1), phân vị kích thước
    (token1, và chuẩn hóa |a1|/(L·√P)), khớp log-chuẩn + KS trên kích thước chuẩn hóa và trên token1."""
    gio = max(0.0, (b_cuoi - b_dau) / BLOCK_GIO)
    s = sw[(sw["block"] >= b_dau) & (sw["block"] < b_cuoi)]
    s = s[np.isfinite(s["a0"]) & np.isfinite(s["a1"]) & (s["a1"] != 0)]
    n = len(s)
    kq = dict(n_swap_mau=n, gio_pha=gio, swap_moi_gio=(n * HE_SO_MAU / gio if gio > 0 else math.nan),
              ty_le_mua0_lenh=math.nan, ty_le_mua0_khoi_luong=math.nan)
    if n:
        mua = (s["a0"] < 0).to_numpy()
        a1 = np.abs(s["a1"].to_numpy()) / 1e18
        kq["ty_le_mua0_lenh"] = float(mua.mean())
        kq["ty_le_mua0_khoi_luong"] = float(a1[mua].sum() / a1.sum()) if a1.sum() > 0 else math.nan
    else:
        a1 = np.array([])
    kq.update(phan_vi(a1, "kt_token1"))
    ok = (s["L"] > 0) & (s["sqrtP"] > 0)
    chuan = np.abs(s["a1"].to_numpy()[ok.to_numpy()]) / (s["L"].to_numpy()[ok.to_numpy()] * s["sqrtP"].to_numpy()[ok.to_numpy()])
    kq.update(phan_vi(chuan, "kt_chuan"))
    k = ks_log(chuan)
    kq.update({f"chuan_{c}": v for c, v in k.items()})
    k2 = ks_log(a1)
    kq.update({f"token1_{c}": v for c, v in k2.items()})
    return kq


# ---------- chạy toàn bộ ----------
def chay(vu_df: pd.DataFrame, ke: list[dict], doan_dc: list[tuple[str, Path]], ra: Path = RA, nhanh: bool = False,
         in_ra=print) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Đo lịch tấn công cho từng vụ và luồng nền cho từng (vụ, pha) và đoạn đối chứng; ghi 3 CSV vào `ra`; trả (lịch, luồng nền, tóm tắt)."""
    lich_rows, nen_rows = [], []
    cache: dict[str, tuple] = {}
    vus = list(vu_df.itertuples())[:3] if nhanh else list(vu_df.itertuples())
    for v in vus:
        d = thu_muc_cho_vu(v, ke)
        if d is None:
            lich_rows.append(dict(vu_id=v.vu_id, thu_muc="", ghi_chu="không có dữ liệu"))
            continue
        key = Path(d).as_posix()
        if key not in cache:
            cache.clear()
            cache[key] = (doc_su_kien(d), doc_swap(d), pd.read_csv(Path(d) / "moc.csv"))
        ev, sw, moc = cache[key]
        nen = nen_L_24h(sw, moc, v.t_m)
        lt = lich_tan_cong(ev, moc, int(v.tick_lower), int(v.t_m), int(v.t_b), nen)
        lt["do_rong_bang"] = float(v.tick_upper - v.tick_lower)
        lich_rows.append(dict(vu_id=v.vu_id, pool=v.pool, n_victim=v.n_victim, t_m=v.t_m, t_b=v.t_b, nen_L_24h=nen,
                              thu_muc=key, **lt))
        b_rut = lt.get("gio_rut_dau_block", math.nan)
        pha = [("truoc_tuong", v.t_m - 24 * BLOCK_GIO, v.t_m),
               ("prep", v.t_m, b_rut if b_rut == b_rut else v.t_b)]
        for ten, b0, b1 in pha:
            b0 = max(b0, float(sw["block"].min()))
            nen_rows.append(dict(kieu="vu", id=v.vu_id, pha=ten, **do_luong_nen(sw, b0, b1)))
        in_ra(f"  vụ {v.vu_id}: đỉnh {lt['L_dinh']:.3g}, dựng {lt['thoi_gian_dung_gio']}, giữ {lt['thoi_gian_giu_gio']}")
    dcs = doan_dc[:1] if nhanh else doan_dc
    for ten, d in dcs:
        sw = doc_swap(d)
        if sw.empty:
            continue
        nen_rows.append(dict(kieu="doi_chung", id=f"{ten}:{Path(d).name}", pha="doi_chung",
                             **do_luong_nen(sw, float(sw["block"].min()), float(sw["block"].max()) + MAU_DAI)))
        in_ra(f"  đối chứng {ten}: {len(sw)} swap mẫu")
    lich, nen = pd.DataFrame(lich_rows), pd.DataFrame(nen_rows)
    tt = tom_tat(lich, nen)
    ra.mkdir(parents=True, exist_ok=True)
    lich.to_csv(ra / "lich_tan_cong.csv", index=False, encoding="utf-8-sig")
    nen.to_csv(ra / "luong_nen.csv", index=False, encoding="utf-8-sig")
    tt.to_csv(ra / "tom_tat.csv", index=False, encoding="utf-8-sig")
    return lich, nen, tt


# giá trị simulator đang đặt: (tên đại lượng) -> (giá trị, nguồn tham số)
MO_PHONG_LICH = {
    "do_rong_boi": (1, "w_attacker=1 (co_so.json)"),
    "so_lan_nap": (2, "wall_schedule=[[48,0.6],[72,0.4]]"),
    "ty_trong_lan_dau": (0.6, "wall_schedule[0][1]"),
    "ty_trong_lan_max": (0.6, "wall_schedule"),
    "thoi_gian_dung_gio": (24, "wall_schedule: 72 − 48"),
    "thoi_gian_giu_gio": (96, "t_0 − 72 = 168 − 72"),
    "so_lat_rut": (1, "so_lat_rut (mặc định 1, run.py)"),
    "khoang_rut_tb_gio": (2, "dump_steps=2 (xả sau rút)"),
    "ty_so_nen": (2000, "L_A/L_bg = 4e8/2e5 (L_A, L_bg co_so.json)"),
}
MO_PHONG_NEN = {
    "swap_moi_gio": (4, "bg_rate=4 (Poisson, run.py dòng 314)"),
    "ty_le_mua0_lenh": (0.5, "u<0.5 mua token0 (run.py dòng 319)"),
    "ty_le_mua0_khoi_luong": (0.5, "cỡ độc lập chiều: kỳ vọng 0,5"),
    "kt_token1_p50": (500, "bg_size=500 × lognormal(0; 0,5)"),
    "kt_token1_p75": (500 * math.exp(0.5 * 0.6745), "bg_size·exp(0,5·z0,75)"),
    "kt_token1_p90": (500 * math.exp(0.5 * 1.2816), "bg_size·exp(0,5·z0,90)"),
    "kt_token1_p99": (500 * math.exp(0.5 * 2.3263), "bg_size·exp(0,5·z0,99)"),
    "kt_token1_p25": (500 * math.exp(-0.5 * 0.6745), "bg_size·exp(−0,5·z0,75)"),
    "kt_token1_p10": (500 * math.exp(-0.5 * 1.2816), "bg_size·exp(−0,5·z0,90)"),
    "token1_sigma": (0.5, "sigma của lognormal(0; 0,5)"),
    "token1_mu": (math.log(500), "ln bg_size"),
}


# Kích thước chuẩn hóa mô phỏng = bg_size·exp(σ·z_q) / (L·√P0), σ = 0,5, √P0 ≈ 1 (z0 ở giữa tick 0); L = L_bg = 2e5 khi chưa có
# tường (pha truoc_tuong, doi_chung) và L = L_A + L_bg ≈ 4e8 khi có tường (pha prep). Xấp xỉ: L hoạt động thật của simulator
# còn phụ thuộc vị thế nền lồng nhau nên đây là bậc độ lớn.
_Z = {"p10": -1.2816, "p25": -0.6745, "p50": 0.0, "p75": 0.6745, "p90": 1.2816, "p99": 2.3263}
for _q, _z in _Z.items():
    for _pha, _L in (("truoc_tuong", 2e5), ("doi_chung", 2e5), ("prep", 4.0002e8)):
        MO_PHONG_NEN[(f"kt_chuan_{_q}", _pha)] = (500 * math.exp(0.5 * _z) / _L, f"bg_size·exp(0,5·z)/(L·√P0), L={_L:.3g}")


def _thong_ke(x: pd.Series) -> dict:
    x = pd.to_numeric(x, errors="coerce").dropna()
    return dict(n_vu_do_duoc=int(len(x)), trung_vi=float(x.median()) if len(x) else math.nan,
                p25=float(x.quantile(.25)) if len(x) else math.nan, p75=float(x.quantile(.75)) if len(x) else math.nan,
                min=float(x.min()) if len(x) else math.nan, max=float(x.max()) if len(x) else math.nan)


def tom_tat(lich: pd.DataFrame, nen: pd.DataFrame) -> pd.DataFrame:
    """Bảng tóm tắt (nhom, dai_luong, pha): số mẫu đo được, trung vị, phân vị 25/75, min, max, gia_tri_mo_phong và nguon_mo_phong."""
    rows = []
    n_vu = len(lich)
    for c, (gt, ng) in MO_PHONG_LICH.items():
        if c in lich.columns:
            rows.append(dict(nhom="lich_tan_cong", dai_luong=c, pha="", n_tong=n_vu, **_thong_ke(lich[c]),
                             gia_tri_mo_phong=gt, nguon_mo_phong=ng))
    for c in ("do_rong_tick", "L_dinh", "tm_den_dinh_gio", "dinh_den_tb_gio", "thoi_gian_rut_gio"):
        if c in lich.columns:
            rows.append(dict(nhom="lich_tan_cong", dai_luong=c, pha="", n_tong=n_vu, **_thong_ke(lich[c]),
                             gia_tri_mo_phong=math.nan, nguon_mo_phong=""))
    if len(nen):
        cac = [c for c in nen.columns if c in MO_PHONG_NEN or any(c == k[0] for k in MO_PHONG_NEN if isinstance(k, tuple)) or c in ("chuan_sigma",
               "chuan_mu", "chuan_ks_lognormal", "token1_ks_lognormal", "chuan_ks_loglaplace", "chuan_ks_loglogistic",
               "token1_ks_loglaplace", "token1_ks_loglogistic", "n_swap_mau")]
        for pha, g in nen.groupby("pha", sort=False):
            for c in cac:
                gt, ng = MO_PHONG_NEN.get((c, pha), MO_PHONG_NEN.get(c, (math.nan, "")))
                rows.append(dict(nhom="luong_nen", dai_luong=c, pha=pha, n_tong=len(g), **_thong_ke(g[c]),
                                 gia_tri_mo_phong=gt, nguon_mo_phong=ng))
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--nhanh", action="store_true", help="chỉ 3 vụ đầu và 1 đoạn đối chứng")
    ap.add_argument("--ra", default=str(RA), help="thư mục ghi CSV")
    a = ap.parse_args()
    t0 = time.time()
    vu = doc_bang_vu(BANG_VU)
    ke = ke_hoach(vu, doc_doi_chung(BANG_DOI_CHUNG))
    dc = [(t, p) for t, p in doan_doi_chung_co_du_lieu(ke) if "doi_chung" in Path(p).parent.name]   # chỉ 5 bể × 3 đoạn, bỏ P1 cũ
    lich, nen, tt = chay(vu, ke, dc, Path(a.ra), a.nhanh)
    pd.set_option("display.width", 220)
    print(tt.drop(columns=["nguon_mo_phong"]).round(4).to_string(index=False))
    print(f"→ {a.ra} ({time.time() - t0:.0f} giây)")


if __name__ == "__main__":
    main()

"""Chạy luật báo động của trần động trên log thật của một bể (file do `scenarios.lay_log_bsc` tải về).

    python -m metrics.phat_hien_that --vao ket_qua/that/<pool> --tm <block t_m> --tb <block t_b> [--N 24]

Đổi log thật sang đúng thứ luật cần: chuỗi L của tick chứa giá theo giờ, lấy từ trường `liquidity` của sự kiện Swap
(thanh khoản hoạt động ngay sau lệnh), giờ không có swap mẫu thì giữ giá trị giờ trước. Rồi phát lại luật
(`metrics.phat_hien.cac_buoc_bao`) với nhiều bội số m và đo: có báo trong [t_m, t_b) không, sớm hơn t_b bao nhiêu giờ,
báo mấy lần trước t_m. Ghi `phat_hien_that.csv` và `chuoi_L_gio.csv` vào thư mục `--vao`.

Giới hạn: swap chỉ là mẫu (≈ 30 giây đầu mỗi giờ) nên L mỗi giờ là một lần chụp; báo trước t_m chưa chắc là báo nhầm,
vì bể có thể đang có một tường khác (xem cột `tick` trong `chuoi_L_gio.csv`).
"""
from __future__ import annotations

import argparse
import math
import statistics
from pathlib import Path

import numpy as np
import pandas as pd

from metrics.phat_hien import cac_buoc_bao


def gio_block(block, moc: pd.DataFrame) -> np.ndarray:
    """Giờ (số thực, tính từ mốc đầu của `moc`) của các block, nội suy tuyến tính và ngoại suy theo nhịp block trung bình."""
    b, ts = moc["block"].to_numpy(float), moc["ts"].to_numpy(float)
    nhip = (ts[-1] - ts[0]) / (b[-1] - b[0])
    x = np.asarray(block, float)
    g = np.interp(x, b, ts)
    g = np.where(x < b[0], ts[0] + (x - b[0]) * nhip, np.where(x > b[-1], ts[-1] + (x - b[-1]) * nhip, g))
    return (g - ts[0]) / 3600.0


def chuoi_L_that(swap: pd.DataFrame, moc: pd.DataFrame, block_dau: int | None = None) -> pd.DataFrame:
    """Bảng theo giờ (chỉ số = giờ nguyên kể từ `block_dau`, mặc định swap đầu): L = thanh khoản hoạt động (đơn vị L
    thô) sau swap cuối của giờ, tick = tick lúc đó, n = số swap mẫu; giờ trống giữ L, tick giờ trước."""
    s = swap.sort_values(["block", "tx_index", "log_index"], kind="stable")
    b0 = int(s["block"].iloc[0]) if block_dau is None else int(block_dau)
    g0 = gio_block([b0], moc)[0]
    h = np.floor(gio_block(s["block"], moc) - g0).astype(int)
    d = pd.DataFrame(dict(h=h, L=s["liquidity_active"].astype(float).to_numpy(), tick=s["tick"].to_numpy()))
    d = d[d["h"] >= 0]
    kq = d.groupby("h").agg(L=("L", "last"), tick=("tick", "last"), n=("L", "size"))
    kq = kq.reindex(range(0, int(kq.index.max()) + 1))
    kq["n"] = kq["n"].fillna(0).astype(int)
    kq[["L", "tick"]] = kq[["L", "tick"]].ffill()
    kq.index.name = "gio"
    return kq.dropna(subset=["L"])


def danh_gia_that(L: pd.Series, h_m: int, h_b: int, m: float = 3.0, N: int = 24) -> dict:
    """Một dòng đánh giá trên chuỗi L thật (chỉ số = giờ): `t_bao` = giờ báo đầu trong [h_m, h_b), `som_hon_rut` =
    h_b − t_bao (giờ), `bao_truoc_tm` = số giờ có tín hiệu trước h_m trên `gio_nen` giờ xét được (đường nền đã đủ N),
    `ty_so_tm` = L giờ h_m / trung vị L của N giờ trước, `ty_so_max` = lớn nhất của tỷ số đó trong [h_m, h_b)."""
    bao = cac_buoc_bao(L, m, N)
    trong = [t for t in bao if h_m <= t < h_b]

    def ty(t):
        truoc = L.loc[max(L.index[0], t - N):t - 1]
        nen = statistics.median(truoc) if len(truoc) else math.nan
        return float(L.loc[t]) / nen if nen and nen > 0 else math.nan

    cac = [ty(t) for t in range(h_m, h_b) if t in L.index]
    return dict(m=m, N=N, bat=bool(trong), t_bao=trong[0] if trong else None,
                som_hon_rut=float(h_b - trong[0]) if trong else math.nan, so_gio_bao=len(trong),
                bao_truoc_tm=sum(t < h_m for t in bao), gio_nen=max(0, h_m - int(L.index[0]) - N),
                ty_so_tm=ty(h_m) if h_m in L.index else math.nan, ty_so_max=np.nanmax(cac) if cac else math.nan)


def chay(vao: Path, tm: int, tb: int, N: int = 24, cac_m=(1.5, 2.0, 3.0, 5.0, 10.0)) -> pd.DataFrame:
    """Đọc `swap.csv`, `moc.csv` trong `vao`, ghi `chuoi_L_gio.csv` và `phat_hien_that.csv`; trả bảng đánh giá theo m."""
    swap = pd.read_csv(vao / "swap.csv")
    moc = pd.read_csv(vao / "moc.csv")
    ch = chuoi_L_that(swap, moc)
    b0 = int(swap["block"].min())
    g0 = gio_block([b0], moc)[0]
    h_m, h_b = (int(math.floor(gio_block([x], moc)[0] - g0)) for x in (tm, tb))
    ch.to_csv(vao / "chuoi_L_gio.csv", encoding="utf-8-sig")
    kq = pd.DataFrame([danh_gia_that(ch["L"], h_m, h_b, m, N) for m in cac_m])
    kq.insert(0, "h_b", h_b)
    kq.insert(0, "h_m", h_m)
    kq.to_csv(vao / "phat_hien_that.csv", index=False, encoding="utf-8-sig")
    return kq


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--vao", required=True, help="thư mục có swap.csv, moc.csv")
    ap.add_argument("--tm", type=int, required=True, help="block dựng tường (t_m của bài gốc)")
    ap.add_argument("--tb", type=int, required=True, help="block giá sập (t_b của bài gốc)")
    ap.add_argument("--N", type=int, default=24, help="số giờ đường nền")
    a = ap.parse_args()
    bang = chay(Path(a.vao), a.tm, a.tb, a.N)
    print(bang.round(2).to_string(index=False))
    print(f"→ {Path(a.vao) / 'phat_hien_that.csv'}")

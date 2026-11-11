"""Quét toàn chuỗi tìm ứng viên tường thanh khoản: vị thế hẹp, lớn, có vị thế khác vào cùng khoảng rồi bị rút.

Bước 1 (tải, chạy tiếp được): `eth_getLogs` Mint/Burn của mọi bể Uniswap v3 / PancakeSwap v3 trên chuỗi, chỉ giữ
vị thế rộng ≤ `--rong_max` tick → `ket_qua/that_quet/<chuoi>/hep.csv`, `moc.csv` (block, thời gian), `tien_do.json`.
Bước 2 (phân tích): ghép mỗi Mint với Burn đầu tiên cùng bể, cùng khoảng, cùng chủ, rút ≥ 90% lượng L; giữ cặp sống
`--gio_min`…`--gio_max` giờ mà trong lúc sống có mint khác vào đúng khoảng đó và không mint nào lớn hơn → `ung_vien.csv`.
Ứng viên đứng đầu được tra thêm người gửi giao dịch (mint qua NonfungiblePositionManager có `owner` là hợp đồng đó, nên
phải đếm theo người gửi) và `tickSpacing()` của bể (khoảng đúng một nấc thì `mot_nac` = True).

Bộ lọc giá sập (11/11): với mỗi ứng viên, tải swap của bể trong `--gio_sau` giờ sau khi tường rút và chỉ giữ ứng
viên mà giá rời khoảng tường ≥ 10% (mốc t_b của bài gốc; bể neo giá như USDC/USDT bị loại ở đây) → `ung_vien_tho.csv`
có cột `sap`; ứng viên qua lọc được đo thêm `ty_ghim` (phần swap nằm trong khoảng tường lúc tường còn), tra người gửi
và tickSpacing → `ung_vien.csv`. Vẫn chưa biết bể có trợ cấp khối lượng hay không; ứng viên cần tải đủ bằng
`scenarios.lay_log_bsc --chuoi ... --pool ...` rồi xem tay.

    python -m scenarios.quet_tuong_that --chuoi eth --ngay 30 [--nhanh]
    python -m scenarios.quet_tuong_that --chuoi arb --tu 300000000 --den 310000000
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from scenarios.lay_log_bsc import CHUOI, COT, RPC, TOPIC, keccak256, tai_doan, url_rpc

_SEL_TICK_SPACING = "0x" + keccak256(b"tickSpacing()")[:4].hex()


def gio_cua(block: pd.Series | np.ndarray, moc: pd.DataFrame) -> np.ndarray:
    """Đổi số block thành giờ Unix (nội suy tuyến tính theo các mốc block → thời gian trong `moc`)."""
    m = moc.sort_values("block").drop_duplicates("block")
    return np.interp(np.asarray(block, float), m["block"].to_numpy(float), m["ts"].to_numpy(float)) / 3600.0


def tim_tuong(df: pd.DataFrame, moc: pd.DataFrame, gio_min: float = 6.0, gio_max: float = 720.0,
              ty_rut: float = 0.9) -> pd.DataFrame:
    """Ghép Mint → Burn cùng (pool, tick_lower, tick_upper, owner), trả các cặp sống trong [gio_min, gio_max] giờ có
    ít nhất một mint khác vào cùng khoảng lúc tường còn và không mint nào trong lúc đó lớn hơn tường.

    Cột: pool, tick_lower, tick_upper, rong (tick), owner, L (thô), block_mint, block_burn, tx_mint, gio_song,
    n_khac (số giao dịch mint khác trong khoảng), L_khac (tổng L thô của chúng), tx_khac (danh sách hash)."""
    if df.empty:
        return pd.DataFrame()
    d = df[df["liquidity"].astype(float) > 0].copy()
    d["liquidity"] = d["liquidity"].astype(float)
    d = d.sort_values(["block", "tx_index", "log_index"], kind="stable")
    d["gio"] = gio_cua(d["block"], moc)
    kq = []
    # chỉ giữ khoảng có ≥ 2 mint và ≥ 1 burn (phần lớn khoảng bị loại ở đây, trước vòng lặp)
    dem = d.groupby(["pool", "tick_lower", "tick_upper"])["kind"].agg(
        n_mint=lambda k: (k == "mint").sum(), n_burn=lambda k: (k == "burn").sum())
    giu = dem[(dem["n_mint"] >= 2) & (dem["n_burn"] >= 1)].index
    d = d.set_index(["pool", "tick_lower", "tick_upper"]).loc[lambda x: x.index.isin(giu)].reset_index()
    for (pool, tl, tu), g in d.groupby(["pool", "tick_lower", "tick_upper"], sort=False):
        kind = g["kind"].to_numpy()
        own = g["owner"].to_numpy()
        L = g["liquidity"].to_numpy()
        tx = g["tx_hash"].to_numpy()
        gio = g["gio"].to_numpy()
        blk = g["block"].to_numpy()
        la_mint = kind == "mint"
        for i in np.flatnonzero(la_mint):
            sau = np.arange(i + 1, len(g))
            b = sau[(kind[sau] == "burn") & (own[sau] == own[i]) & (L[sau] >= ty_rut * L[i])]
            if not len(b):
                continue
            b = b[0]
            if not gio_min <= gio[b] - gio[i] <= gio_max:
                continue
            trong = np.arange(i + 1, b)
            trong = trong[la_mint[trong] & (tx[trong] != tx[i])]
            if not len(trong) or L[trong].max() > L[i]:
                continue
            txk = list(dict.fromkeys(tx[trong]))
            kq.append(dict(pool=pool, tick_lower=int(tl), tick_upper=int(tu), rong=int(tu - tl), owner=own[i],
                           L=L[i], block_mint=int(blk[i]), block_burn=int(blk[b]), tx_mint=tx[i],
                           gio_song=round(float(gio[b] - gio[i]), 2), n_khac=len(txk), L_khac=float(L[trong].sum()),
                           tx_khac=";".join(txk)))
    out = pd.DataFrame(kq)
    return out.sort_values(["n_khac", "gio_song"], ascending=False, ignore_index=True) if len(out) else out


def tai(chuoi: str, tu: int, den: int, ra: Path, rpc: RPC, rong_max: int = 200, buoc: int = 5000) -> dict:
    """Bước 1: tải Mint/Burn toàn chuỗi trong [tu, den], giữ vị thế rộng ≤ rong_max tick, ghi dần; chạy tiếp được."""
    ra.mkdir(parents=True, exist_ok=True)
    f_td = ra / "tien_do.json"
    td = json.loads(f_td.read_text()) if f_td.exists() else {"xong": tu - 1, "tu": tu}
    t0, n = time.time(), 0
    cot = COT + ["pool"]
    for e, rows in tai_doan(rpc, None, [TOPIC["mint"], TOPIC["burn"]], td["xong"] + 1, den, buoc, giu_be=True):
        hep = [r for r in rows if 0 < r["tick_upper"] - r["tick_lower"] <= rong_max]
        p = ra / "hep.csv"
        moi = not p.exists()
        with p.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cot)
            if moi:
                w.writeheader()
            w.writerows(hep)
        ts = int(rpc.goi("eth_getBlockByNumber", [hex(e), False])["timestamp"], 16)
        p = ra / "moc.csv"
        moi = not p.exists()
        with p.open("a", encoding="utf-8") as f:
            f.write(("block,ts\n" if moi else "") + f"{e},{ts}\n")
        td["xong"] = e
        f_td.write_text(json.dumps(td))
        n += len(hep)
        print(f"[{chuoi}] tới block {e} ({(e - tu + 1) / (den - tu + 1):.0%}): +{len(hep)}/{len(rows)} hẹp, "
              f"tổng {n}, {time.time() - t0:.0f}s")
    return td


LN_TICK = np.log(1.0001)


def do_lech(ticks: np.ndarray, tl: int, tu: int) -> tuple[float, float]:
    """Độ lệch giá còn ở lại so với khoảng tường [tl, tu): (giảm, tăng), dạng tỷ lệ (0,1 = 10%).

    `ticks` theo thứ tự thời gian; mức dùng là trung vị tick của nửa sau dãy, nên một cú swap lẻ vọt giá rồi bị
    arbitrage kéo về không tính là sập. Giảm đo từ biên dưới `tl`, tăng từ biên trên `tu`; trong khoảng tường thì bằng 0."""
    if len(ticks) == 0:
        return np.nan, np.nan
    muc = float(np.median(np.asarray(ticks)[len(ticks) // 2:]))
    xuong = max(0.0, tl - muc)
    len_ = max(0.0, muc - tu)
    return float(1 - np.exp(-xuong * LN_TICK)), float(np.exp(len_ * LN_TICK) - 1)


def _tick_swap(rpc: RPC, pool: str, tu: int, den: int, buoc: int) -> np.ndarray:
    tp = [TOPIC["swap_pancake"], TOPIC["swap_uniswap"]]
    return np.array([r["tick"] for _, rows in tai_doan(rpc, pool, tp, tu, den, buoc) for r in rows], dtype=float)


def kiem_sap(uv: pd.DataFrame, rpc: RPC, giay_block: float, gio_sau: float = 24.0) -> pd.DataFrame:
    """Tải swap của bể trong `gio_sau` giờ sau khi tường rút; thêm cột so_swap_sau, giam_sau, tang_sau, sap
    (sap = giá rời khoảng tường ≥ 10% theo một chiều, như mốc t_b của bài gốc). Một lần gọi cho mỗi (pool, block_burn)."""
    n = int(gio_sau * 3600 / giay_block)
    kq = {}
    for i, (pool, bb, tl, tu) in enumerate(uv[["pool", "block_burn", "tick_lower", "tick_upper"]].itertuples(index=False)):
        if (pool, bb, tl, tu) in kq:
            continue
        try:
            t = _tick_swap(rpc, pool, int(bb), int(bb) + n, n + 1)
        except RuntimeError as loi:
            print(f"  bỏ {pool} @ {bb}: {str(loi)[:80]}")
            t = np.array([])
        kq[(pool, bb, tl, tu)] = (len(t),) + do_lech(t, int(tl), int(tu))
        if (i + 1) % 50 == 0:
            print(f"  kiểm giá sập: {i + 1}/{len(uv)}")
    v = [kq[k] for k in uv[["pool", "block_burn", "tick_lower", "tick_upper"]].itertuples(index=False, name=None)]
    uv = uv.copy()
    uv["so_swap_sau"], uv["giam_sau"], uv["tang_sau"] = zip(*v) if v else ([], [], [])
    uv["sap"] = (uv["giam_sau"] >= 0.10) | (uv["tang_sau"] >= 0.10)
    return uv


def kiem_ghim(uv: pd.DataFrame, rpc: RPC, giay_block: float, so_mau: int = 6) -> pd.DataFrame:
    """Lấy `so_mau` cửa sổ một giờ cách đều trong lúc tường sống; ty_ghim = phần swap có tick nằm trong khoảng tường
    (bài gốc: giá bị ghim tại tường trong pha chuẩn bị). NaN nếu không có swap nào trong các cửa sổ."""
    w = max(3, int(3600 / giay_block))
    ty = []
    for pool, bm, bb, tl, tu in uv[["pool", "block_mint", "block_burn", "tick_lower", "tick_upper"]].itertuples(index=False):
        diem = np.linspace(int(bm), int(bb) - w, so_mau).astype(int) if int(bb) - int(bm) > w else [int(bm)]
        t = []
        for a in diem:
            try:
                t.extend(_tick_swap(rpc, pool, int(a), int(a) + w - 1, w))
            except RuntimeError:
                pass
        t = np.array(t)
        ty.append(float(np.mean((t >= tl) & (t < tu))) if len(t) else np.nan)
    uv = uv.copy()
    uv["ty_ghim"] = ty
    return uv


def bo_sung(uv: pd.DataFrame, rpc: RPC, top: int = 100) -> pd.DataFrame:
    """Tra người gửi giao dịch (tối đa 10 giao dịch khác mỗi ứng viên, ~0,6 giây mỗi lần gọi) và tickSpacing cho `top` ứng viên đầu; thêm cột nguoi_tuong, n_nguoi_khac, tick_spacing, mot_nac."""
    uv = uv.head(top).copy()
    gui, ts = {}, {}

    def nguoi(h):
        if h not in gui:
            gui[h] = (rpc.goi("eth_getTransactionByHash", [h]) or {}).get("from", "").lower()
        return gui[h]

    def tick_spacing(p):
        if p not in ts:
            try:
                ts[p] = int(rpc.goi("eth_call", [{"to": p, "data": _SEL_TICK_SPACING}, "latest"]), 16)
            except (RuntimeError, ValueError):
                ts[p] = -1
        return ts[p]

    uv["nguoi_tuong"] = [nguoi(h) for h in uv["tx_mint"]]
    uv["n_nguoi_khac"] = [len({nguoi(h) for h in s.split(";")[:10]} - {w}) for s, w in zip(uv["tx_khac"], uv["nguoi_tuong"])]
    uv["tick_spacing"] = [tick_spacing(p) for p in uv["pool"]]
    uv["mot_nac"] = uv["rong"] == uv["tick_spacing"]
    return uv.sort_values(["mot_nac", "n_nguoi_khac", "gio_song"], ascending=False, ignore_index=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--chuoi", required=True, choices=sorted(CHUOI))
    ap.add_argument("--tu", type=int, default=None, help="block đầu (hoặc dùng --ngay)")
    ap.add_argument("--den", type=int, default=None, help="block cuối (mặc định: block mới nhất lúc chạy lần đầu)")
    ap.add_argument("--ngay", type=float, default=None, help="quét bấy nhiêu ngày trước block cuối")
    ap.add_argument("--rpc", default=None)
    ap.add_argument("--rong_max", type=int, default=200, help="chỉ giữ vị thế rộng ≤ bấy nhiêu tick")
    ap.add_argument("--gio_min", type=float, default=6.0)
    ap.add_argument("--gio_max", type=float, default=720.0)
    ap.add_argument("--buoc", type=int, default=5000)
    ap.add_argument("--nghi", type=float, default=0.2)
    ap.add_argument("--top", type=int, default=100, help="số ứng viên được tra người gửi và tickSpacing")
    ap.add_argument("--gio_sau", type=float, default=24.0, help="cửa sổ sau khi tường rút để tìm giá sập (giờ)")
    ap.add_argument("--khong_loc_sap", action="store_true", help="giữ cả ứng viên không có giá sập")
    ap.add_argument("--chi_phan_tich", action="store_true", help="bỏ bước tải, chỉ phân tích hep.csv đã có")
    ap.add_argument("--nhanh", action="store_true", help="chỉ 1 ngày, thư mục _nhanh, để đo thời gian")
    a = ap.parse_args()
    rpc = RPC(url_rpc(a.chuoi, a.rpc), a.nghi)
    ra = Path("ket_qua/that_quet") / (a.chuoi + ("_nhanh" if a.nhanh else ""))
    f_td = ra / "tien_do.json"
    if not a.chi_phan_tich:
        if f_td.exists():                                       # chạy tiếp: giữ khoảng của lần đầu
            cu = json.loads(f_td.read_text())
            tu, den = cu["tu"], cu["den"]
        else:
            den = a.den or int(rpc.goi("eth_blockNumber", []), 16)
            ngay = 1.0 if a.nhanh else a.ngay
            if a.tu is None and ngay is None:
                raise SystemExit("Cần --tu hoặc --ngay.")
            tu = a.tu if a.tu is not None else den - int(ngay * 86400 / CHUOI[a.chuoi]["giay_block"])
            ra.mkdir(parents=True, exist_ok=True)
            f_td.write_text(json.dumps({"xong": tu - 1, "tu": tu, "den": den}))
        tai(a.chuoi, tu, den, ra, rpc, a.rong_max, a.buoc)
    df = pd.read_csv(ra / "hep.csv", dtype={"owner": str, "pool": str, "tx_hash": str})
    moc = pd.read_csv(ra / "moc.csv")
    uv = tim_tuong(df, moc, a.gio_min, a.gio_max)
    print(f"{len(df)} sự kiện hẹp, {df['pool'].nunique()} bể; {len(uv)} ứng viên thô")
    gb = CHUOI[a.chuoi]["giay_block"]
    if len(uv):
        uv = kiem_sap(uv, rpc, gb, a.gio_sau)
        uv.drop(columns=["tx_khac"]).to_csv(ra / "ung_vien_tho.csv", index=False, encoding="utf-8-sig")
        print(f"{int(uv['sap'].sum())}/{len(uv)} ứng viên có giá rời khoảng tường ≥ 10% trong {a.gio_sau:g} giờ sau khi rút")
        if not a.khong_loc_sap:
            uv = uv[uv["sap"]].reset_index(drop=True)
    if len(uv):
        uv = kiem_ghim(uv.head(a.top), rpc, gb)
        uv = bo_sung(uv, rpc, a.top)
        uv.drop(columns=["tx_khac"]).to_csv(ra / "ung_vien.csv", index=False, encoding="utf-8-sig")
        cot = ["pool", "rong", "mot_nac", "gio_song", "n_nguoi_khac", "ty_ghim", "giam_sau", "tang_sau"]
        print(uv[cot].head(15).round(3).to_string(index=False))
        print(f"→ {ra / 'ung_vien.csv'}")
    else:
        print("Không còn ứng viên nào sau bộ lọc.")

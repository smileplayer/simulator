"""Phát lại một vụ thật qua engine (cải tiến "thực tế hơn", việc 1): nạp bản đồ thanh khoản thật rồi cho engine
thực hiện đúng chuỗi Mint/Burn/Swap on-chain quanh lúc sập, so giá và thanh khoản hoạt động với log.

    python -m metrics.tai_hien_vu --vao ket_qua/that/vu/0xa2070173_59148623 [--phi 0.0001]

Cần `su_kien.csv` (Mint/Burn đủ) và `swap_day_du.csv` (swap ĐỦ trong cửa sổ, do `scenarios.tai_vi_vu` tải).
Bản đồ thanh khoản dựng từ mọi Mint/Burn trước swap đầu của cửa sổ; nếu log không bắt đầu từ lúc tạo bể thì bản đồ
có thể thiếu vị thế cũ, nên bước 1 kiểm L hoạt động suy từ bản đồ với `liquidity_active` ghi trong từng swap.
Đơn vị: L và lượng token là số thô on-chain (chưa chia 10^decimals); giá = token1/token0; tick theo v3.
Kết quả: `ket_qua/that/tai_hien/<thư mục vụ>.csv` (từng swap) và in bảng tóm tắt.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from engine.pool import Pool
from engine.tick_math import MAX_TICK, MIN_TICK, tick_at_sqrt_price

RA = Path(__file__).resolve().parents[1] / "ket_qua" / "that" / "tai_hien"
Q96 = float(2 ** 96)


def _so(x) -> int:
    """Chuỗi số nguyên lớn → int (rỗng/NaN → 0)."""
    s = str(x).strip()
    return int(s) if s not in ("", "nan", "None") else 0


def doc_su_kien(vao: Path) -> pd.DataFrame:
    """Đọc Mint/Burn/Swap của một thư mục vụ thành một bảng xếp theo (block, tx_index, log_index); swap lấy từ
    `swap_day_du.csv`. Cột: kind, tick_lower, tick_upper, L (thô), a0, a1 (thô, có dấu), sqrtP (thực), tick, L_log."""
    ev = pd.read_csv(vao / "su_kien.csv", dtype=str)
    sw = pd.read_csv(vao / "swap_day_du.csv", dtype=str)
    from scenarios.tai_lich_su_be import doc_lich_su       # lịch sử trước cửa sổ (nếu đã tải): bản đồ thanh khoản không thiếu vị thế cũ
    ls = doc_lich_su(Path(vao).name.split("_")[0], int(ev["block"].astype(int).min()), vu=Path(vao).parent)
    if len(ls):
        ev = pd.concat([ls, ev], ignore_index=True)
    ev["kind"] = ev["kind"].str.lower()
    ev = ev[ev["kind"].isin(["mint", "burn"])]
    sw["kind"] = "swap"
    d = pd.concat([ev, sw], ignore_index=True)
    for c in ("block", "tx_index", "log_index"):
        d[c] = d[c].astype(int)
    d["L"] = [float(_so(x)) for x in d["liquidity"]]
    d["a0"] = [float(_so(x)) for x in d["amount0"]]
    d["a1"] = [float(_so(x)) for x in d["amount1"]]
    d["sqrtP"] = [_so(x) / Q96 for x in d["sqrt_price_x96"]]
    d["L_log"] = [float(_so(x)) for x in d["liquidity_active"]]
    d["tick"] = pd.to_numeric(d["tick"], errors="coerce")
    for c in ("tick_lower", "tick_upper"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.drop_duplicates(["block", "tx_index", "log_index"])
    return d.sort_values(["block", "tx_index", "log_index"]).reset_index(drop=True)


def cua_so_swap(vao: Path) -> list[tuple[int, int]]:
    """Các cửa sổ block [đầu, cuối] có swap đủ, đọc từ `tien_do_vi.json` (khóa "swap": {"a-b": …}); rỗng nếu không có."""
    f = vao / "tien_do_vi.json"
    if not f.exists():
        return []
    ks = json.loads(f.read_text(encoding="utf-8")).get("swap", {})
    return sorted(tuple(int(x) for x in k.split("-")) for k in ks)


def phat_lai(d: pd.DataFrame, phi: float, cua_so: list[tuple[int, int]] | None = None, dong_bo: bool = False) -> pd.DataFrame:
    """Phát lại qua engine: mọi Mint/Burn từ đầu log; swap trong từng cửa sổ đủ. Swap đầu mỗi cửa sổ chỉ dùng để đặt
    giá (giá sau swap đó) và L hoạt động theo bản đồ, không so. Trả bảng từng swap: giá, L hoạt động, lượng ra của
    engine so với log (thô), kèm cột `cs` (số thứ tự cửa sổ).

    `dong_bo`: sau mỗi lệnh nạp/rút phủ tick đang chứa giá, đặt lại giá engine bằng giá log của swap ngay trước (nạp/rút không đổi giá).
    Lý do: sai số làm tròn float64 của giá, nhân với L, là một lượng token; khi tường dày gấp trăm–nghìn lần được dựng đúng tick đang
    chứa giá thì lượng lệch đó phóng to theo L và engine vượt tick sớm/muộn hơn log. Số lần và mức lệch lớn nhất lúc đặt lại ghi ở `attrs`."""
    sw = d.index[d["kind"] == "swap"]
    if not cua_so:
        cua_so = [(int(d.at[sw[0], "block"]), int(d.at[sw[-1], "block"]))]
    dau = [a for a, _ in cua_so]
    pool = Pool(fee=phi, sqrt_price=d.at[sw[0], "sqrtP"], tick_spacing=1)
    vi_the: dict[tuple[int, int], list[int]] = {}                 # (lo, hi) → các id vị thế còn L, cũ trước
    dong, thieu, cs = [], 0.0, -1
    truoc, can_db, n_db, lech_db = None, False, 0, 0.0
    for r in d.itertuples(index=False):
        if r.kind != "swap":
            if r.L <= 0:
                continue
            lo, hi = int(max(r.tick_lower, MIN_TICK)), int(min(r.tick_upper, MAX_TICK))
            if dong_bo and truoc is not None and (lo <= pool.tick < hi or lo <= truoc.tick < hi):
                can_db = True
            if r.kind == "mint":
                vi_the.setdefault((lo, hi), []).append(pool.mint("that", lo, hi, r.L)[0])
                continue
            con, ds = r.L, vi_the.get((lo, hi), [])
            while con > 0 and ds:
                p = pool._state(ds[0]).pos
                lay = min(con, p.liquidity)
                pool.burn(ds[0], lay)
                con -= lay
                if p.liquidity <= lay * 1e-12:
                    ds.pop(0)
            thieu += con                                          # > 0: rút vị thế nạp trước đầu log
            continue
        moi_cs = max((i for i, a in enumerate(dau) if r.block >= a), default=0)
        if moi_cs != cs:                                          # swap đầu cửa sổ: đặt lại giá, không so
            cs = moi_cs
            pool.sqrt_price = r.sqrtP
            pool.tick = tick_at_sqrt_price(pool.sqrt_price)
            pool.liquidity, pool.liquidity_weighted = pool._active_sums(pool.tick)
            truoc, can_db = r, False
            continue
        if can_db:                                                # nạp/rút vừa đổi L ở tick chứa giá: lấy lại giá log
            n_db, lech_db, can_db = n_db + 1, max(lech_db, abs(pool.sqrt_price / truoc.sqrtP - 1)), False
            pool.sqrt_price, pool.tick = truoc.sqrtP, int(truoc.tick)
            pool.liquidity, pool.liquidity_weighted = pool._active_sums(pool.tick)
        ban0 = r.a0 > 0                                           # token0 vào bể ⇒ giá giảm
        vao, ra_log = (r.a0, -r.a1) if ban0 else (r.a1, -r.a0)
        if vao <= 0:
            truoc = r
            continue
        z_truoc, L_truoc = pool.sqrt_price, pool.liquidity
        kq = pool.swap("that", zero_for_one=ban0, amount_in=vao)
        dong.append((r.block, r.log_index, cs, ban0, vao, ra_log, kq.amount_out, r.sqrtP, pool.sqrt_price, z_truoc,
                     r.tick, pool.tick, r.L_log, pool.liquidity, L_truoc))
        truoc = r
        if len(pool.log.rows if hasattr(pool.log, "rows") else ()) > 200000:
            pool.log.rows.clear()
    kq = pd.DataFrame(dong, columns=["block", "log_index", "cs", "ban0", "vao", "ra_log", "ra_engine", "sqrtP_log",
                                     "sqrtP_engine", "sqrtP_truoc", "tick_log", "tick_engine", "L_log", "L_engine", "L_truoc"])
    kq.attrs["L_rut_khong_thay_nap"] = thieu
    kq.attrs["n_dong_bo"], kq.attrs["lech_dong_bo_max"] = n_db, lech_db
    return kq


def tom_tat(kq: pd.DataFrame) -> dict:
    """Sai số tương đối của giá (P = sqrtP²), L hoạt động và lượng ra, và số swap vượt tick (đổi tick so với trước)."""
    gia = (kq["sqrtP_engine"] ** 2 / kq["sqrtP_log"] ** 2 - 1).abs()
    L = ((kq["L_engine"] - kq["L_log"]).abs() / kq["L_log"].where(kq["L_log"] > 0)).fillna((kq["L_engine"] > 0).astype(float))
    ra = ((kq["ra_engine"] - kq["ra_log"]).abs() / kq["ra_log"].abs().where(kq["ra_log"] != 0))
    vuot = (kq["sqrtP_truoc"].map(lambda z: math.floor(2 * math.log(z) / math.log(1.0001))) != kq["tick_log"])
    pv = lambda x: {k: float(np.nanpercentile(x, q)) for k, q in (("tv", 50), ("p99", 99), ("max", 100))}
    return dict(n_swap=len(kq), n_vuot_tick=int(vuot.sum()), gia=pv(gia), L=pv(L), ra=pv(ra),
                gia_vuot_tick=pv(gia[vuot]) if vuot.any() else None,
                tick_dau=int(kq["tick_log"].iloc[0]), tick_min=int(kq["tick_log"].min()), tick_max=int(kq["tick_log"].max()),
                L_rut_khong_thay_nap=kq.attrs.get("L_rut_khong_thay_nap", 0.0),
                n_dong_bo=kq.attrs.get("n_dong_bo", 0), lech_dong_bo_max=kq.attrs.get("lech_dong_bo_max", 0.0))


def chay(vao: Path, phi: float, dong_bo: bool = False) -> dict:
    """Phát lại một thư mục vụ, ghi CSV từng swap vào `ket_qua/that/tai_hien/`, trả tóm tắt (kèm tên thư mục)."""
    kq = phat_lai(doc_su_kien(vao), phi, cua_so_swap(vao), dong_bo)
    RA.mkdir(parents=True, exist_ok=True)
    kq.to_csv(RA / f"{vao.name}.csv", index=False)
    t = tom_tat(kq)
    t["thu_muc"] = vao.name
    gia = (kq["sqrtP_engine"] ** 2 / kq["sqrtP_log"] ** 2 - 1).abs()
    t["n_gia_lech_1e-3"], t["n_gia_lech_1e-2"] = int((gia > 1e-3).sum()), int((gia > 1e-2).sum())
    t["gia_lech_cuoi"] = float(gia.iloc[-1]) if len(gia) else float("nan")
    return t


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--vao", nargs="*", default=[], help="thư mục vụ có su_kien.csv và swap_day_du.csv")
    ap.add_argument("--tat_ca", action="store_true", help="mọi thư mục trong ket_qua/that/vu (bỏ đuôi _nhanh)")
    ap.add_argument("--phi", type=float, default=0.0001, help="mức phí của bể (mặc định 0,01%)")
    ap.add_argument("--dong_bo", action="store_true", help="đặt lại giá theo log sau mỗi lệnh nạp/rút phủ tick chứa giá (khử khuếch đại sai số float)")
    a = ap.parse_args()
    ds = [Path(x) for x in a.vao]
    if a.tat_ca:
        ds += sorted(p for p in (RA.parent / "vu").iterdir() if p.is_dir() and not p.name.endswith("_nhanh")
                     and (p / "swap_day_du.csv").exists())
    bang = []
    for vao in ds:
        t = chay(vao, a.phi, a.dong_bo)
        bang.append(dict(thu_muc=t["thu_muc"], n_swap=t["n_swap"], n_vuot_tick=t["n_vuot_tick"], tick_dau=t["tick_dau"],
                         tick_min=t["tick_min"], tick_max=t["tick_max"], gia_tv=t["gia"]["tv"], gia_p99=t["gia"]["p99"],
                         gia_max=t["gia"]["max"], n_gia_lech_1e_3=t["n_gia_lech_1e-3"], n_gia_lech_1e_2=t["n_gia_lech_1e-2"],
                         gia_lech_cuoi=t["gia_lech_cuoi"], L_p99=t["L"]["p99"], ra_tv=t["ra"]["tv"], ra_p99=t["ra"]["p99"],
                         L_rut_khong_thay_nap=t["L_rut_khong_thay_nap"],
                         n_dong_bo=t["n_dong_bo"], lech_dong_bo_max=t["lech_dong_bo_max"]))
        print(f"== {t['thu_muc']}: {t['n_swap']} swap, {t['n_vuot_tick']} vượt tick; tick {t['tick_dau']} → "
              f"[{t['tick_min']}, {t['tick_max']}]; giá lệch trung vị {t['gia']['tv']:.1e}, p99 {t['gia']['p99']:.1e}, "
              f"lớn nhất {t['gia']['max']:.1e}; L thiếu {t['L_rut_khong_thay_nap']:.2e}; đồng bộ {t['n_dong_bo']} lần, "
              f"lệch lúc đồng bộ ≤ {t['lech_dong_bo_max']:.1e}", flush=True)
        pd.DataFrame(bang).to_csv(RA / ("tom_tat_dong_bo.csv" if a.dong_bo else "tom_tat.csv"), index=False)

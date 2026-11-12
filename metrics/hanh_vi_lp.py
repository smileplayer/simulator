"""Thống kê hành vi LP thường trên log thật của các bể đối chứng (không trợ cấp).

    python -m metrics.hanh_vi_lp [--vao <thư mục> ...]

Mặc định lấy mọi đoạn đối chứng có dữ liệu (`ket_qua/that/doi_chung/*`, `P1_doi_chung`). Từ `su_kien.csv`, `swap.csv`,
`moc.csv` ghép mint → burn theo khóa (owner, tick_lower, tick_upper), FIFO theo (block, tx_index, log_index) và theo
lượng L: mỗi lần mint là một lô; burn có liquidity > 0 lấy dần từ lô cũ nhất; lô coi là đóng khi tổng burn ≥ 0,9 tổng
mint của lô (thời điểm đóng = block của burn đó). Mỗi vị thế ghi: độ rộng (tick), độ rộng theo bội tickSpacing (tickSpacing
suy từ ước chung lớn nhất của mọi mốc tick trong bể), thời gian giữ (giờ), `tre_rut_gio` = giờ từ mẫu swap đầu tiên có tick
ngoài [tick_lower, tick_upper) (trong đời vị thế) tới lúc đóng; NaN nếu giá không rời khoảng hoặc vị thế chưa đóng.
Ra `ket_qua/that/hanh_vi_lp.csv` và in phân vị 10/25/50/75/90 cùng tỷ lệ rút trong 1/6/24 giờ sau khi giá rời khoảng.

Hạn chế: (1) chủ vị thế trong log của đa số LP là hợp đồng NonfungiblePositionManager nên khóa ghép gộp mọi LP cùng khoảng
vào một chủ; FIFO theo lượng L chỉ là xấp xỉ (không biết lô nào của LP nào), thời gian giữ có thể lệch. (2) Swap chỉ là
mẫu (~30 giây mỗi giờ), nên thời điểm giá rời khoảng trễ tới một giờ và `tre_rut_gio` bị thiên thấp tương ứng. (3) Mint
trước đoạn tải không có lô để ghép nên burn tương ứng bị bỏ; vị thế đang mở cuối đoạn bị kiểm duyệt phải (không có
`tre_rut_gio`), tỷ lệ rút trong X giờ là cận dưới. (4) Mẫu số của tỷ lệ là vị thế mà giá từng rời khoảng trong đời nó.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

from metrics.danh_gia_vu_that import doan_doi_chung_co_du_lieu
from metrics.phat_hien_that import gio_block
from scenarios.tai_vu_that import GOC, BANG_DOI_CHUNG, BANG_VU, doc_bang_vu, doc_doi_chung, ke_hoach

NGUONG_DONG = 0.9
COT = ["doan", "owner", "tick_lower", "tick_upper", "do_rong", "do_rong_boi", "block_mint", "block_dong", "dong",
       "giu_gio", "tre_rut_gio"]


def ghep_vi_the(ev: pd.DataFrame) -> pd.DataFrame:
    """Ghép mint → burn FIFO theo (owner, tick_lower, tick_upper); trả bảng mỗi lô một dòng: block_mint, block_dong (NaN nếu
    chưa đóng), dong (bool). `ev` cần cột block, tx_index, log_index, kind, owner, tick_lower, tick_upper, liquidity."""
    e = ev[ev["kind"].isin(["mint", "burn"])].copy()
    e["liquidity"] = pd.to_numeric(e["liquidity"], errors="coerce").astype(float)
    e = e[e["liquidity"] > 0].sort_values(["block", "tx_index", "log_index"], kind="stable")
    rows = []
    for (ow, tl, tu), g in e.groupby(["owner", "tick_lower", "tick_upper"], sort=False):
        lo: list[list] = []                       # [block_mint, L_ban_dau, L_da_rut, block_dong]
        for r in g.itertuples():
            if r.kind == "mint":
                lo.append([int(r.block), r.liquidity, 0.0, None])
                continue
            con = r.liquidity
            for x in lo:
                if con <= 0:
                    break
                if x[3] is not None or x[2] >= x[1]:
                    continue
                lay = min(con, x[1] - x[2])
                x[2] += lay
                con -= lay
                if x[3] is None and x[2] >= NGUONG_DONG * x[1]:
                    x[3] = int(r.block)
        for bm, L0, _, bd in lo:
            rows.append(dict(owner=ow, tick_lower=int(tl), tick_upper=int(tu), block_mint=bm,
                             block_dong=float(bd) if bd is not None else math.nan, dong=bd is not None))
    return pd.DataFrame(rows, columns=["owner", "tick_lower", "tick_upper", "block_mint", "block_dong", "dong"])


def them_thoi_gian(vt: pd.DataFrame, swap: pd.DataFrame, moc: pd.DataFrame, tick_spacing: int) -> pd.DataFrame:
    """Thêm do_rong (tick), do_rong_boi (bội tickSpacing hoặc NaN), giu_gio và tre_rut_gio (giờ) cho bảng lô `vt`."""
    vt = vt.copy()
    vt["do_rong"] = vt["tick_upper"] - vt["tick_lower"]
    vt["do_rong_boi"] = vt["do_rong"] / tick_spacing if tick_spacing > 0 else math.nan
    s = swap.sort_values("block", kind="stable")
    sb, st = s["block"].to_numpy(float), s["tick"].to_numpy(float)
    giu, tre = [], []
    for r in vt.itertuples():
        if not r.dong:
            giu.append(math.nan)
            tre.append(math.nan)
            continue
        giu.append(float(gio_block([r.block_dong], moc)[0] - gio_block([r.block_mint], moc)[0]))
        i, j = np.searchsorted(sb, r.block_mint, "left"), np.searchsorted(sb, r.block_dong, "right")
        ngoai = (st[i:j] < r.tick_lower) | (st[i:j] >= r.tick_upper)
        if ngoai.any():
            k = i + int(np.argmax(ngoai))
            tre.append(max(0.0, float(gio_block([r.block_dong], moc)[0] - gio_block([sb[k]], moc)[0])))
        else:
            tre.append(math.nan)
    vt["giu_gio"], vt["tre_rut_gio"] = giu, tre
    return vt


def _roi_khoang(vt: pd.DataFrame, swap: pd.DataFrame) -> np.ndarray:
    """Cờ bool: trong đời vị thế (từ mint tới đóng, hoặc tới hết đoạn) có mẫu swap nào có tick ngoài khoảng không."""
    s = swap.sort_values("block", kind="stable")
    sb, st = s["block"].to_numpy(float), s["tick"].to_numpy(float)
    cuoi = sb[-1] if len(sb) else 0.0
    kq = []
    for r in vt.itertuples():
        den = r.block_dong if r.dong else cuoi
        i, j = np.searchsorted(sb, r.block_mint, "left"), np.searchsorted(sb, den, "right")
        kq.append(bool(((st[i:j] < r.tick_lower) | (st[i:j] >= r.tick_upper)).any()))
    return np.array(kq, dtype=bool)


def hanh_vi_thu_muc(ten: str, ra: Path) -> pd.DataFrame:
    """Bảng vị thế (cột `COT` + `roi_khoang`) của một thư mục đã tải; rỗng nếu thiếu dữ liệu."""
    ev, swap, moc = (pd.read_csv(ra / f) for f in ("su_kien.csv", "swap.csv", "moc.csv"))
    # tải bị ngắt giữa lúc ghi rồi chạy lại có thể ghi trùng vài dòng: bỏ trùng theo (block, log_index)
    ev = ev.drop_duplicates(subset=[c for c in ("block", "tx_index", "log_index", "kind") if c in ev.columns])
    swap = swap.drop_duplicates(subset=[c for c in ("block", "tx_index", "log_index") if c in swap.columns])
    if ev.empty or swap.empty or len(moc) < 2:
        return pd.DataFrame(columns=COT + ["roi_khoang"])
    ticks = pd.concat([ev["tick_lower"], ev["tick_upper"]]).dropna().astype(int).abs()
    ts = int(np.gcd.reduce(ticks.to_numpy())) if len(ticks) else 0
    vt = them_thoi_gian(ghep_vi_the(ev), swap, moc, ts)
    vt["roi_khoang"] = _roi_khoang(vt, swap) if len(vt) else []
    vt.insert(0, "doan", ten)
    return vt[COT + ["roi_khoang"]]


def tom_tat(vt: pd.DataFrame) -> dict:
    """Phân vị 10/25/50/75/90 của do_rong, giu_gio, tre_rut_gio và tỷ lệ rút trong 1/6/24 giờ sau khi giá rời khoảng."""
    q = [10, 25, 50, 75, 90]
    ph = {c: {f"p{p}": float(np.nanpercentile(vt[c].dropna(), p)) if vt[c].notna().any() else math.nan for p in q}
          for c in ("do_rong", "giu_gio", "tre_rut_gio")}
    roi = vt[vt["roi_khoang"].astype(bool)]
    ty = {f"rut_{h}h": float((roi["tre_rut_gio"] <= h).sum() / len(roi)) if len(roi) else math.nan for h in (1, 6, 24)}
    return dict(so_vi_the=len(vt), so_dong=int(vt["dong"].sum()), so_roi_khoang=len(roi), phan_vi=ph, ty_le=ty)


def chay(thu_muc: list[tuple[str, Path]], ra_csv: Path = GOC / "hanh_vi_lp.csv") -> pd.DataFrame:
    """Gộp vị thế của các thư mục, ghi `ra_csv`, trả bảng."""
    ds = [hanh_vi_thu_muc(t, p) for t, p in thu_muc]
    vt = pd.concat([d for d in ds if len(d)], ignore_index=True) if any(len(d) for d in ds) else pd.DataFrame(columns=COT + ["roi_khoang"])
    ra_csv.parent.mkdir(parents=True, exist_ok=True)
    vt.to_csv(ra_csv, index=False, encoding="utf-8-sig")
    return vt


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--vao", nargs="*", default=None, help="thư mục dữ liệu (mặc định: mọi đoạn đối chứng có dữ liệu)")
    a = ap.parse_args()
    if a.vao:
        tm = [(Path(p).name, Path(p)) for p in a.vao]
    else:
        ke = ke_hoach(doc_bang_vu(BANG_VU), doc_doi_chung(BANG_DOI_CHUNG))
        tm = [(f"{t}:{p.name}", p) for t, p in doan_doi_chung_co_du_lieu(ke)]
    print("Thư mục:", ", ".join(p.as_posix() for _, p in tm) or "(không có)")
    vt = chay(tm)
    if vt.empty:
        raise SystemExit("Không có vị thế nào (chưa có dữ liệu đối chứng).")
    t = tom_tat(vt)
    print(f"Vị thế (lô mint): {t['so_vi_the']}, đã đóng: {t['so_dong']}, giá từng rời khoảng: {t['so_roi_khoang']}")
    print(pd.DataFrame(t["phan_vi"]).T.round(2).to_string())
    print("Tỷ lệ rút trong X giờ sau khi giá rời khoảng (mẫu số = vị thế giá từng rời khoảng):",
          {k: round(v, 3) for k, v in t["ty_le"].items()})
    print(f"→ {GOC / 'hanh_vi_lp.csv'}")

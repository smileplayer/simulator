"""Kiểm định engine CLMM bằng log on-chain thật của bể PancakeSwap/Uniswap v3 (file do `scenarios.lay_log_bsc` tải).

    python -m metrics.kiem_engine_that --vao ket_qua/that/0x9485_hai_vu [--nhanh] [--phi 0.0025] [--gap_max 40]

Mức 1 (toán học swap trong một tick): với mỗi swap có swap liền kề trước trong cùng cửa sổ mẫu, dựng bể engine có
một vị thế toàn dải với L = L_pre, đặt giá = giá sau swap trước, cho engine swap đúng lượng vào và chiều như log,
rồi so giá sau swap và lượng ra với log. `L_pre` = L ghi ở swap trước + Σ(mint − burn) nằm giữa hai swap và chứa tick
giá lúc đó; chỉ giữ swap có L ghi trong log = L_pre (không vượt tick đã khởi tạo). Mức 2 (phát lại từ lúc tạo bể)
chỉ xét tính khả thi: cần Initialize/giá đầu và đủ mọi swap, log tải về không có.

Đơn vị: lượng token và L là số nguyên thô trên chuỗi (chưa chia số chữ số thập phân); √P = sqrtPriceX96 / 2^96 là
√(token1 thô / token0 thô); tick là tick của bể. Mức phí không nằm trong file: `--phi` hoặc suy từ 20 swap kiểm được
đầu tiên (chọn trong các bậc phí chuẩn bậc giảm sai số dịch chuyển giá trung vị), rồi đánh giá trên các swap còn lại.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

from engine.pool import Pool
from engine.tick_math import MAX_TICK, MIN_TICK

Q96 = 2 ** 96
BAC_PHI = (0.0001, 0.0005, 0.0025, 0.003, 0.01)      # bậc phí PancakeSwap v3 và Uniswap v3 (0,3%)
SO_SWAP_SUY_PHI = 20
NGUONG_BUI = 1e-9      # swap làm √P đổi tương đối dưới mức này: float64 (eps 1e-16) không còn phân giải được
COT_SWAP = ["block", "tx_index", "log_index", "tx_hash", "kind", "owner", "tick_lower", "tick_upper", "liquidity",
            "amount0", "amount1", "sqrt_price_x96", "tick", "liquidity_active"]


def doc_log(thu_muc) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Đọc `swap.csv`, `su_kien.csv` trong `thu_muc`; số nguyên lớn (L, amount, √P·2^96) giữ dạng int Python
    trong cột object, sắp theo (block, log_index)."""
    d = Path(thu_muc)
    lon = ["liquidity", "amount0", "amount1", "sqrt_price_x96", "liquidity_active"]

    def doc(ten):
        x = pd.read_csv(d / ten, dtype={c: str for c in lon})
        for c in lon:
            if c in x:
                x[c] = [int(v) if isinstance(v, str) and v != "" else None for v in x[c]]
        return x.sort_values(["block", "log_index"], kind="stable").reset_index(drop=True)

    return doc("swap.csv"), doc("su_kien.csv")


def mot_swap_engine(fee: float, z_truoc: float, L: int, amount0: int, amount1: int) -> tuple[float, float]:
    """Cho engine swap một lần trên bể một vị thế toàn dải L (đơn vị L thô) từ √P = `z_truoc`; amount0/amount1 là số
    nguyên thô có dấu của log (dương = bể nhận). Trả (√P sau swap, lượng token ra, dương)."""
    p = Pool(fee, z_truoc, tick_spacing=1)
    p.mint("kiem", MIN_TICK, MAX_TICK, float(L))
    zfo = amount0 > 0
    r = p.swap("kiem", zfo, float(amount0 if zfo else amount1))
    return r.sqrt_price_after, r.amount_out


def _bien_dong_L(su_kien: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Mint/Burn có L > 0 theo thứ tự: (khóa = block·1e6+log_index, tick_lower, tick_upper, ΔL có dấu)."""
    s = su_kien[su_kien["kind"].isin(["mint", "burn"])]
    s = s[np.array([(v or 0) > 0 for v in s["liquidity"]], dtype=bool)]
    khoa = s["block"].astype("int64").to_numpy() * 1_000_000 + s["log_index"].astype("int64").to_numpy()
    dl = np.array([int(v) * (1 if k == "mint" else -1) for v, k in zip(s["liquidity"], s["kind"])], dtype=object)
    return khoa, s["tick_lower"].astype("int64").to_numpy(), s["tick_upper"].astype("int64").to_numpy(), dl, s["block"].astype("int64").to_numpy()


def chuan_bi(swap: pd.DataFrame, su_kien: pd.DataFrame, gap_max: int = 40) -> pd.DataFrame:
    """Gán cho từng swap: `tick_giua` (có biên vị thế đã biết nằm giữa tick trước và tick sau: có thể đã vượt tick dù L không
    đổi, ví dụ băng qua một vị thế mỏng), trạng thái (`ok` hoặc lý do loại), `L_pre`, √P trước và sau (float), chiều.

    Lý do loại: `dau` (swap đầu, không có giá trước), `khong_lien_ke` (swap trước cách > gap_max block: khác cửa sổ
    mẫu, có thể thiếu swap ở giữa), `khong_swap_vao` (amount0 = amount1 = 0 hoặc cùng dấu), `L_doi` (L log ≠ L_pre:
    swap vượt tick đã khởi tạo hoặc thanh khoản đổi do sự kiện không thấy), `L_khong` (L_pre ≤ 0)."""
    khoa, tl, tu, dl, _ = _bien_dong_L(su_kien)
    n = len(swap)
    a0, a1 = swap["amount0"].tolist(), swap["amount1"].tolist()
    L = swap["liquidity_active"].tolist()
    x96 = swap["sqrt_price_x96"].tolist()
    tick = swap["tick"].to_numpy()
    blk = swap["block"].to_numpy(np.int64)
    k_sw = blk * 1_000_000 + swap["log_index"].to_numpy(np.int64)
    ts = np.unique(np.concatenate([tl, tu]))        # mọi tick từng là biên vị thế trong log (chắc chắn đã khởi tạo)
    kq = []
    for i in range(n):
        r = dict(i=i, tick_giua=False, trang_thai="ok", L_pre=math.nan, z_truoc=math.nan, z_sau=x96[i] / Q96,
                 zero_for_one=a0[i] > 0, amount0=a0[i], amount1=a1[i])
        if i == 0:
            r["trang_thai"] = "dau"
        elif blk[i] - blk[i - 1] > gap_max:
            r["trang_thai"] = "khong_lien_ke"
        elif not ((a0[i] > 0 > a1[i]) or (a1[i] > 0 > a0[i])):
            r["trang_thai"] = "khong_swap_vao"
        else:
            lo, hi = np.searchsorted(khoa, k_sw[i - 1], side="right"), np.searchsorted(khoa, k_sw[i], side="left")
            Lp = L[i - 1]
            for j in range(lo, hi):
                if tl[j] <= tick[i - 1] < tu[j]:
                    Lp += dl[j]
            lo_t, hi_t = sorted((int(tick[i - 1]), int(tick[i])))
            r["tick_giua"] = bool(np.searchsorted(ts, hi_t, side="right") - np.searchsorted(ts, lo_t, side="right") > 0)
            r.update(L_pre=float(Lp), z_truoc=x96[i - 1] / Q96)
            if Lp <= 0:
                r["trang_thai"] = "L_khong"
            elif L[i] != Lp:
                r["trang_thai"] = "L_doi"
        kq.append(r)
    d = pd.DataFrame(kq)
    d["block"], d["log_index"], d["tx_hash"] = blk, swap["log_index"].to_numpy(), swap["tx_hash"].to_numpy()
    return d


def so_sanh(d: pd.DataFrame, fee: float) -> pd.DataFrame:
    """Thêm cột sai số cho các dòng `ok`: `rel_gia` = |√P_engine − √P_log| / √P_log, `rel_dich` = sai số tương đối
    của độ dịch √P (|Δ_engine − Δ_log| / |Δ_log|), `rel_ra` = sai số tương đối của lượng ra, `dau_ra` = (ra_engine −
    ra_log) / ra_log có dấu, `dich_tuong_doi` = |Δ√P_log| / √P (độ lớn cú swap). Giữ nguyên các dòng khác (cột NaN)."""
    d = d.copy()
    for c in ("rel_gia", "rel_dich", "rel_ra", "dau_ra", "dich_tuong_doi"):
        d[c] = math.nan
    for ix in d.index[d["trang_thai"] == "ok"]:
        r = d.loc[ix]
        z_e, ra_e = mot_swap_engine(fee, r.z_truoc, int(r.L_pre), r.amount0, r.amount1)
        ra_log = -(r.amount1 if r.zero_for_one else r.amount0)
        dz_log, dz_e = r.z_sau - r.z_truoc, z_e - r.z_truoc
        d.at[ix, "dich_tuong_doi"] = abs(dz_log) / r.z_sau
        d.at[ix, "rel_gia"] = abs(z_e - r.z_sau) / r.z_sau
        d.at[ix, "rel_dich"] = abs(dz_e - dz_log) / abs(dz_log) if dz_log else math.nan
        d.at[ix, "rel_ra"] = abs(ra_e - ra_log) / ra_log if ra_log else math.nan
        d.at[ix, "dau_ra"] = (ra_e - ra_log) / ra_log if ra_log else math.nan
    return d


def suy_phi(d: pd.DataFrame, so_swap: int = SO_SWAP_SUY_PHI, bac=BAC_PHI) -> tuple[float, dict]:
    """Chọn mức phí trong `bac` làm trung vị `rel_dich` nhỏ nhất trên `so_swap` swap `ok` đầu tiên. Trả (phí, {phí: sai số})."""
    dau = d[d["trang_thai"] == "ok"].head(so_swap)
    if dau.empty:
        return bac[0], {}
    diem = {}
    for f in bac:
        e = so_sanh(dau, f)["rel_dich"].dropna()
        diem[f] = float(e.median()) if len(e) else math.inf
    return min(diem, key=diem.get), diem


def kha_thi_muc2(swap: pd.DataFrame, su_kien: pd.DataFrame, gap_lay_mau: int = 1000) -> tuple[bool, str]:
    """Phát lại từ lúc tạo bể có làm được không. Cần: sự kiện đầu là Mint (bể rỗng, L = 0), không có dấu hiệu lấy mẫu
    swap (khoảng trống giữa hai swap liền nhau > `gap_lay_mau` block), và có giá khởi tạo. Log tải không chứa Initialize
    nên điều kiện cuối luôn thiếu; trả (False, lý do) liệt kê mọi điều kiện không đạt."""
    thieu = []
    ev = pd.concat([swap[["block", "log_index"]].assign(kind="swap"), su_kien[["block", "log_index", "kind"]]])
    dau = ev.sort_values(["block", "log_index"], kind="stable").iloc[0]
    if dau["kind"] != "mint":
        thieu.append(f"sự kiện đầu là {dau['kind']} (không phải mint: bể đã có thanh khoản trước đoạn log)")
    gap = swap["block"].diff().dropna()
    n_gap = int((gap > gap_lay_mau).sum())
    if n_gap:
        thieu.append(f"{n_gap} khoảng trống > {gap_lay_mau} block giữa các swap (swap bị lấy mẫu, thiếu swap)")
    thieu.append("không có sự kiện Initialize nên không biết giá khởi tạo")
    return False, "; ".join(thieu)


def tom_tat(d: pd.DataFrame) -> dict:
    """Số swap, số kiểm được, số bị loại theo lý do, sai số (trung vị, p99, lớn nhất) của `rel_gia`, `rel_dich`, `rel_ra`."""
    ok = d[d["trang_thai"] == "ok"]
    r = dict(n_swap=len(d), n_kiem=len(ok))
    for lydo, n in d["trang_thai"].value_counts().items():
        if lydo != "ok":
            r[f"loai_{lydo}"] = int(n)
    for c in ("rel_gia", "rel_dich", "rel_ra"):
        x = ok[c].dropna()
        r[f"{c}_tv"] = float(x.median()) if len(x) else math.nan
        r[f"{c}_p99"] = float(x.quantile(0.99)) if len(x) else math.nan
        r[f"{c}_max"] = float(x.max()) if len(x) else math.nan
    r["dau_ra_tv"] = float(ok["dau_ra"].median()) if len(ok) else math.nan
    lon = ok[ok["dich_tuong_doi"] >= NGUONG_BUI]       # bỏ swap "bụi": √P dịch dưới ngưỡng độ phân giải float64
    sach = ok[~ok["tick_giua"].astype(bool)]            # không có tick đã biết nằm giữa: chắc chắn trong một tick
    r["n_kiem_sach"] = len(sach)
    for c in ("rel_gia", "rel_dich", "rel_ra"):
        x = sach[c].dropna()
        r[f"{c}_sach_p99"] = float(x.quantile(0.99)) if len(x) else math.nan
        r[f"{c}_sach_max"] = float(x.max()) if len(x) else math.nan
    sach_lon = sach[sach["dich_tuong_doi"] >= NGUONG_BUI]
    r["n_bui"] = len(ok) - len(lon)
    x = sach_lon["rel_ra"].dropna()
    r["rel_ra_sach_ngoai_bui_max"] = float(x.max()) if len(x) else math.nan
    x = sach_lon["rel_dich"].dropna()
    r["rel_dich_sach_ngoai_bui_max"] = float(x.max()) if len(x) else math.nan
    for c in ("rel_dich", "rel_ra"):
        x = lon[c].dropna()
        r[f"{c}_ngoai_bui_max"] = float(x.max()) if len(x) else math.nan
        r[f"{c}_ngoai_bui_p99"] = float(x.quantile(0.99)) if len(x) else math.nan
    return r


def chay(thu_muc, nhanh: bool = False, phi: float | None = None, gap_max: int = 40, ra_dir="ket_qua/that/kiem_engine") -> dict:
    """Chạy Mức 1 (và xét Mức 2) trên một thư mục log; ghi CSV từng swap vào `ra_dir/<tên thư mục>.csv`, trả dict tóm tắt
    (gồm `phi`, `phi_suy`, `muc2`, `muc2_ly_do`)."""
    swap, su_kien = doc_log(thu_muc)
    ok2, ly_do = kha_thi_muc2(swap, su_kien)
    d = chuan_bi(swap.head(5000) if nhanh else swap, su_kien, gap_max)
    suy = phi is None
    diem = {}
    if suy:
        phi, diem = suy_phi(d)
    d = so_sanh(d, phi)
    d["phi"] = phi
    out = Path(ra_dir)
    out.mkdir(parents=True, exist_ok=True)
    cot = ["block", "log_index", "tx_hash", "trang_thai", "zero_for_one", "phi", "L_pre", "z_truoc", "z_sau",
           "rel_gia", "rel_dich", "rel_ra", "dau_ra", "dich_tuong_doi", "tick_giua"]
    d[cot].to_csv(out / (Path(thu_muc).name + ".csv"), index=False)
    r = tom_tat(d)
    r.update(thu_muc=Path(thu_muc).name, phi=phi, phi_suy=suy, muc2=ok2, muc2_ly_do=ly_do,
             diem_phi={str(k): v for k, v in diem.items()})
    return r


def _in(r: dict) -> None:
    print(f"\n== {r['thu_muc']}  (phí {r['phi']:.4%}{', suy từ 20 swap đầu' if r['phi_suy'] else ', đặt tay'})")
    if r["diem_phi"]:
        print("   sai số dịch giá trung vị theo bậc phí:", {k: f"{v:.2e}" for k, v in r["diem_phi"].items()})
    loai = {k[5:]: v for k, v in r.items() if k.startswith("loai_")}
    print(f"   swap trong log {r['n_swap']}; Mức 1 kiểm được {r['n_kiem']}; loại {loai}")
    for c, ten in (("rel_gia", "giá sau swap (√P)"), ("rel_dich", "độ dịch √P"), ("rel_ra", "lượng ra")):
        print(f"   {ten:18s} trung vị {r[c + '_tv']:.2e}  p99 {r[c + '_p99']:.2e}  lớn nhất {r[c + '_max']:.2e}")
    print(f"   ngoài {r['n_bui']} swap bụi (√P dịch < {NGUONG_BUI:g}): lượng ra p99 {r['rel_ra_ngoai_bui_p99']:.2e}, "
          f"lớn nhất {r['rel_ra_ngoai_bui_max']:.2e}; độ dịch √P lớn nhất {r['rel_dich_ngoai_bui_max']:.2e}")
    print(f"   chỉ swap không có tick biên đã biết nằm giữa ({r['n_kiem_sach']}): √P lớn nhất {r['rel_gia_sach_max']:.2e}; "
          f"ngoài bụi: độ dịch lớn nhất {r['rel_dich_sach_ngoai_bui_max']:.2e}, lượng ra lớn nhất {r['rel_ra_sach_ngoai_bui_max']:.2e}")
    print(f"   lệch dấu lượng ra (trung vị, engine − log): {r['dau_ra_tv']:+.2e}")
    print(f"   Mức 2: {'làm được' if r['muc2'] else 'KHÔNG làm được: ' + r['muc2_ly_do']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--vao", required=True, help="thư mục log (có swap.csv, su_kien.csv); với --tat_ca: thư mục chứa nhiều bể")
    ap.add_argument("--tat_ca", action="store_true", help="chạy mọi thư mục con (bỏ đuôi _nhanh), gộp tom_tat.csv vào --ra")
    ap.add_argument("--nhanh", action="store_true", help="chỉ 5.000 swap đầu")
    ap.add_argument("--phi", type=float, default=None, help="mức phí (0,0025 = 0,25%); mặc định suy từ 20 swap đầu")
    ap.add_argument("--gap_max", type=int, default=40, help="swap trước cách quá bấy nhiêu block thì coi không liền kề")
    ap.add_argument("--ra", default="ket_qua/that/kiem_engine")
    a = ap.parse_args()
    if a.tat_ca:
        kq = []
        for sub in sorted(Path(a.vao).iterdir()):
            if sub.is_dir() and not sub.name.endswith("_nhanh") and (sub / "swap.csv").exists():
                r = chay(sub, a.nhanh, a.phi, a.gap_max, a.ra)
                _in(r)
                kq.append({k: v for k, v in r.items() if k not in ("diem_phi", "muc2_ly_do")})
        pd.DataFrame(kq).to_csv(Path(a.ra) / "tom_tat.csv", index=False)
    else:
        _in(chay(a.vao, a.nhanh, a.phi, a.gap_max, a.ra))

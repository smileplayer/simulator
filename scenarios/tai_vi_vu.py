"""Tải ví thật đứng sau lệnh nạp/rút và swap đầy đủ quanh một vụ tường thanh khoản (BSC), để tái dựng vụ trong simulator.

Đầu vào: một thư mục vụ do `scenarios.tai_vu_that` tải (`ket_qua/that/vu/<pool[:10]>_<block đầu>/`, có `su_kien.csv`,
`moc.csv`, `tien_do.json`). Các vụ của bảng bài gốc nằm trong thư mục đó được tìm theo địa chỉ bể và khoảng block.

    python -m scenarios.tai_vi_vu --vao ket_qua/that/vu/0x9485ff32_53111803 --ke_hoach      # không gọi mạng
    python -m scenarios.tai_vi_vu --vao ... --nhanh                                         # 20 tx, 2.000 block swap
    python -m scenarios.tai_vi_vu --vao ...                                                  # đầy đủ
    python -m scenarios.tai_vi_vu --vao ... --chi_gan                                        # chỉ gán vai trên dữ liệu đã tải
    python -m scenarios.tai_vi_vu --tat_ca --ke_hoach                                        # bảng kế hoạch mọi vụ

Ba bước, mỗi bước ghi dần và chạy lại thì bỏ phần đã xong:
1. `vi_lenh.csv`: với mỗi tx Mint/Burn/Collect chạm khoảng giá tường trong [t_m − 1 ngày, t_b + 1 ngày] (mặc định chỉ các tx
   này; `--tat_ca_lenh` lấy mọi tx), một lần `eth_getTransactionReceipt`: `from`, `to`, và `tokenId` / thanh khoản từ log
   IncreaseLiquidity / DecreaseLiquidity / Collect của NonfungiblePositionManager (cột `loai_npm`, `liquidity`).
2. `swap_day_du.csv` (cùng cột `swap.csv`): mọi swap của bể trong cửa sổ [min(t_rut, t_b) − `--truoc`, t_b + `--sau`] (giờ → block
   theo thời gian block nội suy từ `moc.csv`). `t_rut` = block của Burn có thanh khoản lớn nhất đúng khoảng giá tường trong
   [t_m, t_b]; không có thì lấy t_b. (`moc.csv` chỉ có cặp block-giờ Unix, không đánh dấu thời điểm rút.) Nhiều vụ trong cùng thư
   mục thì gộp các cửa sổ chồng nhau.
3. `vi_swap.csv`: `from` của `--swap_lon` swap lớn nhất (|amount| của token `--token_dg`, mặc định 1 = token1) trong cửa sổ.
Rồi tự nhận token bị xả (`token_xa`, theo dòng tiền ròng quanh t_b, đối chiếu chiều dịch tick; ép bằng `--token_xa`), phân vai ví theo
hành vi (`phan_vai`: cờ ban_lon / rut_truoc_sap / con_lai_luc_sap, L ròng theo từng thời điểm, ghép theo token_id) và ghi
`<thư mục vụ>/phan_vai.csv` + `tom_tat_vu.json`. Ví = `from` của tx (EOA gửi lệnh), không phải chủ NFT; vị thế được ghép theo token_id.
`gan_vai` (bản cũ, cộng dồn lượt nạp, giả định token0 bị xả) còn giữ để tương thích nhưng `chay` không dùng nữa.
Lượng token trên chuỗi là số nguyên thô (chưa chia số chữ số thập phân). Khóa RPC lấy từ BSC_RPC_URL / BSC_RPC_KEY, không ghi vào mã.
Với `--nhanh`, kết quả ghi vào thư mục con `nhanh/` của thư mục vụ.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

from scenarios import lay_log_bsc as L
from scenarios.tai_vu_that import BANG_VU, _o, doc_bang_vu

GIAY_BLOCK_MAC_DINH = 0.75
BLOCK_MOI_GIO = 4800                   # block/giờ (0,75 s/block)
CUA_SO_RUT_DO_NHAY = (100, 1200, 4800)  # block, bảng độ nhạy của cờ rut_truoc_sap
COT_LENH = ["tx_hash", "from", "to", "token_id", "block", "loai_npm", "liquidity"]
COT_VI_SWAP = ["tx_hash", "from", "block"]
NPM_CHU_KY = {
    "tang": "IncreaseLiquidity(uint256,uint128,uint256,uint256)",
    "giam": "DecreaseLiquidity(uint256,uint128,uint256,uint256)",
    "thu": "Collect(uint256,address,uint256,uint256)",
}
NPM_TOPIC = {ten: L.chu_de(ck) for ten, ck in NPM_CHU_KY.items()}
_NPM_LOAI = {v: k for k, v in NPM_TOPIC.items()}
# NonfungiblePositionManager của PancakeSwap v3 trên BSC (cũng là `owner` trong log Mint/Burn của bể); giả định, chưa kiểm online.
NPM_MAC_DINH = frozenset({"0x46a15b0b27311cedf172ab29e4f4766fbe7f4364"})


# ---------- thời gian block ----------
def giay_moi_block(moc: pd.DataFrame) -> float:
    """Giây mỗi block trung bình từ `moc.csv` (cột block, ts); thiếu dữ liệu thì 0,75."""
    if len(moc) < 2:
        return GIAY_BLOCK_MAC_DINH
    d = moc.sort_values("block")
    db = float(d["block"].iloc[-1] - d["block"].iloc[0])
    return float(d["ts"].iloc[-1] - d["ts"].iloc[0]) / db if db > 0 else GIAY_BLOCK_MAC_DINH


def gio_ra_block(gio: float, moc: pd.DataFrame) -> int:
    """Số block tương ứng `gio` giờ (làm tròn)."""
    return int(round(gio * 3600 / giay_moi_block(moc)))


# ---------- chọn vụ, cửa sổ, tx ----------
def vu_cua_thu_muc(vao: Path, bang: pd.DataFrame | None = None) -> pd.DataFrame:
    """Các vụ của bảng bài gốc nằm trong thư mục `vao` (tên `<pool[:10]>_<block đầu>`; cùng bể và [t_m, t_b] trong khoảng đã tải)."""
    bang = doc_bang_vu(BANG_VU) if bang is None else bang
    ten = Path(vao).name.split("_")
    tien = Path(vao) / "tien_do.json"
    den = json.loads(tien.read_text()).get("su_kien", 0) if tien.exists() else 10 ** 12
    tu = int(ten[1]) if len(ten) > 1 and ten[1].isdigit() else 0
    return bang[bang.pool.str.startswith(ten[0].lower()) & (bang.t_m >= tu) & (bang.t_b <= den)].reset_index(drop=True)


def t_rut_tuong(su_kien: pd.DataFrame, v) -> int:
    """Block rút tường của vụ `v`: Burn có `liquidity` lớn nhất đúng khoảng [tick_lower, tick_upper] tường trong [t_m, t_b]; không có → t_b."""
    b = su_kien[(su_kien.kind == "burn") & (su_kien.tick_lower == v.tick_lower) & (su_kien.tick_upper == v.tick_upper)
                & (su_kien.block >= v.t_m) & (su_kien.block <= v.t_b) & (su_kien.liquidity > 0)]
    return int(b.loc[b.liquidity.idxmax(), "block"]) if len(b) else int(v.t_b)


def cua_so_swap(su_kien: pd.DataFrame, vu: pd.DataFrame, truoc: int, sau: int) -> list[tuple[int, int]]:
    """Cửa sổ block swap đầy đủ: mỗi vụ [min(t_rut, t_b) − truoc, t_b + sau] (block), gộp các cửa sổ chồng nhau, sắp tăng dần."""
    ws = sorted((max(0, min(t_rut_tuong(su_kien, v), int(v.t_b)) - truoc), int(v.t_b) + sau) for v in vu.itertuples())
    kq: list[list[int]] = []
    for a, z in ws:
        if kq and a <= kq[-1][1] + 1:
            kq[-1][1] = max(kq[-1][1], z)
        else:
            kq.append([a, z])
    return [(a, z) for a, z in kq]


def chon_tx(su_kien: pd.DataFrame, vu: pd.DataFrame, ngay_block: int, tat_ca: bool = False,
            rong_max: int | None = None) -> pd.DataFrame:
    """Các tx cần tra ví: duy nhất theo `tx_hash` (cột tx_hash, block), tăng theo block.

    Mặc định chỉ lệnh có khoảng giá chứa hoặc chạm [tick_lower, tick_upper] tường của một vụ, trong [t_m − ngay_block, t_b + ngay_block];
    `tat_ca`: mọi tx trong `su_kien`; `rong_max`: bỏ lệnh rộng hơn bấy nhiêu tick (vd. vị thế toàn dải)."""
    if tat_ca:
        d = su_kien
    else:
        mask = pd.Series(False, index=su_kien.index)
        for v in vu.itertuples():
            m = (su_kien.tick_lower <= v.tick_upper) & (su_kien.tick_upper >= v.tick_lower) \
                & (su_kien.block >= v.t_m - ngay_block) & (su_kien.block <= v.t_b + ngay_block)
            mask |= m
        d = su_kien[mask]
        if rong_max is not None:
            d = d[(d.tick_upper - d.tick_lower) <= rong_max]
    return d.groupby("tx_hash", as_index=False)["block"].min().sort_values(["block", "tx_hash"]).reset_index(drop=True)


# ---------- receipt ----------
def giai_receipt(rc: dict | None, tx_hash: str, block: int = 0, npm=NPM_MAC_DINH) -> list[dict]:
    """Từ receipt của `eth_getTransactionReceipt` lấy các dòng `COT_LENH`: một dòng mỗi log NPM (IncreaseLiquidity/Decrease/Collect).

    `liquidity` = L trong log (0 với Collect); không có log NPM thì một dòng với token_id rỗng; receipt None thì from rỗng."""
    if not rc:
        return [dict(tx_hash=tx_hash, **{"from": "", "to": ""}, token_id="", block=block, loai_npm="", liquidity="")]
    base = {"tx_hash": tx_hash, "from": rc.get("from", "").lower(), "to": (rc.get("to") or "").lower(), "block": block}
    rows = []
    for lg in rc.get("logs", []):
        t = lg.get("topics", [])
        loai = _NPM_LOAI.get(t[0]) if t else None
        if loai is None or lg.get("address", "").lower() not in npm or len(t) < 2:
            continue
        d = lg["data"][2:]
        liq = int(d[:64], 16) if loai in ("tang", "giam") and len(d) >= 64 else 0
        rows.append(dict(base, token_id=int(t[1], 16), loai_npm=loai, liquidity=liq))
    return rows or [dict(base, token_id="", loai_npm="", liquidity="")]


def _da_co(p: Path, cot: str = "tx_hash") -> set[str]:
    return set(pd.read_csv(p, usecols=[cot], dtype=str)[cot]) if p.exists() and p.stat().st_size > 0 else set()


def _da_co_lenh(ra: Path) -> set[str]:
    """Hợp các tx đã tra ở `vi_lenh.csv` và mọi `vi_lenh_p<i>.csv` (các phần chạy song song bằng `--phan`)."""
    kq: set[str] = set()
    for f in sorted(ra.glob("vi_lenh*.csv")):
        kq |= _da_co(f)
    return kq


def _doc_vi_lenh(ra: Path) -> pd.DataFrame:
    """Gộp `vi_lenh.csv` và mọi `vi_lenh_p<i>.csv` (mỗi tx chỉ nằm ở một file); thiếu thì bảng rỗng."""
    fs = [f for f in sorted(ra.glob("vi_lenh*.csv")) if f.stat().st_size > 0]
    if not fs:
        return pd.DataFrame(columns=COT_LENH)
    return pd.concat([_doc(f) for f in fs], ignore_index=True)


def chia_phan(txs: pd.DataFrame, phan: tuple[int, int] | None) -> pd.DataFrame:
    """Phần thứ i trong n của danh sách tx (các tx i, i+n, i+2n… theo thứ tự, đánh số từ 1); `phan=None` giữ nguyên."""
    if phan is None:
        return txs
    i, n = phan
    return txs.iloc[i - 1::n]


def _ghi_dong(p: Path, rows: list[dict], cot: list[str]) -> None:
    moi = not p.exists() or p.stat().st_size == 0
    with p.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cot)
        if moi:
            w.writeheader()
        w.writerows(rows)


def tai_vi_lenh(rpc: L.RPC, txs: pd.DataFrame, ra: Path, npm=NPM_MAC_DINH, gioi_han: int | None = None,
                ten: str = "vi_lenh.csv") -> int:
    """Tra receipt cho các tx chưa có trong mọi `ra/vi_lenh*.csv` (tối đa `gioi_han` tx đầu), ghi dần vào `ra/<ten>`; trả số tx mới."""
    p = ra / ten
    xong = _da_co_lenh(ra)
    dau = txs if gioi_han is None else txs.head(gioi_han)
    n = 0
    for r in dau.itertuples():
        if r.tx_hash in xong:
            continue
        rc = rpc.goi("eth_getTransactionReceipt", [r.tx_hash])
        _ghi_dong(p, giai_receipt(rc, r.tx_hash, int(r.block), npm), COT_LENH)
        n += 1
        if n % 50 == 0:
            print(f"  ví lệnh: {n} receipt mới, {rpc.so_lan} lượt gọi", flush=True)
    return n


# ---------- swap ----------
def tai_swap(rpc: L.RPC, pool: str, cua_so: list[tuple[int, int]], ra: Path, buoc: int = 5000) -> int:
    """Tải mọi swap của `pool` trong các cửa sổ `cua_so` (block) vào `ra/swap_day_du.csv`, tiến độ ở `ra/tien_do_vi.json`; trả số dòng mới."""
    f_td = ra / "tien_do_vi.json"
    td = json.loads(f_td.read_text()) if f_td.exists() else {}
    sw = td.setdefault("swap", {})
    tp = [L.TOPIC["swap_pancake"], L.TOPIC["swap_uniswap"]]
    n = 0
    for a, z in cua_so:
        khoa = f"{a}-{z}"
        for e, rows in L.tai_doan(rpc, pool, tp, sw.get(khoa, a - 1) + 1, z, buoc):
            L._ghi(ra / "swap_day_du.csv", rows)
            sw[khoa] = e
            f_td.write_text(json.dumps(td))
            n += len(rows)
    return n


def chon_swap_lon(swap: pd.DataFrame, n: int, token: int = 1) -> pd.DataFrame:
    """`n` tx có swap lớn nhất theo |amount<token>| (đơn vị thô): cột tx_hash, block, lon; tx nhiều swap lấy swap lớn nhất."""
    d = swap.assign(lon=swap[f"amount{token}"].abs())
    d = d.sort_values("lon", ascending=False).drop_duplicates("tx_hash").head(n)
    return d[["tx_hash", "block", "lon"]].reset_index(drop=True)


def tai_vi_swap(rpc: L.RPC, lon: pd.DataFrame, ra: Path) -> int:
    """Tra `from` của các tx swap lớn `lon` (chưa có trong `ra/vi_swap.csv`), ghi dần; trả số tx mới."""
    p = ra / "vi_swap.csv"
    xong = _da_co(p)
    n = 0
    for r in lon.itertuples():
        if r.tx_hash in xong:
            continue
        rc = rpc.goi("eth_getTransactionReceipt", [r.tx_hash])
        _ghi_dong(p, [dict(tx_hash=r.tx_hash, **{"from": (rc or {}).get("from", "").lower()}, block=int(r.block))], COT_VI_SWAP)
        n += 1
    return n


# ---------- gán vai và lượng xả (thuần, không mạng) ----------
def gan_vai(su_kien: pd.DataFrame, vi_lenh: pd.DataFrame, tick_lower: int, tick_upper: int, t_b: int) -> pd.DataFrame:
    """Bảng theo ví (`from` của tx) cho các lệnh Mint/Burn có khoảng giá chạm tường [tick_lower, tick_upper].

    Cột: vai ("ke_tan_cong" | "nan_nhan" | "khac"), L_nap, L_rut (L thô), block_nap_dau, block_rut_cuoi, token0_nap, token1_nap,
    token0_rut, token1_rut (số nguyên thô), L_rong_tb (nạp − rút tới t_b, chỉ lệnh chứa trọn tường). Kẻ tấn công = ví có L nạp
    lớn nhất đúng khoảng tường (không có thì lệnh chứa tường); nạn nhân = ví khác còn L_rong_tb > 0; tx chưa tra ví → ví "?"."""
    d = su_kien[su_kien.kind.isin(["mint", "burn"]) & (su_kien.tick_lower <= tick_upper) & (su_kien.tick_upper >= tick_lower)].copy()
    tu_dien = vi_lenh.drop_duplicates("tx_hash").set_index("tx_hash")["from"].astype(str).to_dict() if len(vi_lenh) else {}
    d["vi"] = d["tx_hash"].map(tu_dien).replace("", np.nan).fillna("?")
    d["chua"] = (d.tick_lower <= tick_lower) & (d.tick_upper >= tick_upper)
    d["dung"] = (d.tick_lower == tick_lower) & (d.tick_upper == tick_upper)
    cot = ["vai", "L_nap", "L_rut", "block_nap_dau", "block_rut_cuoi", "token0_nap", "token1_nap", "token0_rut", "token1_rut", "L_rong_tb"]
    if d.empty:
        return pd.DataFrame(columns=cot)
    mint, burn = d[d.kind == "mint"], d[d.kind == "burn"]
    g = lambda x, c, f="sum": x.groupby("vi")[c].agg(f)
    bang = pd.DataFrame({
        "L_nap": g(mint, "liquidity"), "L_rut": g(burn, "liquidity"),
        "block_nap_dau": g(mint, "block", "min"), "block_rut_cuoi": g(burn[burn.liquidity > 0], "block", "max"),
        "token0_nap": g(mint, "amount0"), "token1_nap": g(mint, "amount1"),
        "token0_rut": g(burn, "amount0"), "token1_rut": g(burn, "amount1"),
    })
    bang = bang.reindex(d["vi"].unique())
    for c in ("L_nap", "L_rut", "token0_nap", "token1_nap", "token0_rut", "token1_rut"):
        bang[c] = bang[c].fillna(0)
    ct = d[d.chua & (d.block <= t_b)]
    rong = ct.assign(s=np.where(ct.kind == "mint", ct.liquidity, -ct.liquidity)).groupby("vi")["s"].sum()
    bang["L_rong_tb"] = rong.reindex(bang.index).fillna(0)
    nap_tuong = d[d.dung & (d.kind == "mint") & (d.vi != "?")].groupby("vi")["liquidity"].sum()
    if nap_tuong.empty:
        nap_tuong = d[d.chua & (d.kind == "mint") & (d.vi != "?")].groupby("vi")["liquidity"].sum()
    kt = nap_tuong.idxmax() if len(nap_tuong) else None
    bang["vai"] = np.where(bang.index == kt, "ke_tan_cong",
                           np.where((bang.L_rong_tb > 0) & (bang.index != "?"), "nan_nhan", "khac"))
    bang.index.name = "vi"
    return bang[cot].sort_values(["vai", "L_nap"], ascending=[True, False])


def luong_xa(swap: pd.DataFrame, vi_swap: pd.DataFrame, ke_tan_cong, token_xa: int = 0) -> dict:
    """Lượng token bị xả mà các ví `ke_tan_cong` (tập địa chỉ) bán, từ swap đầy đủ `swap` và ví gửi `vi_swap` (cột tx_hash, from).

    `token_xa` (0 hoặc 1) là token bị xả; amount > 0 là bể nhận token = ví bán. Trả token_xa_ban, token_xa_mua, token_dg_nhan (token
    còn lại bể trả ra), n_swap (số swap khớp), phu (tỷ lệ Σ|amount_xa| của swap khớp / của mọi swap; ví chỉ tra cho swap lớn nhất nên < 1)."""
    k, d = f"amount{token_xa}", f"amount{1 - token_xa}"
    kt = {str(x).lower() for x in ke_tan_cong}
    tx = set(vi_swap.loc[vi_swap["from"].astype(str).str.lower().isin(kt), "tx_hash"]) if len(vi_swap) else set()
    s = swap[swap.tx_hash.isin(tx)]
    tong = float(swap[k].abs().sum())
    return dict(token_xa_ban=int(s.loc[s[k] > 0, k].sum()), token_xa_mua=int(-s.loc[s[k] < 0, k].sum()),
                token_dg_nhan=int(-s.loc[s[d] < 0, d].sum()), n_swap=int(len(s)),
                phu=float(s[k].abs().sum() / tong) if tong else 0.0)


# ---------- nhận token bị xả, phân vai theo hành vi (thuần, không mạng) ----------
def _i(x):
    """Số nguyên Python từ chuỗi/số; rỗng hoặc NaN → None (chuỗi đi thẳng qua int, không qua float, nên L cỡ 1e28 không bị làm tròn)."""
    if x is None or (isinstance(x, float) and math.isnan(x)) or (isinstance(x, str) and x.strip() == ""):
        return None
    return int(x) if isinstance(x, (int, np.integer, float)) else int(str(x).strip())


def chuan_hoa(df: pd.DataFrame, cot_nguyen=("liquidity", "amount0", "amount1", "liquidity_active")) -> pd.DataFrame:
    """Bản sao `df` với các cột `cot_nguyen` (nếu có) thành số nguyên Python (dtype object, không mất độ chính xác), block/tick thành số."""
    d = df.copy()
    for c in cot_nguyen:
        if c in d:
            d[c] = d[c].map(_i).astype(object)
    for c in ("block", "tx_index", "log_index", "tick", "tick_lower", "tick_upper"):
        if c in d:
            d[c] = pd.to_numeric(d[c])
    return d


def _sap_xep(d: pd.DataFrame) -> pd.DataFrame:
    cot = [c for c in ("block", "tx_index", "log_index") if c in d]
    return d.sort_values(cot, kind="stable") if cot else d


def _gia_token1_tren_token0(dong) -> float:
    sq = dong["sqrt_price_x96"] if "sqrt_price_x96" in dong.index else None
    if sq is not None and not pd.isna(sq) and float(sq) > 0:
        return (float(sq) / 2 ** 96) ** 2
    return 1.0001 ** float(dong["tick"])


def chi_tiet_xa(swap: pd.DataFrame, t_b: int, cua_so: int) -> dict:
    """Dòng tiền ròng của bể trong [t_b − cua_so, t_b + cua_so] (block) và token bị xả; ném ValueError nếu không xác định hoặc mâu thuẫn.

    Trả dict: token_xa (0|1), net0, net1 (Σ amount thô, > 0 là đi vào bể), gia (token1 trên token0, thô), tick_truoc (swap cuối trước
    cửa sổ), tick_sau (swap cuối trong cửa sổ). Token bị xả = token có giá trị ròng đi vào (quy về token1 theo `gia`) lớn hơn và dương;
    chiều tick dịch phải khớp (tick tăng ⇔ token1 bị xả); lệch nhau thì ValueError."""
    sw = _sap_xep(swap)
    trong = sw[(sw.block >= t_b - cua_so) & (sw.block <= t_b + cua_so)]
    if trong.empty:
        raise ValueError(f"không có swap nào trong ±{cua_so} block quanh t_b={t_b}")
    truoc = sw[sw.block < t_b - cua_so]
    ref = truoc.iloc[-1] if len(truoc) else trong.iloc[0]
    gia = _gia_token1_tren_token0(ref)
    net0, net1 = int(trong.amount0.sum()), int(trong.amount1.sum())
    v0, v1 = net0 * gia, float(net1)
    if max(v0, v1) <= 0:
        raise ValueError(f"không token nào có lượng ròng đi vào bể trong cửa sổ (net0={net0}, net1={net1})")
    tk = 0 if v0 > v1 else 1
    tick_truoc, tick_sau = int(ref["tick"]), int(trong.iloc[-1]["tick"])
    dich = tick_sau - tick_truoc
    if dich != 0 and (1 if dich > 0 else 0) != tk:
        raise ValueError(f"mâu thuẫn: dòng tiền ròng chỉ token{tk} bị xả nhưng tick dịch {tick_truoc} → {tick_sau} "
                         f"(tick {'tăng' if dich > 0 else 'giảm'} nghĩa là token{1 if dich > 0 else 0} bị xả); dùng --token_xa để ép")
    return dict(token_xa=tk, net0=net0, net1=net1, gia=gia, tick_truoc=tick_truoc, tick_sau=tick_sau)


def token_xa(swap: pd.DataFrame, t_b: int, cua_so: int) -> int:
    """Token bị xả (0 hoặc 1) quanh t_b: token có lượng ròng đi vào bể lớn hơn trong ±`cua_so` block, đối chiếu chiều tick; mâu thuẫn → ValueError."""
    return chi_tiet_xa(swap, t_b, cua_so)["token_xa"]


def su_kien_tuong(su_kien: pd.DataFrame, vi_lenh: pd.DataFrame, tick_lower: int, tick_upper: int, che_do: str = "chua") -> pd.DataFrame:
    """Các sự kiện mint/burn có L > 0 tại tường, đã gắn ví và vị thế (L thô, số nguyên Python).

    `che_do`: "chua" = vị thế chứa trọn [tick_lower, tick_upper] (đang hoạt động ở tường); "dung" = đúng khoảng tường. Mỗi sự kiện ghép
    với log IncreaseLiquidity/DecreaseLiquidity cùng tx và cùng L trong `vi_lenh` để lấy token_id và ví gửi (`vi`); không ghép được thì
    `vi` = from của tx (token_id rỗng) hoặc "?" nếu tx chưa tra. Vị thế = token_id (hoặc ví|khoảng giá), chủ (`chu`) = ví gửi lệnh rút đầu
    tiên của vị thế (người rút phải là chủ NFT lúc đó, có thể khác ví đã nạp), chưa rút thì ví nạp đầu tiên, nên nạp–rút–nạp nhiều lần một vị thế chỉ là một vị thế. Cột: block, kind, L, vi, chu, khoa, amount0, amount1, tx_hash."""
    d = _sap_xep(su_kien[su_kien.kind.isin(["mint", "burn"])])
    if che_do == "dung":
        d = d[(d.tick_lower == tick_lower) & (d.tick_upper == tick_upper)]
    else:
        d = d[(d.tick_lower <= tick_lower) & (d.tick_upper >= tick_upper)]
    tu_from: dict = {}
    pool: dict = {}
    for r in vi_lenh.rename(columns={"from": "vi_gui"}).itertuples(index=False):
        if isinstance(r.vi_gui, str) and r.vi_gui:
            tu_from.setdefault(r.tx_hash, r.vi_gui.lower())
        liq, tid = _i(getattr(r, "liquidity", None)), _i(getattr(r, "token_id", None))
        if getattr(r, "loai_npm", None) in ("tang", "giam") and liq and tid is not None:
            pool.setdefault((r.tx_hash, r.loai_npm), []).append([liq, tid, False])
    rows, chu_cua = [], {}
    for r in d.itertuples(index=False):
        L = _i(r.liquidity) or 0
        if L <= 0:
            continue
        vi, tid = tu_from.get(r.tx_hash, "?"), None
        for c in pool.get((r.tx_hash, "tang" if r.kind == "mint" else "giam"), []):
            if not c[2] and c[0] == L:
                c[2], tid = True, c[1]
                break
        khoa = f"nft{tid}" if tid is not None else f"{vi}|{r.tick_lower}|{r.tick_upper}"
        if khoa not in chu_cua or (r.kind == "burn" and chu_cua[khoa][1] != "burn" and vi != "?"):
            chu_cua[khoa] = (vi, r.kind)
        rows.append(dict(block=int(r.block), kind=r.kind, L=L, vi=vi, khoa=khoa, amount0=_i(r.amount0) or 0, amount1=_i(r.amount1) or 0,
                         tx_hash=r.tx_hash))
    ev = pd.DataFrame(rows, columns=["block", "kind", "L", "vi", "khoa", "amount0", "amount1", "tx_hash"])
    ev["chu"] = ev["khoa"].map(lambda k: chu_cua[k][0])
    return ev


def l_rong_theo_vi(ev: pd.DataFrame, t: int) -> dict:
    """L ròng (mint − burn, L thô) của từng chủ vị thế tại tường tính tới hết block `t`; chỉ giữ ví có L ròng ≠ 0."""
    kq: dict = {}
    for r in ev[ev.block <= t].itertuples(index=False):
        kq[r.chu] = kq.get(r.chu, 0) + (r.L if r.kind == "mint" else -r.L)
    return {k: v for k, v in kq.items() if v != 0}


def rut_truoc_sap(ev: pd.DataFrame, t_b: int, cua_so_rut: int) -> pd.DataFrame:
    """Ví có L ròng tại tường giảm trong `cua_so_rut` block trước t_b (từ t_b − cua_so_rut tới t_b), kèm ít nhất một burn trong cửa sổ.

    Cột theo ví (chỉ ví có L_rut > 0): L_truoc (L ròng đầu cửa sổ), L_tb (L ròng tại t_b), L_rut = L_truoc − L_tb (L thô),
    block_rut_dau, block_rut_cuoi (các burn L > 0 trong cửa sổ)."""
    t0 = t_b - cua_so_rut
    truoc, tai = l_rong_theo_vi(ev, t0), l_rong_theo_vi(ev, t_b)
    bu = ev[(ev.kind == "burn") & (ev.block > t0) & (ev.block <= t_b)].groupby("chu")["block"].agg(["min", "max"])
    rows = []
    for vi in set(truoc) | set(tai):
        lt, lb = truoc.get(vi, 0), tai.get(vi, 0)
        if lt - lb > 0 and vi in bu.index:
            rows.append(dict(vi=vi, L_truoc=lt, L_tb=lb, L_rut=lt - lb, block_rut_dau=int(bu.loc[vi, "min"]), block_rut_cuoi=int(bu.loc[vi, "max"])))
    return pd.DataFrame(rows, columns=["vi", "L_truoc", "L_tb", "L_rut", "block_rut_dau", "block_rut_cuoi"]).set_index("vi")


def ban_theo_vi(swap: pd.DataFrame, vi_swap: pd.DataFrame, token_xa: int, t_b: int, cua_so: int) -> tuple[pd.DataFrame, dict]:
    """Lượng token bị xả bán theo ví trong [t_b − cua_so, t_b + cua_so] (block); amount_xa > 0 là bể nhận = ví bán (cộng theo swap, số thô).

    Trả (bảng theo ví: ban_token_xa, token_dg_nhan, n_swap_ban, ty_trong_ban; thông tin chung: tong_ban, token_dg_ra, do_phu). `tong_ban` =
    Σ amount_xa > 0 của mọi swap trong cửa sổ, `token_dg_ra` = Σ −amount_dg của các swap bể trả token định giá, `do_phu` = tỷ lệ tong_ban
    đã biết ví (ví chỉ tra cho swap lớn nhất). `ty_trong_ban` = ban_token_xa / tong_ban."""
    k, dg = f"amount{token_xa}", f"amount{1 - token_xa}"
    w = swap[(swap.block >= t_b - cua_so) & (swap.block <= t_b + cua_so)]
    tu = {r.tx_hash: str(r.vi_gui).lower() for r in vi_swap.rename(columns={"from": "vi_gui"}).itertuples(index=False)
          if isinstance(r.vi_gui, str) and r.vi_gui}
    ban = w[w[k] > 0]
    tong_ban = int(ban[k].sum())
    cong: dict = {}
    for r in ban.itertuples(index=False):
        vi = tu.get(r.tx_hash)
        if vi is None:
            continue
        a, b = int(getattr(r, k)), int(getattr(r, dg))
        c = cong.setdefault(vi, [0, 0, 0])
        c[0] += a
        c[1] += -b if b < 0 else 0
        c[2] += 1
    bang = pd.DataFrame([dict(vi=v, ban_token_xa=c[0], token_dg_nhan=c[1], n_swap_ban=c[2], ty_trong_ban=(c[0] / tong_ban if tong_ban else 0.0))
                         for v, c in cong.items()], columns=["vi", "ban_token_xa", "token_dg_nhan", "n_swap_ban", "ty_trong_ban"]).set_index("vi")
    biet = sum(c[0] for c in cong.values())
    return bang, dict(tong_ban=tong_ban, token_dg_ra=int(-w.loc[w[dg] < 0, dg].sum()), do_phu=(biet / tong_ban if tong_ban else 0.0))


def phan_vai(su_kien: pd.DataFrame, vi_lenh: pd.DataFrame, swap: pd.DataFrame, vi_swap: pd.DataFrame, tick_lower: int, tick_upper: int,
             t_m: int, t_b: int, token_xa: int, cua_so_rut: int = 1200, cua_so_sap: int = 300, nguong_ban: float = 0.01,
             che_do: str = "chua") -> tuple[pd.DataFrame, dict]:
    """Phân vai ví theo hành vi quanh t_b, bằng L ròng tại từng thời điểm (không cộng dồn lượt nạp); KHÔNG kết luận ví nào cùng chủ.

    Cờ boolean mỗi ví: `ban_lon` (bán token bị xả trong ±cua_so_sap block quanh t_b với tỷ trọng ≥ `nguong_ban` tổng lượng bán của cửa sổ),
    `rut_truoc_sap` (L ròng tại tường giảm trong `cua_so_rut` block trước t_b), `con_lai_luc_sap` (L ròng tại tường > 0 đúng t_b). Cột
    `nhom`: "tan_cong" nếu ban_lon hoặc rut_truoc_sap; "nan_nhan_ung_vien" nếu chỉ con_lai_luc_sap; còn lại "khac". Lưu ý: ví 0xa9d837c8…
    được bài gốc gọi là chủ tường chính nhưng theo quy tắc này còn L lúc sập nên rơi vào nan_nhan_ung_vien (trừ khi cũng bán lớn/rút trước).
    Trả (bảng theo ví, ngữ cảnh: ev = sự kiện tường, ban_chung, tham số). Đơn vị: L, amount là số nguyên thô; block."""
    ev = su_kien_tuong(su_kien, vi_lenh, tick_lower, tick_upper, che_do)
    rut = rut_truoc_sap(ev, t_b, cua_so_rut)
    ban, ban_chung = ban_theo_vi(swap, vi_swap, token_xa, t_b, cua_so_sap)
    l_tb, l_t0 = l_rong_theo_vi(ev, t_b), l_rong_theo_vi(ev, t_b - cua_so_rut)
    sau = ev[(ev.kind == "burn") & (ev.block > t_b)]
    rows = []
    for vi in sorted(set(ev.chu.dropna()) | set(ban.index)):
        r = dict(vi=vi)
        r["ban_lon"] = bool(vi in ban.index and ban.loc[vi, "ty_trong_ban"] >= nguong_ban)
        r["rut_truoc_sap"] = bool(vi in rut.index)
        r["con_lai_luc_sap"] = bool(l_tb.get(vi, 0) > 0)
        r["nhom"] = "tan_cong" if (r["ban_lon"] or r["rut_truoc_sap"]) else ("nan_nhan_ung_vien" if r["con_lai_luc_sap"] else "khac")
        r["L_truoc"], r["L_tb"] = int(l_t0.get(vi, 0)), int(l_tb.get(vi, 0))
        r["L_rut"] = int(rut.loc[vi, "L_rut"]) if vi in rut.index else 0
        r["block_rut_dau"] = int(rut.loc[vi, "block_rut_dau"]) if vi in rut.index else None
        r["block_rut_cuoi"] = int(rut.loc[vi, "block_rut_cuoi"]) if vi in rut.index else None
        for c in ("ban_token_xa", "token_dg_nhan", "n_swap_ban", "ty_trong_ban"):
            r[c] = ban.loc[vi, c] if vi in ban.index else 0
        s = sau[sau.chu == vi] if r["con_lai_luc_sap"] else sau.iloc[0:0]
        r["block_rut_sau"] = int(s.block.min()) if len(s) else None
        r["token0_nhan_sau"], r["token1_nhan_sau"] = int(s.amount0.sum()), int(s.amount1.sum())
        rows.append(r)
    cot = ["vi", "nhom", "ban_lon", "rut_truoc_sap", "con_lai_luc_sap", "L_truoc", "L_tb", "L_rut", "block_rut_dau", "block_rut_cuoi",
           "ban_token_xa", "ty_trong_ban", "token_dg_nhan", "n_swap_ban", "block_rut_sau", "token0_nhan_sau", "token1_nhan_sau"]
    bang = pd.DataFrame(rows, columns=cot).set_index("vi")
    for c in ("block_rut_dau", "block_rut_cuoi", "block_rut_sau"):
        bang[c] = bang[c].astype("Int64")
    bang["_o"] = bang.nhom.map({"tan_cong": 0, "nan_nhan_ung_vien": 1, "khac": 2})
    bang = bang.sort_values(["_o", "L_rut", "ban_token_xa"], ascending=[True, False, False], kind="stable").drop(columns="_o")
    return bang, dict(ev=ev, ban_chung=ban_chung, che_do=che_do, t_m=t_m, t_b=t_b, token_xa=token_xa, cua_so_rut=cua_so_rut, cua_so_sap=cua_so_sap)


def do_nhay_cua_so_rut(ev: pd.DataFrame, swap: pd.DataFrame, t_b: int, cac_cua_so=CUA_SO_RUT_DO_NHAY) -> pd.DataFrame:
    """Độ nhạy của cờ rut_truoc_sap theo độ dài cửa sổ (block): so_vi, L_rut (thô), L hoạt động đầu cửa sổ, tỷ lệ, block đầu/cuối."""
    sw = _sap_xep(swap)
    kq = []
    for w in cac_cua_so:
        r = rut_truoc_sap(ev, t_b, w)
        truoc = sw[sw.block <= t_b - w]
        lhd = int(truoc.iloc[-1]["liquidity_active"]) if len(truoc) else 0
        tong = int(r.L_rut.sum()) if len(r) else 0
        kq.append(dict(cua_so_rut=w, so_vi=len(r), L_rut=tong, L_hoat_dong=lhd, ty_le=(tong / lhd if lhd else float("nan")),
                       block_dau=int(r.block_rut_dau.min()) if len(r) else None, block_cuoi=int(r.block_rut_cuoi.max()) if len(r) else None))
    return pd.DataFrame(kq)


def tom_tat_vu(bang: pd.DataFrame, ctx: dict, swap: pd.DataFrame, chi_tiet: dict | None = None) -> dict:
    """Bảng tóm tắt một vụ (dict, số thô trừ khi nói khác): token bị xả, L hoạt động và L tại tường trước sập, L rút trước sập, lượng bán,
    tick trước/tại t_b/sau 2 giờ, ví còn lại lúc sập, thời gian từ t_m tới lần rút đầu của nhóm tấn công (giờ, 4.800 block/giờ)."""
    ev, tb, w = ctx["ev"], ctx["t_b"], ctx["cua_so_rut"]
    sw = _sap_xep(swap)
    cuoi = lambda m: sw[m].iloc[-1] if m.any() else None
    truoc, tai, sau = cuoi(sw.block <= tb - w), cuoi(sw.block <= tb), cuoi(sw.block <= tb + 2 * BLOCK_MOI_GIO)
    lhd = int(truoc["liquidity_active"]) if truoc is not None else None
    d0 = {k: v for k, v in l_rong_theo_vi(ev, tb - w).items() if v > 0}
    tong0 = sum(d0.values())
    rut, bl, cl = bang[bang.rut_truoc_sap], bang[bang.ban_lon], bang[bang.con_lai_luc_sap]
    lr = int(rut.L_rut.sum())
    return dict(
        token_bi_xa=ctx["token_xa"], dong_tien_rong_cua_so=chi_tiet, che_do_tuong=ctx["che_do"], cua_so_rut_block=w, cua_so_sap_block=ctx["cua_so_sap"],
        L_hoat_dong_truoc_sap=lhd, L_tai_tuong_truoc_sap=tong0, so_vi_gop_tuong_truoc_sap=len(d0),
        ty_trong_vi_lon_nhat_tai_tuong=(max(d0.values()) / tong0 if tong0 else None), vi_lon_nhat_tai_tuong=(max(d0, key=d0.get) if d0 else None),
        L_rut_truoc_sap=lr, ty_le_L_rut_tren_L_hoat_dong=(lr / lhd if lhd else None), so_vi_rut_truoc_sap=int(len(rut)),
        block_rut_dau=(int(rut.block_rut_dau.min()) if len(rut) else None), block_rut_cuoi=(int(rut.block_rut_cuoi.max()) if len(rut) else None),
        tong_ban_token_xa_trong_cua_so=ctx["ban_chung"]["tong_ban"], token_dg_rut_ra_trong_cua_so=ctx["ban_chung"]["token_dg_ra"],
        so_vi_ban_lon=int(len(bl)), ty_trong_ban_vi_lon_nhat=(float(bl.ty_trong_ban.max()) if len(bl) else None),
        ban_cua_cac_vi_ban_lon=int(bl.ban_token_xa.sum()) if len(bl) else 0, do_phu_vi_swap=ctx["ban_chung"]["do_phu"],
        tick_truoc_sap=(int(truoc["tick"]) if truoc is not None else None), tick_tai_t_b=(int(tai["tick"]) if tai is not None else None),
        tick_sau_2_gio=(int(sau["tick"]) if sau is not None else None),
        so_vi_con_lai_luc_sap=int(len(cl)), L_con_lai_luc_sap=int(cl.L_tb.sum()) if len(cl) else 0,
        gio_tu_t_m_den_lan_rut_dau=((int(rut.block_rut_dau.min()) - ctx["t_m"]) / BLOCK_MOI_GIO if len(rut) else None), t_m=ctx["t_m"], t_b=tb)


def doc_dia_chi_bai_goc(path: Path | str = BANG_VU) -> pd.DataFrame:
    """Địa chỉ trong bảng bài gốc (chữ thường): pool, t_m, t_b, chu_tuong (main wall provider), nan_nhan_1..3 (top victim)."""
    rows = []
    for dong in Path(path).read_text(encoding="utf-8").splitlines():
        if dong.startswith("| `0x"):
            c = [_o(x) for x in dong.strip().strip("|").split("|")]
            rows.append(dict(pool=c[0].lower(), t_m=int(c[3]), t_b=int(c[5]), chu_tuong=c[8].lower(),
                             nan_nhan_1=c[9].lower(), nan_nhan_2=c[11].lower(), nan_nhan_3=c[13].lower()))
    return pd.DataFrame(rows, columns=["pool", "t_m", "t_b", "chu_tuong", "nan_nhan_1", "nan_nhan_2", "nan_nhan_3"])


def so_sanh_bai_goc(bang: pd.DataFrame, dong) -> list[str]:
    """Các dòng so sánh bảng phân vai với chủ tường chính và top-3 nạn nhân của bài gốc (`dong` = một dòng của `doc_dia_chi_bai_goc`)."""
    out = []
    for ten, a in (("chủ tường chính", dong.chu_tuong), ("nạn nhân top1", dong.nan_nhan_1),
                   ("nạn nhân top2", dong.nan_nhan_2), ("nạn nhân top3", dong.nan_nhan_3)):
        if a in bang.index:
            r = bang.loc[a]
            out.append(f"  bài gốc {ten} {a[:10]}…: nhóm={r.nhom}, ban_lon={r.ban_lon}, rut_truoc_sap={r.rut_truoc_sap}, "
                       f"con_lai_luc_sap={r.con_lai_luc_sap}, L_tb={r.L_tb:.3e}, L_rut={r.L_rut:.3e}, bán={float(r.ban_token_xa):.3e}, block rút sau={r.block_rut_sau}")
        else:
            out.append(f"  bài gốc {ten} {a[:10]}…: không có trong bảng phân vai (không có lệnh tại tường / chưa tra ví)")
    return out


# ---------- kế hoạch và chạy ----------
def ke_hoach(vao: Path, truoc_gio: float = 2.0, sau_gio: float = 2.0, swap_lon: int = 200, buoc: int = 5000,
             tat_ca_lenh: bool = False, rong_max: int | None = None, nhanh: bool = False, bang: pd.DataFrame | None = None,
             phan: tuple[int, int] | None = None) -> dict:
    """Kế hoạch một thư mục vụ, không gọi mạng: số vụ, tx cần tra (tổng, còn lại sau khi trừ `vi_lenh.csv` đã có), cửa sổ swap,
    số lượt getLogs swap (ước, chưa tính lần chia đôi khi node từ chối), receipt swap (≤ `swap_lon`), tổng lượt gọi."""
    vao = Path(vao)
    su, moc = pd.read_csv(vao / "su_kien.csv"), pd.read_csv(vao / "moc.csv")
    vu = vu_cua_thu_muc(vao, bang)
    ra = vao / "nhanh" if nhanh else vao
    ngay = gio_ra_block(24, moc)
    txs = chia_phan(chon_tx(su, vu, ngay, tat_ca_lenh, rong_max), phan)
    if nhanh:
        txs = txs.head(20)
    ws = cua_so_swap(su, vu, gio_ra_block(truoc_gio, moc), gio_ra_block(sau_gio, moc))
    if nhanh and ws:
        ws = [(ws[0][0], ws[0][0] + 1999)]
    n_ws = sum(math.ceil((z - a + 1) / buoc) for a, z in ws)
    con = len(txs.loc[~txs.tx_hash.isin(_da_co_lenh(ra))])
    n_rc_swap = min(swap_lon, 200 if nhanh else swap_lon)
    if phan is not None and phan[0] != 1:                 # bước 2, 3 (swap đầy đủ, ví swap) chỉ do phần 1 làm
        n_ws = n_rc_swap = 0
    return dict(thu_muc=vao.name, n_vu=len(vu), tx_lenh=len(txs), tx_lenh_con=con, cua_so=ws,
               block_swap=sum(z - a + 1 for a, z in ws), getlogs_swap=n_ws, receipt_swap=n_rc_swap,
               tong=con + n_ws + n_rc_swap)


def _doc(p: Path) -> pd.DataFrame:
    """Đọc CSV mọi cột là chuỗi (giữ số nguyên lớn nguyên vẹn)."""
    return pd.read_csv(p, dtype=str)


def _py(x):
    """Đổi numpy sang kiểu JSON được (đệ quy trong dict)."""
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.floating):
        return float(x)
    if isinstance(x, dict):
        return {k: _py(v) for k, v in x.items()}
    return x


def _chon_token(sw: pd.DataFrame, t_b: int, cua_so_sap: int, ep: int | None) -> tuple[int, dict | None]:
    """Token bị xả của một vụ: `ep` nếu có (vẫn thử tự nhận để cảnh báo khi lệch), không thì tự nhận; không xác định được → ValueError."""
    try:
        ct = chi_tiet_xa(sw, t_b, cua_so_sap)
    except ValueError as e:
        if ep is None:
            raise
        print(f"  (cảnh báo: tự nhận token bị xả không được: {e}; dùng --token_xa {ep})")
        return ep, None
    if ep is not None and ep != ct["token_xa"]:
        print(f"  (cảnh báo: ép token{ep} bị xả nhưng dòng tiền chỉ token{ct['token_xa']})")
    return (ep if ep is not None else ct["token_xa"]), ct


def chay(vao: Path, rpc: L.RPC, truoc_gio: float, sau_gio: float, swap_lon: int, buoc: int, tat_ca_lenh: bool,
         rong_max: int | None, nhanh: bool, token_dg: int | None, chi_gan: bool, token_xa_ep: int | None = None,
         cua_so_rut: int = 1200, cua_so_sap: int = 300, nguong_ban: float = 0.01, che_do: str = "chua",
         chu_so: int = 18, phan: tuple[int, int] | None = None) -> pd.DataFrame | None:
    """Chạy ba bước tải (trừ khi `chi_gan`) rồi, với từng vụ trong thư mục, nhận token bị xả, phân vai ví theo hành vi, in bảng và ghi
    `phan_vai.csv` + `tom_tat_vu.json` (thêm hậu tố `_<vu_id>` nếu thư mục có nhiều vụ); trả bảng vai của vụ cuối.

    `token_dg`: token dùng xếp swap lớn ở bước 3 (None = token bị xả tự nhận); `token_xa_ep`: ép token bị xả; `chu_so`: số chữ số thập phân
    chỉ dùng khi in (tệp ghi số thô).

    `phan=(i, n)`: chỉ tra receipt phần i trong n của các tx lệnh, ghi vào `vi_lenh_p<i>.csv` (để n khóa RPC chạy song song); phần 1
    làm thêm bước 2, 3. Chỉ chạy phần xong thì không gán vai; gán vai chạy sau cùng bằng `--chi_gan` khi đã đủ các phần."""
    vao = Path(vao)
    ra = vao / "nhanh" if nhanh else vao
    ra.mkdir(parents=True, exist_ok=True)
    su, moc = chuan_hoa(_doc(vao / "su_kien.csv")), pd.read_csv(vao / "moc.csv")
    vu = vu_cua_thu_muc(vao)
    if vu.empty:
        raise SystemExit(f"Không vụ nào của bảng bài gốc nằm trong {vao}")
    pool = vu.pool.iloc[0]
    f_sw = ra / "swap_day_du.csv"
    if not chi_gan:
        txs = chia_phan(chon_tx(su, vu, gio_ra_block(24, moc), tat_ca_lenh, rong_max), phan)
        if nhanh:
            txs = txs.head(20)
        print(f"Bước 1: {len(txs)} tx lệnh nạp/rút" + (f" (phần {phan[0]}/{phan[1]})" if phan else ""))
        tai_vi_lenh(rpc, txs, ra, ten=f"vi_lenh_p{phan[0]}.csv" if phan else "vi_lenh.csv")
        if phan and phan[0] != 1:
            print(f"Xong phần {phan[0]}/{phan[1]}, {rpc.so_lan} lượt gọi → {ra}. Khi đủ các phần, chạy lại với --chi_gan để gán vai.")
            return None
        ws = cua_so_swap(su, vu, gio_ra_block(truoc_gio, moc), gio_ra_block(sau_gio, moc))
        if nhanh and ws:
            ws = [(ws[0][0], ws[0][0] + 1999)]
        print(f"Bước 2: swap đầy đủ trong {len(ws)} cửa sổ, {sum(z - a + 1 for a, z in ws):,} block")
        tai_swap(rpc, pool, ws, ra, buoc)
        if f_sw.exists():
            sw0 = chuan_hoa(_doc(f_sw))
            toks = [token_dg] if token_dg is not None else []
            if token_dg is None:
                for v in vu.itertuples():
                    try:
                        toks.append(_chon_token(sw0, int(v.t_b), cua_so_sap, token_xa_ep)[0])
                    except ValueError as e:
                        print(f"  vụ {v.vu_id}: chưa xác định token bị xả ({e}); xếp swap lớn theo token1")
                        toks.append(1)
            lon = pd.concat([chon_swap_lon(sw0, swap_lon, t) for t in sorted(set(toks))]).drop_duplicates("tx_hash")
            print(f"Bước 3: tra ví cho {len(lon)} swap lớn nhất (token xếp hạng {sorted(set(toks))})")
            tai_vi_swap(rpc, lon, ra)
        print(f"Xong, {rpc.so_lan} lượt gọi → {ra}")
        if phan:
            print(f"Xong phần {phan[0]}/{phan[1]}. Khi đủ các phần, chạy lại với --chi_gan để gán vai.")
            return None
    vl = _doc_vi_lenh(ra)
    sw = chuan_hoa(_doc(f_sw)) if f_sw.exists() else pd.DataFrame(columns=L.COT)
    vs = _doc(ra / "vi_swap.csv") if (ra / "vi_swap.csv").exists() else pd.DataFrame(columns=COT_VI_SWAP)
    dc = doc_dia_chi_bai_goc(BANG_VU)
    bang = None
    h = 10 ** chu_so
    for v in vu.itertuples():
        print(f"\n== {v.vu_id}: tường [{v.tick_lower},{v.tick_upper}], t_m={v.t_m}, t_b={v.t_b}, nạn nhân theo bài gốc {v.n_victim}")
        if sw.empty:
            print("(chưa có swap đầy đủ)")
            continue
        try:
            tk, ct = _chon_token(sw, int(v.t_b), cua_so_sap, token_xa_ep)
        except ValueError as e:
            print(f"KHÔNG XÁC ĐỊNH ĐƯỢC token bị xả: {e}\n  (thử --token_xa 0|1 để ép)")
            continue
        if ct:
            print(f"token bị xả: token{tk} (ròng vào bể trong ±{cua_so_sap} block: token0 {ct['net0'] / h:+,.1f}, token1 {ct['net1'] / h:+,.1f}; "
                  f"tick {ct['tick_truoc']} → {ct['tick_sau']})")
        bang, ctx = phan_vai(su, vl, sw, vs, int(v.tick_lower), int(v.tick_upper), int(v.t_m), int(v.t_b), tk, cua_so_rut, cua_so_sap,
                             nguong_ban, che_do)
        tt = tom_tat_vu(bang, ctx, sw, ct)
        hau = "" if len(vu) == 1 else f"_{v.vu_id}"
        bang.to_csv(ra / f"phan_vai{hau}.csv")
        (ra / f"tom_tat_vu{hau}.json").write_text(json.dumps(_py(tt), ensure_ascii=False, indent=1), encoding="utf-8")
        hien = bang[bang.nhom != "khac"].copy()
        for c in ("L_truoc", "L_tb", "L_rut"):
            hien[c] = hien[c].map(lambda x: f"{float(x):.3e}")
        for c in ("token0_nhan_sau", "token1_nhan_sau", "ban_token_xa", "token_dg_nhan"):
            hien[c] = hien[c].map(lambda x: f"{float(x) / h:,.2f}")
        hien["ty_trong_ban"] = hien["ty_trong_ban"].map(lambda x: f"{float(x):.1%}")
        hien.index = [i[:12] + "…" for i in hien.index]
        print(hien.drop(columns=["L_truoc"]).to_string() if len(hien) else "(không ví nào thuộc nhóm tấn công / nạn nhân ứng viên)")
        print(f"(L: số thô; token: chia 1e{chu_so}; chế độ tường '{che_do}'; còn {int((bang.nhom == 'khac').sum())} ví nhóm khac trong "
              f"{ra / f'phan_vai{hau}.csv'})")
        gon = {k: (round(x / h, 2) if k.startswith(("tong_ban", "token_dg_rut", "ban_cua")) else x) for k, x in _py(tt).items()
               if k != "dong_tien_rong_cua_so"}
        print("tóm tắt:", json.dumps(gon, ensure_ascii=False))
        print("độ nhạy cửa sổ rút (block):")
        dn = do_nhay_cua_so_rut(ctx["ev"], sw, int(v.t_b))
        print(dn.to_string(index=False, formatters={"L_rut": "{:.3e}".format, "L_hoat_dong": "{:.3e}".format, "ty_le": "{:.1%}".format}))
        m = dc[(dc.pool == v.pool) & (dc.t_m == v.t_m) & (dc.t_b == v.t_b)]
        if len(m):
            print("so với bài gốc:")
            print("\n".join(so_sanh_bai_goc(bang, m.iloc[0])))
    return bang


def bao_ve_han_muc(rpc: L.RPC) -> L.RPC:
    """Bọc `rpc.goi`: lỗi hết hạn mức / khóa hỏng thành `HetHanMuc` (dừng gọn); 429 thì chờ lâu dần rồi thử lại, kéo dài mới dừng."""
    goc = rpc.goi

    def goi(method, params):
        nghen = 0
        while True:
            try:
                return goc(method, params)
            except RuntimeError as e:
                if isinstance(e, L.HetHanMuc):
                    raise
                s = str(e).lower()
                if any(k in s for k in L._LOI_HAN_MUC):
                    raise L.HetHanMuc(str(e)) from e
                if any(k in s for k in L._LOI_TOC_DO):
                    nghen += 1
                    if nghen > L.SO_LAN_CHO_TOC_DO:
                        raise L.HetHanMuc(f"{e} (bị giới hạn liên tục)") from e
                    print(f"  bị giới hạn tốc độ (lần {nghen}/{L.SO_LAN_CHO_TOC_DO}), chờ {L.GIAY_CHO_TOC_DO * nghen}s", flush=True)
                    time.sleep(L.GIAY_CHO_TOC_DO * nghen)
                    continue
                raise
    rpc.goi = goi
    return rpc


def _thu_muc_tat_ca(goc: Path = Path("ket_qua/that/vu")) -> list[Path]:
    return sorted(p for p in goc.iterdir() if p.is_dir() and not p.name.endswith("_nhanh") and (p / "su_kien.csv").exists())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--vao", nargs="+", default=[], help="thư mục vụ (ket_qua/that/vu/<pool[:10]>_<block>)")
    ap.add_argument("--tat_ca", action="store_true", help="mọi thư mục trong ket_qua/that/vu (bỏ đuôi _nhanh)")
    ap.add_argument("--ke_hoach", action="store_true", help="chỉ in số lượt gọi RPC dự kiến, không gọi mạng")
    ap.add_argument("--nhanh", action="store_true", help="chỉ 20 tx đầu và 2.000 block swap, ghi vào <vao>/nhanh/")
    ap.add_argument("--chi_gan", action="store_true", help="chỉ gán vai và tính lượng xả trên dữ liệu đã tải")
    ap.add_argument("--rpc", default=None, help="URL JSON-RPC (mặc định biến môi trường BSC_RPC_URL)")
    ap.add_argument("--phan", default=None, help="i/n: chỉ tra receipt phần i trong n của tx lệnh (ghi vi_lenh_p<i>.csv), để n khóa chạy song "
                    "song trên cùng một vụ; phần 1 làm thêm swap đầy đủ và ví swap; gán vai chạy sau bằng --chi_gan")
    ap.add_argument("--nghi", type=float, default=0.2, help="giây nghỉ giữa hai lượt gọi")
    ap.add_argument("--truoc", type=float, default=2.0, help="giờ swap đầy đủ trước lúc rút tường")
    ap.add_argument("--sau", type=float, default=2.0, help="giờ swap đầy đủ sau t_b")
    ap.add_argument("--swap_lon", type=int, default=200, help="chỉ tra ví gửi cho bấy nhiêu swap lớn nhất")
    ap.add_argument("--token_dg", type=int, default=None, choices=[0, 1], help="token dùng xếp swap lớn ở bước 3 (mặc định: token bị xả tự nhận)")
    ap.add_argument("--token_xa", type=int, default=None, choices=[0, 1], help="ép token bị xả (mặc định tự nhận theo dòng tiền ròng và chiều tick)")
    ap.add_argument("--cua_so_rut", type=int, default=1200, help="block trước t_b để tính cờ rut_truoc_sap (1.200 ≈ 15 phút)")
    ap.add_argument("--cua_so_sap", type=int, default=300, help="± block quanh t_b để nhận token bị xả và tính cờ ban_lon")
    ap.add_argument("--nguong_ban", type=float, default=0.01, help="tỷ trọng tối thiểu trong lượng bán của cửa sổ để có cờ ban_lon")
    ap.add_argument("--che_do_tuong", choices=["chua", "dung"], default="chua", help="vị thế tính là tại tường: chứa trọn tường hoặc đúng khoảng tường")
    ap.add_argument("--chu_so", type=int, default=18, help="số chữ số thập phân của token, chỉ dùng khi in")
    ap.add_argument("--buoc", type=int, default=5000, help="số block mỗi lần getLogs swap (tự chia đôi khi node từ chối)")
    ap.add_argument("--tat_ca_lenh", action="store_true", help="tra ví cho mọi tx Mint/Burn/Collect, không chỉ lệnh chạm tường")
    ap.add_argument("--rong_max", type=int, default=None, help="bỏ lệnh rộng hơn bấy nhiêu tick (vd. vị thế toàn dải), giảm số receipt")
    a = ap.parse_args()
    dirs = _thu_muc_tat_ca() if a.tat_ca else [Path(x) for x in a.vao]
    if not dirs:
        raise SystemExit("Cần --vao <thư mục> hoặc --tat_ca")
    phan = None
    if a.phan:
        i_p, n_p = (int(x) for x in a.phan.split("/"))
        if not 1 <= i_p <= n_p:
            raise SystemExit("--phan phải dạng i/n với 1 ≤ i ≤ n")
        phan = (i_p, n_p)
    if a.ke_hoach:
        bang_vu = doc_bang_vu(BANG_VU)
        kq = [ke_hoach(d, a.truoc, a.sau, a.swap_lon, a.buoc, a.tat_ca_lenh, a.rong_max, a.nhanh, bang_vu, phan) for d in dirs]
        t = pd.DataFrame(kq).drop(columns="cua_so")
        print(t.to_string(index=False))
        print(f"Tổng: {int(t.tong.sum()):,} lượt gọi (receipt lệnh {int(t.tx_lenh_con.sum()):,}, getLogs swap "
              f"{int(t.getlogs_swap.sum()):,}, receipt swap {int(t.receipt_swap.sum()):,})")
    else:
        rpc = None if a.chi_gan else bao_ve_han_muc(L.RPC(L.url_rpc("bsc", a.rpc), a.nghi))
        for d in dirs:
            try:
                chay(d, rpc, a.truoc, a.sau, a.swap_lon, a.buoc, a.tat_ca_lenh, a.rong_max, a.nhanh, a.token_dg, a.chi_gan,
                     a.token_xa, a.cua_so_rut, a.cua_so_sap, a.nguong_ban, a.che_do_tuong, a.chu_so, phan)
            except L.HetHanMuc as e:
                raise SystemExit(f"Hết hạn mức hoặc khóa hỏng: {e}. Đổi BSC_RPC_KEY sang tài khoản khác rồi chạy lại đúng lệnh; "
                                 "phần đã tải được giữ nguyên.") from e

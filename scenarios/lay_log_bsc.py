"""Tải log sự kiện của một bể PancakeSwap v3 / Uniswap v3 qua JSON-RPC (`eth_getLogs`), ghi dần ra CSV.

Dùng cho cải tiến E (dữ liệu thật): địa chỉ bể, block `t_m`, `t_b` của 29 vụ lấy từ phụ lục bài gốc
(`../00_Bai_goc/manual-validation-events-table.md`); 5 bể đối chứng ở `non-incentivized-pool-aliases.md`.

Chạy (từ `04_Simulator/`; RPC phải giữ được log cũ, tức node lưu trữ; đặt URL có khóa vào biến môi trường, không ghi vào mã):
    $env:BSC_RPC_URL = "https://..."            # PowerShell
    python -m scenarios.lay_log_bsc --pool 0x9485... --tu 54100000 --den 54760000 [--swap mau] [--nhanh]
Chuỗi khác (`--chuoi eth|arb|base`) có sẵn RPC công khai trả được log năm 2025 (xem `CHUOI`); ghi vào `ket_qua/that/<chuoi>/`.
Tìm ứng viên tường trên toàn chuỗi: `scenarios.quet_tuong_that`.

Ghi vào `ket_qua/that/<pool>/`: `su_kien.csv` (Mint/Burn/Collect, đủ), `swap.csv` (theo `--swap`), `moc.csv`
(block, thời gian Unix ở đầu mỗi đoạn tải, để nội suy giờ), `tien_do.json`. Chạy lại đúng lệnh thì tiếp tục từ chỗ dừng.
`--swap mau` (mặc định): chỉ tải swap trong `--mau_dai` block đầu của mỗi `--mau_moi` block (đủ để biết giá mỗi giờ);
`day_du`: mọi swap (bể được trợ cấp có thể tới hàng triệu dòng); `khong`: bỏ swap. Lượng token và L là số nguyên thô
trên chuỗi (chưa chia số chữ số thập phân). Module chỉ dùng thư viện chuẩn.
"""
from __future__ import annotations

import argparse
import csv
import http.client
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

# ---------- keccak-256 (thư viện chuẩn không có; hashlib.sha3_256 là SHA-3, khác phần đệm) ----------
_RC = [0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000, 0x000000000000808B,
       0x0000000080000001, 0x8000000080008081, 0x8000000000008009, 0x000000000000008A, 0x0000000000000088,
       0x0000000080008009, 0x000000008000000A, 0x000000008000808B, 0x800000000000008B, 0x8000000000008089,
       0x8000000000008003, 0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
       0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008]
_ROT = [[0, 36, 3, 41, 18], [1, 44, 10, 45, 2], [62, 6, 43, 15, 61], [28, 55, 25, 21, 56], [27, 20, 39, 8, 14]]
_M = (1 << 64) - 1


def _f1600(a: list[list[int]]) -> None:
    for rc in _RC:
        c = [a[x][0] ^ a[x][1] ^ a[x][2] ^ a[x][3] ^ a[x][4] for x in range(5)]
        d = [c[(x - 1) % 5] ^ (((c[(x + 1) % 5] << 1) | (c[(x + 1) % 5] >> 63)) & _M) for x in range(5)]
        a[:] = [[a[x][y] ^ d[x] for y in range(5)] for x in range(5)]
        b = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                r = _ROT[x][y]
                b[y][(2 * x + 3 * y) % 5] = ((a[x][y] << r) | (a[x][y] >> (64 - r))) & _M if r else a[x][y]
        a[:] = [[b[x][y] ^ (~b[(x + 1) % 5][y] & b[(x + 2) % 5][y] & _M) for y in range(5)] for x in range(5)]
        a[0][0] ^= rc


def keccak256(data: bytes) -> bytes:
    """Keccak-256 (hàm băm của Ethereum) của `data`, trả 32 byte."""
    rate = 136
    p = bytearray(data) + b"\x01" + b"\x00" * ((-len(data) - 2) % rate) + b"\x80"
    if (len(data) + 1) % rate == 0:                       # đệm vừa một byte: 0x01 và 0x80 gộp thành 0x81
        p = bytearray(data) + b"\x81"
    a = [[0] * 5 for _ in range(5)]
    for off in range(0, len(p), rate):
        for i in range(rate // 8):
            a[i % 5][i // 5] ^= int.from_bytes(p[off + 8 * i:off + 8 * i + 8], "little")
        _f1600(a)
    return b"".join(a[i % 5][i // 5].to_bytes(8, "little") for i in range(4))


def chu_de(chu_ky: str) -> str:
    """topic0 (0x…64 hex) của một chữ ký sự kiện, ví dụ `Burn(address,int24,int24,uint128,uint256,uint256)`."""
    return "0x" + keccak256(chu_ky.encode()).hex()


SU_KIEN = {
    "mint": "Mint(address,address,int24,int24,uint128,uint256,uint256)",
    "burn": "Burn(address,int24,int24,uint128,uint256,uint256)",
    "collect": "Collect(address,address,int24,int24,uint128,uint128)",
    "swap_pancake": "Swap(address,address,int256,int256,uint160,uint128,int24,uint128,uint128)",
    "swap_uniswap": "Swap(address,address,int256,int256,uint160,uint128,int24)",
}
TOPIC = {ten: chu_de(ck) for ten, ck in SU_KIEN.items()}
_LOAI = {v: k for k, v in TOPIC.items()}
COT = ["block", "tx_index", "log_index", "tx_hash", "kind", "owner", "tick_lower", "tick_upper", "liquidity",
       "amount0", "amount1", "sqrt_price_x96", "tick", "liquidity_active"]


# Chuỗi hỗ trợ: biến môi trường chứa URL riêng (ưu tiên), RPC công khai đã thử trả được log năm 2025 (11/11/2026;
# None = chưa thấy RPC công khai nào), số giây mỗi block (gần đúng, chỉ để chọn nhịp lấy mẫu swap ≈ 1 giờ).
CHUOI = {
    "bsc": dict(bien="BSC_RPC_URL", cong_khai=None, giay_block=0.75),
    "eth": dict(bien="ETH_RPC_URL", cong_khai="https://rpc.mevblocker.io", giay_block=12.0),
    "arb": dict(bien="ARB_RPC_URL", cong_khai="https://arb1.arbitrum.io/rpc", giay_block=0.25),
    "base": dict(bien="BASE_RPC_URL", cong_khai="https://base.gateway.tenderly.co", giay_block=2.0),
}


def url_rpc(chuoi: str, rpc: str | None = None) -> str:
    """URL JSON-RPC cho `chuoi`: `rpc` nếu có, rồi biến môi trường của chuỗi, rồi RPC công khai; không có thì dừng."""
    c = CHUOI[chuoi]
    url = rpc or os.environ.get(c["bien"]) or c["cong_khai"]
    if not url:
        raise SystemExit(f"Cần --rpc hoặc biến môi trường {c['bien']} (node lưu trữ giữ được log cũ).")
    return url


def _so(hex32: str, co_dau: bool = False) -> int:
    v = int(hex32, 16)
    return v - (1 << 256) if co_dau and v >> 255 else v


def giai_ma(log: dict) -> dict | None:
    """Đổi một log thô của `eth_getLogs` thành dòng theo `COT` (số nguyên thô); None nếu không phải 4 loại sự kiện.

    `owner`: chủ vị thế theo sự kiện (mint qua hợp đồng quản lý vị thế thì là hợp đồng đó); swap: người nhận.
    amount0/amount1 của swap có dấu theo bể (dương = bể nhận vào)."""
    loai = _LOAI.get(log["topics"][0])
    if loai is None:
        return None
    t = log["topics"]
    d = log["data"][2:]
    w = [d[i:i + 64] for i in range(0, len(d), 64)]
    r = dict.fromkeys(COT, "")
    r.update(block=int(log["blockNumber"], 16), tx_index=int(log["transactionIndex"], 16),
             log_index=int(log["logIndex"], 16), tx_hash=log["transactionHash"], kind=loai.split("_")[0])
    dia_chi = lambda x: "0x" + x[-40:]
    if loai == "mint":                                    # data: sender, amount, amount0, amount1
        r.update(owner=dia_chi(t[1]), tick_lower=_so(t[2], True), tick_upper=_so(t[3], True),
                 liquidity=_so(w[1]), amount0=_so(w[2]), amount1=_so(w[3]))
    elif loai == "burn":                                  # data: amount, amount0, amount1
        r.update(owner=dia_chi(t[1]), tick_lower=_so(t[2], True), tick_upper=_so(t[3], True),
                 liquidity=_so(w[0]), amount0=_so(w[1]), amount1=_so(w[2]))
    elif loai == "collect":                               # data: recipient, amount0, amount1
        r.update(owner=dia_chi(t[1]), tick_lower=_so(t[2], True), tick_upper=_so(t[3], True),
                 amount0=_so(w[1]), amount1=_so(w[2]))
    else:                                                 # swap: amount0, amount1, sqrtPriceX96, liquidity, tick
        r.update(owner=dia_chi(t[2]), amount0=_so(w[0], True), amount1=_so(w[1], True),
                 sqrt_price_x96=_so(w[2]), liquidity_active=_so(w[3]), tick=_so(w[4], True))
    return r


class RPC:
    """Gọi JSON-RPC có thử lại; `goi` trả `result` hoặc ném RuntimeError kèm thông báo của node."""

    def __init__(self, url: str, nghi: float = 0.2):
        self.url, self.nghi, self.so_lan = url, nghi, 0

    def goi(self, method: str, params: list):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        loi = None
        for lan in range(5):
            time.sleep(self.nghi * (1 + 4 * lan))
            self.so_lan += 1
            try:
                dau = {"Content-Type": "application/json", "User-Agent": "python-client"}
                if os.environ.get("BSC_RPC_KEY"):               # nhà cung cấp nhận khóa qua header (vd. Blockmachine)
                    dau["Authorization"] = "Bearer " + os.environ["BSC_RPC_KEY"]
                req = urllib.request.Request(self.url, data=body, headers=dau)
                with urllib.request.urlopen(req, timeout=60) as resp:
                    kq = json.loads(resp.read())
            except urllib.error.HTTPError as e:
                loi = f"HTTP {e.code}"
                if e.code not in (429, 500, 502, 503, 504):
                    try:                                        # HTTP 400 thường kèm lý do (vd. giới hạn khoảng block của gói miễn phí)
                        loi += " " + e.read().decode("utf-8", "replace")[:300]
                    except OSError:
                        pass
                    break
                continue
            except (OSError, http.client.HTTPException, json.JSONDecodeError) as e:   # gồm URLError, Timeout, RemoteDisconnected
                loi = str(e)
                continue
            if "result" in kq:
                return kq["result"]
            raise RuntimeError(json.dumps(kq.get("error"), ensure_ascii=False))
        raise RuntimeError(f"RPC không trả lời: {loi}")


_LOI_KHOANG = ("range", "limit", "exceed", "too many", "too large", "response size", "10000", "10,000", "closed connection")


def tai_doan(rpc: RPC, pool: str | None, topics: list[str], tu: int, den: int, buoc: int, giu_be: bool = False):
    """Sinh (block_cuoi_đã_xong, [dòng]) cho từng đoạn trong [tu, den]; node báo lỗi khoảng thì chia đôi `buoc`.

    `pool=None`: lấy log của mọi hợp đồng trên chuỗi (quét toàn chuỗi); `giu_be`: thêm cột `pool` = địa chỉ phát log."""
    b, tran, hong = tu, buoc, 0
    while b <= den:
        e = min(b + buoc - 1, den)
        loc = {"topics": [topics], "fromBlock": hex(b), "toBlock": hex(e)}
        if pool:
            loc["address"] = pool
        try:
            logs = rpc.goi("eth_getLogs", [loc])
        except RuntimeError as loi:
            s = str(loi).lower()
            if any(k in s for k in _LOI_KHOANG) and buoc > 1:   # node từ chối vì khoảng quá rộng / quá nhiều log
                buoc = max(1, buoc // 2)
                continue
            hong += 1
            if hong > 3 or "header not found" in s:             # lỗi khác: thử lại vài lần rồi dừng (chạy lại để tiếp tục)
                raise
            time.sleep(2.0 * hong)
            continue
        hong = 0
        rows = []
        for lg in logs:
            r = giai_ma(lg)
            if r is not None:
                if giu_be:
                    r["pool"] = lg.get("address", "").lower()
                rows.append(r)
        yield e, rows
        b = e + 1
        buoc = min(tran, buoc * 2)                              # nới dần lại sau khi thành công


def _ghi(p: Path, rows: list[dict]) -> None:
    moi = not p.exists()
    with p.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COT)
        if moi:
            w.writeheader()
        w.writerows(rows)


def chay(pool: str, tu: int, den: int, ra: Path, rpc: RPC, swap: str = "mau", buoc: int = 5000,
         mau_moi: int = 4800, mau_dai: int = 40) -> dict:
    """Tải sự kiện của `pool` trong block [tu, den] vào thư mục `ra`, tiếp tục từ `tien_do.json` nếu có. Trả tiến độ."""
    ra.mkdir(parents=True, exist_ok=True)
    f_td = ra / "tien_do.json"
    td = json.loads(f_td.read_text()) if f_td.exists() else {}
    td.setdefault("su_kien", tu - 1)
    td.setdefault("swap", tu - 1)
    luu = lambda: f_td.write_text(json.dumps(td))
    t0 = time.time()

    def moc(block: int) -> None:
        ts = int(rpc.goi("eth_getBlockByNumber", [hex(block), False])["timestamp"], 16)
        p = ra / "moc.csv"
        moi = not p.exists()
        with p.open("a", encoding="utf-8") as f:
            f.write(("block,ts\n" if moi else "") + f"{block},{ts}\n")

    n = 0
    for e, rows in tai_doan(rpc, pool, [TOPIC["mint"], TOPIC["burn"], TOPIC["collect"]], td["su_kien"] + 1, den, buoc):
        _ghi(ra / "su_kien.csv", rows)
        moc(e)
        td["su_kien"] = e
        luu()
        n += len(rows)
        print(f"sự kiện LP: tới block {e} ({(e - tu + 1) / (den - tu + 1):.0%}), +{len(rows)} dòng, {time.time() - t0:.0f}s")
    if swap != "khong":
        tp = [TOPIC["swap_pancake"], TOPIC["swap_uniswap"]]
        if swap == "day_du":
            doan = [(td["swap"] + 1, den)]
        else:
            doan = [(b, min(b + mau_dai - 1, den)) for b in range(tu, den + 1, mau_moi) if b > td["swap"]]
        for a, z in doan:
            for e, rows in tai_doan(rpc, pool, tp, a, z, buoc):
                _ghi(ra / "swap.csv", rows)
                td["swap"] = e
                luu()
                n += len(rows)
            if swap == "mau" and (a - tu) // mau_moi % 20 == 0:
                print(f"swap mẫu: tới block {z} ({(z - tu + 1) / (den - tu + 1):.0%}), {time.time() - t0:.0f}s")
    print(f"Xong: {n} dòng mới, {rpc.so_lan} lần gọi, {time.time() - t0:.0f}s → {ra}")
    return td


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pool", required=True, help="địa chỉ hợp đồng bể (0x…)")
    ap.add_argument("--tu", type=int, required=True, help="block đầu")
    ap.add_argument("--den", type=int, required=True, help="block cuối")
    ap.add_argument("--ra", default=None, help="thư mục ghi (mặc định ket_qua/that/<pool>)")
    ap.add_argument("--chuoi", default="bsc", choices=sorted(CHUOI), help="chuỗi (mặc định bsc)")
    ap.add_argument("--rpc", default=None, help="URL JSON-RPC; mặc định biến môi trường của chuỗi, rồi RPC công khai")
    ap.add_argument("--swap", default="mau", choices=["mau", "day_du", "khong"])
    ap.add_argument("--buoc", type=int, default=5000, help="số block mỗi lần gọi (tự chia đôi khi node từ chối)")
    ap.add_argument("--mau_moi", type=int, default=None, help="lấy mẫu swap mỗi bấy nhiêu block (mặc định ≈ 1 giờ của chuỗi)")
    ap.add_argument("--mau_dai", type=int, default=None, help="số block mỗi mẫu swap (mặc định ≈ 30 giây, tối thiểu 3)")
    ap.add_argument("--nghi", type=float, default=0.2, help="giây nghỉ giữa hai lần gọi")
    ap.add_argument("--nhanh", action="store_true", help="chỉ 2.000 block đầu, ghi vào thư mục _nhanh, để đo thời gian")
    a = ap.parse_args()
    gb = CHUOI[a.chuoi]["giay_block"]
    pool = a.pool.lower()
    goc = Path("ket_qua/that") if a.chuoi == "bsc" else Path("ket_qua/that") / a.chuoi
    ra = Path(a.ra) if a.ra else goc / (pool + ("_nhanh" if a.nhanh else ""))
    chay(pool, a.tu, min(a.den, a.tu + 1999) if a.nhanh else a.den, ra, RPC(url_rpc(a.chuoi, a.rpc), a.nghi), a.swap,
         a.buoc, a.mau_moi or round(3600 / gb), a.mau_dai or max(3, round(30 / gb)))

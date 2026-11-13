"""Tải lịch sử Mint/Burn của bể từ lúc tạo bể đến đầu cửa sổ đã có, để bản đồ thanh khoản của vụ không thiếu vị thế cũ.

Các bể cần tải lấy từ hai bảng kết quả: thư mục vụ có `L_ok` < ngưỡng trong `ket_qua/that/tai_hien/theo_vu.csv` (nối với
`so_bai_goc.csv` qua `vu_id` → `thu_muc`). Với mỗi bể, quét LÙI từ đầu thư mục vụ cuối cùng cần sửa về phía block nhỏ: mỗi lần
`eth_getLogs` lấy Mint, Burn và Initialize trong một khoảng, bỏ qua các cửa sổ vụ đã có, và dừng ngay khi gặp Initialize (sự kiện bể
phát một lần lúc khởi tạo). Không cần biết trước block tạo bể, không cần trạng thái cũ của node.

    python -m scenarios.tai_lich_su_be --ke_hoach                # không gọi mạng: bể nào, cửa sổ nào, cửa sổ chạy nào làm bể nào
    python -m scenarios.tai_lich_su_be --be 3/10                 # tải các bể thứ 3, 13, 23… (n cửa sổ, mỗi cửa sổ một khóa)
    python -m scenarios.tai_lich_su_be --chi_pool 0x985c205b,0x08a10ae0     # hoặc chọn bể theo tiền tố địa chỉ

Kết quả: `ket_qua/that/lich_su/<bể[:10]>/lui/su_kien.csv` (chỉ Mint, Burn; cùng cột `su_kien.csv`) và `tien_do.json`
(`thap` = block nhỏ nhất đã quét, `xong` = đã gặp Initialize). Chạy lại thì tiếp tục, bỏ phần đã xong. Hết hạn mức hoặc khóa hỏng thì
dừng gọn; đổi `BSC_RPC_KEY` rồi chạy lại đúng lệnh. `doc_lich_su` đọc lại phần lịch sử trước một block (dùng trong `metrics.tai_hien_vu`).
Khoảng block mỗi lần gọi (`--buoc`, mặc định 5.000) tự chia đôi khi node từ chối và không tăng lại. Khóa RPC và URL lấy từ biến môi trường.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd

from scenarios import lay_log_bsc as L
from scenarios.tai_vi_vu import bao_ve_han_muc
from scenarios.tai_vu_that import BANG_DOI_CHUNG, BANG_VU, doc_bang_vu, doc_doi_chung, ke_hoach

GOC = Path("ket_qua/that")
LICH_SU = GOC / "lich_su"
LO_MAC_DINH = 26_000_000      # trước khi PancakeSwap v3 ra mắt trên BSC: không quét lùi quá block này
BLOCK_MOI_LAN = 5000
KICH_TOI_THIEU = 500
DO_TRE_KIEM_TAO = 10_000      # sự kiện đầu của cửa sổ đầu cách đầu cửa sổ quá bấy nhiêu block thì kiểm Initialize có nằm trong cửa sổ không
TOPIC_INITIALIZE = L.chu_de("Initialize(uint160,int24)")


# ---------- thuần (không mạng) ----------
def thu_muc_can_lich_su(nguong_L: float = 0.99, theo_vu: Path = GOC / "tai_hien" / "theo_vu.csv",
                        so_bai_goc: Path = GOC / "so_bai_goc.csv") -> set[str]:
    """Tên thư mục vụ có `L_ok` < `nguong_L` (bản đồ thanh khoản dựng lại không khớp log), nối `vu` ↔ `vu_id`."""
    t, s = pd.read_csv(theo_vu), pd.read_csv(so_bai_goc)
    d = t.merge(s[["vu_id", "thu_muc"]], left_on="vu", right_on="vu_id")
    return set(d.loc[d["L_ok"] < nguong_L, "thu_muc"])


def bang_be(nguong_L: float = 0.99) -> dict[str, dict]:
    """Mỗi bể cần tải: {pool đầy đủ: {"cua_so": [(đầu, cuối)…] của mọi thư mục vụ, "can_den": đầu của thư mục cuối cùng cần sửa}}."""
    can = thu_muc_can_lich_su(nguong_L)
    kh = [k for k in ke_hoach(doc_bang_vu(BANG_VU), doc_doi_chung(BANG_DOI_CHUNG)) if k["kieu"] == "vu"]
    be: dict[str, dict] = {}
    for k in kh:
        e = be.setdefault(k["pool"], dict(cua_so=[], can_den=0))
        e["cua_so"].append((k["tu"], k["den"]))
        if Path(k["ra"]).name in can:
            e["can_den"] = max(e["can_den"], k["tu"])
    be = {p: e for p, e in be.items() if e["can_den"] > 0}
    for p, e in be.items():                                    # block sự kiện đầu tiên của cửa sổ đầu (nếu đã tải)
        f = GOC / "vu" / f"{p[:10]}_{min(a for a, _ in e['cua_so'])}" / "su_kien.csv"
        e["dau_su_kien"] = int(pd.read_csv(f, usecols=["block"])["block"].min()) if f.exists() else None
    return be


def chon_be(pools: list[str], phan: str | None = None, tien_to: str | None = None) -> list[str]:
    """Chọn bể của một cửa sổ: `phan="i/n"` lấy các bể thứ i, i+n, … (từ 1, theo thứ tự sắp xếp); `tien_to` lọc theo tiền tố địa chỉ, cách nhau dấu phẩy."""
    pools = sorted(pools)
    if tien_to:
        tt = tuple(x.strip().lower() for x in tien_to.split(",") if x.strip())
        pools = [p for p in pools if p.lower().startswith(tt)]
    if phan:
        i, n = (int(x) for x in phan.split("/"))
        if not 1 <= i <= n:
            raise SystemExit("--be phải dạng i/n với 1 ≤ i ≤ n")
        pools = pools[i - 1::n]
    return pools


def khoang_tiep(cur_hi: int, cua_so: list[tuple[int, int]], kich: int, lo: int) -> tuple[int, int] | None:
    """Khoảng [đầu, cuối] kế tiếp khi quét lùi từ `cur_hi`: dài tối đa `kich` block, không nhỏ hơn `lo`, nhảy qua và không chạm các cửa sổ
    `cua_so` đã có. None khi hết (cur_hi < lo)."""
    while True:
        trong = [(a, z) for a, z in cua_so if a <= cur_hi <= z]
        if not trong:
            break
        cur_hi = min(a for a, _ in trong) - 1
    if cur_hi < lo:
        return None
    dau = max(lo, cur_hi - kich + 1)
    for a, z in cua_so:
        if z < cur_hi and z >= dau:
            dau = z + 1
    return dau, cur_hi


def doc_lich_su(pool: str, truoc_block: int, goc: Path = LICH_SU, vu: Path | None = None) -> pd.DataFrame:
    """Mint/Burn đã tải của `pool` (địa chỉ hoặc 10 ký tự đầu) với block < `truoc_block`; rỗng nếu chưa tải. Mọi cột là chuỗi.

    `vu`: thư mục gốc các thư mục vụ (`ket_qua/that/vu`); có thì gộp thêm `su_kien.csv` của MỌI cửa sổ vụ khác của cùng bể, vì lịch sử ở `goc`
    chỉ gồm phần ngoài các cửa sổ đó (bể có nhiều cửa sổ: phát lại cửa sổ sau cần cả các cửa sổ trước)."""
    thu = goc / pool[:10].lower()
    fs = sorted(thu.glob("*/su_kien.csv")) if thu.exists() else []
    if vu is not None and Path(vu).exists():
        fs += sorted(f for f in Path(vu).glob(pool[:10].lower() + "_*/su_kien.csv") if not f.parent.name.endswith("_nhanh"))
    fs = [f for f in fs if f.stat().st_size > 0]
    if not fs:
        return pd.DataFrame(columns=L.COT, dtype=str)
    d = pd.concat([pd.read_csv(f, dtype=str) for f in fs], ignore_index=True)
    d = d[d["block"].astype(int) < truoc_block]
    return d.drop_duplicates(["block", "tx_index", "log_index"]).reset_index(drop=True)


# ---------- tải ----------
def co_initialize(rpc, pool: str, dau: int, cuoi: int, kich: int) -> bool:
    """Có sự kiện Initialize của `pool` trong [dau, cuoi] không (quét xuôi từng khoảng `kich`, chia đôi khi node từ chối)."""
    b = dau
    while b <= cuoi:
        e = min(b + kich - 1, cuoi)
        try:
            logs = rpc.goi("eth_getLogs", [{"address": pool, "topics": [[TOPIC_INITIALIZE]], "fromBlock": hex(b), "toBlock": hex(e)}])
        except L.HetHanMuc:
            raise
        except RuntimeError as err:
            if any(k in str(err).lower() for k in L._LOI_KHOANG) and kich > KICH_TOI_THIEU:
                kich = max(KICH_TOI_THIEU, kich // 2)
                continue
            raise
        if logs:
            return True
        b = e + 1
    return False


def lui_mot_be(rpc, pool: str, cua_so: list[tuple[int, int]], can_den: int, buoc: int, lo: int = LO_MAC_DINH,
               goc: Path = LICH_SU, dau_su_kien: int | None = None) -> dict:
    """Quét lùi Mint/Burn/Initialize của `pool` từ `can_den - 1` tới khi gặp Initialize (hoặc `lo`), ghi dần vào `goc/<pool[:10]>/lui/`.

    `dau_su_kien`: block sự kiện đầu tiên của cửa sổ đầu. Bể tạo ngay trong cửa sổ đầu (Initialize nằm trong cửa sổ đã tải, mà quét lùi bỏ qua
    cửa sổ) thì không có lịch sử trước cửa sổ: nếu sự kiện đầu cách đầu cửa sổ hơn `DO_TRE_KIEM_TAO` block, kiểm Initialize trong khoảng đó
    một lần; có thì chỉ quét các khoảng giữa các cửa sổ rồi dừng ở đầu cửa sổ đầu thay vì lùi tới `lo`."""
    ra = goc / pool[:10] / "lui"
    ra.mkdir(parents=True, exist_ok=True)
    f_td = ra / "tien_do.json"
    td = json.loads(f_td.read_text()) if f_td.exists() else {"thap": can_den, "xong": False, "kich": buoc}
    kich, t0, dem, n = min(buoc, td.get("kich", buoc)), time.time(), 0, 0
    topics = [[L.TOPIC["mint"], L.TOPIC["burn"], TOPIC_INITIALIZE]]
    a0 = min((a for a, _ in cua_so), default=can_den)
    if "tao_trong_cua_so_dau" not in td and dau_su_kien is not None and dau_su_kien - a0 > DO_TRE_KIEM_TAO:
        td["tao_trong_cua_so_dau"] = co_initialize(rpc, pool, a0, dau_su_kien, kich)
        f_td.write_text(json.dumps(td))
    if td.get("tao_trong_cua_so_dau"):
        lo = max(lo, a0)
    while not td["xong"]:
        kt = khoang_tiep(td["thap"] - 1, cua_so, kich, lo)
        if kt is None:
            td["xong"] = True
            td["ghi_chu"] = "tao_trong_cua_so_dau" if td.get("tao_trong_cua_so_dau") else f"khong_thay_Initialize_toi_block_{lo}"
            break
        dau, cuoi = kt
        try:
            logs = rpc.goi("eth_getLogs", [{"address": pool, "topics": topics, "fromBlock": hex(dau), "toBlock": hex(cuoi)}])
        except L.HetHanMuc:
            raise
        except RuntimeError as err:
            if any(k in str(err).lower() for k in L._LOI_KHOANG) and kich > KICH_TOI_THIEU:
                kich = max(KICH_TOI_THIEU, kich // 2)           # node từ chối khoảng này: chia đôi, không tăng lại
                td["kich"] = kich
                continue
            raise
        rows = [r for r in (L.giai_ma(lg) for lg in logs) if r is not None]
        if rows:
            L._ghi(ra / "su_kien.csv", rows)
        n += len(rows)
        td["thap"] = dau
        if any(lg["topics"][0] == TOPIC_INITIALIZE for lg in logs):
            td["xong"] = True
        f_td.write_text(json.dumps(td))
        dem += 1
        if dem % 50 == 0:
            print(f"  {pool[:10]}: lùi tới block {dau:,} (cách đầu cửa sổ {can_den - dau:,}), +{n} dòng, {rpc.so_lan} lượt, {time.time() - t0:.0f}s", flush=True)
    f_td.write_text(json.dumps(td))
    return td


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ke_hoach", action="store_true", help="chỉ in bể và cửa sổ, không gọi mạng")
    ap.add_argument("--be", default=None, help="i/n: chỉ các bể thứ i, i+n, … (theo thứ tự địa chỉ), để n cửa sổ chạy song song, mỗi cửa sổ một khóa")
    ap.add_argument("--chi_pool", default=None, help="chỉ các bể có địa chỉ bắt đầu bằng một trong các tiền tố này, cách nhau dấu phẩy")
    ap.add_argument("--nguong_L", type=float, default=0.99, help="thư mục vụ có L_ok dưới ngưỡng này thì bể cần lịch sử")
    ap.add_argument("--lo", type=int, default=LO_MAC_DINH, help="không quét lùi quá block này")
    ap.add_argument("--buoc", type=int, default=BLOCK_MOI_LAN, help="số block mỗi lần getLogs (tự chia đôi khi node từ chối)")
    ap.add_argument("--nghi", type=float, default=0.2, help="giây nghỉ giữa hai lượt gọi")
    ap.add_argument("--rpc", default=None, help="URL JSON-RPC (mặc định biến môi trường BSC_RPC_URL)")
    a = ap.parse_args()
    be = bang_be(a.nguong_L)
    ds = chon_be(list(be), a.be, a.chi_pool)
    if a.ke_hoach:
        for k, p in enumerate(sorted(be), 1):
            print(f"{k:2d} {p[:10]} cần tới block {be[p]['can_den']:,}; cửa sổ đã có: {be[p]['cua_so']}"
                  + ("   <- chọn" if p in ds else ""))
        print(f"Chọn {len(ds)}/{len(be)} bể")
        return
    rpc = bao_ve_han_muc(L.RPC(L.url_rpc("bsc", a.rpc), a.nghi))
    for k, pool in enumerate(ds, 1):
        e = be[pool]
        print(f"=== bể {k}/{len(ds)}: {pool[:10]}, lùi từ block {e['can_den']:,}", flush=True)
        try:
            td = lui_mot_be(rpc, pool, e["cua_so"], e["can_den"], a.buoc, a.lo, dau_su_kien=e.get("dau_su_kien"))
            print(f"  xong: quét tới block {td['thap']:,} ({e['can_den'] - td['thap']:,} block), {rpc.so_lan} lượt gọi"
                  + (f", {td['ghi_chu']}" if td.get("ghi_chu") else ", đã gặp Initialize"), flush=True)
        except L.HetHanMuc as err:
            raise SystemExit(f"Hết hạn mức hoặc khóa hỏng: {err}. Đổi BSC_RPC_KEY sang tài khoản khác rồi chạy lại đúng lệnh; "
                             "phần đã tải được giữ nguyên.") from err
        except Exception as err:   # noqa: BLE001 — lỗi mạng/RPC: ghi lại, chuyển bể sau
            msg = f"{time.strftime('%Y-%m-%d %H:%M:%S')} lịch sử {pool[:10]}: {err}"
            print("LỖI:", msg, flush=True)
            with (GOC / "loi_tai.txt").open("a", encoding="utf-8") as f:
                f.write(msg + "\n")


if __name__ == "__main__":
    main()

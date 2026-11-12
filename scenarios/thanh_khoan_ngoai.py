"""Đo thanh khoản của token bị tấn công ở NGOÀI bể bị tấn công, trên chuỗi BSC, tại block t_m của từng vụ.

Câu hỏi: giả định "giá bị ghim vì không có giá tham chiếu độc lập" có hợp lý không? Nếu token alpha còn nhiều
thanh khoản ở bể khác (PancakeSwap v3/v2, Uniswap v3 trên BSC) thì arbitrageur có chỗ neo giá.

Cách đo: với mỗi bể vụ, `eth_call` tại block t_m lấy token0/token1/fee/factory; token alpha = token không thuộc tập
đồng định giá (USDT, WBNB, USDC, BUSD, USD1); tìm bể khác chứa alpha bằng `getPool`/`getPair` của ba factory; số dư
`balanceOf(bể)` (đơn vị token, đã chia 10^decimals) của alpha và của đồng định giá.

Hạn chế (quan trọng khi diễn giải):
- Không thấy niêm yết trên sàn tập trung (CEX) và thanh khoản ở chuỗi khác; Binance Alpha có thể có giá tham chiếu
  ngoài chuỗi, nên "không có bể ngoài" chưa chứng minh "không có giá tham chiếu".
- Chỉ dò các bể có cặp với tập đồng định giá ở trên và phí chuẩn của từng factory; bể cặp với token khác, bể của
  DEX khác (Thena, Biswap, …) và bể ra đời bằng factory khác không được đếm.
- Số dư token của bể gồm cả phí chưa thu và (ở bể v3) thanh khoản nằm ngoài vùng giá hiện tại; đây là cận trên của
  thanh khoản dùng được quanh giá hiện tại. Bể ngoài còn thanh khoản thật có thể nằm xa giá.
- Cần node lưu trữ (archive) vì gọi tại block cũ.

Chạy (từ 04_Simulator, PowerShell; cần biến BSC_RPC_URL do người dùng đặt):
    $env:PYTHONIOENCODING="utf-8"; python -m scenarios.thanh_khoan_ngoai
    (thêm --nhanh để chỉ chạy 2 vụ đầu)
Kết quả: ket_qua/that/thanh_khoan_ngoai.csv, mỗi vụ một dòng, ghi dần; chạy lại bỏ qua vụ đã có (khóa pool+t_m).
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import time
from pathlib import Path

from scenarios.lay_log_bsc import _LOI_HAN_MUC, _LOI_TOC_DO, RPC, HetHanMuc, keccak256, url_rpc

# Dòng kết quả mà nguyên nhân có thể là node từ chối chứ không phải dữ liệu thiếu: chạy lại thì đo lại.
GHI_CHU_CAN_DO_LAI = ("khong_doc_duoc_token", "pcs_v2_loi_goi")

BANG_VU = Path(__file__).resolve().parents[2] / "00_Bai_goc" / "manual-validation-events-table.md"
RA = Path(__file__).resolve().parents[1] / "ket_qua" / "that" / "thanh_khoan_ngoai.csv"

FACTORY_PANCAKE_V3 = "0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865"
FACTORY_PANCAKE_V2 = "0xca143ce32fe78f1f7019d7d551a6402fc5350c73"   # factory() của router v2 0x10ED43…024E (đã kiểm 12/11)
FACTORY_UNI_V3 = "0xdB1d10011AD0Ff90774D0C6Bb92e5C5c8b4461F7"
PHI_V3 = (100, 500, 2500, 10000)
# Đồng định giá: địa chỉ thường -> (ký hiệu, nhóm). Nhóm "usd" coi 1 token = 1 USD thô; "wbnb" ghi riêng.
# USD1 (World Liberty) địa chỉ lấy theo trí nhớ, chưa đối chiếu với trình duyệt khối; sai thì chỉ làm thiếu bể USD1.
DONG_DINH_GIA = {
    "0x55d398326f99059ff775485246999027b3197955": ("USDT", "usd"),
    "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c": ("WBNB", "wbnb"),
    "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d": ("USDC", "usd"),
    "0xe9e7cea3dedca5984780bafc599bd69add087d56": ("BUSD", "usd"),
    "0x8d0d000ee44948fc98c9b98a4fa4921476f08b0d": ("USD1", "usd"),
}
ZERO = "0x" + "0" * 40

COT = ["pool", "t_m", "t_b", "factory_be_vu", "factory_dung", "phi_be_vu", "alpha", "alpha_symbol", "alpha_decimals",
       "quote", "quote_symbol", "quote_nhom", "alpha_trong_be_vu", "quote_trong_be_vu", "so_be_ngoai", "be_ngoai",
       "alpha_ngoai", "quote_ngoai_usd", "quote_ngoai_wbnb", "ty_le_alpha_ngoai", "quote_ngoai_ge_quote_vu",
       "ghi_chu"]


def selector(chu_ky: str) -> str:
    """4 byte đầu (hex, không 0x) của keccak256 chữ ký hàm, ví dụ `balanceOf(address)` -> `70a08231`."""
    return keccak256(chu_ky.encode()).hex()[:8]


def _dia_chi_tham_so(addr: str) -> str:
    return addr.lower().replace("0x", "").rjust(64, "0")


def _uint_tham_so(v: int) -> str:
    return hex(v)[2:].rjust(64, "0")


def calldata(chu_ky: str, *tham_so: str | int) -> str:
    """Calldata ABI (0x…): selector + tham số; chuỗi địa chỉ hoặc số nguyên (uint) đệm trái tới 32 byte."""
    d = selector(chu_ky)
    for t in tham_so:
        d += _uint_tham_so(t) if isinstance(t, int) else _dia_chi_tham_so(t)
    return "0x" + d


def eth_call(rpc, to: str, data: str, block: int) -> str | None:
    """`eth_call` tại `block`; trả hex kết quả, hoặc None nếu lỗi / hợp đồng chưa tồn tại / trả về rỗng."""
    for lan in range(1, 6):
        try:
            kq = rpc.goi("eth_call", [{"to": to, "data": data}, hex(block)])
            break
        except RuntimeError as e:
            s = str(e).lower()
            if any(k in s for k in _LOI_HAN_MUC):          # hết hạn mức / khóa hỏng: dừng, không coi là "hợp đồng không tồn tại"
                raise HetHanMuc(str(e)) from e
            if any(k in s for k in _LOI_TOC_DO):            # giới hạn tốc độ: chờ rồi thử lại, kéo dài mới dừng
                if lan >= 5:
                    raise HetHanMuc(f"{e} (bị giới hạn liên tục)") from e
                time.sleep(15 * lan)
                continue
            return None                                      # revert / hợp đồng chưa có tại block này
    if not isinstance(kq, str) or kq in ("0x", ""):
        return None
    return kq


def _dia_chi(kq: str | None) -> str | None:
    """Địa chỉ chữ thường từ 32 byte trả về của eth_call; None nếu thiếu."""
    if kq is None or len(kq) < 66:
        return None
    return "0x" + kq[26:66].lower()


def _so(kq: str | None) -> int | None:
    if kq is None:
        return None
    try:
        return int(kq, 16)
    except ValueError:
        return None


def giai_ma_symbol(kq: str | None) -> str:
    """Ký hiệu token từ kết quả `symbol()`: bytes32 hoặc string ABI; lỗi thì trả chuỗi rỗng."""
    if not kq:
        return ""
    try:
        raw = bytes.fromhex(kq[2:])
        if len(raw) == 32:
            return raw.rstrip(b"\x00").decode("utf-8", "replace")
        n = int.from_bytes(raw[32:64], "big")
        return raw[64:64 + n].decode("utf-8", "replace")
    except (ValueError, IndexError):
        return ""


def doc_bang_vu(duong_dan: Path = BANG_VU) -> list[dict]:
    """Đọc bảng 29 vụ: danh sách dict {pool, tick_lower, tick_upper, t_m, t_b, victims} (block là số nguyên)."""
    vu = []
    for dong in duong_dan.read_text(encoding="utf-8").splitlines():
        if not dong.startswith("| `0x"):
            continue
        o = [c.strip().strip("`") for c in dong.strip().strip("|").split("|")]
        vu.append(dict(pool=o[0].lower(), tick_lower=int(o[1]), tick_upper=int(o[2]), t_m=int(o[3]), t_b=int(o[5]),
                       victims=int(o[7])))
    return vu


def tim_alpha(token0: str, token1: str) -> tuple[str | None, str | None, str]:
    """Tách (alpha, quote, ghi_chú) từ hai token; alpha là token không thuộc tập đồng định giá. None nếu cả hai đều thuộc tập."""
    t0, t1 = token0.lower(), token1.lower()
    in0, in1 = t0 in DONG_DINH_GIA, t1 in DONG_DINH_GIA
    if in0 and in1:
        return None, None, "ca_hai_token_la_dong_dinh_gia"
    if in1:
        return t0, t1, ""
    if in0:
        return t1, t0, ""
    return t0, t1, "khong_token_nao_la_dong_dinh_gia(chon token0 lam alpha)"


def tong_hop(alpha_vu: float, alpha_ngoai: float) -> float | None:
    """Tỷ lệ alpha_ngoai / (alpha_ngoai + alpha_trong_be_vu); None nếu cả hai bằng 0."""
    tong = alpha_ngoai + alpha_vu
    return alpha_ngoai / tong if tong > 0 else None


def tim_be_ngoai(rpc, alpha: str, be_vu: str, block: int, ghi_chu: list[str]) -> list[tuple[str, str, str, str]]:
    """Các bể ngoài chứa alpha tại `block`: danh sách (địa chỉ, loại, phí, token đồng định giá của cặp); bỏ địa chỉ 0 và bể vụ, bỏ trùng."""
    ket: dict[str, tuple[str, str, str, str]] = {}
    quotes = list(DONG_DINH_GIA)
    for ten, factory in (("pcs_v3", FACTORY_PANCAKE_V3), ("uni_v3", FACTORY_UNI_V3)):
        loi = 0
        for q in quotes:
            for phi in PHI_V3:
                kq = eth_call(rpc, factory, calldata("getPool(address,address,uint24)", alpha, q, phi), block)
                if kq is None:
                    loi += 1
                    continue
                a = _dia_chi(kq)
                if a and a != ZERO and a != be_vu:
                    ket.setdefault(a, (a, ten, str(phi), q))
        if loi == len(quotes) * len(PHI_V3):
            ghi_chu.append(f"{ten}_loi_goi")
    loi = 0
    for q in quotes:
        kq = eth_call(rpc, FACTORY_PANCAKE_V2, calldata("getPair(address,address)", alpha, q), block)
        if kq is None:
            loi += 1
            continue
        a = _dia_chi(kq)
        if a and a != ZERO and a != be_vu:
            ket.setdefault(a, (a, "pcs_v2", "2500", q))
    if loi == len(quotes):
        ghi_chu.append("pcs_v2_loi_goi")
    return list(ket.values())


class _ThongTin:
    """Bộ nhớ đệm decimals/symbol theo token."""

    def __init__(self, rpc, block):
        self.rpc, self.block, self.dec, self.sym = rpc, block, {}, {}

    def decimals(self, tok: str) -> int:
        if tok not in self.dec:
            v = _so(eth_call(self.rpc, tok, calldata("decimals()"), self.block))
            self.dec[tok] = v if v is not None and v <= 36 else 18
        return self.dec[tok]

    def symbol(self, tok: str) -> str:
        if tok not in self.sym:
            self.sym[tok] = giai_ma_symbol(eth_call(self.rpc, tok, calldata("symbol()"), self.block))
        return self.sym[tok]


def so_du(rpc, token: str, chu: str, block: int, dec: int) -> float | None:
    """Số dư `token` của địa chỉ `chu` tại `block`, đơn vị token (chia 10^dec); None nếu gọi lỗi."""
    v = _so(eth_call(rpc, token, calldata("balanceOf(address)", chu), block))
    return None if v is None else v / 10 ** dec


def do_mot_vu(rpc, vu: dict) -> dict:
    """Đo một vụ tại block t_m; trả dict theo cột COT (ô không đo được để trống, nguyên nhân trong `ghi_chu`)."""
    blk, pool = vu["t_m"], vu["pool"]
    d = {c: "" for c in COT}
    d.update(pool=pool, t_m=blk, t_b=vu["t_b"])
    gc: list[str] = []
    t0 = _dia_chi(eth_call(rpc, pool, calldata("token0()"), blk))
    t1 = _dia_chi(eth_call(rpc, pool, calldata("token1()"), blk))
    phi = _so(eth_call(rpc, pool, calldata("fee()"), blk))
    fac = _dia_chi(eth_call(rpc, pool, calldata("factory()"), blk))
    if t0 is None or t1 is None:
        d["ghi_chu"] = "khong_doc_duoc_token(node_khong_archive_hoac_be_chua_ton_tai)"
        return d
    d["factory_be_vu"] = fac or ""
    d["phi_be_vu"] = "" if phi is None else phi
    d["factory_dung"] = int(fac is not None and fac == FACTORY_PANCAKE_V3.lower())
    if not d["factory_dung"]:
        gc.append("factory_khong_phai_pancake_v3")
    alpha, quote, c = tim_alpha(t0, t1)
    if c:
        gc.append(c)
    if alpha is None:
        d["ghi_chu"] = ";".join(gc)
        return d
    tt = _ThongTin(rpc, blk)
    da, dq = tt.decimals(alpha), tt.decimals(quote)
    d.update(alpha=alpha, alpha_symbol=tt.symbol(alpha), alpha_decimals=da, quote=quote,
             quote_symbol=DONG_DINH_GIA.get(quote, ("",))[0] or tt.symbol(quote),
             quote_nhom=DONG_DINH_GIA.get(quote, ("", ""))[1])
    a_vu, q_vu = so_du(rpc, alpha, pool, blk, da), so_du(rpc, quote, pool, blk, dq)
    d["alpha_trong_be_vu"], d["quote_trong_be_vu"] = "" if a_vu is None else a_vu, "" if q_vu is None else q_vu
    be = tim_be_ngoai(rpc, alpha, pool, blk, gc)
    a_ng, usd, wbnb, ds = 0.0, 0.0, 0.0, []
    for addr, loai, p, q in be:
        a_b = so_du(rpc, alpha, addr, blk, da)
        a_ng += a_b or 0.0
        bal = so_du(rpc, q, addr, blk, tt.decimals(q)) or 0.0
        if DONG_DINH_GIA[q][1] == "wbnb":
            wbnb += bal
        else:
            usd += bal
        ds.append(f"{addr}:{loai}:{p}")
    d.update(so_be_ngoai=len(be), be_ngoai="|".join(ds), alpha_ngoai=a_ng, quote_ngoai_usd=usd, quote_ngoai_wbnb=wbnb)
    if a_vu is not None:
        r = tong_hop(a_vu, a_ng)
        d["ty_le_alpha_ngoai"] = "" if r is None else r
    if q_vu is not None:
        so_ngoai = wbnb if d["quote_nhom"] == "wbnb" else usd
        d["quote_ngoai_ge_quote_vu"] = int(bool(be) and so_ngoai >= q_vu)
    d["ghi_chu"] = ";".join(gc)
    return d


def da_xong(ra: Path) -> set[tuple[str, str]]:
    """Khóa (pool, t_m) các vụ đã có trong CSV kết quả."""
    if not ra.exists():
        return set()
    with ra.open(encoding="utf-8", newline="") as f:
        return {(r["pool"], r["t_m"]) for r in csv.DictReader(f)
                if not any(k in r.get("ghi_chu", "") for k in GHI_CHU_CAN_DO_LAI)}


def bo_dong_can_do_lai(ra: Path) -> int:
    """Xóa khỏi CSV các dòng có `ghi_chu` thuộc GHI_CHU_CAN_DO_LAI (để đo lại, không trùng dòng); trả số dòng đã xóa."""
    if not ra.exists():
        return 0
    with ra.open(encoding="utf-8", newline="") as f:
        dong = list(csv.DictReader(f))
    giu = [r for r in dong if not any(k in r.get("ghi_chu", "") for k in GHI_CHU_CAN_DO_LAI)]
    if len(giu) < len(dong):
        with ra.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COT)
            w.writeheader()
            w.writerows(giu)
    return len(dong) - len(giu)


def ghi_dong(ra: Path, d: dict) -> None:
    """Ghi thêm một dòng vào CSV (tạo file kèm tiêu đề nếu chưa có)."""
    ra.parent.mkdir(parents=True, exist_ok=True)
    moi = not ra.exists()
    with ra.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COT)
        if moi:
            w.writeheader()
        w.writerow(d)


def tom_tat(ra: Path) -> None:
    """In tóm tắt từ CSV: số vụ có bể ngoài, phân phối tỷ lệ alpha ngoài, vụ có quote ngoài ≥ quote bể vụ."""
    import pandas as pd
    df = pd.read_csv(ra)
    do = df[df["alpha"].notna()]
    print(f"Số vụ đo được: {len(do)}/{len(df)}")
    co = do[do["so_be_ngoai"] > 0]
    print(f"Số vụ có ít nhất một bể ngoài: {len(co)}/{len(do)}")
    ty = do["ty_le_alpha_ngoai"].dropna()
    if len(ty):
        print("Phân phối ty_le_alpha_ngoai:", ty.describe(percentiles=[.25, .5, .75]).round(4).to_dict())
    ge = do[do["quote_ngoai_ge_quote_vu"] == 1]
    print(f"Vụ có quote ở bể ngoài >= quote của bể vụ: {len(ge)}")
    for _, r in ge.iterrows():
        print(f"  {r['pool']} t_m={r['t_m']} alpha={r['alpha_symbol']} ty_le={r['ty_le_alpha_ngoai']}")


def main() -> None:
    """Chạy đo cho các vụ trong bảng; ghi dần CSV, bỏ vụ đã có."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--nhanh", action="store_true", help="chỉ 2 vụ đầu")
    ap.add_argument("--rpc", default=None)
    ap.add_argument("--ra", default=str(RA))
    a = ap.parse_args()
    if not (a.rpc or os.environ.get("BSC_RPC_URL")):
        raise SystemExit("Cần biến môi trường BSC_RPC_URL (node BSC archive) hoặc --rpc.")
    rpc = RPC(url_rpc("bsc", a.rpc))
    ra = Path(a.ra)
    vus = doc_bang_vu()
    if a.nhanh:
        vus = vus[:2]
    n_bo = bo_dong_can_do_lai(ra)
    if n_bo:
        print(f"Bỏ {n_bo} dòng cũ không đọc được (có thể do hết hạn mức) để đo lại.")
    xong = da_xong(ra)
    for i, vu in enumerate(vus, 1):
        if (vu["pool"], str(vu["t_m"])) in xong:
            print(f"[{i}/{len(vus)}] bỏ qua (đã có) {vu['pool']} {vu['t_m']}")
            continue
        try:
            d = do_mot_vu(rpc, vu)
        except HetHanMuc as e:
            raise SystemExit(f"Hết hạn mức hoặc khóa hỏng: {e}. "
                             "Đổi BSC_RPC_KEY sang tài khoản khác rồi chạy lại đúng lệnh; "
                             "các vụ đã đo được giữ nguyên.") from e
        ghi_dong(ra, d)
        print(f"[{i}/{len(vus)}] {vu['pool']} t_m={vu['t_m']} alpha={d['alpha_symbol']} be_ngoai={d['so_be_ngoai']} "
              f"ty_le={d['ty_le_alpha_ngoai']} {d['ghi_chu']}")
    if ra.exists():
        tom_tat(ra)


if __name__ == "__main__":
    main()

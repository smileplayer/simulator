"""Kế hoạch và lệnh tải log BSC của mọi vụ trong bảng 29 vụ của bài gốc, cộng bể đối chứng P1–P5.

Chạy từ `04_Simulator/` (cần node lưu trữ; đặt `BSC_RPC_URL`, `BSC_RPC_KEY` trong môi trường, không ghi vào mã):
    python -m scenarios.tai_vu_that --ke_hoach            # chỉ in kế hoạch, không gọi mạng
    python -m scenarios.tai_vu_that --nhanh               # 2.000 block đầu của đoạn đầu tiên, đo tốc độ
    python -m scenarios.tai_vu_that [--chi_vu | --chi_doi_chung]

Vụ: mỗi bể một hay nhiều đoạn [min t_m − đệm_trước, max t_b + đệm_sau] (tách khi hai vụ cách nhau > 400.000 block),
ghi vào `ket_qua/that/vu/<pool[:10]>_<tu>/`. Đối chứng: mỗi bể P1–P5 ba đoạn 14 ngày (đầu, giữa, cuối khoảng thời gian
của 29 vụ), ghi vào `ket_qua/that/doi_chung/<alias>_<tu>/`. Mỗi đoạn gọi `scenarios.lay_log_bsc.chay`, tự tiếp tục khi
chạy lại; đoạn đã xong thì bỏ qua. Lỗi mạng ghi vào `ket_qua/that/loi_tai.txt` rồi chuyển đoạn sau.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import pandas as pd

GOC = Path("ket_qua/that")
BANG_VU = Path(__file__).resolve().parents[2] / "00_Bai_goc" / "manual-validation-events-table.md"
BANG_DOI_CHUNG = Path(__file__).resolve().parents[2] / "00_Bai_goc" / "non-incentivized-pool-aliases.md"
KHOANG_TACH = 400_000          # block; hai vụ cùng bể cách nhau hơn mức này thì tải hai đoạn riêng
NGAY_DOI_CHUNG = 14            # ngày mỗi đoạn đối chứng


def _o(s: str) -> str:
    return s.strip().strip("`").strip()


def doc_bang_vu(path: Path | str) -> pd.DataFrame:
    """Đọc bảng 29 vụ (markdown): pool (chữ thường), tick_lower, tick_upper, t_m, t_b (block), n_victim, wall_provider, vu_id."""
    rows = []
    for dong in Path(path).read_text(encoding="utf-8").splitlines():
        if not dong.startswith("| `0x"):
            continue
        c = [_o(x) for x in dong.strip().strip("|").split("|")]
        rows.append(dict(pool=c[0].lower(), tick_lower=int(c[1]), tick_upper=int(c[2]), t_m=int(c[3]), t_b=int(c[5]),
                         n_victim=int(c[7]), wall_provider=c[8].lower()))
    d = pd.DataFrame(rows, columns=["pool", "tick_lower", "tick_upper", "t_m", "t_b", "n_victim", "wall_provider"])
    d["vu_id"] = d["pool"].str[:6] + "_" + d["tick_lower"].astype(str)
    return d


def doc_doi_chung(path: Path | str) -> pd.DataFrame:
    """Đọc bảng bí danh bể đối chứng (markdown): cột `alias` (P1…P5) và `pool` (địa chỉ chữ thường)."""
    rows = []
    for dong in Path(path).read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`(P\d+)`\s*\|\s*`(0x[0-9a-fA-F]{40})`", dong)
        if m:
            rows.append(dict(alias=m.group(1), pool=m.group(2).lower()))
    return pd.DataFrame(rows, columns=["alias", "pool"])


def ke_hoach(vu: pd.DataFrame, doi_chung: pd.DataFrame, dem_truoc_gio: float = 72, dem_sau_gio: float = 48,
             giay_block: float = 0.75, goc: Path = GOC) -> list[dict]:
    """Danh sách đoạn cần tải (block): mỗi dict có kieu ('vu'|'doi_chung'), ten, pool, tu, den, so_block, ra, vu_ids, so_vu.

    Giờ đổi sang block theo `giay_block` (giây mỗi block)."""
    gb = lambda gio: int(round(gio * 3600 / giay_block))
    dt, ds = gb(dem_truoc_gio), gb(dem_sau_gio)
    kq: list[dict] = []
    for pool, g in vu.groupby("pool", sort=False):
        g = g.sort_values("t_m")
        doan: list[list] = []
        for r in g.itertuples():
            if doan and r.t_m - doan[-1][1] <= KHOANG_TACH:
                doan[-1][1] = max(doan[-1][1], r.t_b)
                doan[-1][2].append(r.vu_id)
            else:
                doan.append([r.t_m, r.t_b, [r.vu_id]])
        for tm, tb, ids in doan:
            tu, den = max(0, tm - dt), tb + ds
            kq.append(dict(kieu="vu", ten=pool[:10], pool=pool, tu=tu, den=den, so_block=den - tu + 1,
                           ra=goc / "vu" / f"{pool[:10]}_{tu}", vu_ids=ids, so_vu=len(ids)))
    if len(vu) and len(doi_chung):
        lo, hi, dai = int(vu["t_m"].min()), int(vu["t_b"].max()), gb(NGAY_DOI_CHUNG * 24)
        dau = [lo, (lo + hi - dai) // 2, hi - dai + 1]
        for r in doi_chung.itertuples():
            for tu in dau:
                den = tu + dai - 1
                kq.append(dict(kieu="doi_chung", ten=r.alias, pool=r.pool, tu=tu, den=den, so_block=dai,
                               ra=goc / "doi_chung" / f"{r.alias}_{tu}", vu_ids=[], so_vu=0))
    return kq


def _da_xong(ra: Path, den: int, tu: int | None = None, mau_moi: int | None = None, mau_dai: int | None = None) -> bool:
    """Đoạn đã tải xong: sự kiện LP tới `den` và swap tới `den` (hoặc tới hết mẫu swap cuối cùng nếu lấy mẫu)."""
    f = ra / "tien_do.json"
    if not f.exists():
        return False
    td = json.loads(f.read_text())
    het_swap = den
    if tu is not None and mau_moi and mau_dai:
        b_cuoi = tu + (den - tu) // mau_moi * mau_moi
        het_swap = min(b_cuoi + mau_dai - 1, den)
    return td.get("su_kien", -1) >= den and td.get("swap", -1) >= het_swap


def _in_ke_hoach(kh: list[dict]) -> None:
    d = pd.DataFrame(kh)[["kieu", "ten", "ra", "tu", "den", "so_block", "so_vu"]]
    d["ra"] = d["ra"].map(lambda p: Path(p).as_posix())
    print(d.to_string(index=False))
    print(f"Tổng: {len(kh)} đoạn, {int(d['so_block'].sum()):,} block "
          f"(vụ {int(d.loc[d.kieu == 'vu', 'so_block'].sum()):,}; đối chứng {int(d.loc[d.kieu == 'doi_chung', 'so_block'].sum()):,}); "
          f"ước ≈ {d['so_block'].sum() / 1_460_000 * 10 / 60:.1f} giờ nếu 1,46 triệu block mất 10 phút")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--chi_vu", action="store_true", help="chỉ tải các đoạn vụ")
    ap.add_argument("--chi_doi_chung", action="store_true", help="chỉ tải các đoạn đối chứng")
    ap.add_argument("--nhanh", action="store_true", help="chỉ 2.000 block đầu của đoạn đầu tiên (thư mục _nhanh)")
    ap.add_argument("--ke_hoach", action="store_true", help="chỉ in kế hoạch, không gọi mạng")
    ap.add_argument("--nghi", type=float, default=0.2, help="giây nghỉ giữa hai lần gọi RPC")
    ap.add_argument("--swap", default="mau", choices=["mau", "day_du", "khong"])
    ap.add_argument("--chi_pool", default=None, help="chỉ tải đoạn của các bể có địa chỉ bắt đầu bằng một trong các tiền tố này, cách nhau dấu phẩy (vd. 0x985c205b,0x430d8186); dùng để chia phần còn lại giữa các cửa sổ, không dùng chung với --phan")
    ap.add_argument("--phan", default=None, help="i/n: chỉ tải các đoạn thứ i, i+n, i+2n… (đánh số từ 1), để chạy n cửa sổ song song, mỗi cửa sổ một khóa RPC")
    ap.add_argument("--rpc", default=None, help="URL RPC cho riêng cửa sổ này (ưu tiên hơn biến môi trường BSC_RPC_URL)")
    a = ap.parse_args()
    from scenarios import lay_log_bsc as L

    gb = L.CHUOI["bsc"]["giay_block"]
    kh = ke_hoach(doc_bang_vu(BANG_VU), doc_doi_chung(BANG_DOI_CHUNG), giay_block=gb)
    if a.chi_vu:
        kh = [k for k in kh if k["kieu"] == "vu"]
    if a.chi_doi_chung:
        kh = [k for k in kh if k["kieu"] == "doi_chung"]
    if a.chi_pool:
        tien_to = tuple(x.strip().lower() for x in a.chi_pool.split(",") if x.strip())
        kh = [k for k in kh if k["pool"].lower().startswith(tien_to)]
    if a.phan:
        i_phan, n_phan = (int(x) for x in a.phan.split("/"))
        if not 1 <= i_phan <= n_phan:
            ap.error("--phan phải dạng i/n với 1 ≤ i ≤ n")
        kh = kh[i_phan - 1::n_phan]
    if a.ke_hoach:
        _in_ke_hoach(kh)
        return
    mau_moi, mau_dai = round(3600 / gb), max(3, round(30 / gb))
    rpc = L.RPC(L.url_rpc("bsc", a.rpc), a.nghi)
    if a.nhanh:
        kh = [dict(kh[0], den=kh[0]["tu"] + 1999, ra=kh[0]["ra"].parent / (kh[0]["ra"].name + "_nhanh"))]
    GOC.mkdir(parents=True, exist_ok=True)
    for i, k in enumerate(kh, 1):
        print(f"=== đoạn {i}/{len(kh)}: {k['kieu']} {k['ten']} block {k['tu']}–{k['den']} → {k['ra']}")
        if _da_xong(k["ra"], k["den"], k["tu"], mau_moi if a.swap == "mau" else None, mau_dai):
            print("đã xong, bỏ qua")
            continue
        try:
            L.chay(k["pool"], k["tu"], k["den"], k["ra"], rpc, a.swap, 5000, mau_moi, mau_dai)
        except L.HetHanMuc as e:
            msg = f"{time.strftime('%Y-%m-%d %H:%M:%S')} đoạn {k['ra']}: HẾT HẠN MỨC / KHÓA HỎNG: {e}"
            print("DỪNG:", msg)
            with (GOC / "loi_tai.txt").open("a", encoding="utf-8") as f:
                f.write(msg + "\n")
            raise SystemExit("Có vẻ khóa này hết hạn mức. Đổi BSC_RPC_KEY sang tài khoản khác rồi chạy lại đúng lệnh; "
                             "phần đã tải được giữ nguyên.")
        except Exception as e:   # noqa: BLE001 — lỗi mạng/RPC: ghi lại, chuyển đoạn sau
            msg = f"{time.strftime('%Y-%m-%d %H:%M:%S')} đoạn {k['ra']}: {e}"
            print("LỖI:", msg)
            with (GOC / "loi_tai.txt").open("a", encoding="utf-8") as f:
                f.write(msg + "\n")


if __name__ == "__main__":
    main()

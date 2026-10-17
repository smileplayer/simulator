"""Bảng GĐ2 (RQ2) bằng một lệnh: `python -m metrics.chay_gd2 [--gd2 ket_qua/gd2] [--B 2000] [--nhanh]`.

**v4** đọc `tomtat_v4.csv` (16 bp × victim), `tomtat_knho_v4.csv` (vùng k nhỏ, farm 0,3),
`tomtat_farm_v4.csv` (× farm_share), `tomtat_luoi_v4.csv` (lưới σ × Q) → `ket_qua/gd2/bang/`. v4 sửa phản thực
bán thẳng của v3 (farmer trong pha xả tối ưu lại trên bể phản thực). Tệp:
`danh_doi*.csv` (bảng dài: hiệu cặp so với `khong`, CI, % thay đổi), `gon*.csv` (bảng rộng), `ty_le_sap*.csv`,
`q_sao_vu*.csv`, `q_sao_tomtat*.csv`, `don_dieu_gop*.csv` / `don_dieu_vu*.csv` (kiểm
đơn điệu theo trần, Theorem 6), `ba_vung.csv`, `luoi_gia_dinh.csv` (kiểm Giả định 1–2: chạy lại 25 ô ×
2 victim × 2 bp × 3 seed ≈ 10 s, lần sau đọc lại file; xóa file để chạy lại).
(Bộ v1, v2, v3 đã xóa ngày 17/10/2026; còn trong lịch sử git. Tham số `phien` giữ để đọc bộ khác cùng cấu trúc nếu chạy lại.)
`--nhanh`: B = 200.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd

from metrics.gd2 import (ba_vung, bang_danh_doi, bang_gon, kiem_don_dieu, kiem_gia_dinh, q_sao_vu, them_cot,
                         tom_tat_q_sao, ty_le_sap)


def chay_gia_dinh(seeds=(0, 1, 2), bps=("khong", "cap50")) -> pd.DataFrame:
    """Chạy lại các ô lưới `--luoi` của C (không ghi log) và đo `kiem_gia_dinh` cho mỗi lượt."""
    from scenarios.quet_gd2 import BIEN_PHAP, cau_hinh, to_hop_luoi
    from scenarios.run import run_frame
    dong = []
    for v in to_hop_luoi():
        for bp in bps:
            for vt in ("omniscient", "adaptive"):
                for s in seeds:
                    cfg = cau_hinh(v)
                    cfg.update(defense=BIEN_PHAP[bp], victim_type=vt, attacker_farm_share=0.0)
                    dong.append(dict(sigma=v["sigma"], Q=v["Q"], bp=bp, victim_type=vt, seed=s,
                                     **kiem_gia_dinh(run_frame(cfg, s))))
    return pd.DataFrame(dong)


def _ghi(out: dict, ra: Path) -> list[Path]:
    """Ghi mỗi bảng thành `ra/<tên>.csv`."""
    ra.mkdir(parents=True, exist_ok=True)
    files = []
    for ten, bang in out.items():
        f = ra / f"{ten}.csv"
        bang.to_csv(f, index=False)
        files.append(f)
    return files


def main(gd2: str = "ket_qua/gd2", B: int = 2000, ra: str | None = None, phien: str = "v4") -> list[Path]:
    """Bảng cho bộ `_v4` (→ `bang/`; phiên khác cùng cấu trúc → `bang_<phien>/`). Trả danh sách file."""
    d = Path(gd2)
    ra = Path(ra) if ra else d / ("bang" if phien == "v4" else f"bang_{phien}")
    tt = them_cot(pd.read_csv(d / f"tomtat_{phien}.csv"))
    kn = them_cot(pd.read_csv(d / f"tomtat_knho_{phien}.csv"))
    fm = them_cot(pd.read_csv(d / f"tomtat_farm_{phien}.csv"))
    lu = them_cot(pd.read_csv(d / f"tomtat_luoi_{phien}.csv"))
    t0 = time.time()
    out = {"danh_doi": bang_danh_doi(tt, ("victim_type",), B=B),
           "danh_doi_theo_dang": bang_danh_doi(tt, ("subsidy_form", "victim_type"), B=B),
           "danh_doi_knho": bang_danh_doi(kn, ("victim_type",), B=B),
           "danh_doi_knho_theo_k": bang_danh_doi(kn, ("k", "victim_type"), B=B),
           "danh_doi_farm": bang_danh_doi(fm, ("farm_share", "victim_type"), B=B)}
    print(f"bảng đánh đổi: {time.time() - t0:.0f} s")
    out["gon"] = bang_gon(out["danh_doi"])
    out["gon_theo_dang"] = bang_gon(out["danh_doi_theo_dang"], ("subsidy_form", "victim_type"))
    out["gon_knho"] = bang_gon(out["danh_doi_knho"])
    out["gon_knho_theo_k"] = bang_gon(out["danh_doi_knho_theo_k"], ("k", "victim_type"))
    out["gon_farm"] = bang_gon(out["danh_doi_farm"], ("farm_share", "victim_type"))
    out["ty_le_sap"] = ty_le_sap(tt, B=B)
    out["ty_le_sap_knho"] = ty_le_sap(kn, B=B)
    out["ty_le_sap_farm"] = ty_le_sap(fm, ("farm_share", "victim_type"), B=B)
    out["q_sao_vu"] = q_sao_vu(tt)
    out["q_sao_tomtat"] = tom_tat_q_sao(out["q_sao_vu"])
    out["q_sao_vu_knho"] = q_sao_vu(kn)
    out["q_sao_tomtat_knho"] = tom_tat_q_sao(out["q_sao_vu_knho"])
    out["don_dieu_gop"], out["don_dieu_vu"] = kiem_don_dieu(tt, B=B)
    out["don_dieu_gop_knho"], out["don_dieu_vu_knho"] = kiem_don_dieu(kn, B=B)
    f_gd = ra / "luoi_gia_dinh.csv"
    gd = pd.read_csv(f_gd) if f_gd.exists() else chay_gia_dinh()
    out["luoi_gia_dinh"] = gd
    out["ba_vung"] = ba_vung(lu, gd)
    return _ghi(out, ra)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gd2", default="ket_qua/gd2")
    ap.add_argument("--phien", default="v4")
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--nhanh", action="store_true")
    a = ap.parse_args()
    B = 200 if a.nhanh else a.B
    files = main(a.gd2, B, phien=a.phien)
    for f in files:
        print(f)

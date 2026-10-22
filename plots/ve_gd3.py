"""Sinh hình GĐ3 bằng một lệnh: `python -m plots.ve_gd3 [--gd3 ket_qua/gd3]` (≈ vài giây).

Cần chạy `python -m metrics.chay_gd3` trước (đọc `ket_qua/gd3/bang/`). Ghi `ket_qua/gd3/hinh/`: `ban_do_vung.png`,
`theo_alpha.png`, `lp_lanh_manh.png`; có `so_sanh_wA.csv` (kẻ tấn công nới tường) → thêm `theo_wA.png`,
`so_sanh_wA.png`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from plots.hinh import in_bai
from plots.hinh_gd3 import ve_ban_do_vung, ve_lp, ve_so_sanh_wA, ve_theo_alpha, ve_theo_wA


def main(gd3: str = "ket_qua/gd3") -> list[Path]:
    """Vẽ 3 hình, trả danh sách đường dẫn."""
    d = Path(gd3)
    bang, ra = d / "bang", d / "hinh"
    ra.mkdir(parents=True, exist_ok=True)
    gon = pd.read_csv(bang / "gon.csv")
    f = [ra / "ban_do_vung.png", ra / "theo_alpha.png", ra / "lp_lanh_manh.png"]
    ve_ban_do_vung(pd.read_csv(bang / "doi_chieu_giai_tich.csv"), gon, f[0])
    ve_theo_alpha(gon, f[1])
    ve_lp(gon, f[2])
    if (bang / "so_sanh_wA.csv").exists():
        f += [ra / "theo_wA.png", ra / "so_sanh_wA.png"]
        ve_theo_wA(pd.read_csv(bang / "wA_trung_vi.csv"), pd.read_csv(bang / "gon_wA.csv"), f[3])
        with in_bai():                                          # hình bài báo: đúng khổ in LNCS
            ve_so_sanh_wA(pd.read_csv(bang / "so_sanh_wA.csv"), f[4])
    return f


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gd3", default="ket_qua/gd3")
    a = ap.parse_args()
    for p in main(a.gd3):
        print(p)

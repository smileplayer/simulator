"""Sinh hình GĐ3 bằng một lệnh: `python -m plots.ve_gd3 [--gd3 ket_qua/gd3]` (≈ vài giây).

Cần chạy `python -m metrics.chay_gd3` trước (đọc `ket_qua/gd3/bang/`). Ghi `ket_qua/gd3/hinh/`: `ban_do_vung.png`,
`theo_alpha.png`, `lp_lanh_manh.png`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from plots.hinh_gd3 import ve_ban_do_vung, ve_lp, ve_theo_alpha


def main(gd3: str = "ket_qua/gd3") -> list[Path]:
    """Vẽ 3 hình, trả danh sách đường dẫn."""
    d = Path(gd3)
    bang, ra = d / "bang", d / "hinh"
    ra.mkdir(parents=True, exist_ok=True)
    gon = pd.read_csv(bang / "gon.csv")
    f = [ra / "ban_do_vung.png", ra / "theo_alpha.png", ra / "lp_lanh_manh.png"]
    ve_ban_do_vung(pd.read_csv(bang / "doi_chieu_giai_tich.csv"), gon, f[0],
                   "Range-aware φ = min(1, (w/w₀)^α): khi nào giảm vốn victim (so với pro-rata, 10 seed/ô)")
    ve_theo_alpha(gon, f[1], "Lợi kẻ tấn công và lãi victim theo α (so với pro-rata cùng vụ + seed)")
    ve_lp(gon, f[2], "Cái giá với LP lành mạnh (vốn 1.000 token1, pha bình thường)")
    return f


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gd3", default="ket_qua/gd3")
    a = ap.parse_args()
    for p in main(a.gd3):
        print(p)

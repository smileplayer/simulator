"""Sinh mọi hình GĐ2 bằng một lệnh: `python -m plots.ve_gd2 [--phien v4|v3] [--gd2 ket_qua/gd2]` (≈ vài giây).

Cần chạy `python -m metrics.chay_gd2 [--phien ...]` trước. v4 (mặc định; v3 → `bang_v3/`, `hinh_v3/`) đọc `ket_qua/gd2/bang/`, ghi
`ket_qua/gd2/hinh/`: `pareto.png` (biên đánh đổi, vùng RQ1 + k nhỏ), `danh_doi_farm.png`, `ba_vung.png`
(bản đồ σ × Q), `q_sao.png`, `q_sao_knho.png`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from plots.hinh_gd2 import ve_ba_vung, ve_danh_doi_farm, ve_pareto, ve_q_sao

TD_FARM = "Trả trễ / thu hồi khi kẻ tấn công cũng farm (so với không biện pháp cùng phần farm)"


def main(gd2: str = "ket_qua/gd2", phien: str = "v4") -> list[Path]:
    """Vẽ bộ hình v4 (`bang/` → `hinh/`) hoặc v3 (`bang_v3/` → `hinh_v3/`), trả danh sách đường dẫn."""
    d = Path(gd2)
    hau = "" if phien == "v4" else f"_{phien}"
    bang, ra = d / f"bang{hau}", d / f"hinh{hau}"
    ra.mkdir(parents=True, exist_ok=True)
    f = {k: ra / f"{k}.png" for k in ("pareto", "danh_doi_farm", "ba_vung", "q_sao", "q_sao_knho")}
    ve_pareto({"vùng RQ1 (k ∈ {0,64; 0,80; 0,95}, nạn nhân nhỏ)": pd.read_csv(bang / "danh_doi.csv"),
               "vùng k nhỏ (k ∈ {0,10; 0,25; 0,45}, nạn nhân lớn, kẻ tấn công farm 0,3)":
                   pd.read_csv(bang / "danh_doi_knho.csv")},
              f["pareto"], "Biên đánh đổi: biện pháp so với không biện pháp (30 vụ × 10 seed, CI 95% bootstrap cặp)")
    fm = pd.read_csv(bang / "danh_doi_farm.csv")
    ve_danh_doi_farm(fm[fm["farm_share"] > 0], f["danh_doi_farm"], TD_FARM)
    ve_ba_vung(pd.read_csv(bang / "ba_vung.csv"), f["ba_vung"],
               "Ba vùng thiết kế trên lưới (σ, Q) quanh co_so (c_V cố định, 10 seed/ô)")
    ve_q_sao(pd.read_csv(bang / "q_sao_vu.csv"), f["q_sao"],
             "Ngưỡng trần làm nạn nhân rút r_V = Q*_V/Q — vùng RQ1 (lưới cap 9 mức)")
    ve_q_sao(pd.read_csv(bang / "q_sao_vu_knho.csv"), f["q_sao_knho"],
             "Ngưỡng trần làm nạn nhân rút r_V = Q*_V/Q — vùng k nhỏ (lưới cap 4 mức)")
    return list(f.values())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gd2", default="ket_qua/gd2")
    ap.add_argument("--phien", default="v4", choices=["v4", "v3"])
    a = ap.parse_args()
    for p in main(a.gd2, a.phien):
        print(p)

"""Sinh mọi hình GĐ2 bằng một lệnh: `python -m plots.ve_gd2 [--gd2 ket_qua/gd2]` (≈ vài giây).

Cần chạy `python -m metrics.chay_gd2` trước (đọc `ket_qua/gd2/bang/*.csv`). Ghi PNG vào `ket_qua/gd2/hinh/`:
`danh_doi.png`, `danh_doi_farm.png`, `nhiet_sigma_Q.png`, `q_sao.png`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from plots.hinh_gd2 import ve_danh_doi, ve_danh_doi_farm, ve_nhiet, ve_q_sao


def main(gd2: str = "ket_qua/gd2") -> list[Path]:
    """Vẽ 4 hình, trả danh sách đường dẫn."""
    d = Path(gd2)
    ra = d / "hinh"
    ra.mkdir(parents=True, exist_ok=True)
    bang = d / "bang"
    files = [ra / "danh_doi.png", ra / "danh_doi_farm.png", ra / "nhiet_sigma_Q.png", ra / "q_sao.png"]
    ve_danh_doi(pd.read_csv(bang / "danh_doi.csv"), files[0],
                "Đánh đổi của biện pháp (so với không biện pháp, 30 vụ × 10 seed, CI 95% bootstrap cặp theo vụ)")
    fm = pd.read_csv(bang / "danh_doi_farm.csv")
    ve_danh_doi_farm(fm[fm["farm_share"] > 0], files[1],
                     "Trả trễ / thu hồi khi kẻ tấn công cũng farm (so với không biện pháp cùng phần farm)")
    ve_nhiet(pd.read_csv(d / "tomtat_v2.csv"), files[2],
             tieu_de="Không biện pháp: trung vị theo ô (σ, Q), trợ cấp tuyến tính, chỉ lượt sập ≥ 10%")
    ve_q_sao(pd.read_csv(bang / "q_sao_vu.csv"), files[3],
             "Ngưỡng trần làm victim không vào (nội suy Lemma 4 trên lưới cap)")
    return files


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gd2", default="ket_qua/gd2")
    a = ap.parse_args()
    for f in main(a.gd2):
        print(f)

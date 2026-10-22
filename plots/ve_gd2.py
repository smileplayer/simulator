"""Sinh mọi hình GĐ2 bằng một lệnh: `python -m plots.ve_gd2 [--gd2 ket_qua/gd2]` (≈ vài giây).

Cần chạy `python -m metrics.chay_gd2 [--phien ...]` trước. Đọc `ket_qua/gd2/bang/`, ghi
`ket_qua/gd2/hinh/`: `pareto.png` (biên đánh đổi, vùng RQ1 + k nhỏ), `danh_doi_farm.png`, `ba_vung.png`
(bản đồ σ × Q), `q_sao.png`, `q_sao_knho.png`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from plots.hinh import in_bai
from plots.hinh_gd2 import ve_ba_vung, ve_danh_doi_farm, ve_pareto, ve_q_sao


def main(gd2: str = "ket_qua/gd2", phien: str = "v4") -> list[Path]:
    """Vẽ bộ hình v4 (`bang/` → `hinh/`; phiên khác → `bang_<phien>/` → `hinh_<phien>/`), trả danh sách đường dẫn."""
    d = Path(gd2)
    hau = "" if phien == "v4" else f"_{phien}"
    bang, ra = d / f"bang{hau}", d / f"hinh{hau}"
    ra.mkdir(parents=True, exist_ok=True)
    f = {k: ra / f"{k}.png" for k in ("pareto", "danh_doi_farm", "ba_vung", "q_sao", "q_sao_knho")}
    with in_bai():                                              # hình bài báo: đúng khổ in LNCS
        ve_pareto({"(a) RQ1 region": pd.read_csv(bang / "danh_doi.csv"),
                   "(b) small-k region": pd.read_csv(bang / "danh_doi_knho.csv")}, f["pareto"])
    fm = pd.read_csv(bang / "danh_doi_farm.csv")
    ve_danh_doi_farm(fm[fm["farm_share"] > 0], f["danh_doi_farm"])
    ve_ba_vung(pd.read_csv(bang / "ba_vung.csv"), f["ba_vung"])
    ve_q_sao(pd.read_csv(bang / "q_sao_vu.csv"), f["q_sao"])
    ve_q_sao(pd.read_csv(bang / "q_sao_vu_knho.csv"), f["q_sao_knho"])
    return list(f.values())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gd2", default="ket_qua/gd2")
    ap.add_argument("--phien", default="v4")
    a = ap.parse_args()
    for p in main(a.gd2, a.phien):
        print(p)

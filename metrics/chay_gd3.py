"""Bảng GĐ3 (RQ3) bằng một lệnh: `python -m metrics.chay_gd3 [--gd3 ket_qua/gd3] [--B 2000] [--nhanh]`.

Đọc `ket_qua/gd3/tomtat.csv` (16 mức φ × 6 vụ × 2 victim × 10 seed), ghi `ket_qua/gd3/bang/`:
`danh_doi.csv` (bảng dài, so cặp với pro-rata), `gon.csv` (bảng rộng), `nen_tuong.csv` (L_A, B = L nền phủ tick
tường — chạy lại 6 lượt pro-rata seed 0 ≈ 3 s, lần sau đọc lại), `doi_chieu_giai_tich.csv` (tỷ lệ vốn mô phỏng vs
`agents.do_rong.ty_le_von`). Có `tomtat_wA.csv` (kẻ tấn công nới tường w_A) → thêm `wA_trung_vi.csv` (trung vị theo w_A),
`gon_wA1.csv` (tường 1 tick), `wA_toi_uu.csv` / `gon_wA.csv` / `danh_doi_wA.csv` (w_A tối ưu theo trung vị dc_excess
qua seed mỗi vụ/α/w₀/victim; bản `_theo_seed` chọn từng seed để đối chiếu), `so_sanh_wA.csv` (so với pro-rata tường
1 tick, cột `ty_le_von_giai_tich_wA` = 1/(4k(1/√k − 1)) khi k ≥ 1/4). `--nhanh`: B = 200.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd

from metrics.gd3 import (L_nen_tuong, bang_gd3, bang_gon_gd3, chon_w_A_toi_uu, chuan_bi, doi_chieu, so_sanh_wA,
                         ty_le_von_wA_giai_tich)


def chay_nen() -> pd.DataFrame:
    """Chạy lượt pro-rata seed 0 của mỗi vụ GĐ3, đo L_A và B (`L_nen_tuong`)."""
    from scenarios.quet_gd3 import cau_hinh_gd3, to_hop_gd3
    from scenarios.run import run_frame
    return pd.DataFrame([dict(scenario_id=v["id"], **L_nen_tuong(run_frame(cau_hinh_gd3(v, 0.0, 0, "omniscient"), 0)))
                         for v in to_hop_gd3()])


def main(gd3: str = "ket_qua/gd3", B: int = 2000) -> list[Path]:
    """Tính mọi bảng GĐ3, trả danh sách file đã ghi."""
    d = Path(gd3)
    ra = d / "bang"
    ra.mkdir(parents=True, exist_ok=True)
    tt = chuan_bi(pd.read_csv(d / "tomtat.csv"))
    t0 = time.time()
    dai = bang_gd3(tt, B=B)
    print(f"bảng so cặp: {time.time() - t0:.0f} s")
    gon = bang_gon_gd3(dai)
    f_nen = ra / "nen_tuong.csv"
    nen = pd.read_csv(f_nen) if f_nen.exists() else chay_nen()
    out = {"danh_doi": dai, "gon": gon, "nen_tuong": nen, "doi_chieu_giai_tich": doi_chieu(gon, nen)}
    f_wa = d / "tomtat_wA.csv"
    if f_wa.exists():                                   # kẻ tấn công nới tường: phản ứng tối ưu theo dc_excess
        wa = pd.read_csv(f_wa)
        out["wA_trung_vi"] = (wa.groupby(["scenario_id", "k", "victim_type", "alpha", "w0", "w_A"])
                              [["von_victim", "dc_excess", "vl_lai_tien", "do_sap", "w_victim"]].median().reset_index())
        mot = chuan_bi(wa[wa["w_A"] == 1])
        out["gon_wA1"] = bang_gon_gd3(bang_gd3(mot, B=B))
        for cach, hau in (("trung_vi", ""), ("theo_seed", "_theo_seed")):
            opt = chuan_bi(chon_w_A_toi_uu(wa, cach=cach))
            dai_wa = bang_gd3(opt, B=B)
            gon_wa = bang_gon_gd3(dai_wa)
            gon_wa["ty_le_von_giai_tich_wA"] = [ty_le_von_wA_giai_tich(k) for k in gon_wa["k"]]
            gon_wa = gon_wa.merge(opt.groupby(["scenario_id", "victim_type", "alpha", "w0"])["w_A_toi_uu"]
                                  .agg(lambda x: x.mode().iloc[0]).reset_index(), on=["scenario_id", "victim_type",
                                                                                     "alpha", "w0"], how="left")
            out["wA_toi_uu" + hau], out["danh_doi_wA" + hau], out["gon_wA" + hau] = opt, dai_wa, gon_wa
        out["so_sanh_wA"] = so_sanh_wA(out["gon_wA1"], out["gon_wA"])
    files = []
    for ten, bang in out.items():
        f = ra / f"{ten}.csv"
        bang.to_csv(f, index=False)
        files.append(f)
    return files


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gd3", default="ket_qua/gd3")
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--nhanh", action="store_true")
    a = ap.parse_args()
    for f in main(a.gd3, 200 if a.nhanh else a.B):
        print(f)

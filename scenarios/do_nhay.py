"""Độ nhạy RQ1 (CH, 15/10): chạy bộ 30 vụ × seed với các biến thể môi trường (`scenarios.batch.BIEN_THE`) rồi
kiểm định bằng hàm của B (chỉ gọi `metrics.chay_rq1.tom_tat_thu_muc`, `metrics.validate.validate_rq1`).

Log → `ket_qua/do_nhay/rq1_<biến thể>/` (như `rq1_tohop`), bảng → `ket_qua/do_nhay/{tomtat,kiemdinh}_<biến thể>.csv`,
bảng gộp `ket_qua/do_nhay/so_sanh.csv` (dấu hiệu × biến thể, gồm bộ gốc đọc từ `ket_qua/rq1_tohop/`).
Chạy: `python -m scenarios.do_nhay [--seeds 10] [--bien_the vol vol_prep vol_post f001]` (bỏ qua log đã có).
"""
from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import pandas as pd

from scenarios.batch import chay

RA = Path("ket_qua/do_nhay")
THU_MUC = {"goc": Path("ket_qua/rq1_tohop")}


def kiem_dinh(ten: str, vao: Path) -> pd.DataFrame:
    """Tóm tắt + kiểm định một thư mục log; ghi tomtat_/kiemdinh_<ten>.csv, trả bảng kiểm định."""
    from metrics.chay_rq1 import tom_tat_thu_muc
    from metrics.validate import validate_rq1
    tt = tom_tat_thu_muc(vao)
    kd = validate_rq1(tt)
    tt.to_csv(RA / f"tomtat_{ten}.csv", index=False, encoding="utf-8-sig")
    kd.to_csv(RA / f"kiemdinh_{ten}.csv", index=False, encoding="utf-8-sig")
    return kd


def main(seeds: int, bien_the: list[str]) -> pd.DataFrame:
    """Chạy log còn thiếu cho từng biến thể, kiểm định, gộp bảng so sánh với bộ gốc."""
    warnings.filterwarnings("ignore")
    RA.mkdir(parents=True, exist_ok=True)
    cot = {}
    for ten in ["goc", *bien_the]:
        vao = THU_MUC.get(ten, RA / f"rq1_{ten}")
        if ten != "goc":
            chay(seeds, vao, bien_the=ten)
        kd = kiem_dinh(ten, vao)
        cot[ten] = kd.set_index("dau_hieu")[["ty_le_mo_phong", "ket_qua"]]
    bang = pd.concat(cot, axis=1)
    bang.to_csv(RA / "so_sanh.csv", encoding="utf-8-sig")
    return bang


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--bien_the", nargs="+", default=["vol", "vol_prep", "vol_post", "f001"])
    a = ap.parse_args()
    print(main(a.seeds, a.bien_the).to_string())

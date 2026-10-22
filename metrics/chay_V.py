"""Độ nhạy cách ước V̂ của nạn nhân thích nghi (W15, 22/10/2026): `python -m metrics.chay_V [--gd2 ket_qua/gd2] [--B 2000]`.

Đọc `tomtat_V_v5.csv` (`scenarios.quet_gd2 --V --phien v5`). Với mỗi biến thể ước (goc, H72, H168, chi_mua, bo_arb) ghép
cặp từng biện pháp (cap50, cap05, warn40) với lượt `khong` CÙNG biến thể: % thay đổi lợi tăng thêm (CI bootstrap phân
cụm theo vụ) và tỷ lệ lượt còn nạn nhân (`LV_chia_LA` > 0,001) ở mỗi biện pháp, trên mọi lượt và trên lượt có sập.
→ `ket_qua/gd2/bang_V/V_do_nhay.csv`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from metrics.gd2 import _ma_tran_mau, ghep_cap, hieu_cap, them_cot
from metrics.validate import SEED_BOOT

BIEN_THE = ["goc", "H72", "H168", "chi_mua", "bo_arb"]
BIEN_PHAP = ["cap50", "cap05", "warn40"]
NGUONG_CON_VICTIM = 0.001


def ten_bp(bp: str, bt: str) -> str:
    """Tên biện pháp trong file: biến thể `goc` không hậu tố, còn lại `<bp>_<biến thể>`."""
    return bp if bt == "goc" else f"{bp}_{bt}"


def bang_V(df: pd.DataFrame, B: int = 2000) -> pd.DataFrame:
    """Một dòng mỗi (biến thể, biện pháp): % lợi tăng thêm (CI), tỷ lệ còn nạn nhân (mọi lượt / lượt có sập)."""
    d = them_cot(df)
    dong = []
    for bt in BIEN_THE:
        goc = ten_bp("khong", bt)
        for bp in BIEN_PHAP:
            P = ghep_cap(d, ten_bp(bp, bt), bp_goc=goc)
            if P.empty:
                continue
            mau = _ma_tran_mau(P["scenario_id"].to_numpy(), B, SEED_BOOT)
            r = hieu_cap(P, "loi_tang_them", False, "trung_vi", mau)
            con = P["LV_chia_LA"] > NGUONG_CON_VICTIM
            sap = P["breached"] > 0
            dong.append(dict(bien_the=bt, bp=bp, n_cap=r["n_cap"], loi_tang_them_goc=r["tk_goc"],
                             loi_tang_them_bp=r["tk_bp"], pct=r["pct"], pct_lo=r["pct_lo"], pct_hi=r["pct_hi"],
                             ty_le_con_victim=float(con.mean()),
                             ty_le_con_victim_khi_sap=float(con[sap].mean()) if sap.any() else float("nan"),
                             ty_le_con_victim_goc=float((P["LV_chia_LA_goc"] > NGUONG_CON_VICTIM).mean())))
    return pd.DataFrame(dong)


def main(gd2: str = "ket_qua/gd2", B: int = 2000) -> Path:
    """Ghi `bang_V/V_do_nhay.csv`, trả đường dẫn."""
    d = Path(gd2)
    ra = d / "bang_V"
    ra.mkdir(parents=True, exist_ok=True)
    f = ra / "V_do_nhay.csv"
    bang_V(pd.read_csv(d / "tomtat_V_v5.csv"), B).to_csv(f, index=False)
    return f


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gd2", default="ket_qua/gd2")
    ap.add_argument("--B", type=int, default=2000)
    a = ap.parse_args()
    print(main(a.gd2, a.B))

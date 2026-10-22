"""Bảng cải tiến G và F (22/10/2026): `python -m metrics.chay_GF [--gd2 ket_qua/gd2] [--B 2000] [--nhanh]`.

G (`tomtat_phat_v5.csv`): mỗi biện pháp phạt rút sớm ghép cặp với lượt gốc cùng kịch bản tấn công — `phat168`,
`phat336`, `phat168_lat10` với `khong`; `phat168_giu168` với `khong_giu168` (cùng t_0 kéo dài) — và cái giá của việc
giữ tường lâu: `khong_giu168` với `khong`. Chỉ số: lợi tăng thêm, lãi tổng kẻ tấn công (gồm phí tường), lợi nhuận
ròng nạn nhân, phí nạn nhân, khối lượng, trợ cấp, tỷ lệ sập; % = tỷ số trung bình trên cùng cặp (`metrics.gd2.hieu_cap`).

F (`tomtat_F_v5.csv`): `chon_LA` chọn độ dày tường tốt nhất cho kẻ tấn công theo trung vị lợi tăng thêm (mục tiêu
chính) hoặc lãi tổng; bảng đánh đổi trên các dòng được chọn, so với lượt `khong` cũng đã chọn; phân bố m được chọn.
→ `ket_qua/gd2/bang_GF/`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from metrics.gd2 import CHI_SO_V3, _ma_tran_mau, bang_danh_doi, chon_LA, ghep_cap, hieu_cap, them_cot
from metrics.validate import SEED_BOOT

CHI_SO_G = [
    ("loi_tang_them", False, "trung_vi"), ("dc_lai_tong", False, "trung_vi"), ("dc_excess", False, "trung_vi"),
    ("victim_net", True, "trung_vi"), ("victim_fees", True, "trung_vi"), ("vol_tong", False, "trung_vi"),
    ("subsidy_total", False, "trung_vi"), ("breached", False, "trung_binh"), ("phat_attacker", False, "trung_vi"),
    ("phat_tong", False, "trung_vi"),
]
CAP_G = [("phat168", "khong"), ("phat336", "khong"), ("phat168_lat10", "khong"),
         ("phat168_giu168", "khong_giu168"), ("khong_giu168", "khong")]


def bang_G(df: pd.DataFrame, B: int = 2000) -> pd.DataFrame:
    """Hiệu cặp và % thay đổi (CI 95% bootstrap phân cụm theo vụ) cho từng cặp (bp, gốc) × loại victim."""
    d = them_cot(df)
    dong = []
    for bp, goc in CAP_G:
        P_all = ghep_cap(d, bp, bp_goc=goc)
        for vt, P in P_all.groupby("victim_type"):
            mau = _ma_tran_mau(P["scenario_id"].to_numpy(), B, SEED_BOOT)
            for cot, can_sap, kieu in CHI_SO_G:
                if cot not in P:
                    continue
                r = hieu_cap(P, cot, can_sap, kieu, mau)
                dong.append(dict(bp=bp, goc=goc, victim_type=vt, chi_so=cot, **r))
    return pd.DataFrame(dong)


def bang_F(df: pd.DataFrame, muc_tieu: str = "loi_tang_them", B: int = 2000) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(bảng đánh đổi trên mức L_A kẻ tấn công chọn, phân bố m được chọn theo bp × victim)."""
    c = chon_LA(df, muc_tieu)
    chi_so = [x for x in CHI_SO_V3 if x[0] in ("loi_tang_them", "dc_lai_tong", "victim_net", "vol_tong",
                                                 "subsidy_total", "breached", "LV_chia_LA")]
    dd = bang_danh_doi(c, ("victim_type",), chi_so=chi_so, B=B)
    dd.insert(0, "muc_tieu", muc_tieu)
    pb = (c.drop_duplicates(["scenario_id", "bp", "victim_type"])
            .groupby(["bp", "victim_type"]).m_LA_chon.value_counts().unstack(fill_value=0).reset_index())
    pb.insert(0, "muc_tieu", muc_tieu)
    return dd, pb


def main(gd2: str = "ket_qua/gd2", B: int = 2000) -> list[Path]:
    """Ghi `bang_GF/G_danh_doi.csv`, `F_danh_doi.csv`, `F_m_chon.csv`, `F_co_dinh.csv` (m = 1, đối chứng)."""
    d = Path(gd2)
    ra = d / "bang_GF"
    ra.mkdir(parents=True, exist_ok=True)
    out = {"G_danh_doi": bang_G(pd.read_csv(d / "tomtat_phat_v5.csv"), B)}
    F = them_cot(pd.read_csv(d / "tomtat_F_v5.csv"))
    dd1, pb1 = bang_F(F, "loi_tang_them", B)
    dd2, pb2 = bang_F(F, "dc_lai_tong", B)
    out["F_danh_doi"] = pd.concat([dd1, dd2])
    out["F_m_chon"] = pd.concat([pb1, pb2])
    co_dinh = F[F.m_LA == 1.0]
    chi_so = [x for x in CHI_SO_V3 if x[0] in ("loi_tang_them", "victim_net", "vol_tong")]
    out["F_co_dinh"] = bang_danh_doi(co_dinh, ("victim_type",), chi_so=chi_so, B=B)
    files = []
    for ten, bang in out.items():
        f = ra / f"{ten}.csv"
        bang.to_csv(f, index=False)
        files.append(f)
    return files


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gd2", default="ket_qua/gd2")
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--nhanh", action="store_true")
    a = ap.parse_args()
    for f in main(a.gd2, 200 if a.nhanh else a.B):
        print(f)

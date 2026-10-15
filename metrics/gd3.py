"""Đo lường GĐ3 (RQ3): range-aware φ(w) = min(1, (w/w₀)^α) so với pro-rata (α = 0).

Cặp phản thực = cùng `scenario_id` + `seed` + `victim_type`, mức φ − pro-rata (`bp` = "khong" cho α = 0, "a<α>_w<w₀>"
cho mức khác) → dùng lại `metrics.gd2.bang_danh_doi` (bootstrap cặp; mỗi nhóm một vụ nên thực chất lấy lại seed).
Tỷ lệ vốn victim mô phỏng C_RA/C_PR = 1 + pct/100 của `von_victim` (tỷ số trung bình cặp).

Đối chiếu giải tích (vai C, `agents.do_rong.ty_le_von`): C_RA/C_PR = (√(u/k) − u)/(1/√k − 1), với
u = [ℓ(1)/(φ(w*)·ℓ(w*))]·[(L_A·φ(1) + B)/(L_A + B)], ℓ(w) = L trên mỗi token1 vốn ở dải w tick căn giữa (hình học
CLMM thật), B = thanh khoản LP nền phủ tick tường (φ = 1 vì dải rộng ≥ w₀). Với w* = w₀, B ≪ L_A:
u ≈ w₀^(1−α) + w₀·B/L_A (công thức của C). Range-aware giảm vốn victim ⇔ u > 1 hoặc u < (1/√k − 1)² — xem `vung`.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from metrics.gd2 import bang_danh_doi, bang_gon

KHOA_GD3 = ("scenario_id", "seed", "victim_type")

# (cột, nhóm, cần sập?, thống kê, mô tả + đơn vị)
CHI_SO_GD3 = [
    ("von_victim", "victim", False, "trung_vi", "vốn victim nạp (token1, theo giá trước khi rút tường)"),
    ("w_victim", "victim", False, "trung_vi", "độ rộng victim chọn (tick)"),
    ("LV_chia_LA", "victim", False, "trung_vi", "L victim trong tick tường / L_A"),
    ("phan_duong_sap", "victim", False, "trung_vi", "phần vốn victim bị cú sập quét qua (0–1)"),
    ("vl_lai_tien", "victim", False, "trung_vi", "lãi/lỗ victim: nhận lại + phí − nạp (token1, không cần t_b)"),
    ("vl_loss_full", "victim", True, "trung_vi", "thiệt hại victim so với ôm (token1, chỉ lượt sập)"),
    ("dc_excess", "tan_cong", False, "trung_vi", "lợi nhuận tăng thêm của kẻ tấn công (token1)"),
    ("dc_lai_tong", "tan_cong", False, "trung_vi", "lãi tổng kẻ tấn công theo địa chỉ (token1)"),
    ("do_sap", "tan_cong", False, "trung_vi", "độ dời giá khi xả (âm = sập)"),
    ("breached", "tan_cong", False, "trung_binh", "tỷ lệ có thiệt hại đo được (sập ≥ 10%)"),
    ("vol_tong", "chi_phi", False, "trung_vi", "tổng khối lượng (token1)"),
    ("vol_farmer", "chi_phi", False, "trung_vi", "khối lượng farmer (token1)"),
    ("lp0_w", "lp", False, "trung_vi", "LP lành mạnh tự chọn: độ rộng (tick)"),
    ("lp0_phi_tren_von", "lp", False, "trung_vi", "LP tự chọn: phí / vốn mỗi cửa sổ"),
    ("lp1_phi_tren_von", "lp", False, "trung_vi", "LP dải cố định 10 tick: phí / vốn mỗi cửa sổ"),
    ("lp0_trong_dai", "lp", False, "trung_vi", "LP tự chọn: tỷ lệ bước giá trong dải"),
    ("lp0_L_gia", "lp", False, "trung_vi", "LP tự chọn: L tại giá (TB)"),
    ("lp0_truot", "lp", False, "trung_vi", "trượt giá lệnh mua 1.000 token1 khi có LP tự chọn"),
    ("lp1_truot", "lp", False, "trung_vi", "trượt giá lệnh mua 1.000 token1 khi có LP 10 tick"),
]


def ma_phi(alpha: float, w0: float) -> str:
    """Mã mức φ: α = 0 → "khong" (pro-rata, gốc so sánh), còn lại "a<α>_w<w₀>"."""
    return "khong" if alpha == 0 else f"a{alpha:g}_w{int(w0)}"


def chuan_bi(df: pd.DataFrame) -> pd.DataFrame:
    """Thêm `bp` (mã φ), `breached` (= có `vl_loss_full`, tức sập ≥ 10%) cho bảng `ket_qua/gd3/tomtat.csv`."""
    d = df.copy()
    d["bp"] = [ma_phi(a, w) for a, w in zip(d["alpha"], d["w0"])]
    d["breached"] = d["vl_loss_full"].notna().astype(float)
    return d


def bang_gd3(df: pd.DataFrame, B: int = 2000) -> pd.DataFrame:
    """Bảng dài: mỗi (vụ, k, victim, mức φ, chỉ số) → hiệu cặp so với pro-rata + CI, % thay đổi + CI; thêm cột
    `alpha`, `w0` và `ty_le` = 1 + pct/100 (tỷ số trung bình cặp, ví dụ C_RA/C_PR với `von_victim`)."""
    d = chuan_bi(df) if "bp" not in df else df
    dai = bang_danh_doi(d, ("scenario_id", "k", "victim_type"), chi_so=CHI_SO_GD3, B=B)
    ma = d.drop_duplicates("bp").set_index("bp")[["alpha", "w0"]]
    dai = dai.join(ma, on="bp")
    for c in ("", "_lo", "_hi"):
        dai["ty_le" + c] = 1 + dai["pct" + c] / 100
    return dai


def bang_gon_gd3(dai: pd.DataFrame) -> pd.DataFrame:
    """Bảng rộng một dòng / (vụ, k, victim, α, w₀): tỷ lệ vốn [CI], w victim, phần trên đường sập, hiệu lãi victim,
    % dc_excess, hiệu độ sập (điểm %), % khối lượng, % phí/vốn của hai LP lành mạnh."""
    dong = []
    for (vu, k, vt, bp), g in dai.groupby(["scenario_id", "k", "victim_type", "bp"], sort=True):
        h = g.set_index("chi_so")
        r = dict(scenario_id=vu, k=k, victim_type=vt, alpha=h["alpha"].iloc[0], w0=h["w0"].iloc[0], bp=bp)
        v = h.loc["von_victim"]
        r |= dict(ty_le_von=v.ty_le, ty_le_von_lo=v.ty_le_lo, ty_le_von_hi=v.ty_le_hi,
                  w_victim=h.loc["w_victim", "tk_bp"], phan_duong_sap=h.loc["phan_duong_sap", "tk_bp"],
                  lai_victim_goc=h.loc["vl_lai_tien", "tk_goc"], lai_victim_hieu=h.loc["vl_lai_tien", "hieu"],
                  lai_victim_hieu_lo=h.loc["vl_lai_tien", "hieu_lo"], lai_victim_hieu_hi=h.loc["vl_lai_tien", "hieu_hi"],
                  dc_excess_goc=h.loc["dc_excess", "tk_goc"], dc_excess_pct=h.loc["dc_excess", "pct"],
                  dc_excess_pct_lo=h.loc["dc_excess", "pct_lo"], dc_excess_pct_hi=h.loc["dc_excess", "pct_hi"],
                  do_sap_hieu=h.loc["do_sap", "hieu"], vol_pct=h.loc["vol_tong", "pct"],
                  lp0_w=h.loc["lp0_w", "tk_bp"], lp0_phi_pct=h.loc["lp0_phi_tren_von", "pct"],
                  lp1_phi_pct=h.loc["lp1_phi_tren_von", "pct"], lp0_truot_pct=h.loc["lp0_truot", "pct"])
        dong.append(r)
    return pd.DataFrame(dong)


# ---------------------------------------------------------------- đối chiếu giải tích

def L_nen_tuong(df: pd.DataFrame) -> dict:
    """Từ log một lượt: tick tường (mint đầu của `attacker:0`), L_A, và B = Σ L của vị thế **không** thuộc
    attacker/victim/lp phủ tick tường ngay trước `t_rut` (đơn vị L)."""
    m = df.attrs["meta"]
    a = df[(df["kind"] == "mint") & (df["owner"] == "attacker:0")]
    lo, hi = int(a["tick_lower"].iloc[0]), int(a["tick_upper"].iloc[0])
    t_r = int(m["t_rut"])
    mb = df[df["kind"].isin(["mint", "burn"]) & (df["tick_lower"] <= lo) & (df["tick_upper"] >= hi) & (df["t"] < t_r)]
    mb = mb[~mb["owner"].astype(str).str.startswith(("attacker", "victim", "lp"))]
    B = float((np.where(mb["kind"] == "mint", 1.0, -1.0) * mb["liquidity"]).sum())
    return dict(wall_tick=lo, L_A=float(m["L_A"]), B=B)


def u_giai_tich(alpha: float, w0: float, w_sao: int, L_A: float, B: float, l_tren_von) -> float:
    """u = [ℓ(1)/(φ(w*)·ℓ(w*))]·[(L_A·φ(1) + B)/(L_A + B)] (không thứ nguyên); `l_tren_von(w)` → ℓ(w)."""
    phi = (lambda w: 1.0) if alpha == 0 else (lambda w: min(1.0, (w / w0) ** alpha))
    return l_tren_von(1) / (phi(w_sao) * l_tren_von(w_sao)) * (L_A * phi(1) + B) / (L_A + B)


TOL_VUNG = 0.01        # |C_RA/C_PR − 1| < 1% coi như không đổi


def vung(k: float, u: float, tol: float = TOL_VUNG) -> str:
    """Dự đoán của giải tích: "giam" nếu C_RA/C_PR < 1 − tol, "tang" nếu > 1 + tol, còn lại "bang"."""
    from agents.do_rong import ty_le_von
    r = ty_le_von(k, u)
    return "bang" if abs(r - 1) < tol else ("tang" if r > 1 else "giam")


def doi_chieu(gon: pd.DataFrame, nen: pd.DataFrame, z0: float | None = None) -> pd.DataFrame:
    """Đối chiếu tỷ lệ vốn mô phỏng (victim toàn tri) với `agents.do_rong.ty_le_von`. `nen`: mỗi vụ một dòng
    (`scenario_id`, `L_A`, `B`, `wall_tick`). w* lý thuyết = `w_sao_hinh_hoc` (lưới của C); u tính bằng cả w* lý
    thuyết và w thực chọn. Trả thêm `sai_so` = mô phỏng − giải tích, `sai_so_tuong_doi`, dự đoán vùng và khớp vùng."""
    from agents.do_rong import PhiLuyThua, l_tren_von, ty_le_von, w_sao_hinh_hoc
    from engine import sqrt_price_at_tick
    if z0 is None:
        z0 = sqrt_price_at_tick(0) * 1.0001 ** 0.25
    l = lambda w: l_tren_von(int(w), z0, 0)                                  # noqa: E731
    g = gon[(gon["victim_type"] == "omniscient")].merge(nen, on="scenario_id")
    dong = []
    for _, r in g.iterrows():
        phi = PhiLuyThua(r["alpha"], r["w0"])
        w_lt = w_sao_hinh_hoc(phi, z0, tick=0)
        u_lt = u_giai_tich(r["alpha"], r["w0"], w_lt, r["L_A"], r["B"], l)
        u_th = u_giai_tich(r["alpha"], r["w0"], int(round(r["w_victim"])), r["L_A"], r["B"], l)
        u_c = r["w0"] ** (1 - r["alpha"]) + r["w0"] * r["B"] / r["L_A"] if w_lt == r["w0"] else math.nan
        tl = ty_le_von(r["k"], u_lt)
        dong.append(dict(scenario_id=r["scenario_id"], k=r["k"], alpha=r["alpha"], w0=r["w0"], w_sao_ly_thuyet=w_lt,
                         w_thuc=r["w_victim"], u=u_lt, u_theo_w_thuc=u_th, u_cong_thuc_C=u_c,
                         nguong_u=(1 / math.sqrt(r["k"]) - 1) ** 2, ty_le_giai_tich=tl,
                         ty_le_mo_phong=r["ty_le_von"], ci_lo=r["ty_le_von_lo"], ci_hi=r["ty_le_von_hi"],
                         sai_so=r["ty_le_von"] - tl, sai_so_tuong_doi=(r["ty_le_von"] - tl) / tl if tl > 0 else math.nan,
                         vung_giai_tich=vung(r["k"], u_lt),
                         vung_mo_phong="bang" if abs(r["ty_le_von"] - 1) < TOL_VUNG else
                         ("tang" if r["ty_le_von"] > 1 else "giam")))
    out = pd.DataFrame(dong)
    out["khop_vung"] = out["vung_giai_tich"] == out["vung_mo_phong"]
    return out


# ---------------------------------------------------------------- kẻ tấn công nới tường (tomtat_wA.csv)

def cot_w_A(df: pd.DataFrame) -> str:
    """Tên cột độ rộng tường của kẻ tấn công trong bảng `tomtat_wA.csv` (`w_A` hoặc `w_attacker`)."""
    return next(c for c in ("w_A", "w_attacker", "w_tuong") if c in df.columns)


def chon_w_A_toi_uu(df: pd.DataFrame, cot: str = "dc_excess") -> pd.DataFrame:
    """Phản ứng tối ưu của kẻ tấn công: mỗi (vụ, α, w₀, victim, seed) giữ dòng có `cot` (token1) lớn nhất qua các
    độ rộng tường w_A; thêm `w_A_toi_uu`. Hòa → w_A nhỏ nhất. Pro-rata (α = 0) giữ nguyên các dòng w_A = 1."""
    w = cot_w_A(df)
    d = df.sort_values([*KHOA_GD3, "alpha", "w0", cot, w], ascending=[True] * 5 + [False, True])
    out = d.groupby(["scenario_id", "seed", "victim_type", "alpha", "w0"], sort=False).head(1).copy()
    out["w_A_toi_uu"] = out[w]
    return out.sort_values([*KHOA_GD3, "alpha", "w0"]).reset_index(drop=True)


def ty_le_von_wA_giai_tich(k: float) -> float:
    """Giải tích của C khi kẻ tấn công nới tường tối ưu: k ≥ 1/4 → C_RA/C_PR = 1/(4k(1/√k − 1)); k < 1/4 → 1."""
    return 1 / (4 * k * (1 / math.sqrt(k) - 1)) if k >= 0.25 else 1.0

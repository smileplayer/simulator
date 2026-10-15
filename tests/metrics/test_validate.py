import pandas as pd
import pytest

from metrics.report import summarize_many
import numpy as np

from metrics.validate import (BAI_GOC_DROP, BAI_GOC_LIFT, bang_chia_nhom, bootstrap_cap, bootstrap_ci,
                             validate_rq1)
from scenarios.fake_log import make_fake_log


@pytest.fixture(scope="module")
def tom_tat():
    return summarize_many([make_fake_log(s) for s in (0, 1, 2)])


def _kq(bang, dau_hieu, loai="chính"):
    return bang[(bang["dau_hieu"] == dau_hieu) & (bang["loai"] == loai)].iloc[0]


def test_cau_truc(tom_tat):
    b = validate_rq1(tom_tat)
    assert list(b.columns) == ["dau_hieu", "loai", "phat_bieu", "so_vu", "ty_le_mo_phong", "ci_lo", "ci_hi",
                               "ci_lo_cheo", "ci_hi_cheo", "ty_le_bai_goc", "trung_vi", "tv_ci_lo", "tv_ci_hi", "ket_qua"]
    assert set(b["ket_qua"]) <= {"Đạt", "Không đạt", "Chưa đo"}
    assert not b["phat_bieu"].str.contains("1–1,5|1.5", regex=True).any()      # đã bỏ tiêu chuẩn Prep
    assert b.attrs["n_vu"] == 3


def test_ty_le_bai_goc(tom_tat):
    b = validate_rq1(tom_tat)
    assert _kq(b, "Khối lượng Post dưới nền")["ty_le_bai_goc"] == pytest.approx(23 / 29)
    assert _kq(b, "Tường cạn tại t_b")["ty_le_bai_goc"] == pytest.approx(25 / 29)


def test_nhan_list_log_giong_bang_tom_tat(tom_tat):
    a = validate_rq1([make_fake_log(s) for s in (0, 1, 2)])
    assert a["ket_qua"].tolist() == validate_rq1(tom_tat)["ket_qua"].tolist()


def test_ket_qua_tren_log_gia(tom_tat):
    b = validate_rq1(tom_tat)
    assert _kq(b, "Có cú sập ≥ 10%")["ket_qua"] == "Đạt"
    assert _kq(b, "Khối lượng Attack bùng")["ket_qua"] == "Đạt"
    assert _kq(b, "Khối lượng Post dưới nền", "phụ")["ket_qua"] == "Đạt"      # lift_trade ≈ 0,8
    assert _kq(b, "Khối lượng Post dưới nền")["ket_qua"] == "Không đạt"       # vol_total gồm arb ≈ 1,1
    assert _kq(b, "Giá sập sau rút")["ket_qua"] == "Không đạt"                # VWAP ≈ −8%
    assert _kq(b, "Giá sập sau rút", "phụ")["ket_qua"] == "Đạt"               # trước burn ≈ −16%


def test_theo_phan_phoi(tom_tat):
    t = tom_tat.copy()
    t.loc[0, "lift_Post"] = 0.5
    t.loc[1, "lift_Post"] = 0.6
    r = _kq(validate_rq1(t), "Khối lượng Post dưới nền")
    assert r["ket_qua"] == "Đạt" and r["ty_le_mo_phong"] == pytest.approx(2 / 3)
    r2 = _kq(validate_rq1(t, ty_le_dat=0.9), "Khối lượng Post dưới nền")
    assert r2["ket_qua"] == "Không đạt"


def test_bang_chia_nhom(tom_tat):
    b = bang_chia_nhom(tom_tat)
    b4, b7 = b["bang4_lift"], b["bang7_drop"]
    assert list(b4.index) == ["<1×", "1–1.5×", "1.5–2×", "2–5×", ">5×"]
    assert b4["Attack_mo_phong"].sum() == 3 and b4.loc[">5×", "Attack_mo_phong"] == 3
    for k, v in BAI_GOC_LIFT.items():
        assert b4[f"{k}_bai_goc"].tolist() == v and sum(v) == 29
    assert b7["drop_bai_goc"].tolist() == BAI_GOC_DROP
    assert b7.loc["40–60%", "drop_mo_phong"] == 3                              # log giả: drop ≈ 0,5
    assert b["bang6_gia"]["attack_bai_goc"].sum() == 29


def test_nhom_bien():
    t = pd.DataFrame({"lift_Prep": [1.0, 0.999, 5.0], "lift_Attack": [1, 1, 1], "lift_Post": [1, 1, 1],
                      "lift_trade_Prep": [1, 1, 1], "lift_trade_Attack": [1, 1, 1], "lift_trade_Post": [1, 1, 1],
                      "before_price_change": [0, 0, 0], "attack_price_change": [0, 0, 0],
                      "attack_price_change_preburn": [0, 0, 0], "L_drop_at_tb": [1.0, 0.8, 0.79]})
    b = bang_chia_nhom(t)
    assert b["bang4_lift"]["Prep_mo_phong"].tolist() == [1, 1, 0, 0, 1]       # 1,0 → 1–1,5×; 5,0 → >5×
    assert b["bang7_drop"]["drop_mo_phong"].tolist() == [0, 0, 0, 1, 1, 1]


def test_ci_bao_quanh_ty_le(tom_tat):
    b = validate_rq1(tom_tat)
    d = b[b["ty_le_mo_phong"].notna()]
    assert (d["ci_lo"] <= d["ty_le_mo_phong"] + 1e-12).all() and (d["ty_le_mo_phong"] <= d["ci_hi"] + 1e-12).all()
    assert ((d["ci_lo"] >= 0) & (d["ci_hi"] <= 1)).all()
    assert validate_rq1(tom_tat, B=0)["ci_lo"].isna().all()


def _bang_vu(n_vu=30, n_seed=10, p_vu=None, seed=0):
    """Bảng giả: mỗi vụ có xác suất thỏa riêng (khác biệt giữa vụ lớn), seed là nhiễu nhỏ."""
    rng = np.random.default_rng(seed)
    p = rng.uniform(0, 1, n_vu) if p_vu is None else np.asarray(p_vu)
    rows = [dict(vu=f"v{i}", seed=j, y=float(rng.random() < p[i])) for i in range(n_vu) for j in range(n_seed)]
    return pd.DataFrame(rows)


def test_bootstrap_ci_tat_dinh_va_phan_cum():
    t = _bang_vu()
    a = bootstrap_ci(t, np.mean, cot="y", B=500)
    assert a == bootstrap_ci(t, np.mean, cot="y", B=500)                       # seed cố định
    assert a[0] < t["y"].mean() < a[1]
    # bỏ phân cụm (coi 300 dòng độc lập) → CI hẹp hơn hẳn: phương sai chủ yếu giữa vụ
    b = bootstrap_ci(t, np.mean, cot="y", B=500, cum=None)
    assert (a[1] - a[0]) > 1.5 * (b[1] - b[0])
    # 30 vụ, mỗi vụ thỏa trọn hoặc không (p = 0,5) → nửa độ rộng ≈ 1,96·√(0,25/30) ≈ 0,18
    c = bootstrap_ci(_bang_vu(p_vu=[1.0, 0.0] * 15), np.mean, cot="y", B=1000)
    assert 0.14 < (c[1] - c[0]) / 2 < 0.22
    # ham nhận DataFrame cũng chạy, cùng kết quả
    assert bootstrap_ci(t, lambda d: d["y"].mean(), B=500) == pytest.approx(a)


def test_bootstrap_cap():
    rng = np.random.default_rng(1)
    rows = []
    for i in range(20):
        nen = rng.normal(100, 30)                                              # khác biệt giữa vụ lớn
        for s in range(5):
            for bp, hieu in (("khong", 0.0), ("cap50", -10.0)):
                rows.append(dict(scenario_id=f"v{i}", seed=s, victim_type="omniscient", bp=bp,
                                 loi=nen + hieu + rng.normal(0, 1)))
    d = pd.DataFrame(rows)
    r = bootstrap_cap(d, "loi", "cap50", B=500)
    assert r["n_cap"] == 100 and r["n_vu"] == 20
    assert r["hieu"] == pytest.approx(-10, abs=0.5)
    assert r["ci_lo"] < -10 < r["ci_hi"] and r["ci_hi"] - r["ci_lo"] < 2       # ghép cặp khử phần giữa vụ
    assert bootstrap_cap(d, "loi", "khong_co", B=50)["n_cap"] == 0


def test_bootstrap_cheo_thay_yeu_to_seed_chung():
    """Seed dùng chung mọi vụ (cùng dòng ngẫu nhiên) → bootstrap chéo rộng hơn hẳn bootstrap lồng nhau."""
    rng = np.random.default_rng(3)
    hieu_seed = rng.normal(0, 1, 10)                                          # yếu tố seed chung
    rows = [dict(vu=f"v{i}", seed=j, y=hieu_seed[j] + 0.1 * rng.normal()) for i in range(30) for j in range(10)]
    t = pd.DataFrame(rows)
    a = bootstrap_ci(t, np.mean, cot="y", B=500)
    c = bootstrap_ci(t, np.mean, cot="y", B=500, cheo="seed")
    assert (c[1] - c[0]) > 2 * (a[1] - a[0])
    assert c[0] < t["y"].mean() < c[1]


def test_validate_co_ci_cheo():
    tt = summarize_many([make_fake_log(s) for s in (0, 1, 2, 3)])
    tt["vu"], tt["seed"] = ["a", "a", "b", "b"], [0, 1, 0, 1]
    b = validate_rq1(tt, B=200)
    d = b[b["ty_le_mo_phong"].notna()]
    assert d["ci_lo_cheo"].notna().all() and (d["ci_lo_cheo"] <= d["ci_hi_cheo"]).all()

import pandas as pd
import pytest

from metrics.report import summarize_many
from metrics.validate import BAI_GOC_DROP, BAI_GOC_LIFT, bang_chia_nhom, validate_rq1
from scenarios.fake_log import make_fake_log


@pytest.fixture(scope="module")
def tom_tat():
    return summarize_many([make_fake_log(s) for s in (0, 1, 2)])


def _kq(bang, dau_hieu, loai="chính"):
    return bang[(bang["dau_hieu"] == dau_hieu) & (bang["loai"] == loai)].iloc[0]


def test_cau_truc(tom_tat):
    b = validate_rq1(tom_tat)
    assert list(b.columns) == ["dau_hieu", "loai", "phat_bieu", "so_vu", "ty_le_mo_phong", "ty_le_bai_goc",
                               "trung_vi", "ket_qua"]
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

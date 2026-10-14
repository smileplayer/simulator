import pytest

from metrics.report import summarize_many
from metrics.validate import validate_rq1
from scenarios.fake_log import make_fake_log


@pytest.fixture(scope="module")
def tom_tat():
    return summarize_many([make_fake_log(s) for s in (0, 1, 2)])


def _kq(bang, dau_hieu, loai="chính"):
    return bang[(bang["dau_hieu"] == dau_hieu) & (bang["loai"] == loai)].iloc[0]


def test_cau_truc(tom_tat):
    b = validate_rq1(tom_tat)
    assert list(b.columns) == ["dau_hieu", "loai", "tieu_chuan", "gia_tri", "ty_le_vu", "ket_qua"]
    assert set(b["ket_qua"]) <= {"Đạt", "Không đạt", "Chưa đo"}
    assert b.attrs["n_vu"] == 3
    assert len(b) == 14


def test_nhan_list_log_giong_bang_tom_tat(tom_tat):
    a = validate_rq1([make_fake_log(s) for s in (0, 1, 2)])
    b = validate_rq1(tom_tat)
    assert a["ket_qua"].tolist() == b["ket_qua"].tolist()


def test_ket_qua_tren_log_gia(tom_tat):
    b = validate_rq1(tom_tat)
    assert _kq(b, "Có cú sập ≥ 10%")["ket_qua"] == "Đạt"
    assert _kq(b, "Chuẩn bị theo ngày")["gia_tri"] == 96
    assert _kq(b, "Khối lượng Attack bùng")["ket_qua"] == "Đạt"
    assert _kq(b, "Khối lượng Post dưới nền", "phụ")["ket_qua"] == "Đạt"      # lift_trade ≈ 0,8
    assert _kq(b, "Khối lượng Post dưới nền")["ket_qua"] == "Không đạt"       # vol_total gồm arb ≈ 1,1
    assert _kq(b, "Biến động Prep thấp hơn Attack")["ket_qua"] == "Đạt"


def test_dao_nguong_va_vu_le(tom_tat):
    t = tom_tat.copy()
    t.loc[0, "lift_Post"] = 0.5
    t.loc[1, "lift_Post"] = 0.6
    b = validate_rq1(t)
    r = _kq(b, "Khối lượng Post dưới nền")
    assert r["ket_qua"] == "Đạt" and r["ty_le_vu"] == pytest.approx(2 / 3)
    b2 = validate_rq1(tom_tat, nguong=dict(post_max=2.0))
    assert _kq(b2, "Khối lượng Post dưới nền")["ket_qua"] == "Đạt"

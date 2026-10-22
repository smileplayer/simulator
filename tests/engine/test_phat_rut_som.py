"""Cải tiến G (22/10): donate và phạt phí khi rút sớm, theo OpenZeppelin LiquidityPenaltyHook."""
import pytest

from engine import Pool, sqrt_price_at_tick

Z0 = sqrt_price_at_tick(0) * 1.0001 ** 0.25       # giữa tick 0


def _be(cua_so=None):
    p = Pool(0.003, Z0, phat_rut_som=cua_so)
    a, _, _ = p.mint("a", 0, 1, 1000.0)
    b, _, _ = p.mint("b", 0, 1, 3000.0)
    xa, _, _ = p.mint("x", 5, 6, 500.0)             # ngoài dải, không được chia
    return p, a, b, xa


def _giao_dich(p, n=6):
    phi = 0.0
    for i in range(n):
        r = p.swap("t", i % 2 == 0, amount_in=0.01)
        phi += r.fee
    return phi


def test_donate_chia_theo_L_trong_dai():
    p, a, b, xa = _be()
    assert p.donate("ai", 0.0, 4.0)
    assert p.fees_owed(a)[1] == pytest.approx(1.0)
    assert p.fees_owed(b)[1] == pytest.approx(3.0)
    assert p.fees_owed(xa) == (0.0, 0.0)


def test_donate_khi_khong_co_thanh_khoan_thi_mat():
    p = Pool(0.003, Z0)
    p.mint("x", 5, 6, 500.0)
    assert not p.donate("ai", 1.0, 1.0)
    assert p.log.rows[-1]["kind"] == "donate" and p.log.rows[-1]["liquidity_active_after"] == 0


def test_phat_ty_le_va_bao_toan_phi():
    p, a, b, _ = _be(cua_so=40)
    p.t = 0
    _giao_dich(p)
    phi_a0, phi_a1 = p.fees_owed(a)
    phi_b0, phi_b1 = p.fees_owed(b)
    p.t = 10                                       # giữ 10/40 bước → mất 75% phí
    p.burn(a)
    con0, con1 = p.collect(a)
    assert con0 == pytest.approx(0.25 * phi_a0) and con1 == pytest.approx(0.25 * phi_a1)
    nhan0, nhan1 = p.collect(b)                    # b nhận toàn bộ phần phạt (a đã rút hết)
    assert nhan0 == pytest.approx(phi_b0 + 0.75 * phi_a0)
    assert nhan1 == pytest.approx(phi_b1 + 0.75 * phi_a1)


def test_rut_ngoai_cua_so_khong_phat():
    p, a, _, _ = _be(cua_so=40)
    _giao_dich(p)
    phi = p.fees_owed(a)
    p.t = 40
    p.burn(a)
    assert p.collect(a) == pytest.approx(phi)
    assert not any(r["kind"] == "donate" for r in p.log.rows)


def test_tat_thi_nhu_cu():
    p, a, _, _ = _be(cua_so=None)
    _giao_dich(p)
    phi = p.fees_owed(a)
    p.t = 1
    p.burn(a)
    assert p.collect(a) == pytest.approx(phi)


def test_rut_tung_lat_phan_phat_chay_ve_phan_con_lai():
    """Cách né OZ tự cảnh báo: rút nửa đầu thì phần phạt chia cả cho nửa còn lại của chính mình."""
    p = Pool(0.003, Z0, phat_rut_som=40)
    a, _, _ = p.mint("a", 0, 1, 3000.0)
    b, _, _ = p.mint("b", 0, 1, 1000.0)
    _giao_dich(p)
    phi_a = p.fees_owed(a)[1]
    p.t = 10
    p.burn(a, 1500.0)                              # phạt 75%·phi_a, chia cho 1500 (a) + 1000 (b)
    phat = 0.75 * phi_a
    assert p.fees_owed(a)[1] == pytest.approx(0.25 * phi_a + phat * 1500 / 2500)
    p.burn(a)                                      # lần hai chỉ phạt phần mới nhận
    con_a = p.collect(a)[1]
    assert con_a == pytest.approx(0.25 * phi_a + 0.25 * phat * 1500 / 2500)

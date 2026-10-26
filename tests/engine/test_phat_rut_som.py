"""Cải tiến G (22/10): donate và phạt phí khi rút sớm, theo OpenZeppelin LiquidityPenaltyHook; giữ phí khi collect sớm (26/10)."""
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
    assert p.collect(b) == (0.0, 0.0)              # b chưa đủ tuổi: phí (kể cả phần được chia) còn bị giữ
    p.t = 40
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


def test_collect_truoc_burn_khong_ne_duoc_phat():
    """Lỗ hổng do Hoàng báo (26/10): collect trước rồi burn từng lấy được 100% phí."""
    p, a, b, _ = _be(cua_so=40)
    _giao_dich(p)
    phi_a, phi_b = p.fees_owed(a), p.fees_owed(b)
    p.t = 10
    truoc = p.collect(a)
    assert truoc == (0.0, 0.0)
    p.burn(a)
    sau = p.collect(a)
    assert sau == pytest.approx(tuple(0.25 * x for x in phi_a))
    p.t = 40
    assert p.collect(b) == pytest.approx(tuple(y + 0.75 * x for x, y in zip(phi_a, phi_b)))


def test_phi_bi_giu_tra_het_khi_du_tuoi():
    p, a, _, _ = _be(cua_so=40)
    _giao_dich(p)
    phi = p.fees_owed(a)
    p.t = 10
    assert p.collect(a) == (0.0, 0.0)
    assert p.fees_owed(a) == pytest.approx(phi)
    p.t = 40
    assert p.collect(a) == pytest.approx(phi)
    assert p.collect(a) == (0.0, 0.0)


def test_collect_sau_burn_khong_phat_hai_lan():
    p, a, _, _ = _be(cua_so=40)
    _giao_dich(p)
    phi = p.fees_owed(a)
    p.t = 10
    p.burn(a)
    assert p.collect(a) == pytest.approx(tuple(0.25 * x for x in phi))
    assert p.collect(a) == (0.0, 0.0)


@pytest.mark.parametrize("so_lat", [1, 2, 10])
def test_collect_xen_burn_tung_lat_bao_toan_phi(so_lat):
    """Collect xen giữa các lát burn: tổng phí trả ra (sau khi mọi vị thế đủ tuổi) = tổng phí giao dịch."""
    p, a, b, _ = _be(cua_so=40)
    _giao_dich(p)
    tong = tuple(x + y for x, y in zip(p.fees_owed(a), p.fees_owed(b)))
    p.t = 10
    da_tra = [0.0, 0.0]
    for _ in range(so_lat):
        for pid in (a, b):
            da_tra = [x + y for x, y in zip(da_tra, p.collect(pid))]
        p.burn(a, 1000.0 / so_lat)
    p.t = 40
    for pid in (a, b):
        da_tra = [x + y for x, y in zip(da_tra, p.collect(pid))]
    assert da_tra == pytest.approx(tong)
    assert all(x == pytest.approx(0) for pid in (a, b) for x in p.fees_owed(pid))


def test_fee_balances_chi_ghi_vi_the_con_phi():
    p, a, b, xa = _be(cua_so=40)
    _giao_dich(p)
    p.t = 10
    p.burn(a)
    p.collect(a)
    bang = {r["position_id"]: r for r in p.fee_balances()}
    assert set(bang) == {b}                        # a đã thu hết, x ngoài dải không có phí
    assert bang[b]["locked1"] == pytest.approx(bang[b]["owed1"])
    p.t = 40
    assert p.fee_balances()[0]["locked1"] == 0.0

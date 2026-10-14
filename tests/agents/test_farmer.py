"""Farmer: khớp nghiệm đóng Theorem 1 trên bể L hằng, không vượt Q, tường dày → giao dịch nhiều hơn."""
import math
from types import SimpleNamespace

import pytest

from agents.base import ThiTruongCoDinh
from agents.farmer import Farmer, thuong_log, thuong_tuyen_tinh


class BeLHang:
    """Bể đôi giả: thanh khoản L hằng ở mọi giá (một tick rất rộng). Chỉ cài chiều mua token0."""

    def __init__(self, L: float, fee: float = 0.0025, sqrt_price: float = 1.0):
        self.L, self.fee, self.sqrt_price = L, fee, sqrt_price
        self.lich_su = []

    def quote_swap(self, zero_for_one, amount_in=None, sqrt_price_limit=None):
        assert not zero_for_one
        z0 = self.sqrt_price
        z1 = z0 + amount_in * (1 - self.fee) / self.L
        return SimpleNamespace(amount_in=amount_in, amount_out=self.L * (1 / z0 - 1 / z1),
                               fee=amount_in * self.fee, zero_for_one=False,
                               sqrt_price_before=z0, sqrt_price_after=z1)

    def swap(self, owner, zero_for_one, amount_in=None, sqrt_price_limit=None):
        r = self.quote_swap(zero_for_one, amount_in, sqrt_price_limit)
        self.sqrt_price = r.sqrt_price_after
        self.lich_su.append((owner, r))
        return r


def v_sao(L, f, sigma, P_e, z0):
    """Theorem 1: V*(σ; L) = (L/(1−f))·(√(P_e(1−f)/(1−σ)) − z₀)."""
    return L / (1 - f) * (math.sqrt(P_e * (1 - f) / (1 - sigma)) - z0)


F, L, Q = 0.0025, 1e7, 1e5


def test_khop_theorem1_nghiem_trong():
    sigma = 0.01                                    # σ₀ = 0,0025 < σ < σ_cap ≈ 0,022
    be = BeLHang(L, F)
    v, u = Farmer("farmer:0", thuong_tuyen_tinh(sigma, Q), Q).ke_hoach(be, 1.0)
    assert v == pytest.approx(v_sao(L, F, sigma, 1.0, 1.0), rel=1e-5)   # ≈ 37.906 USDT
    assert 0 < v < Q and u > 0


def test_duoi_sigma0_khong_giao_dich():
    be = BeLHang(L, F)
    v, u = Farmer("farmer:0", thuong_tuyen_tinh(0.002, Q), Q).ke_hoach(be, 1.0)   # σ < σ₀ = f
    assert v == 0.0 and u == 0.0


def test_tran_Q_rang_buoc_va_khong_vuot():
    be, tt = BeLHang(L, F), ThiTruongCoDinh(1.0)
    fa = Farmer("farmer:0", thuong_tuyen_tinh(0.05, Q), Q, window=24)          # σ > σ_cap
    for t in range(5):
        fa.act(t, be, tt)
        be.sqrt_price = 1.0                         # thay cho arb kéo giá về P_e
    assert fa.v_cua_so == pytest.approx(Q, rel=1e-9)
    assert fa.v_cua_so <= Q * (1 + 1e-12)
    assert len(be.lich_su) == 1                     # bước 1–4 hết trần, không mua thêm
    fa.act(24, be, tt)                              # cửa sổ mới → mua lại
    assert len(be.lich_su) == 2 and fa.v_cua_so == pytest.approx(Q, rel=1e-9)


def test_tuong_day_thi_mua_nhieu_hon():
    fa = Farmer("farmer:0", thuong_tuyen_tinh(0.01, 1e9), 1e9)
    v_mong, _ = fa.ke_hoach(BeLHang(1e6, F), 1.0)
    v_day, _ = fa.ke_hoach(BeLHang(1e8, F), 1.0)
    assert v_day == pytest.approx(100 * v_mong, rel=1e-4)                     # V* ∝ L


def test_thuong_log_dieu_kien_bien():
    sigma = 0.03
    be = BeLHang(L, F)
    fa = Farmer("farmer:0", thuong_log(sigma, Q), Q=None, v_tran=10 * Q)
    v, u = fa.ke_hoach(be, 1.0)
    assert 0 < v < 10 * Q and u > 0
    # điều kiện bậc nhất: thưởng biên = chi phí biên 1 − P_e·x'(v)
    h = 1e-3 * v
    thuong_bien = sigma * Q / ((Q + v) * math.log(2))
    x = lambda w: be.quote_swap(False, w).amount_out
    chi_phi_bien = 1 - (x(v + h) - x(v - h)) / (2 * h)
    assert thuong_bien == pytest.approx(chi_phi_bien, rel=1e-3)
    v2, _ = Farmer("farmer:0", thuong_log(2 * sigma, Q), Q=None, v_tran=10 * Q).ke_hoach(be, 1.0)
    assert v2 > v

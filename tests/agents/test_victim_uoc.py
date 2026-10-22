"""Kiểm cách ước V̂ của VictimThichNghi (W15): mặc định giữ hành vi cũ, các cách ước lọc không tăng V̂."""
import pytest

from agents.arb import Arbitrageur
from agents.victim import VictimThichNghi
from tests.agents.test_arb_victim import ThiTruongCoDinh, be_co_tuong


def _log_hon_hop(n=8):
    """Bể có lệnh mua nền (bg), bán nền (bg) và arb kéo giá về; trả (pool, tt)."""
    pool, tt = be_co_tuong(1e9), ThiTruongCoDinh(1.0)
    for t in range(n):
        pool.t = t
        pool.swap("bg:0", zero_for_one=False, amount_in=1000.0)    # mua token0
        pool.swap("bg:1", zero_for_one=True, amount_in=500.0)      # bán token0
        pool.swap("arb:0", zero_for_one=False, amount_in=300.0)    # arb mua
    pool.t = n
    return pool, tt


def _uoc(cach, H=4, n=8):
    pool, _ = _log_hon_hop(n)
    v = VictimThichNghi("victim:0", c_V=1e-9, window=24, H=H, cach_uoc=cach)
    v.quan_sat(n, pool)
    return v.uoc_V(n, pool)


def test_mac_dinh_la_tat_ca():
    pool, _ = _log_hon_hop()
    v = VictimThichNghi("victim:0", c_V=1e-9, window=24, H=4)
    assert v.cach_uoc == "tat_ca"
    v.quan_sat(8, pool)
    assert v.uoc_V(8, pool) == pytest.approx(_uoc("tat_ca"))


def test_loc_khong_tang_V():
    tc = _uoc("tat_ca")
    assert 0 < _uoc("chi_mua") <= tc
    assert 0 < _uoc("bo_arb") <= tc
    assert _uoc("chi_mua") < tc and _uoc("bo_arb") < tc          # log này có cả bán và arb


def test_H_doi_duoc():
    pool, _ = _log_hon_hop(12)
    v72 = VictimThichNghi("victim:0", c_V=1e-9, window=24, H=8)
    v72.quan_sat(12, pool)
    assert v72.H == 8 and v72.uoc_V(12, pool) is not None
    assert VictimThichNghi("v:1", c_V=1e-9, H=168).H == 168


def test_cach_uoc_sai():
    with pytest.raises(ValueError):
        VictimThichNghi("victim:0", c_V=1e-9, cach_uoc="xyz")

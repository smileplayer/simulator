"""Dòng ngẫu nhiên theo vụ (tao_rng) và chỗ đặt tường/victim khi tick_spacing > 1 hoặc giá ở biên tick."""
import numpy as np
import pytest

from agents.attacker import Attacker
from agents.base import ThiTruongCoDinh, khoang_quanh_gia, tick_chua_gia
from agents.victim import VictimToanTri
from engine import Pool, sqrt_price_at_tick
from scenarios.batch import cau_hinh, to_hop_rq1
from scenarios.run import run_frame, tao_dong_ngau_nhien

F = 0.0025
TT = ThiTruongCoDinh(1.0)


def test_dong_ngau_nhien_khac_vu_thi_khac_cung_vu_thi_giong():
    a = tao_dong_ngau_nhien({"scenario_id": "L27_00"}, 5)
    b = tao_dong_ngau_nhien({"scenario_id": "L27_01"}, 5)
    c = tao_dong_ngau_nhien({"scenario_id": "L27_00", "defense": {"name": "cap", "ty_le": 0.25},
                             "victim_type": "adaptive", "attacker_farm_share": 0.6}, 5)
    xa, xb, xc = (d["nen"].random(8) for d in (a, b, c))
    assert not np.allclose(xa, xb) and np.array_equal(xa, xc)
    assert np.array_equal(a["gia"].random(8), c["gia"].random(8))
    assert not np.allclose(tao_dong_ngau_nhien({}, 5)["nen"].random(8), tao_dong_ngau_nhien({}, 5)["gia"].random(8))


def _ghi(cfg, seed):
    g = {}
    df = run_frame(cfg, seed, ghi=g)
    return df, g


def _giong(g1, g2):
    assert [t for t, _, _ in g1["nen"]] == [t for t, _, _ in g2["nen"]]
    for (_, c1, u1), (_, c2, u2) in zip(g1["nen"], g2["nen"]):
        assert np.array_equal(c1, c2) and np.array_equal(u1, u2)
    assert g1["soc"] == g2["soc"]


@pytest.mark.parametrize("sua", [{"defense": {"name": "cap", "ty_le": 0.25}},
                                 {"attacker_farm_share": 0.6, "victim_type": "adaptive"}])
def test_cap_phan_thuc_rut_cung_so_ngau_nhien_moi_buoc(sua):
    """Cùng vụ + seed: lệnh nền (cỡ, chiều, theo bước) và cú sốc giá ngoài trùng ở MỌI bước, kể cả sau khi
    trạng thái bể đã tách nhau (log khác)."""
    cfg = cau_hinh(to_hop_rq1()[4])
    df0, g0 = _ghi(cfg, 2)
    df1, g1 = _ghi(dict(cfg, **sua), 2)
    assert len(g0["nen"]) == cfg["steps"] and len(g0["soc"]) == cfg["steps"]
    _giong(g0, g1)
    p0 = df0[df0.kind == "step"].sqrt_price_after.to_numpy()
    p1 = df1[df1.kind == "step"].sqrt_price_after.to_numpy()
    assert not np.allclose(p0, p1)                      # bể đã tách nhau
    _, g2 = _ghi(dict(cfg, scenario_id="vu_khac"), 2)
    assert not np.allclose(g0["soc"], g2["soc"])


def test_khoang_quanh_gia_theo_tick_spacing():
    pool = Pool(F, sqrt_price_at_tick(3) * 1.0001 ** 0.25, tick_spacing=10)
    assert khoang_quanh_gia(pool, 1) == (0, 10)
    pool = Pool(F, sqrt_price_at_tick(-3) * 1.0001 ** 0.25, tick_spacing=10)
    assert khoang_quanh_gia(pool, 1) == (-10, 0)
    assert khoang_quanh_gia(pool, 25) == (-10, 20)


def test_tuong_va_victim_khi_tick_spacing_10():
    pool = Pool(F, sqrt_price_at_tick(13) * 1.0001 ** 0.25, tick_spacing=10)
    pool.mint("bg:1", -1000, 1000, 1e6)
    att = Attacker("attacker:0", L_A=1e8, t_m=0, kho_token0=0, c_A=0.0, t_0=100)
    att.act(0, pool, TT)                                # trước đây: ValueError (tick 13 không chia hết 10)
    assert (att.tick_lower, att.tick_upper) == (10, 20)
    v = VictimToanTri("victim:0", V=1e6, c_V=F * 1e6 / (4 * 1e8 * 1.01), t_vao=0)
    v.act(1, pool, TT)
    assert v.tick_lower == 10 and v.L_hien_tai(pool) > 0


def _be_o_bien_tren():
    """Như test của A: đi xuống chạm biên tick 0 → pool.tick = −1, giá = P(0)."""
    pool = Pool(F, 1.0001 ** 0.25)
    pool.mint("bg:1", 0, 10, 1e6)
    pool.mint("bg:2", -10, 0, 1e3)
    pool.swap("arb:0", True, sqrt_price_limit=sqrt_price_at_tick(0))
    assert pool.tick == -1 and pool.sqrt_price == sqrt_price_at_tick(0)
    return pool


def test_tuong_o_bien_tren_lay_tick_ke_tiep_va_chan_lenh_mua():
    pool = _be_o_bien_tren()
    assert tick_chua_gia(pool) == 0
    att = Attacker("attacker:0", L_A=1e8, t_m=0, kho_token0=0, c_A=0.0, t_0=100)
    att.act(0, pool, TT)
    assert (att.tick_lower, att.tick_upper) == (0, 1)
    mua = pool.quote_swap(False, amount_in=100.0)
    assert mua.tick_after == 0                         # tường toàn token0 hấp thụ lệnh mua (trước: đi xuyên)


def test_victim_o_bien_tren_doc_L_cua_tick_chua_gia():
    pool = _be_o_bien_tren()
    pool.mint("attacker:0", 0, 1, 1e8)
    L_A = 1e8 + 1e6                                    # L hoạt động trong tick 0
    c_V = F * 1e6 / (4 * L_A)                          # L_A = fV/(4c_V) → L_V* = L_A
    v = VictimToanTri("victim:0", V=1e6, c_V=c_V, t_vao=0)
    v.act(0, pool, TT)
    assert v.tick_lower == 0
    assert v.L_hien_tai(pool) == pytest.approx(L_A, rel=1e-9)

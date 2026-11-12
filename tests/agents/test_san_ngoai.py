"""Sàn ngoài độ sâu hữu hạn (cải tiến H): bảo toàn token0, cân bằng giá, và không đổi hành vi khi tắt."""
import math

from agents.san_ngoai import SanNgoai, can_bang
from engine import Pool, sqrt_price_at_tick
from scenarios.batch import cau_hinh, to_hop_rq1
from scenarios.run import run_frame


def test_san_mua_ban_doi_xung():
    s = SanNgoai(1e4, 1.0)
    s.ban_token0(100.0)
    assert s.gia < 1.0
    s.mua_token0(100.0)
    assert abs(s.gia - 1.0) < 1e-12
    assert abs(s.token0_de_toi(math.sqrt(1.21)) - s.L * (1 - 1 / 1.1)) < 1e-9


def _be(z):
    p = Pool(0.0025, z)
    p.mint("bg", -2000, 2000, 1e6)
    return p


def test_can_bang_dua_hai_gia_ve_mot_va_bao_toan_token0():
    for P_san in (0.97, 1.03):
        p, s = _be(sqrt_price_at_tick(0)), SanNgoai(5e4, P_san)
        x_truoc = s.L / s.z
        dx = can_bang(p, s)
        assert abs(p.sqrt_price / s.z - 1) < 1e-9                       # cùng giá
        assert abs((x_truoc - s.L / s.z) - dx) < 1e-6 * max(1.0, abs(dx))   # token0 sàn mất = token0 bể nhận
        assert (dx > 0) == (P_san < 1.0)                                 # bể đắt hơn → token0 đi từ sàn vào bể


def test_san_sau_vo_cung_giu_gia_san():
    p, s = _be(sqrt_price_at_tick(0)), SanNgoai(1e12, 1.02)
    can_bang(p, s)
    assert abs(s.gia - 1.02) < 1e-6


def test_tat_san_ngoai_khong_doi_log():
    vu = to_hop_rq1()[0]
    a = run_frame(cau_hinh(vu), 0)
    b = run_frame({**cau_hinh(vu), "san_ngoai": None}, 0)
    assert a.equals(b)


def test_bat_san_ngoai_chay_duoc_va_ghi_meta():
    cfg = {**cau_hinh(to_hop_rq1()[0]), "san_ngoai": {"do_sau": 1e5, "vol_prep": 0.0}}
    m = run_frame(cfg, 0).attrs["meta"]
    assert m["san_ban0"] > 0 and m["san_gia_cuoi"] > 0

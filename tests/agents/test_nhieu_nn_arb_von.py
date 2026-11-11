"""Nhiều nạn nhân (n_victims) và arbitrageur có vốn hữu hạn (arb_budget)."""
import pandas as pd
import pytest

from agents.arb import Arbitrageur
from agents.base import ThiTruongCoDinh
from engine.pool import Pool
from scenarios.quet_nhieu_nan_nhan import do_tre_vao
from scenarios.run import nap_config, run_frame


def cfg_nho(**sua):
    """Cấu hình nhỏ (120 bước) như test_run, có sập; `sua` ghi đè."""
    cfg = nap_config("co_so")
    cfg.update(steps=120, t_m=24, wall_schedule=[[24, 0.6], [36, 0.4]], t_0=96, victim_delay=12, bg_band=0.2)
    cfg.update(sua)
    return cfg


def test_arb_von_none_trung_luot_cu():
    """arb_budget = None (hoặc không có khóa) cho log giống hệt từng bit."""
    a = run_frame(cfg_nho(), 3)
    b = run_frame(cfg_nho(arb_budget=None), 3)
    pd.testing.assert_frame_equal(a, b, check_exact=True)
    c = run_frame(cfg_nho(arb_budget=1e12), 3)         # vốn không bao giờ cạn → cũng trùng
    pd.testing.assert_frame_equal(a, c, check_exact=True)


def test_arb_von_nho_lam_arb_dung():
    """Ngân sách nhỏ: tổng token1 arb bỏ ra mua token0 không vượt ngân sách, và ít hơn lượt không giới hạn."""
    goc = run_frame(nap_config("co_so"), 0)            # kịch bản đầy đủ: arb có mua token0 (≈ 21k token1)
    mua = lambda d: d[(d.owner == "arb:0") & (d.kind == "swap") & (d.amount1 > 0)].amount1.sum()
    von = 0.25 * mua(goc)
    assert von > 0
    d = run_frame({**nap_config("co_so"), "arb_budget": von}, 0)
    assert mua(d) <= von * (1 + 1e-12)
    assert mua(d) == pytest.approx(von, rel=1e-9)        # dùng hết rồi dừng
    assert d.attrs["meta"]["arb_da_chi"] == pytest.approx(von, rel=1e-9)
    assert mua(d) < mua(goc)


def test_arb_don_vi_hoat_dong_hai_chieu():
    """Arb có vốn: mua token0 tới hết vốn thì thôi; bán token0 (giá bể > P_e) không bị chặn."""
    pool = Pool(0.0025, 1.0)
    pool.mint("bg:1", -20000, 20000, 1e6)
    arb = Arbitrageur(von=100.0)
    arb.act(0, pool, ThiTruongCoDinh(1.05))              # P_e cao hơn giá bể → mua, vốn 100 chỉ kéo được một phần
    assert arb.da_chi == pytest.approx(100.0)
    assert pool.sqrt_price ** 2 < 1.05
    z = pool.sqrt_price
    arb.act(1, pool, ThiTruongCoDinh(1.05))              # hết vốn → không làm gì
    assert pool.sqrt_price == z
    arb.act(2, pool, ThiTruongCoDinh(0.9))              # P_e thấp → bán, kéo giá xuống
    assert pool.sqrt_price ** 2 == pytest.approx(0.9, rel=1e-9)


def test_do_tre_vao():
    assert [do_tre_vao(n) for n in (1, 2, 4, 8)] == [30, 15, 7, 3]


def test_hai_nan_nhan_du_dia_chi_va_thiet_hai_cong_du():
    """n_victims = 2: log có cả victim:0 và victim:1, thiệt hại TOTAL = tổng từng nạn nhân, L nạn nhân cộng cả hai."""
    from metrics.phases import phases
    from metrics.pnl import victim_loss
    from metrics.report import summarize
    from scenarios.hieu_chinh import LV_chia_LA
    df = run_frame(cfg_nho(n_victims=2, victim_delay=6), 0)
    owners = set(df[df.role == "victim"].owner)
    assert owners == {"victim:0", "victim:1"}
    ph = phases(df)
    vl = victim_loss(df, ph)
    assert set(vl.index) == {"victim:0", "victim:1", "TOTAL"}
    assert vl.loc["TOTAL", "loss_full"] == pytest.approx(vl.drop(index="TOTAL").loss_full.sum())
    s = summarize(df)
    assert s["n_victims"] == 2
    assert s["victim_loss_full"] == pytest.approx(vl.loc["TOTAL", "loss_full"])
    L_hai = sum(df[(df.owner == o) & (df.t < df.attrs["meta"]["t_rut"])].pipe(
        lambda g: g[g.kind == "mint"].liquidity.sum() - g[g.kind == "burn"].liquidity.sum()) for o in owners)
    assert LV_chia_LA(df) * df.attrs["meta"]["L_A"] == pytest.approx(L_hai)
    assert min(df[(df.kind == "mint") & (df.owner == o)].liquidity.sum() for o in owners) > 0


def test_phan_thuc_ban_thang_bo_moi_nan_nhan():
    """Phát lại 'bán thẳng' bỏ mọi victim:*: lợi tăng thêm tính được với 2 nạn nhân và bể phát lại không có vị thế victim."""
    from scenarios.quet_gd2 import loi_nhuan_dia_chi
    df = run_frame(cfg_nho(n_victims=2, victim_delay=6), 0)
    r = loi_nhuan_dia_chi(df)
    assert r["dc_excess"] == r["dc_excess"]              # không NaN
    r1 = loi_nhuan_dia_chi(run_frame(cfg_nho(n_victims=1), 0))
    assert r["dc_ban_thang"] == pytest.approx(r1["dc_ban_thang"], rel=0.05)   # bán thẳng không phụ thuộc số nạn nhân

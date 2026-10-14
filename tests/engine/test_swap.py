"""Test swap / quote_swap cross-tick, phí feeGrowth, bảo toàn token."""
import random

import pytest

from engine.pool import Pool
from engine.tick_math import amount0_delta, amount1_delta, sqrt_price_at_tick, tick_at_sqrt_price

FEE = 0.0025


def test_mot_tick_khop_cong_thuc_tay_xuong():
    """Bán 100 token0 trong một khoảng L = 1e6: 1/z' = 1/z + 100·(1−f)/L, ra L·(z − z')."""
    pool = Pool(FEE, 1.0)
    pool.mint("victim:0", -10, 10, 1e6)
    r = pool.swap("bg:0", True, amount_in=100.0)
    net = 100 * (1 - FEE)
    z_new = 1 / (1 + net / 1e6)
    assert abs(r.sqrt_price_after - z_new) < 1e-12
    assert abs(r.amount_out - 1e6 * (1 - z_new)) < 1e-9
    assert abs(r.fee - 100 * FEE) < 1e-12 and r.amount_in == 100.0
    # P = z'² ≈ 1 − 2·1e-4 → tick −2 (P(−2) = 0,99980 ≤ P < P(−1))
    assert r.tick_after == pool.tick == tick_at_sqrt_price(z_new) == -2 and r.ticks_crossed == 2


def test_mot_tick_khop_cong_thuc_tay_len():
    pool = Pool(FEE, 1.0)
    pool.mint("victim:0", -10, 10, 1e6)
    r = pool.swap("bg:0", False, amount_in=30.0)
    net = 30 * (1 - FEE)
    z_new = 1 + net / 1e6
    assert abs(r.sqrt_price_after - z_new) < 1e-12
    assert abs(r.amount_out - 1e6 * (1 - 1 / z_new)) < 1e-9


def test_toi_gia_gioi_han():
    pool = Pool(FEE, 1.0)
    pool.mint("victim:0", -100, 100, 1e6)
    lim = sqrt_price_at_tick(-37) * 1.00001
    r = pool.swap("arb:0", True, sqrt_price_limit=lim)
    assert r.sqrt_price_after == lim and pool.tick == -37
    assert r.amount_in == pytest.approx(amount0_delta(lim, 1.0, 1e6) / (1 - FEE), rel=1e-12)
    # giới hạn sai chiều → không làm gì
    r2 = pool.swap("arb:0", True, sqrt_price_limit=1.5)
    assert r2.amount_in == 0 and pool.sqrt_price == lim
    with pytest.raises(ValueError):
        pool.swap("arb:0", True)


def test_amount_va_gioi_han_dung_o_dieu_kien_den_truoc():
    pool = Pool(FEE, 1.0)
    pool.mint("victim:0", -100, 100, 1e6)
    lim = sqrt_price_at_tick(-50)
    q = pool.quote_swap(True, amount_in=1e9, sqrt_price_limit=lim)
    assert q.sqrt_price_after == lim and q.amount_in < 1e9           # giới hạn đến trước
    q = pool.quote_swap(True, amount_in=10.0, sqrt_price_limit=lim)
    assert q.amount_in == 10.0 and q.sqrt_price_after > lim          # lượng đến trước


def test_xuyen_1500_tick_mot_tick_moi_vi_the():
    """1500 vị thế độ rộng 1 xếp liền: L hằng số → đi xuống khớp công thức đóng của một khoảng."""
    L = 1e5
    pool = Pool(FEE, 1.0)
    for i in range(-1500, 0):
        pool.mint(f"victim:{i}", i, i + 1, L)
    assert pool.liquidity == 0                                       # giá ở tick 0, ngoài mọi vị thế
    lim = sqrt_price_at_tick(-1200)
    r = pool.swap("attacker:0", True, sqrt_price_limit=lim)
    assert r.sqrt_price_after == lim
    assert r.amount_in * (1 - FEE) == pytest.approx(amount0_delta(lim, 1.0, L), rel=1e-9)
    assert r.amount_out == pytest.approx(amount1_delta(lim, 1.0, L), rel=1e-9)
    assert pool.tick == -1201 and r.ticks_crossed == 1201
    assert pool.liquidity == pytest.approx(L)
    # đi ngược lên lại qua 1200 tick
    r2 = pool.swap("arb:0", False, sqrt_price_limit=sqrt_price_at_tick(-1) * 1.00001)
    assert pool.tick == -1 and pool.liquidity == pytest.approx(L)
    assert r2.amount_out == pytest.approx(amount0_delta(lim, sqrt_price_at_tick(-1) * 1.00001, L),
                                          rel=1e-9)


def test_het_thanh_khoan_thi_dung():
    pool = Pool(FEE, 1.0)
    pool.mint("victim:0", -5, 5, 1e6)
    r = pool.swap("attacker:0", True, amount_in=1e12)
    assert r.amount_in < 1e12
    assert pool.sqrt_price == sqrt_price_at_tick(-5) and pool.tick == -6 and pool.liquidity == 0
    assert r.amount_out == pytest.approx(amount1_delta(sqrt_price_at_tick(-5), 1.0, 1e6))
    r2 = pool.swap("attacker:0", True, amount_in=1.0)
    assert r2.amount_in == 0 and r2.amount_out == 0
    # chiều ngược lại vẫn có thanh khoản
    assert pool.swap("arb:0", False, amount_in=1.0).amount_out > 0


def test_khoang_trong_giua_hai_vi_the():
    """Có khoảng trống không thanh khoản: giá nhảy qua miễn phí rồi tiếp tục ở vị thế dưới."""
    pool = Pool(FEE, 1.0)
    pool.mint("victim:0", -5, 5, 1e6)
    pool.mint("victim:1", -60, -40, 2e6)
    lim = sqrt_price_at_tick(-50)
    r = pool.swap("attacker:0", True, sqrt_price_limit=lim)
    need = amount0_delta(sqrt_price_at_tick(-5), 1.0, 1e6) + \
        amount0_delta(lim, sqrt_price_at_tick(-40), 2e6)
    assert r.amount_in * (1 - FEE) == pytest.approx(need, rel=1e-12)
    assert pool.liquidity == pytest.approx(2e6)


def test_hai_lp_cung_tick_chia_phi_theo_L():
    pool = Pool(FEE, 1.0)
    a, *_ = pool.mint("victim:0", -1, 1, 1e6)
    b, *_ = pool.mint("attacker:0", -1, 1, 3e6)
    c, *_ = pool.mint("victim:1", 5, 9, 5e6)                         # ngoài khoảng: không có phí
    r1 = pool.swap("farmer:0", False, amount_in=50.0)
    r2 = pool.swap("farmer:0", True, amount_in=40.0)
    fa, fb, fc = pool.fees_owed(a), pool.fees_owed(b), pool.fees_owed(c)
    assert fa[1] == pytest.approx(r1.fee / 4, rel=1e-12) and fb[1] == pytest.approx(3 * r1.fee / 4)
    assert fa[0] == pytest.approx(r2.fee / 4, rel=1e-12) and fb[0] == pytest.approx(3 * r2.fee / 4)
    assert fc == (0.0, 0.0)
    assert pool.collect(a) == pytest.approx(fa) and pool.fees_owed(a) == (0.0, 0.0)


def test_phi_chi_tinh_phan_trong_khoang():
    """Swap đi qua biên vị thế: vị thế chỉ nhận phí của đoạn giá nằm trong khoảng của nó."""
    pool = Pool(0.01, 1.0)
    a, *_ = pool.mint("victim:0", -10, 10, 1e6)                      # có mặt cả đoạn
    b, *_ = pool.mint("victim:1", -4, 10, 1e6)                       # rời khỏi ở tick -4
    lim = sqrt_price_at_tick(-8)
    pool.swap("bg:0", True, sqrt_price_limit=lim)
    z4 = sqrt_price_at_tick(-4)
    r = 0.01 / 0.99                                   # phí / lượng vào ròng
    chung = amount0_delta(z4, 1.0, 2e6) * r           # đoạn [−4, 0]: L = 2e6, mỗi bên một nửa
    rieng = amount0_delta(lim, z4, 1e6) * r           # đoạn [−8, −4]: chỉ a
    fee_a, fee_b = chung / 2 + rieng, chung / 2
    assert pool.fees_owed(b)[0] == pytest.approx(fee_b, rel=1e-9)
    assert pool.fees_owed(a)[0] == pytest.approx(fee_a, rel=1e-9)


def test_quote_swap_khong_doi_trang_thai():
    pool = Pool(FEE, 1.0)
    pid, *_ = pool.mint("victim:0", -30, 30, 1e6)
    truoc = (pool.sqrt_price, pool.tick, pool.liquidity, len(pool.log), pool.fees_owed(pid),
             pool.fee_growth_global0)
    q = pool.quote_swap(True, amount_in=5000.0)
    assert q.ticks_crossed > 0
    assert (pool.sqrt_price, pool.tick, pool.liquidity, len(pool.log), pool.fees_owed(pid),
            pool.fee_growth_global0) == truoc
    r = pool.swap("farmer:0", True, amount_in=5000.0)
    assert r == q


def test_log_swap():
    pool = Pool(FEE, 1.0)
    pool.mint("victim:0", -30, 30, 1e6)
    r1 = pool.swap("farmer:3", False, amount_in=20.0)
    r2 = pool.swap("farmer:3", True, amount_in=r1.amount_out)          # khứ hồi
    s = pool.log.to_frame().query("kind == 'swap'").to_dict("records")
    assert s[0]["amount1"] == 20.0 and s[0]["amount0"] == -r1.amount_out
    assert s[0]["fee1"] == r1.fee and s[0]["fee0"] == 0
    assert s[1]["amount0"] == r1.amount_out and s[1]["amount1"] == -r2.amount_out
    assert s[1]["fee0"] == r2.fee and s[1]["role"] == "farmer"
    assert s[1]["sqrt_price_after"] == pool.sqrt_price
    assert r2.amount_out < 20.0                                         # mất phí hai chiều


@pytest.mark.parametrize("seed", range(5))
def test_bao_toan_token_ngau_nhien(seed):
    """Mint/swap ngẫu nhiên hai chiều rồi rút hết + thu phí: số dư bể về ≈ 0, phí thu = phí swap."""
    rng = random.Random(seed)
    pool = Pool(0.003, 1.0)
    pids = []
    for k in range(25):
        lo = rng.randint(-400, 300)
        pids.append(pool.mint(f"victim:{k}", lo, lo + rng.randint(1, 150), rng.uniform(1e4, 1e6))[0])
    for _ in range(300):
        down = rng.random() < 0.5
        if rng.random() < 0.3:
            pool.swap("arb:0", down, sqrt_price_limit=sqrt_price_at_tick(rng.randint(-450, 450)))
        else:
            pool.swap("bg:0", down, amount_in=rng.uniform(1, 3000))
        if rng.random() < 0.05:
            lo = rng.randint(-400, 300)
            pids.append(pool.mint("victim:x", lo, lo + rng.randint(1, 50), rng.uniform(1e4, 1e5))[0])
    for pid in pids:
        pool.burn(pid)
        pool.collect(pid)
    df = pool.log.to_frame()
    swaps = df[df.kind == "swap"]
    coll = df[df.kind == "collect"]
    for k in "01":
        du = df[f"amount{k}"].sum() - coll[f"fee{k}"].sum()   # token còn trong bể
        quy_mo = df[f"amount{k}"].abs().sum()
        assert abs(du) <= 1e-9 * quy_mo
        assert coll[f"fee{k}"].sum() == pytest.approx(swaps[f"fee{k}"].sum(), rel=1e-9)
    assert pool.liquidity == 0 and pool._ticks == {}


def test_tuong_ngay_duoi_gia_kich_hoat_khi_ban():
    """P₀ = 1 nằm đúng biên tick 0, tường [-1, 0) chưa hoạt động; bán token0 → vào tường ngay."""
    L_A = 1000 / (1 - 1.0001 ** -0.5)                 # 1.000 USDT ≈ 20 triệu L
    pool = Pool(FEE, 1.0)
    pool.mint("attacker:0", -1, 0, L_A)
    assert pool.liquidity == 0
    r = pool.swap("farmer:0", True, amount_in=10.0)
    assert pool.tick == -1 and pool.liquidity == pytest.approx(L_A)
    assert r.amount_out == pytest.approx(amount1_delta(r.sqrt_price_after, 1.0, L_A), rel=1e-12)
    # khứ hồi: mua lại đúng lượng token1 nhận được → giá về gần 1, vẫn trong tường
    r2 = pool.swap("farmer:0", False, amount_in=r.amount_out)
    assert pool.tick == -1 and r2.amount_out < 10.0

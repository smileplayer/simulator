"""Log tự đủ: phát lại các dòng mint/burn/collect/swap trên bể mới cho đúng trạng thái từng dòng.

Đây là điều kiện để vai B chỉ đọc log mà vẫn tính đúng (INTERFACE mục 4), và là cách kiểm log của
kịch bản thật (CH-4). Kèm một test ghi lại quy ước v3 ở biên tick mà tác nhân dựng tường phải biết.
"""
import random

import pytest

from engine import Pool, sqrt_price_at_tick, tick_at_sqrt_price

FEE = 0.0025


def _be_ngau_nhien(seed: int) -> Pool:
    """Bể có vị thế lồng nhau, tường một tick, swap theo lượng và theo giá giới hạn, burn một phần."""
    rng = random.Random(seed)
    pool = Pool(FEE, 1.0001 ** 0.25)
    pids = [pool.mint(f"bg:{k}", -40 * k, 40 * k, 1e5)[0] for k in range(1, 4)]
    for t in range(150):
        pool.t = t
        if t == 20:
            pids.append(pool.mint("attacker:0", pool.tick, pool.tick + 1, 5e7)[0])
        if rng.random() < 0.1:
            lo = rng.randint(-60, 50)
            pids.append(pool.mint(f"victim:{t}", lo, lo + rng.randint(1, 10), rng.uniform(1e5, 1e7))[0])
        down = rng.random() < 0.5
        if rng.random() < 0.3:
            pool.swap("arb:0", down, sqrt_price_limit=sqrt_price_at_tick(rng.randint(-150, 150)))
        else:
            pool.swap("bg:0", down, amount_in=rng.uniform(1, 5000))
        if rng.random() < 0.1:
            pid = rng.choice(pids)
            L = next((p.liquidity for p in pool.positions() if p.id == pid), 0.0)
            if L > 0:
                pool.burn(pid, L * rng.choice([0.3, 1.0]))
                pool.collect(pid)
    return pool


@pytest.mark.parametrize("seed", range(3))
def test_phat_lai_log_trung_trang_thai(seed):
    """Mỗi dòng log khớp bể phát lại (giá, tick, L_active, lượng, phí). Dòng swap phát lại bằng giá sau làm
    giới hạn: phát lại theo lượng vào thì ca dừng đúng biên tick có thể lệch qua/không qua tick do làm tròn."""
    goc = _be_ngau_nhien(seed)
    df = goc.log.to_frame()
    moi = Pool(FEE, 1.0001 ** 0.25)
    ma_id = {}
    for r in df.itertuples():
        moi.t = r.t
        if r.kind == "mint":
            ma_id[r.position_id], a0, a1 = moi.mint(r.owner, int(r.tick_lower), int(r.tick_upper), r.liquidity)
            assert (a0, a1) == pytest.approx((r.amount0, r.amount1), rel=1e-9, abs=1e-9)
        elif r.kind == "burn":
            a0, a1 = moi.burn(ma_id[r.position_id], r.liquidity)
            assert (-a0, -a1) == pytest.approx((r.amount0, r.amount1), rel=1e-7, abs=1e-6)
        elif r.kind == "collect":
            f0, f1 = moi.collect(ma_id[r.position_id])
            assert (f0, f1) == pytest.approx((r.fee0, r.fee1), rel=1e-7, abs=1e-6)
        else:
            # chiều theo dấu lượng; swap chỉ nhảy qua khoảng trống (lượng 0) thì theo chiều giá
            xuong = r.amount0 > 0 or (r.amount1 == 0 and r.sqrt_price_after < moi.sqrt_price)
            res = moi.swap(r.owner, xuong, sqrt_price_limit=r.sqrt_price_after)
            assert res.amount_in == pytest.approx(r.amount0 if xuong else r.amount1, rel=1e-7, abs=1e-6)
            assert res.amount_out == pytest.approx(-(r.amount1 if xuong else r.amount0), rel=1e-7, abs=1e-6)
            assert res.fee == pytest.approx(r.fee0 if xuong else r.fee1, rel=1e-9, abs=1e-9)
        assert moi.sqrt_price == pytest.approx(r.sqrt_price_after, rel=1e-9) and moi.tick == r.tick_after
        assert moi.liquidity == pytest.approx(r.liquidity_active_after, rel=1e-9, abs=1e-6)
        # tick_after = tick chứa giá, trừ khi vừa đi xuống chạm đúng biên tick đã khởi tạo (khi đó nhỏ hơn 1)
        assert r.tick_after - tick_at_sqrt_price(r.sqrt_price_after) in (0, -1)


@pytest.mark.parametrize("seed", range(3))
def test_bao_toan_chi_tu_log(seed):
    """Chỉ từ log: Σ amount (mint, burn, swap) − Σ phí đã collect = token trong vị thế + phí chưa thu."""
    pool = _be_ngau_nhien(seed)
    df = pool.log.to_frame()
    ids = df.loc[df.kind == "mint", "position_id"].astype(int)
    for k in (0, 1):
        vao = df.loc[df.kind != "collect", f"amount{k}"].sum() - df.loc[df.kind == "collect", f"fee{k}"].sum()
        trong_be = sum(pool.position_amounts(i)[k] + pool.fees_owed(i)[k] for i in ids)
        assert vao == pytest.approx(trong_be, rel=1e-9, abs=1e-9 * df[f"amount{k}"].abs().max())
        phi_swap = df.loc[df.kind == "swap", f"fee{k}"].sum()
        da_thu = df.loc[df.kind == "collect", f"fee{k}"].sum() + sum(pool.fees_owed(i)[k] for i in ids)
        assert da_thu == pytest.approx(phi_swap, rel=1e-9)


def test_mint_tai_bien_tren_sau_khi_di_xuong():
    """Quy ước v3: đi xuống chạm biên tick 0 → tick = −1, giá nằm ở MÉP TRÊN của [−1, 0). Mint tường ở
    `pool.tick` lúc này cho vị thế toàn token1: lệnh bán đi vào tường, lệnh mua bỏ qua tường ngay."""
    pool = Pool(FEE, 1.0001 ** 0.25)
    pool.mint("bg:1", 0, 10, 1e6)
    pool.mint("bg:2", -10, 0, 1e3)
    pool.swap("arb:0", True, sqrt_price_limit=sqrt_price_at_tick(0))
    assert pool.tick == -1 and pool.sqrt_price == sqrt_price_at_tick(0)
    _, a0, a1 = pool.mint("attacker:0", pool.tick, pool.tick + 1, 1e8)
    assert a0 == 0 and a1 > 0 and pool.liquidity == pytest.approx(1e8 + 1e3)
    mua = pool.quote_swap(False, amount_in=100.0)
    assert mua.tick_after >= 0                         # đi qua tường không tốn gì
    ban = pool.quote_swap(True, amount_in=100.0)
    assert ban.tick_after == -1                        # tường hấp thụ lệnh bán

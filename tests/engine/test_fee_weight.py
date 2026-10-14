"""Móc GĐ3 fee_weight = φ(w): chia lại phí theo L·φ(w), tổng phí giữ nguyên."""
import random

import pytest

from engine import Pool, sqrt_price_at_tick


def phi(w, w0=100, alpha=1.0):
    """φ(w) = min(1, (w/w0)^α) như kế hoạch GĐ3."""
    return min(1.0, (w / w0) ** alpha)


def test_chia_phi_theo_L_phi():
    """Vị thế hẹp w=2 và rộng w=100 cùng chứa giá: phí chia theo L·φ, không theo L."""
    pool = Pool(0.003, 1.0, fee_weight=phi)
    a, *_ = pool.mint("attacker:0", -1, 1, 4e6)          # φ(2) = 0,02 → trọng số 8e4
    b, *_ = pool.mint("victim:0", -50, 50, 1e6)          # φ(100) = 1   → trọng số 1e6
    assert pool.liquidity == pytest.approx(5e6) and pool.liquidity_weighted == pytest.approx(1.08e6)
    r = pool.swap("farmer:0", False, amount_in=50.0)
    assert pool.tick == 0                                 # vẫn trong cả hai vị thế
    fa, fb = pool.fees_owed(a)[1], pool.fees_owed(b)[1]
    assert fa + fb == pytest.approx(r.fee, rel=1e-12)    # tổng phí giữ nguyên
    assert fa / fb == pytest.approx(8e4 / 1e6, rel=1e-12)


def test_gia_khong_doi_theo_phi():
    """φ chỉ đổi cách chia phí; giá và lượng swap như bể không có φ."""
    def dung(fw):
        pool = Pool(0.003, 1.0, fee_weight=fw)
        pool.mint("attacker:0", -1, 1, 4e6)
        pool.mint("victim:0", -50, 50, 1e6)
        return pool.swap("bg:0", True, amount_in=3e4)
    r0, r1 = dung(None), dung(phi)
    assert r1 == r0


def test_phi_hang_so_tuong_duong_pro_rata():
    """φ(w) = c (ví dụ GĐ1 mọi vị thế cùng độ rộng): c triệt tiêu trong tỷ lệ → như v3."""
    def phi_cua(fw):
        pool = Pool(0.003, 1.0, fee_weight=fw)
        ids = [pool.mint(f"victim:{k}", -k - 1, k + 3, 1e5 * (k + 1))[0] for k in range(5)]
        pool.swap("bg:0", True, amount_in=500.0)
        pool.swap("bg:0", False, amount_in=900.0)
        return [pool.fees_owed(i) for i in ids]
    for x, y in zip(phi_cua(None), phi_cua(lambda w: 0.37)):
        assert x == pytest.approx(y, rel=1e-12)


def test_phi_phai_duong():
    pool = Pool(0.003, 1.0, fee_weight=lambda w: 0.0)
    with pytest.raises(ValueError):
        pool.mint("victim:0", -1, 1, 1.0)


@pytest.mark.parametrize("seed", range(3))
def test_bao_toan_co_phi(seed):
    """Swap ngẫu nhiên qua nhiều tick với φ: rút hết, phí thu = phí swap, bể về ≈ 0."""
    rng = random.Random(seed)
    pool = Pool(0.003, 1.0, fee_weight=lambda w: phi(w, w0=40, alpha=1.5))
    pids = []
    for k in range(25):
        lo = rng.randint(-300, 250)
        pids.append(pool.mint(f"victim:{k}", lo, lo + rng.randint(1, 120), rng.uniform(1e4, 1e6))[0])
    for _ in range(300):
        if rng.random() < 0.3:
            pool.swap("arb:0", rng.random() < 0.5,
                      sqrt_price_limit=sqrt_price_at_tick(rng.randint(-350, 350)))
        else:
            pool.swap("bg:0", rng.random() < 0.5, amount_in=rng.uniform(1, 3000))
    for pid in pids:
        pool.burn(pid)
        pool.collect(pid)
    df = pool.log.to_frame()
    coll, swaps = df[df.kind == "collect"], df[df.kind == "swap"]
    for k in "01":
        assert coll[f"fee{k}"].sum() == pytest.approx(swaps[f"fee{k}"].sum(), rel=1e-9)
        du = df[f"amount{k}"].sum() - coll[f"fee{k}"].sum()
        assert abs(du) <= 1e-9 * df[f"amount{k}"].abs().sum()
    assert pool.liquidity == 0 and pool.liquidity_weighted == 0

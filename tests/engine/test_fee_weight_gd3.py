"""Kiểm `fee_weight` cho GĐ3: vị thế nhiều độ rộng chồng lấn, swap xuyên nhiều tick.

So bể với một bộ tính tay độc lập (`_BeTay`): không dùng feeGrowth/feeGrowthOutside, mà đi từng đoạn
giữa hai biên vị thế, tính phí của đoạn rồi chia trực tiếp cho các vị thế đang chứa giá theo
L_i·φ(w_i) / Σ_active L_j·φ(w_j). Công thức một bước swap giống v3 (để giá đi trùng), còn phần
chia phí hoàn toàn độc lập với engine.
"""
import math
import random

import pytest

from engine import Pool, sqrt_price_at_tick, tick_at_sqrt_price
from engine.tick_math import amount0_delta, amount1_delta

FEE = 0.003


def phi(w, w0=100, alpha=1.0):
    """φ(w) = min(1, (w/w0)^α), w tính bằng số tick."""
    return min(1.0, (w / w0) ** alpha)


class _BeTay:
    """Bộ tính tay: danh sách vị thế {lo, hi, L, wt, phi0, phi1}, chia phí trực tiếp từng đoạn."""

    def __init__(self, fee, z, fw):
        self.fee, self.z, self.tick, self.fw = fee, z, tick_at_sqrt_price(z), fw
        self.pos = {}
        self.chia = []           # (tỷ lệ engine kỳ vọng) — ghi mỗi đoạn để kiểm (b)

    def mint(self, pid, lo, hi, L):
        wt = 1.0 if self.fw is None else self.fw(hi - lo)
        self.pos[pid] = dict(lo=lo, hi=hi, L=L, wt=wt, f0=0.0, f1=0.0)

    def burn(self, pid, L):
        self.pos[pid]["L"] -= L

    def _active(self):
        return [p for p in self.pos.values() if p["L"] > 0 and p["lo"] <= self.tick < p["hi"]]

    def _bien(self, down):
        bs = {b for p in self.pos.values() if p["L"] > 0 for b in (p["lo"], p["hi"])}
        if down:
            c = [b for b in bs if b <= self.tick]
            return max(c) if c else None
        c = [b for b in bs if b > self.tick]
        return min(c) if c else None

    def swap(self, down, amount_in=None, limit=None):
        if limit is None:
            limit = sqrt_price_at_tick(-887272 if down else 887272)
        rem = math.inf if amount_in is None else amount_in
        gamma, fee_tong = 1 - self.fee, 0.0
        while rem > 0 and (self.z > limit if down else self.z < limit):
            act = self._active()
            L = sum(p["L"] for p in act)
            b = self._bien(down)
            if b is None and L <= 0:
                break
            zb = None if b is None else sqrt_price_at_tick(b)
            target = limit if zb is None else (max(zb, limit) if down else min(zb, limit))
            z_new = target
            if L > 0:
                net_max = amount0_delta(target, self.z, L) if down else amount1_delta(self.z, target, L)
                if rem >= net_max / gamma:
                    step_in, net = net_max / gamma, net_max
                else:
                    step_in, net = rem, rem * gamma
                    z_new = 1 / (1 / self.z + net / L) if down else self.z + net / L
                    z_new = max(z_new, target) if down else min(z_new, target)
                f = step_in - net
                fee_tong += f
                W = sum(p["L"] * p["wt"] for p in act)
                for p in act:                                  # chia trực tiếp theo L·φ
                    p["f0" if down else "f1"] += f * p["L"] * p["wt"] / W
                self.chia.append([p["L"] * p["wt"] / W for p in act])
                rem = 0.0 if step_in == rem else rem - step_in
            self.z = z_new
            if zb is not None and z_new == zb:
                self.tick = b - 1 if down else b
            else:
                self.tick = tick_at_sqrt_price(self.z)
        return fee_tong


def _cap(fw, spacing=1, seed=0, n_swap=200, giua_chung=True):
    """Chạy song song Pool và _BeTay: w = 1,5,50,200 (× spacing) + vị thế ngẫu nhiên, swap qua lại,
    mint/burn giữa chừng. Trả (pool, ref, map id pool → id ref, tổng phí swap (fee0, fee1))."""
    rng = random.Random(seed)
    s = spacing
    pool, ref = Pool(FEE, 1.0, tick_spacing=s, fee_weight=fw), _BeTay(FEE, 1.0, fw)
    ids = []

    def mint(lo, hi, L):
        pid = pool.mint("victim:0", lo, hi, L)[0]
        ref.mint(pid, lo, hi, L)
        ids.append(pid)

    for w, L in ((1, 5e7), (5, 3e6), (50, 1e6), (200, 4e5)):  # chồng lấn quanh giá
        lo = -(w // 2) * s
        mint(lo, lo + w * s, L)
    for _ in range(12):
        w = rng.choice([1, 2, 5, 13, 50, 120, 200])
        lo = rng.randint(-150, 150) * s
        mint(lo, lo + w * s, rng.uniform(1e4, 2e6))
    phi_swap = [0.0, 0.0]
    for k in range(n_swap):
        if giua_chung and k % 25 == 10:                        # mint/burn khi giá đang trong dải
            lo = (pool.tick // s - rng.randint(0, 4)) * s
            mint(lo, lo + rng.choice([1, 5, 50, 200]) * s, rng.uniform(1e5, 5e6))
            cand = [i for i in ids if any(p.id == i for p in pool.positions())
                    and ref.pos[i]["lo"] <= pool.tick < ref.pos[i]["hi"]]
            if cand:
                i = rng.choice(cand)
                L = ref.pos[i]["L"] * rng.choice([0.4, 1.0])
                pool.burn(i, L)
                ref.burn(i, L)
        down = rng.random() < 0.5
        if rng.random() < 0.3:
            lim = sqrt_price_at_tick(rng.randint(-170, 170) * s)
            r = pool.swap("arb:0", down, sqrt_price_limit=lim)
            f = ref.swap(down, limit=lim)
        else:
            a = rng.uniform(1, 3e4)
            r = pool.swap("bg:0", down, amount_in=a)
            f = ref.swap(down, amount_in=a)
        assert r.fee == pytest.approx(f, rel=1e-9, abs=1e-12)
        assert pool.sqrt_price == pytest.approx(ref.z, rel=1e-9) and pool.tick == ref.tick
        phi_swap[0 if down else 1] += r.fee
    return pool, ref, ids, phi_swap


FWS = [None, phi, lambda w: phi(w, w0=40, alpha=1.5), lambda w: math.log1p(w)]


@pytest.mark.parametrize("fw", FWS, ids=["pro-rata", "phi_w0_100", "phi_a1.5", "log"])
@pytest.mark.parametrize("seed", range(3))
def test_phi_tung_vi_the_khop_tinh_tay(fw, seed):
    """(b)+(e): phí từng vị thế = bộ tính tay chia trực tiếp theo L·φ từng đoạn (có mint/burn giữa chừng)."""
    pool, ref, ids, phi_swap = _cap(fw, seed=seed)
    for k in (0, 1):
        quy_mo = phi_swap[k]
        for i in ids:
            assert pool.fees_owed(i)[k] == pytest.approx(ref.pos[i][f"f{k}"], abs=1e-9 * quy_mo)


@pytest.mark.parametrize("seed", range(3))
def test_tong_phi_collect_bang_tong_phi_swap(seed):
    """(a): rút hết + collect: Σ phí collect = Σ phí swap, sai < 1e-9 quy mô; bể về rỗng."""
    pool, ref, ids, phi_swap = _cap(phi, seed=seed)
    for i in ids:
        if any(p.id == i for p in pool.positions()):
            pool.burn(i)
    thu = [0.0, 0.0]
    for i in ids:
        f0, f1 = pool.collect(i)
        thu[0] += f0
        thu[1] += f1
    for k in (0, 1):
        assert abs(thu[k] - phi_swap[k]) <= 1e-9 * phi_swap[k]
    assert pool.liquidity == 0 and pool.liquidity_weighted == 0


def test_ty_le_chia_tung_doan():
    """(b) trực tiếp: một swap nhỏ trong một tick → tỷ lệ phí từng vị thế = L_i·φ(w_i)/Σ L_j·φ(w_j)."""
    pool = Pool(FEE, sqrt_price_at_tick(0) * 1.00001, fee_weight=phi)
    spec = [(0, 1, 5e7), (-2, 3, 3e6), (-25, 25, 1e6), (-100, 100, 4e5), (10, 60, 1e6)]
    ids = [pool.mint("victim:0", lo, hi, L)[0] for lo, hi, L in spec]
    r = pool.swap("bg:0", False, amount_in=10.0)
    assert pool.tick == 0
    w = [L * phi(hi - lo) if lo <= 0 < hi else 0.0 for lo, hi, L in spec]
    for i, wi in zip(ids, w):
        assert pool.fees_owed(i)[1] == pytest.approx(r.fee * wi / sum(w), rel=1e-12, abs=1e-15)
    assert pool.fees_owed(ids[-1]) == (0.0, 0.0)                # (d) ngoài dải: không nhận phí


def test_phi_hang_trung_pro_rata_nhieu_do_rong():
    """(c): φ ≡ c trùng pro-rata từng vị thế, kể cả với w = 1..200 và mint/burn giữa chừng."""
    a, *_ = _cap(None, seed=7)
    b, *_ = _cap(lambda w: 0.37, seed=7)
    for i in range(1, a._next_id):                            # gồm cả vị thế đã burn hết
        x, y = a.fees_owed(i), b.fees_owed(i)
        assert x == pytest.approx(y, rel=1e-10, abs=1e-12)


def test_ngoai_dai_khong_nhan_phi():
    """(d): vị thế nằm ngoài toàn bộ đường giá không nhận gì; vị thế bị giá đi qua chỉ nhận phần trong dải."""
    pool = Pool(FEE, 1.0, fee_weight=phi)
    pool.mint("bg:0", -300, 300, 1e6)
    xa = pool.mint("victim:0", 500, 700, 1e6)[0]
    qua = pool.mint("victim:1", 20, 25, 1e6)[0]               # w=5, giá sẽ đi qua rồi quay về
    pool.swap("bg:0", False, sqrt_price_limit=sqrt_price_at_tick(60))
    pool.swap("bg:0", True, sqrt_price_limit=sqrt_price_at_tick(-60))
    f_qua = pool.fees_owed(qua)
    pool.swap("bg:0", True, amount_in=500.0)                  # giá dưới −60, ngoài [20, 25)
    pool.swap("bg:0", False, amount_in=1.0)
    assert pool.fees_owed(xa) == (0.0, 0.0)
    assert pool.fees_owed(qua) == f_qua and f_qua[0] > 0 and f_qua[1] > 0


@pytest.mark.parametrize("seed", range(2))
def test_tick_spacing_10(seed):
    """(f): tick_spacing = 10, w = 10..2000 tick; φ nhận w theo TICK (tick_upper − tick_lower)."""
    nhan = []

    def fw(w):
        nhan.append(w)
        return phi(w, w0=1000)

    pool, ref, ids, phi_swap = _cap(fw, spacing=10, seed=seed, n_swap=120)
    assert all(w % 10 == 0 for w in nhan) and 2000 in nhan and 10 in nhan
    for k in (0, 1):
        for i in ids:
            assert pool.fees_owed(i)[k] == pytest.approx(ref.pos[i][f"f{k}"], abs=1e-9 * phi_swap[k])


@pytest.mark.parametrize("seed", range(3))
def test_phat_lai_log_co_phi(seed):
    """Log tự đủ khi có fee_weight: phát lại trên bể mới cùng φ → từng dòng khớp; bảo toàn token từ log."""
    goc, *_ = _cap(phi, seed=seed, n_swap=150)
    for p in goc.positions()[::2]:
        goc.burn(p.id, p.liquidity * 0.5)
        goc.collect(p.id)
    df = goc.log.to_frame()
    moi = Pool(FEE, 1.0, fee_weight=phi)
    ma = {}
    for r in df.itertuples():
        if r.kind == "mint":
            ma[r.position_id], a0, a1 = moi.mint(r.owner, int(r.tick_lower), int(r.tick_upper), r.liquidity)
            assert (a0, a1) == pytest.approx((r.amount0, r.amount1), rel=1e-9, abs=1e-9)
        elif r.kind == "burn":
            a0, a1 = moi.burn(ma[r.position_id], r.liquidity)
            assert (-a0, -a1) == pytest.approx((r.amount0, r.amount1), rel=1e-7, abs=1e-6)
        elif r.kind == "collect":
            assert moi.collect(ma[r.position_id]) == pytest.approx((r.fee0, r.fee1), rel=1e-7, abs=1e-6)
        else:
            xuong = r.amount0 > 0 or (r.amount1 == 0 and r.sqrt_price_after < moi.sqrt_price)
            res = moi.swap(r.owner, xuong, sqrt_price_limit=r.sqrt_price_after)
            assert res.fee == pytest.approx(r.fee0 if xuong else r.fee1, rel=1e-9, abs=1e-9)
        assert moi.sqrt_price == pytest.approx(r.sqrt_price_after, rel=1e-9) and moi.tick == r.tick_after
        assert moi.liquidity == pytest.approx(r.liquidity_active_after, rel=1e-9, abs=1e-6)
    ids = df.loc[df.kind == "mint", "position_id"].astype(int)
    for k in (0, 1):
        vao = df.loc[df.kind != "collect", f"amount{k}"].sum() - df.loc[df.kind == "collect", f"fee{k}"].sum()
        trong_be = sum(goc.position_amounts(i)[k] + goc.fees_owed(i)[k] for i in ids)
        assert vao == pytest.approx(trong_be, rel=1e-9, abs=1e-9 * df[f"amount{k}"].abs().max())


@pytest.mark.parametrize("fw", [None, phi], ids=["pro-rata", "phi"])
def test_vi_the_nho_trong_so_sau_tuong_lon(fw):
    """Tường L lớn w=100 (φ=1) rời dải, chỉ còn vị thế nhỏ w=1 (L·φ nhỏ hơn 1e-9 lần tường):
    bể vẫn phải thấy thanh khoản nhỏ đó (không coi là rỗng) và trả hết phí cho nó.
    Trước bản sửa: L·φ bị làm tròn về 0 ⇒ L cũng về 0 ⇒ giá nhảy qua vị thế, phí mất."""
    pool = Pool(FEE, sqrt_price_at_tick(50) * 1.00001, fee_weight=fw)
    tuong = pool.mint("attacker:0", 0, 100, 1e9)[0]
    nho = pool.mint("victim:0", 100, 101, 10.0)[0]            # L·φ = 0,1 ≪ 1e-9 · 1e9
    pool.swap("bg:0", False, sqrt_price_limit=sqrt_price_at_tick(100))
    pool.swap("bg:0", False, sqrt_price_limit=sqrt_price_at_tick(101) * 0.99999)
    assert pool.tick == 100 and pool.liquidity == pytest.approx(10.0)
    f0 = pool.fees_owed(nho)[1]
    r = pool.swap("bg:0", False, amount_in=1e-4)
    assert pool.fees_owed(nho)[1] - f0 == pytest.approx(r.fee, rel=1e-9)
    assert pool.fees_owed(tuong)[1] > 0

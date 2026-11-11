"""Quét ứng viên tường trên chuỗi thật: ghép Mint → Burn, lọc theo thời gian sống và mint khác cùng khoảng (không cần mạng)."""
import pandas as pd

import numpy as np

import scenarios.quet_tuong_that as q
from scenarios.quet_tuong_that import do_lech, gio_cua, kiem_sap, tim_tuong

MOC = pd.DataFrame({"block": [0, 1000], "ts": [0, 1000 * 3600]})          # 1 block = 1 giờ


def _r(block, kind, owner, L, tx, pool="0xp", tl=10, tu=11):
    return dict(block=block, tx_index=0, log_index=0, tx_hash=tx, kind=kind, owner=owner, tick_lower=tl,
                tick_upper=tu, liquidity=L, pool=pool)


def test_gio_cua_noi_suy():
    assert list(gio_cua([0, 500, 1000], MOC)) == [0.0, 500.0, 1000.0]


def test_tim_tuong_bat_tuong_va_bo_truong_hop_sai():
    df = pd.DataFrame([
        _r(100, "mint", "0xA", 1e6, "t1"),                 # tường
        _r(130, "mint", "0xV", 1e4, "t2"),                 # nạn nhân vào lúc tường còn
        _r(220, "burn", "0xA", 1e6, "t3"),                 # rút sau 120 giờ
        # khoảng khác: không ai vào cùng → không phải ứng viên
        _r(100, "mint", "0xB", 1e6, "u1", tl=20, tu=21), _r(300, "burn", "0xB", 1e6, "u2", tl=20, tu=21),
        # khoảng khác: sống 2 giờ < 6 giờ → loại
        _r(100, "mint", "0xC", 1e6, "w1", tl=30, tu=31), _r(101, "mint", "0xV", 1e3, "w2", tl=30, tu=31),
        _r(102, "burn", "0xC", 1e6, "w3", tl=30, tu=31),
        # khoảng khác: người vào sau lớn hơn "tường" → loại
        _r(100, "mint", "0xD", 1e3, "z1", tl=40, tu=42), _r(110, "mint", "0xV", 1e6, "z2", tl=40, tu=42),
        _r(200, "burn", "0xD", 1e3, "z3", tl=40, tu=42),
    ])
    uv = tim_tuong(df, MOC)
    assert len(uv) == 1
    r = uv.iloc[0]
    assert (r["owner"], r["rong"], r["gio_song"], r["n_khac"], r["tx_mint"]) == ("0xA", 1, 120.0, 1, "t1")


def test_tim_tuong_rut_mot_phan_khong_tinh():
    df = pd.DataFrame([_r(100, "mint", "0xA", 1e6, "t1"), _r(130, "mint", "0xV", 1e4, "t2"),
                       _r(220, "burn", "0xA", 5e5, "t3")])             # chỉ rút 50% → chưa phải rút tường
    assert tim_tuong(df, MOC).empty


def test_do_lech_giam_tang_va_trong_khoang():
    giam, tang = do_lech(np.array([10, 10 - 1054, 10 - 1054]), 10, 11)  # ở lại 1054 tick dưới biên dưới ≈ giảm 10%
    assert abs(giam - 0.10) < 1e-3 and tang == 0
    giam, tang = do_lech(np.array([11 + 954]), 10, 11)                  # 954 tick trên biên trên ≈ tăng 10%
    assert giam == 0 and abs(tang - 0.10) < 1e-3
    assert do_lech(np.array([10, 11 + 50000, 10, 10]), 10, 11) == (0.0, 0.0)   # vọt lẻ rồi về: không tính
    assert do_lech(np.array([10]), 10, 11) == (0.0, 0.0)
    assert all(np.isnan(do_lech(np.array([]), 10, 11)))


def test_kiem_sap_loc_be_neo_gia(monkeypatch):
    """Bể A sập 50% sau khi tường rút, bể B (neo giá) đứng yên: chỉ A có sap = True; mỗi (pool, block_burn) gọi một lần."""
    goi = []

    def gia(rpc, pool, tu, den, buoc):
        goi.append(pool)
        return np.array([10.0, 10 - 6932.0]) if pool == "A" else np.array([10.0, 10.0])

    monkeypatch.setattr(q, "_tick_swap", gia)
    uv = pd.DataFrame(dict(pool=["A", "A", "B"], block_burn=[5, 5, 7], tick_lower=[10, 10, 10], tick_upper=[11, 11, 11]))
    kq = kiem_sap(uv, rpc=None, giay_block=12.0)
    assert list(kq["sap"]) == [True, True, False] and goi == ["A", "B"]
    assert abs(kq["giam_sau"][0] - 0.5) < 1e-3

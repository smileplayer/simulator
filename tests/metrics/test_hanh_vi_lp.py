"""Hành vi LP từ log giả: ghép mint→burn, độ trễ rút sau khi giá rời khoảng (không gọi mạng)."""
import math

import pandas as pd

from metrics.hanh_vi_lp import ghep_vi_the, hanh_vi_thu_muc, tom_tat

MOC = pd.DataFrame({"block": [0, 1000], "ts": [0, 1000 * 3600]})             # 1 block = 1 giờ


def _ev(block, kind, tl, tu, L, owner="0xo", i=0):
    return dict(block=block, tx_index=i, log_index=i, tx_hash="", kind=kind, owner=owner, tick_lower=tl, tick_upper=tu,
                liquidity=L)


def _sw(block, tick):
    return dict(block=block, tx_index=0, log_index=0, liquidity_active=1, tick=tick)


def _chay(tmp_path, ev, sw):
    pd.DataFrame(ev).to_csv(tmp_path / "su_kien.csv", index=False)
    pd.DataFrame(sw).to_csv(tmp_path / "swap.csv", index=False)
    MOC.to_csv(tmp_path / "moc.csv", index=False)
    return hanh_vi_thu_muc("t", tmp_path)


def test_tre_rut_3_gio(tmp_path):
    ev = [_ev(0, "mint", 0, 10, 100), _ev(13, "burn", 0, 10, 100, i=1),
          _ev(0, "mint", 20, 30, 100, owner="0xp", i=2), _ev(14, "burn", 20, 30, 100, owner="0xp", i=3)]
    sw = [_sw(b, 5) for b in range(0, 10)] + [_sw(b, 15) for b in range(10, 16)]   # giá rời [0,10) ở giờ 10
    d = _chay(tmp_path, ev, sw).set_index("tick_lower")
    assert d.loc[0, "tre_rut_gio"] == 3 and d.loc[0, "giu_gio"] == 13 and d.loc[0, "do_rong"] == 10
    assert d.loc[20, "tre_rut_gio"] == 14                # ngoài khoảng ngay từ mẫu swap đầu (giờ 0)


def test_khong_roi_khoang_thi_nan(tmp_path):
    ev = [_ev(0, "mint", 0, 10, 100), _ev(8, "burn", 0, 10, 100, i=1)]
    d = _chay(tmp_path, ev, [_sw(b, 5) for b in range(0, 10)])
    assert len(d) == 1 and math.isnan(d["tre_rut_gio"][0]) and d["dong"][0]


def test_ghep_fifo_va_nguong_dong():
    ev = pd.DataFrame([_ev(1, "mint", 0, 10, 100), _ev(2, "mint", 0, 10, 50, i=1), _ev(5, "burn", 0, 10, 60, i=2),
                       _ev(6, "burn", 0, 10, 90, i=3)])
    vt = ghep_vi_the(ev)
    assert list(vt["dong"]) == [True, True] and list(vt["block_dong"]) == [6, 6]
    chua = ghep_vi_the(pd.DataFrame([_ev(1, "mint", 0, 10, 100), _ev(5, "burn", 0, 10, 50, i=1)]))
    assert not chua["dong"][0]


def test_tom_tat_ty_le():
    vt = pd.DataFrame(dict(do_rong=[10, 10], giu_gio=[5.0, 5.0], tre_rut_gio=[0.5, 10.0], dong=[True, True],
                           roi_khoang=[True, True]))
    t = tom_tat(vt)
    assert t["ty_le"]["rut_1h"] == 0.5 and t["ty_le"]["rut_24h"] == 1.0

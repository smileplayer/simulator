"""Biện pháp GĐ2: hạ trần Q và trả thưởng trễ — đơn vị, thời điểm trả, tác động lên farmer/victim."""
import pytest

from defenses.thuong import LichTraThuong, Q_hieu_luc, ten_bien_phap
from scenarios.run import nap_config, run_frame


def test_Q_hieu_luc():
    assert Q_hieu_luc(24000, None) == 24000
    assert Q_hieu_luc(24000, {"name": "cap", "ty_le": 0.5}) == 12000
    assert Q_hieu_luc(24000, {"name": "cap", "Q_cap": 30000}) == 24000
    assert Q_hieu_luc(24000, {"name": "delay", "D": 5}) == 24000
    with pytest.raises(NotImplementedError):
        ten_bien_phap({"name": "warning"})


def test_lich_tra_ngay_va_tre_token0():
    ngay = LichTraThuong()
    ngay.chot(23, "farmer:0", 100.0, gia=2.0)
    assert ngay.den_han(23, gia=1.0) == [("farmer:0", 100.0)]
    tre = LichTraThuong(D=48, don_vi="token0", chiet_khau=0.99)
    assert tre.he_so_cam_nhan == pytest.approx(0.99 ** 48)
    tre.chot(23, "farmer:0", 100.0, gia=2.0)          # = 50 token0
    assert tre.den_han(70, gia=1.0) == []
    assert tre.con_treo(gia=1.0) == pytest.approx(50.0)
    assert tre.den_han(71, gia=1.0) == [("farmer:0", pytest.approx(50.0))]   # giá sập một nửa → trả 50


def cfg_nho(**sua):
    cfg = nap_config("co_so")
    cfg.update(steps=120, t_m=24, wall_schedule=[[24, 0.6], [36, 0.4]], t_0=96, victim_delay=12)
    cfg.update(sua)
    return cfg


def test_cap_ha_khoi_luong_farmer_va_V_victim():
    df = run_frame(cfg_nho(defense={"name": "cap", "ty_le": 0.5}), 0)
    cfg = cfg_nho()
    mua = df[(df.kind == "swap") & (df.role == "farmer")]
    theo_cua_so = mua.groupby([mua.owner, mua.t // cfg["subsidy_window"]]).amount1.sum()
    assert theo_cua_so.max() <= 0.5 * cfg["Q"] * (1 + 1e-9)
    assert df.attrs["meta"]["Q_eff"] == 0.5 * cfg["Q"]
    # c_V của co_so đặt k = 0,75 với Q gốc; trần 0,5Q → k_eff = 1,5 ≥ 1 → khi tường đủ, victim toàn tri rút hết
    # (có thể vào tạm lúc tường mới 60%: k_eff = 0,9 < 1)
    from scenarios.hieu_chinh import LV_chia_LA
    assert LV_chia_LA(df) == pytest.approx(0.0, abs=1e-9)


def test_delay_tra_sau_D_buoc_va_ghi_khoan_treo():
    D = 30
    df = run_frame(cfg_nho(defense={"name": "delay", "D": D, "don_vi": "token0", "chiet_khau": 0.995}), 0)
    sub = df[df.kind == "subsidy"]
    W = cfg_nho()["subsidy_window"]
    assert not sub.empty and set((sub.t - D + 1) % W) == {0}
    assert df.attrs["meta"]["subsidy_pending"] > 0      # khoản chốt ở cửa sổ cuối chưa tới hạn

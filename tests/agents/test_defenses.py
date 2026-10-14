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


def test_quet_gd2_ghi_dan_va_bo_qua(tmp_path):
    import pandas as pd
    from scenarios.quet_gd2 import BIEN_PHAP, LOAI_VICTIM, chay
    out = tmp_path / "tomtat.csv"
    chay(1, out, nhanh=True)
    d = pd.read_csv(out)
    assert len(d) == 2 * len(BIEN_PHAP) * len(LOAI_VICTIM)
    assert {"victim_loss_full", "attacker_profit_paper", "subsidy_total", "LV_chia_LA"} <= set(d.columns)
    chay(1, out, nhanh=True)                          # chạy lại: không thêm dòng
    assert len(pd.read_csv(out)) == len(d)


def test_clawback_chi_huy_khoan_cua_LP_khi_sap():
    lich = LichTraThuong(D=48, don_vi="token0", clawback=0.10)
    lich.chot(23, "attacker:0", 100.0, gia=1.0)
    lich.chot(23, "farmer:0", 100.0, gia=1.0)
    assert lich.thu_hoi(gia=1.0, chu_lp={"attacker:0"}) == []        # đánh dấu, chưa sập
    assert lich.thu_hoi(gia=0.95, chu_lp=set()) == []                # sập 5% < ngưỡng
    assert lich.thu_hoi(gia=0.85, chu_lp=set()) == [("attacker:0", pytest.approx(85.0))]   # đã rút tường vẫn bị hủy
    assert lich.da_thu_hoi == pytest.approx(85.0)
    assert lich.den_han(71, gia=0.85) == [("farmer:0", pytest.approx(85.0))]               # farmer thuần vẫn nhận
    assert LichTraThuong(D=5).thu_hoi(gia=0.1, chu_lp={"farmer:0"}) == []                 # không bật clawback


def test_attacker_farm_share_ghi_thuong_cho_attacker_va_clawback():
    d = {"name": "delay", "D": 30, "don_vi": "token0", "chiet_khau": 0.995}
    df0 = run_frame(cfg_nho(attacker_farm_share=0.0, defense=d), 0)
    df = run_frame(cfg_nho(attacker_farm_share=0.5, defense=d), 0)
    dfc = run_frame(cfg_nho(attacker_farm_share=0.5, defense=dict(d, clawback=0.10)), 0)
    assert df.attrs["meta"]["attacker_farm_accounts"] == pytest.approx(3.0)       # s/(1−s)·n_farmers
    mua = df[(df.kind == "swap") & (df.owner == "attacker:0") & (df.amount1 > 0)]
    assert not mua.empty and mua.t.max() < 240
    assert (df0[df0.kind == "subsidy"].owner == "attacker:0").sum() == 0
    sub, subc = df[df.kind == "subsidy"], dfc[dfc.kind == "subsidy"]
    assert sub[sub.owner == "attacker:0"].amount1.sum() > 0
    assert dfc.attrs["meta"]["subsidy_clawed"] > 0                                # có khoản treo qua cú sập
    assert subc[subc.owner == "attacker:0"].amount1.sum() < sub[sub.owner == "attacker:0"].amount1.sum()
    # farmer thuần không bị thu hồi: cùng seed, cùng hành vi → cùng thưởng
    assert subc[subc.role == "farmer"].amount1.sum() == pytest.approx(sub[sub.role == "farmer"].amount1.sum())
    with pytest.raises(ValueError):
        run_frame(cfg_nho(attacker_farm_share=1.0), 0)


def test_quet_gd2_che_do_farm(tmp_path):
    import pandas as pd
    from scenarios.quet_gd2 import BIEN_PHAP_FARM, LOAI_VICTIM, chay
    out = tmp_path / "farm.csv"
    chay(1, out, nhanh=True, farm=True)
    d = pd.read_csv(out)
    so_bp = 4 + 2 * len(BIEN_PHAP_FARM)                   # s = 0: không claw
    assert len(d) == 2 * so_bp * len(LOAI_VICTIM)
    assert {"farm_share", "farm_share_thuc", "sub_att", "sub_att_treo", "chi_phi_farm_att",
            "subsidy_clawed"} <= set(d.columns)
    assert (d.sub_att_treo <= d.subsidy_pending + 1e-9).all()
    assert (d[d.farm_share == 0].vol_farm_att == 0).all()
    chay(1, out, nhanh=True, farm=True)
    assert len(pd.read_csv(out)) == len(d)

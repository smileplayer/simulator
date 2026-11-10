"""Bảng ghép cặp kiểm độ bền RQ3 (victim tính rủi ro theo khoảng, 30/10) trên bảng giả dựng tay."""
import pandas as pd
import pytest

from metrics.gd3 import bang_ruiro, ket_luan_ruiro


def _dong(vu, sd, lam, alpha, excess, von):
    return dict(scenario_id=vu, k=0.64, seed=sd, victim_type="omniscient", lam=lam, alpha=alpha,
                w0=0 if alpha == 0 else 50, dc_excess=excess, von_victim=von, phan_duong_sap=0.5,
                vl_loss_full=10.0)


@pytest.fixture(scope="module")
def bang():
    rows = []
    for sd in (0, 1):
        for lam in (0.0, 0.5):
            rows += [_dong("A", sd, lam, 0.0, 100.0, 1000.0), _dong("A", sd, lam, 2.0, 60.0 if lam == 0 else 30.0, 900.0),
                     _dong("B", sd, lam, 0.0, 100.0, 1000.0 if lam == 0 else 700.0),
                     _dong("B", sd, lam, 2.0, 95.0, 950.0)]
    return bang_ruiro(pd.DataFrame(rows), B=20)


def test_phi_so_voi_pro_rata_cung_lam(bang):
    phi = bang["phi"]
    a = phi[(phi.scenario_id == "A") & (phi.lam == 0.5) & (phi.chi_so == "dc_excess")]
    b = phi[(phi.scenario_id == "B") & (phi.lam == 0.5) & (phi.chi_so == "dc_excess")]
    assert a.pct.iloc[0] == pytest.approx(-70.0) and b.pct.iloc[0] == pytest.approx(-5.0)


def test_lam_so_voi_lam_0_o_pro_rata(bang):
    lam = bang["lam"]
    b = lam[(lam.scenario_id == "B") & (lam.chi_so == "von_victim")]
    assert b.pct.iloc[0] == pytest.approx(-30.0)


def test_ket_luan_r2_la_chenh_lech_kep_so_voi_lam_0(bang):
    """A: φ cắt 40% ở λ = 0 và 70% ở λ = 0,5 → λ thêm −30 điểm (đếm); B: φ cắt 5% ở cả hai → không đếm."""
    kl = ket_luan_ruiro(bang, toi_thieu=1)
    assert kl["R2"] and not kl["R1"] and kl["R3"]
    assert kl["chi_tiet_R2"]["0.5|a2_w50|omniscient"] == 1
    assert kl["chi_tiet_lam0"]["a2_w50|omniscient"] == 1      # φ riêng ở λ = 0 đã cắt ≥ 25% ở vụ A
    assert ket_luan_ruiro(bang, toi_thieu=2)["R1"]


def test_thieu_lam_0_bao_loi():
    rows = [_dong("A", 0, 0.5, 0.0, 100.0, 1000.0), _dong("A", 0, 0.5, 2.0, 60.0, 900.0)]
    with pytest.raises(ValueError):
        bang_ruiro(pd.DataFrame(rows), B=20)

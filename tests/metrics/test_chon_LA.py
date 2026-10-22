"""Cải tiến F (22/10): chọn độ dày tường tốt nhất cho kẻ tấn công theo trung vị qua seed."""
import pandas as pd

from metrics.gd2 import chon_LA, ghep_cap


def _bang():
    dong = []
    for bp, tot in (("khong", 2.0), ("cap50", 0.5)):
        for m in (0.5, 1.0, 2.0):
            for sd in range(3):
                loi = 100 - 50 * abs(m - tot) + sd           # đỉnh ở m = tot
                dong.append(dict(scenario_id="V1", bp=bp, victim_type="adaptive", m_LA=m, seed=sd,
                                 loi_tang_them=loi, breached=1.0))
    return pd.DataFrame(dong)


def test_chon_dung_dinh_va_giu_moi_seed():
    c = chon_LA(_bang())
    chon = c.groupby("bp").m_LA_chon.unique()
    assert list(chon["khong"]) == [2.0] and list(chon["cap50"]) == [0.5]
    assert len(c) == 6


def test_ghep_cap_sau_khi_chon():
    P = ghep_cap(chon_LA(_bang()), "cap50")
    assert len(P) == 3 and (P.m_LA == 0.5).all() and (P.m_LA_goc == 2.0).all()

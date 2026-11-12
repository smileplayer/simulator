import math

from metrics.la_lv_bai_goc import mot_vu


def _r(LA, LV):
    return {"pool": "0xabc", "tick_key": "10_11", "pool_liquidity": {"L_pool_t0": 100},
            "attacker_details": [{"L_u_t0": x} for x in LA], "victim_details_tb": [{"L_u_t0": x} for x in LV],
            "wall_providers": ["a"] * len(LA)}


def test_k_suy_khop_bo_de_4():
    d = mot_vu(_r([30, 10], [40]))           # L_V/L_A = 1 ⇒ k = 1/4
    assert d["LV_chia_LA"] == 1.0 and math.isclose(d["k_suy"], 0.25)
    assert d["ty_phan_A"] == 0.4 and d["n_victim"] == 1


def test_khong_co_ke_tan_cong_thi_nan():
    d = mot_vu(_r([], [5]))
    assert math.isnan(d["LV_chia_LA"]) and math.isnan(d["k_suy"])

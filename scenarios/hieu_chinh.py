"""Bảng trước/sau của 3 thay đổi hiệu chỉnh RQ1: dựng lại config từng giai đoạn trên cùng các seed.

Giai đoạn 0 = co_so ban đầu (commit a843d09): nền phủ đều ±20.000 tick, c_V ở mốc fV/(4c_V), kho 60k.
1 = + nền hữu hạn ±10% (5 vị thế lồng nhau). 2 = + L_A = 0,75·fV/c_V. 3 = + đuôi nền 7,5% + kho 25k (= co_so ở rq1-v1).

Chạy: `python -m scenarios.hieu_chinh [--seeds 5] [--out ket_qua/rq1/hieu_chinh_truoc_sau.csv]` (≈ 2 s).
"""
from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import pandas as pd

from scenarios.run import nap_config, run_frame

GIAI_DOAN = {
    "0_ban_dau": dict(bg_band=None, bg_tail=0.0, bg_range=20000, c_V=1.125e-7, attacker_inventory=60000),
    "1_nen_huu_han": dict(bg_tail=0.0, c_V=1.125e-7, attacker_inventory=60000),
    "2_LA_075": dict(bg_tail=0.0, attacker_inventory=60000),
    "3_duoi_va_kho": dict(),
}
CHI_SO = ["do_sap", "breached", "attack_price_change", "lift_Prep", "lift_Post", "RV_Prep", "RV_Attack",
          "RV_Post", "L_drop_at_tb", "LV_chia_LA", "victim_loss_full", "attacker_profit_paper", "subsidy_total"]


def do_sap(df: pd.DataFrame) -> float:
    """Độ sập theo giá step: từ bước trước khi rút tường tới cuối pha xả (tỷ lệ, âm = giảm)."""
    m = df.attrs["meta"]
    P = df[df.kind == "step"].set_index("t").sqrt_price_after ** 2
    return P.loc[m["t_rut"] + m["dump_steps"] - 1] / P.loc[m["t_rut"] - 1] - 1


def LV_chia_LA(df: pd.DataFrame) -> float:
    """L ròng của nạn nhân ngay trước khi rút tường chia cho L_A."""
    m = df.attrs["meta"]
    v = df[(df.role == "victim") & (df.t < m["t_rut"])]
    return (v[v.kind == "mint"].liquidity.sum() - v[v.kind == "burn"].liquidity.sum()) / m["L_A"]


def bang(seeds: int = 5) -> pd.DataFrame:
    """Trung vị các chỉ số qua `seeds` seed cho từng giai đoạn (dòng = chỉ số, cột = giai đoạn)."""
    from metrics.report import summarize_many
    cot = {}
    for ten, sua in GIAI_DOAN.items():
        cfg = nap_config("co_so")
        cfg.update(sua)
        dfs = [run_frame(cfg, s) for s in range(seeds)]
        sm = summarize_many(dfs)
        sm["do_sap"] = [do_sap(d) for d in dfs]
        sm["LV_chia_LA"] = [LV_chia_LA(d) for d in dfs]
        cot[ten] = sm[CHI_SO].astype(float).median()
    return pd.DataFrame(cot)


if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--out", default="ket_qua/rq1/hieu_chinh_truoc_sau.csv")
    a = ap.parse_args()
    b = bang(a.seeds)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    b.to_csv(a.out)
    print(b.round(3).to_string())

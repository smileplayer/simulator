"""Hình RQ3 cho bài báo: tường một tick so với tường nới rộng, nạn nhân toàn tri, α ≥ 1,5.

    python -m plots.ve_rq3_wA --ra ../02_Bao_cao_va_trinh_bay/hinh/rq3_wA.pdf

Đọc `ket_qua/gd3/bang/so_sanh_wA.csv`. Khung trái: vốn nạn nhân so với pro-rata (thang log, 1 = không đổi).
Khung phải: thay đổi lợi tăng thêm của kẻ tấn công so với pro-rata (%). Đường = trung vị, dải = nhỏ nhất đến lớn nhất
trên 9 tổ hợp (α ∈ {1,5; 2; 3}, w0 ∈ {10; 50; 200}). Chữ 7 pt, nhãn tiếng Anh, khổ in LNCS.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

GOC = Path(__file__).resolve().parent.parent / "ket_qua" / "gd3" / "bang" / "so_sanh_wA.csv"


def ve(ra: Path) -> None:
    """Vẽ hình hai khung ra `ra` (PDF hoặc PNG), rộng 11,7 cm."""
    d = pd.read_csv(GOC)
    d = d[(d["victim_type"] == "omniscient") & (d["alpha"] >= 1.5)]
    plt.rcParams.update({"font.size": 7, "axes.linewidth": 0.5, "xtick.major.width": 0.5, "ytick.major.width": 0.5})
    fig, ax = plt.subplots(1, 2, figsize=(11.7 / 2.54, 4.0 / 2.54))
    mau = {"1tick": "#1f77b4", "toi_uu": "#d62728"}
    nhan = {"1tick": "one-tick wall", "toi_uu": "attacker widens the wall"}
    cot = {0: ("ty_le_von_{}", "victim capital ratio"), 1: ("dc_excess_pct_{}", "excess change (%)")}
    ks = sorted(d["k"].unique())
    x = range(len(ks))
    for j in (0, 1):
        for h in ("1tick", "toi_uu"):
            g = d.groupby("k")[cot[j][0].format(h)]
            ax[j].fill_between(x, g.min().loc[ks], g.max().loc[ks], color=mau[h], alpha=0.15, linewidth=0)
            ax[j].plot(x, g.median().loc[ks], color=mau[h], marker="o", ms=2.5, lw=1, label=nhan[h])
        ax[j].set_xticks(list(x))
        ax[j].set_xticklabels([f"{k:g}" for k in ks])
        ax[j].set_xlabel("$k$")
        ax[j].set_ylabel(cot[j][1])
        ax[j].spines[["top", "right"]].set_visible(False)
    ax[0].set_yscale("log")
    ax[0].axhline(1, color="gray", lw=0.5, ls=":")
    ax[1].axhline(0, color="gray", lw=0.5, ls=":")
    ax[0].legend(frameon=False, loc="upper left", fontsize=6)
    fig.tight_layout(pad=0.4)
    ra.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ra, dpi=300)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ra", required=True, help="file hình đầu ra (.pdf hoặc .png)")
    ve(Path(ap.parse_args().ra))

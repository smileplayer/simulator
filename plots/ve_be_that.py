"""Hình bể thật cho bài báo: giá và thanh khoản tick chứa giá theo giờ, kèm ngưỡng của luật báo động.

    python -m plots.ve_be_that --vao ket_qua/that/0x9485_hai_vu --vu 53457403:54063197 54207412:54652307 --ra ../02_Bao_cao_va_trinh_bay/hinh/be_that.pdf

Đọc `chuoi_L_gio.csv` (do `metrics.phat_hien_that` ghi) và `swap.csv`, `moc.csv` (để đổi block t_m, t_b sang giờ).
Khung trên: giá so với giờ đầu (1,0001^tick). Khung dưới: L (thang log) và m × trung vị N giờ trước đó.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from metrics.phat_hien_that import gio_block


def ve(vao: Path, vu: list[tuple[int, int]], ra: Path, m: float = 3.0, N: int = 24) -> None:
    """Vẽ hình hai khung (khổ in LNCS, chữ 7 pt, nhãn tiếng Anh) ra `ra` (PDF hoặc PNG); `vu` = các cặp block (t_m, t_b)."""
    ch = pd.read_csv(vao / "chuoi_L_gio.csv").set_index("gio")
    moc = pd.read_csv(vao / "moc.csv")
    b0 = int(pd.read_csv(vao / "swap.csv", usecols=["block"])["block"].min())
    g0 = gio_block([b0], moc)[0]
    gio = [(math.floor(gio_block([a], moc)[0] - g0), math.floor(gio_block([b], moc)[0] - g0)) for a, b in vu]
    gia = 1.0001 ** (ch["tick"] - ch["tick"].iloc[0])
    nguong = m * ch["L"].shift(1).rolling(N).median()
    with matplotlib.rc_context({"font.size": 7, "axes.labelsize": 7, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
                                "legend.fontsize": 6.5, "axes.linewidth": 0.5, "pdf.fonttype": 42}):
        fig, (a1, a2) = plt.subplots(2, 1, figsize=(4.8, 1.75), sharex=True, gridspec_kw=dict(hspace=0.12))
        a1.step(ch.index, gia, where="post", color="#1f77b4", lw=0.9)
        a1.set_ylabel("price / initial")
        a2.semilogy(ch.index, ch["L"], color="#1f77b4", lw=0.9, label="active-tick liquidity $L$")
        a2.semilogy(ch.index, nguong, color="#d62728", lw=0.8, ls="--", label=f"{m:g} $\\times$ {N}-hour median")
        a2.set_ylabel("$L$ (raw units)")
        a2.set_xlabel("hour")
        a2.legend(loc="lower left", bbox_to_anchor=(0.06, 0.02), ncol=1, frameon=False, handlelength=1.6)
        a1.set_ylim(0.0, gia.max() * 1.3)
        for ax in (a1, a2):
            for k, (hm, hb) in enumerate(gio):
                ax.axvspan(hm, hb, color="0.88", lw=0)
            for s in ("top", "right"):
                ax.spines[s].set_visible(False)
            ax.tick_params(width=0.5, length=2)
        for k, (hm, hb) in enumerate(gio):
            a1.text((hm + hb) / 2, 1.0, f"incident {k + 1}", ha="center", va="top", transform=a1.get_xaxis_transform(), fontsize=6.5)
        a1.set_xlim(ch.index.min(), ch.index.max())
        fig.subplots_adjust(left=0.105, right=0.995, top=0.97, bottom=0.2)
        ra.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(ra, dpi=300)
        plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--vao", required=True)
    ap.add_argument("--vu", nargs="+", required=True, help="các cặp block t_m:t_b")
    ap.add_argument("--ra", required=True)
    ap.add_argument("--m", type=float, default=3.0)
    ap.add_argument("--N", type=int, default=24)
    a = ap.parse_args()
    ve(Path(a.vao), [tuple(int(x) for x in v.split(":")) for v in a.vu], Path(a.ra), a.m, a.N)
    print(f"→ {a.ra}")

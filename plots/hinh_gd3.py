"""Biểu đồ GĐ3 (RQ3): bản đồ vùng range-aware giảm/tăng vốn victim (giải tích + mô phỏng), lợi kẻ tấn công và
lãi victim theo α, cái giá với LP lành mạnh. Màu theo bảng màu đã kiểm của `plots.hinh` (dataviz)."""
from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator, FuncFormatter

from plots.hinh import CHU, CHU_PHU, LUOI, MAU, NEN, _hinh, _kieu

# phân kỳ xanh (giảm vốn victim) ↔ đỏ (tăng), giữa xám trung tính
PHAN_KY = LinearSegmentedColormap.from_list("xanh_do", ["#1c5cab", "#86b6ef", "#f0efec", "#ee9a99", "#b8302f"])
MAU_W0 = {10: MAU[0], 50: MAU[1], 200: MAU[2]}
DANG_VICTIM = {"omniscient": "o", "adaptive": "s"}
TEN_VICTIM = {"omniscient": "victim toàn tri", "adaptive": "victim thích nghi"}


def ve_ban_do_vung(dc: pd.DataFrame, gon: pd.DataFrame, path: str | Path, tieu_de: str = "") -> None:
    """(a) Trái: mặt phẳng (u, k) — vùng giải tích range-aware giảm vốn victim (u < (1/√k − 1)² hoặc u > 1, nền
    xanh) / tăng (nền đỏ), điểm = mô phỏng victim toàn tri (`doi_chieu_giai_tich.csv`), màu = log₂(C_RA/C_PR).
    Phải: bản đồ nhiệt log₂ tỷ lệ vốn theo (k × victim) × mức φ (`gon.csv`), chữ = tỷ lệ."""
    fig, (a1, a2) = _hinh(1, 2, (13, 5.4), gridspec_kw=dict(width_ratios=[1, 1.35]))
    _kieu(a1)
    us = np.logspace(-2.2, 0.3, 400)
    ks = np.linspace(0.02, 0.99, 300)
    U, K = np.meshgrid(us, ks)
    nguong = (1 / np.sqrt(K) - 1) ** 2
    tang = (U > nguong) & (U < 1)
    a1.contourf(U, K, tang.astype(float), levels=[-0.5, 0.5, 1.5], colors=["#e6eef8", "#fbe3e3"], zorder=0)
    a1.plot((1 / np.sqrt(ks) - 1) ** 2, ks, color=CHU, linewidth=1.4, label="u = (1/√k − 1)²")
    a1.axvline(1, color=CHU, linewidth=1.0, linestyle=(0, (4, 3)), label="u = 1")
    a1.axhline(0.25, color=CHU_PHU, linewidth=0.8, linestyle=(0, (1, 2)))
    x = dc[dc["ty_le_mo_phong"] > 0]
    sc = a1.scatter(x["u"], x["k"], c=np.log2(x["ty_le_mo_phong"]), cmap=PHAN_KY,
                    norm=TwoSlopeNorm(0, -3.5, 3.5), s=46, edgecolors=NEN, linewidths=1.2, zorder=3)
    z = dc[dc["ty_le_mo_phong"] <= 0]
    a1.scatter(z["u"], z["k"], marker="x", color=CHU, s=30, zorder=3, label="victim rút hẳn (tỷ lệ 0)")
    a1.set_xscale("log")
    a1.set_xlim(us[0], us[-1])
    a1.set_ylim(0, 1)
    a1.set_xlabel("u = [ℓ(1)/(φ(w*)ℓ(w*))]·[(L_Aφ(1) + B)/(L_A + B)]")
    a1.set_ylabel("k = c_V·L_A/(f·V)")
    a1.text(0.012, 0.9, "tăng vốn victim", color="#b8302f", fontsize=8)
    a1.text(0.012, 0.08, "giảm vốn victim", color="#1c5cab", fontsize=8)
    a1.legend(frameon=False, fontsize=7.5, labelcolor=CHU, loc="center left")
    a1.set_title("Giải tích (nền) và mô phỏng (điểm), victim toàn tri", loc="left", fontsize=9, color=CHU)
    cb = fig.colorbar(sc, ax=a1, shrink=0.85)
    cb.set_label("log₂(C_RA/C_PR)", color=CHU_PHU, fontsize=8)
    cb.ax.tick_params(labelsize=7, colors=CHU_PHU)
    cb.outline.set_visible(False)

    g = gon.assign(hang=lambda d: [f"k={k:g} {'TT' if v == 'omniscient' else 'TN'}" for k, v in
                                    zip(d["k"], d["victim_type"])],
                   cot=lambda d: [f"{a:g}/{int(w)}" for a, w in zip(d["alpha"], d["w0"])])
    thu_tu = sorted(g["cot"].unique(), key=lambda s: (float(s.split("/")[0]), int(s.split("/")[1])))
    hang = sorted(g["hang"].unique(), key=lambda s: (float(s.split()[0][2:]), s.split()[1]))
    M = g.pivot_table(index="hang", columns="cot", values="ty_le_von").reindex(index=hang, columns=thu_tu)
    L2 = np.log2(M.clip(lower=1 / 16).to_numpy())
    im = a2.imshow(L2, cmap=PHAN_KY, norm=TwoSlopeNorm(0, -3.5, 3.5), aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M.iat[i, j]
            a2.text(j, i, f"{v:.2f}" if v < 10 else f"{v:.1f}", ha="center", va="center", fontsize=6.5,
                    color="white" if abs(L2[i, j]) > 2 else CHU)
    a2.set_xticks(range(len(thu_tu)), thu_tu, rotation=60, fontsize=7)
    a2.set_yticks(range(len(hang)), hang, fontsize=7)
    a2.set_xlabel("mức φ: α / w₀ (tick)", color=CHU_PHU)
    a2.tick_params(colors=CHU_PHU)
    for s in a2.spines.values():
        s.set_visible(False)
    a2.set_title("Tỷ lệ vốn victim C_RA/C_PR (TT toàn tri, TN thích nghi)", loc="left", fontsize=9, color=CHU)
    fig.suptitle(tieu_de, color=CHU, fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(path, dpi=150, facecolor=NEN)
    plt.close(fig)


def ve_theo_alpha(gon: pd.DataFrame, path: str | Path, tieu_de: str = "",
                  cs=("dc_excess_pct", "lai_victim_hieu"),
                  nhan=("% thay đổi lợi tăng thêm kẻ tấn công", "hiệu lãi/lỗ victim (token1)")) -> None:
    """(b) Hàng = vụ (theo k), cột = chỉ số; x = α (0 = pro-rata), đường = w₀, hình = loại victim. Đơn vị theo cột:
    % so với pro-rata (dc_excess) hoặc token1 (hiệu lãi victim, dương = victim đỡ lỗ)."""
    ks = sorted(gon["k"].unique())
    fig, axs = _hinh(len(ks), len(cs), (5.2 * len(cs), 2.2 * len(ks)), sharex=True, squeeze=False)
    for i, k in enumerate(ks):
        for j, (c, n) in enumerate(zip(cs, nhan)):
            ax = axs[i, j]
            _kieu(ax)
            for vt, dang in DANG_VICTIM.items():
                for w0, m in MAU_W0.items():
                    h = gon[(gon["k"] == k) & (gon["victim_type"] == vt) & (gon["w0"] == w0)].sort_values("alpha")
                    ax.plot([0, *h["alpha"]], [0, *h[c]], marker=dang, ms=4.5, color=m, linewidth=1.4,
                            linestyle="-" if vt == "omniscient" else (0, (3, 2)), mec=NEN, mew=0.8)
            ax.axhline(0, color=CHU_PHU, linewidth=0.8)
            ax.set_title(f"k = {k:g} ({gon.loc[gon['k'] == k, 'scenario_id'].iloc[0]})", loc="left", fontsize=8,
                         color=CHU)
            if i == len(ks) - 1:
                ax.set_xlabel("α (φ = min(1, (w/w₀)^α))")
            if i == 0:
                ax.set_ylabel(n, fontsize=8)
            if c.endswith("pct"):
                ax.set_yscale("symlog", linthresh=100, linscale=2)
                ax.yaxis.set_major_locator(FixedLocator([-100, -50, 0, 50, 100, 300, 1000]))
                ax.yaxis.set_minor_locator(FixedLocator([]))
                ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    h = [Line2D([], [], color=m, linewidth=2, label=f"w₀ = {w0}") for w0, m in MAU_W0.items()]
    h += [Line2D([], [], color=CHU_PHU, marker=d, linestyle="-" if v == "omniscient" else (0, (3, 2)),
                 label=TEN_VICTIM[v]) for v, d in DANG_VICTIM.items()]
    fig.legend(handles=h, loc="lower center", ncol=len(h), frameon=False, fontsize=8, labelcolor=CHU)
    fig.suptitle(tieu_de, color=CHU, fontsize=11)
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    fig.savefig(path, dpi=150, facecolor=NEN)
    plt.close(fig)


def ve_lp(gon: pd.DataFrame, path: str | Path, tieu_de: str = "") -> None:
    """(c) Cái giá với LP lành mạnh (trung vị qua 6 vụ × 2 victim): % thay đổi phí/vốn của LP tự chọn w (trái),
    LP dải cố định 10 tick (giữa), và trượt giá lệnh mua 1.000 token1 (phải), theo α, đường = w₀."""
    cs = [("lp0_phi_pct", "LP tự chọn w: % phí/vốn"), ("lp1_phi_pct", "LP cố định 10 tick: % phí/vốn"),
          ("lp0_truot_pct", "% trượt giá lệnh 1.000 token1")]
    fig, axs = _hinh(1, 3, (14, 4.2))
    tv = gon.groupby(["alpha", "w0"])[[c for c, _ in cs]].median().reset_index()
    for ax, (c, n) in zip(axs, cs):
        _kieu(ax)
        for w0, m in MAU_W0.items():
            h = tv[tv["w0"] == w0].sort_values("alpha")
            ax.plot([0, *h["alpha"]], [0, *h[c]], marker="o", ms=6, color=m, linewidth=2, mec=NEN, mew=1.5,
                    label=f"w₀ = {w0}")
        ax.axhline(0, color=CHU_PHU, linewidth=0.8)
        ax.set_xlabel("α")
        ax.set_title(n, loc="left", fontsize=9, color=CHU)
    axs[0].legend(frameon=False, fontsize=8, labelcolor=CHU)
    fig.suptitle(tieu_de, color=CHU, fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(path, dpi=150, facecolor=NEN)
    plt.close(fig)

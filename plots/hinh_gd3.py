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

from plots.hinh import CHU, CHU_PHU, DPI, LUOI, MAU, NEN, _hinh, _kieu, so_vn

# phân kỳ xanh (giảm vốn victim) ↔ đỏ (tăng), giữa xám trung tính
PHAN_KY = LinearSegmentedColormap.from_list("xanh_do", ["#1c5cab", "#86b6ef", "#f0efec", "#ee9a99", "#b8302f"])
MAU_W0 = {10: MAU[0], 50: MAU[1], 200: MAU[2]}
DANG_VICTIM = {"omniscient": "o", "adaptive": "s"}
TEN_VICTIM = {"omniscient": "nạn nhân toàn tri", "adaptive": "nạn nhân thích nghi"}


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
    a1.scatter(z["u"], z["k"], marker="x", color=CHU, s=30, zorder=3, label="nạn nhân rút hẳn (tỷ lệ 0)")
    a1.set_xscale("log")
    a1.set_xlim(us[0], us[-1])
    a1.set_ylim(0, 1)
    a1.set_xlabel("u = [ℓ(1)/(φ(w*)ℓ(w*))]·[(L_Aφ(1) + B)/(L_A + B)]")
    a1.set_ylabel("k = c_V·L_A/(f·V)")
    a1.text(0.012, 0.9, "tăng vốn nạn nhân", color="#b8302f", fontsize=8)
    a1.text(0.012, 0.08, "giảm vốn nạn nhân", color="#1c5cab", fontsize=8)
    a1.legend(frameon=False, fontsize=7.5, labelcolor=CHU, loc="center left")
    a1.set_title("Giải tích (nền) và mô phỏng (điểm), nạn nhân toàn tri", loc="left", fontsize=9, color=CHU)
    cb = fig.colorbar(sc, ax=a1, shrink=0.85)
    cb.set_label("log₂(C_RA/C_PR)", color=CHU_PHU, fontsize=8)
    cb.ax.tick_params(labelsize=7, colors=CHU_PHU)
    cb.outline.set_visible(False)

    g = gon.assign(hang=lambda d: [f"k = {so_vn(k)} {'TT' if v == 'omniscient' else 'TN'}" for k, v in
                                    zip(d["k"], d["victim_type"])],
                   cot=lambda d: [f"{so_vn(a)}/{int(w)}" for a, w in zip(d["alpha"], d["w0"])])
    thu_tu = list(dict.fromkeys(g.sort_values(["alpha", "w0"])["cot"]))
    hang = list(dict.fromkeys(g.sort_values(["k", "victim_type"], ascending=[True, True])["hang"]))
    M = g.pivot_table(index="hang", columns="cot", values="ty_le_von").reindex(index=hang, columns=thu_tu)
    L2 = np.log2(M.clip(lower=1 / 16).to_numpy())
    im = a2.imshow(L2, cmap=PHAN_KY, norm=TwoSlopeNorm(0, -3.5, 3.5), aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M.iat[i, j]
            a2.text(j, i, so_vn(v, 2) if v < 10 else so_vn(v, 1), ha="center", va="center", fontsize=6.5,
                    color="white" if abs(L2[i, j]) > 2 else CHU)
    a2.set_xticks(range(len(thu_tu)), thu_tu, rotation=60, fontsize=7)
    a2.set_yticks(range(len(hang)), hang, fontsize=7)
    a2.set_xlabel("mức φ: α / w₀ (tick)", color=CHU_PHU)
    a2.tick_params(colors=CHU_PHU)
    for s in a2.spines.values():
        s.set_visible(False)
    a2.set_title("Tỷ lệ vốn nạn nhân C_RA/C_PR (TT toàn tri, TN thích nghi)", loc="left", fontsize=9, color=CHU)
    fig.suptitle(tieu_de, color=CHU, fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(path, dpi=DPI, facecolor=NEN)
    plt.close(fig)


def ve_theo_alpha(gon: pd.DataFrame, path: str | Path, tieu_de: str = "",
                  cs=("dc_excess_pct", "lai_victim_hieu"),
                  nhan=("lợi tăng thêm kẻ tấn công (% so với pro-rata)", "hiệu lãi/lỗ nạn nhân (token1)")) -> None:
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
            ax.set_title(f"k = {so_vn(k)} ({gon.loc[gon['k'] == k, 'scenario_id'].iloc[0]})", loc="left", fontsize=8,
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
    fig.savefig(path, dpi=DPI, facecolor=NEN)
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
        ax.set_xlabel("α (không đơn vị)")
        ax.set_ylabel("% so với pro-rata")
        ax.set_title(n, loc="left", fontsize=9, color=CHU)
    axs[0].legend(frameon=False, fontsize=8, labelcolor=CHU)
    fig.suptitle(tieu_de, color=CHU, fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(path, dpi=DPI, facecolor=NEN)
    plt.close(fig)


def ve_theo_wA(tv: pd.DataFrame, gon_opt: pd.DataFrame, path: str | Path, tieu_de: str = "",
               vu=("KN_L27_10", "KN_L27_22", "L27_10", "L27_16"), alpha: float = 2.0) -> None:
    """(d) Kẻ tấn công nới tường: hàng trên = vốn victim / pro-rata, hàng dưới = dc_excess / pro-rata (trung vị 10 seed,
    bảng `wA_trung_vi.csv`), theo w_A/w₀ (trục log), cột = vụ, đường = w₀, nét = loại victim; sao = w_A tối ưu
    (trung vị dc_excess lớn nhất, `gon_wA.csv`). Vạch ngang 1 = như pro-rata."""
    fig, axs = _hinh(2, len(vu), (4 * len(vu), 7), sharex=True, squeeze=False)
    for j, v in enumerate(vu):
        g = tv[tv["scenario_id"] == v]
        for i, (c, n) in enumerate((("von_victim", "vốn nạn nhân (lần pro-rata)"),
                                    ("dc_excess", "lợi tăng thêm (lần pro-rata)"))):
            ax = axs[i, j]
            _kieu(ax)
            for vt in DANG_VICTIM:
                goc = g[(g["alpha"] == 0) & (g["victim_type"] == vt)][c]
                if goc.empty or goc.iloc[0] == 0:
                    continue
                for w0, m in ((50, MAU[1]), (200, MAU[2])):
                    h = g[(g["alpha"] == alpha) & (g["w0"] == w0) & (g["victim_type"] == vt)].sort_values("w_A")
                    x = h["w_A"] / w0
                    y = (h[c] / goc.iloc[0]).clip(lower=1e-2)
                    ax.plot(x, y, marker=DANG_VICTIM[vt], ms=5, color=m, linewidth=1.6, mec=NEN, mew=1,
                            linestyle="-" if vt == "omniscient" else (0, (3, 2)))
                    o = gon_opt[(gon_opt["scenario_id"] == v) & (gon_opt["victim_type"] == vt)
                                & (gon_opt["alpha"] == alpha) & (gon_opt["w0"] == w0)]
                    if len(o):
                        wa = o["w_A_toi_uu"].iloc[0]
                        yy = h.loc[h["w_A"] == wa, c]
                        if len(yy):
                            ax.plot(wa / w0, max(yy.iloc[0] / goc.iloc[0], 1e-2), "*", ms=13, color=m, mec=CHU,
                                    mew=0.6, zorder=4)
            ax.axhline(1, color=CHU_PHU, linewidth=0.8)
            ax.set_xscale("log")
            ax.set_yscale("log")
            if i == 0:
                k = g["k"].iloc[0]
                ax.set_title(f"{v} (k = {so_vn(k)})", loc="left", fontsize=9, color=CHU)
            if j == 0:
                ax.set_ylabel(n)
            if i == 1:
                ax.set_xlabel("w_A / w₀ (không đơn vị)")
    h = [Line2D([], [], color=m, linewidth=2, label=f"w₀ = {w0}") for w0, m in ((50, MAU[1]), (200, MAU[2]))]
    h += [Line2D([], [], color=CHU_PHU, marker=d, linestyle="-" if v == "omniscient" else (0, (3, 2)),
                 label=TEN_VICTIM[v]) for v, d in DANG_VICTIM.items()]
    h.append(Line2D([], [], marker="*", ls="", color=CHU_PHU, ms=11, label="w_A tối ưu của kẻ tấn công"))
    fig.legend(handles=h, loc="lower center", ncol=len(h), frameon=False, fontsize=8, labelcolor=CHU)
    fig.suptitle(tieu_de, color=CHU, fontsize=11)
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    fig.savefig(path, dpi=DPI, facecolor=NEN)
    plt.close(fig)


def ve_so_sanh_wA(ss: pd.DataFrame, path: str | Path, tieu_de: str = "") -> None:
    """(e) Tường 1 tick (rỗng) vs tường tối ưu (đặc): tỷ lệ vốn victim (trái, log) và % đổi dc_excess (phải) theo k,
    mỗi điểm một (α, w₀) — trung vị qua các mức, thanh = min–max; nét = loại victim. Giải tích tường tối ưu: đường đen."""
    fig, (a1, a2) = _hinh(1, 2, (12, 4.6))
    for ax, (c1, c2, n) in zip((a1, a2), (("ty_le_von_1tick", "ty_le_von_toi_uu", "vốn nạn nhân C_RA/C_PR (lần)"),
                                          ("dc_excess_pct_1tick", "dc_excess_pct_toi_uu",
                                           "lợi tăng thêm kẻ tấn công (% so với pro-rata)"))):
        _kieu(ax)
        for vt, lech in (("omniscient", -0.008), ("adaptive", 0.008)):
            g = ss[ss["victim_type"] == vt].groupby("k")
            for c, mau, rong in ((c1, MAU[0], True), (c2, MAU[1], False)):
                tv, lo, hi = g[c].median(), g[c].min(), g[c].max()
                x = np.array(tv.index) + lech + (0.004 if not rong else -0.004)
                ax.errorbar(x, tv, yerr=[tv - lo, hi - tv], fmt="none", ecolor=mau, elinewidth=1, alpha=0.6)
                ax.plot(x, tv, DANG_VICTIM[vt], ms=7, color=mau if not rong else NEN, mec=mau, mew=1.6,
                        linestyle="none")
        if c1.startswith("ty_le"):
            ks = np.linspace(0.25, 0.96, 100)
            ax.plot(ks, 1 / (4 * ks * (1 / np.sqrt(ks) - 1)), color=CHU, linewidth=1.2, label="giải tích tường tối ưu")
            ax.plot([0.08, 0.25], [1, 1], color=CHU, linewidth=1.2)
            ax.set_yscale("log")
            ax.axhline(1, color=CHU_PHU, linewidth=0.8, linestyle=(0, (2, 2)))
            ax.legend(frameon=False, fontsize=8, labelcolor=CHU, loc="upper left")
        else:
            ax.set_yscale("symlog", linthresh=100, linscale=2)
            ax.yaxis.set_major_locator(FixedLocator([-100, -50, 0, 50, 100, 300, 1000]))
            ax.yaxis.set_minor_locator(FixedLocator([]))
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
            ax.axhline(0, color=CHU_PHU, linewidth=0.8)
        ax.set_xlabel("k = c_V·L_A/(f·V) (không đơn vị)")
        ax.set_ylabel(n)
        ax.set_title(n, loc="left", fontsize=9, color=CHU)
    h = [Line2D([], [], marker="o", ls="", color=NEN, mec=MAU[0], mew=1.6, ms=7, label="tường 1 tick"),
         Line2D([], [], marker="o", ls="", color=MAU[1], ms=7, label="tường tối ưu (w_A)")]
    h += [Line2D([], [], marker=d, ls="", color=CHU_PHU, ms=7, label=TEN_VICTIM[v]) for v, d in DANG_VICTIM.items()]
    fig.legend(handles=h, loc="lower center", ncol=len(h), frameon=False, fontsize=8, labelcolor=CHU)
    fig.suptitle(tieu_de, color=CHU, fontsize=11)
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))
    fig.savefig(path, dpi=DPI, facecolor=NEN)
    plt.close(fig)

"""Biểu đồ RQ1 (matplotlib, PNG cho báo cáo): timeline một vụ (như Hình 1 bài gốc), hộp RV theo pha
(Hình 2), cột chia nhóm Bảng 4 / Bảng 7 mô phỏng cạnh bài gốc. Màu theo bảng màu đã kiểm (dataviz)."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from metrics.phases import PHA, label_phases, phases, wall_liquidity
from metrics.timeseries import build_timeseries

# bảng màu phân loại (thứ tự cố định), mặt nền, chữ
MAU = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
NEN, CHU, CHU_PHU, LUOI = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
MAU_VAI = {"bg": MAU[0], "farmer": MAU[1], "arb": MAU[2], "attacker": MAU[3], "victim": MAU[4]}
TEN_VAI = {"bg": "nền", "farmer": "farmer", "arb": "arb", "attacker": "kẻ tấn công", "victim": "nạn nhân"}
MAU_PHA = {"Before": "#f1f0ec", "Prep": "#e6eef8", "Attack": "#fbe6dc", "Post": "#eeeeea"}


def _kieu(ax) -> None:
    """Trục nhạt, lưới ngang mảnh, chữ màu chữ (không dùng màu chuỗi)."""
    ax.set_facecolor(NEN)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(LUOI)
    ax.tick_params(colors=CHU_PHU, labelsize=8)
    ax.yaxis.grid(True, color=LUOI, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.xaxis.label.set_color(CHU_PHU)
    ax.yaxis.label.set_color(CHU_PHU)


def _hinh(nrows: int, ncols: int, size: tuple[float, float], **kw):
    """Tạo figure nền sáng."""
    fig, axs = plt.subplots(nrows, ncols, figsize=size, facecolor=NEN, **kw)
    return fig, axs


def ve_timeline(df: pd.DataFrame, path: str | Path, tieu_de: str = "") -> dict:
    """Timeline một vụ, 3 tầng chung trục thời gian (giờ): giá bể + giá ngoài (token1/token0);
    thanh khoản tick tường theo bên (kẻ tấn công / nạn nhân, đơn vị L); khối lượng swap mỗi giờ theo vai (token1).
    Tô nền 4 pha, vạch mốc t_m, t_peak, t_0, t_b. Trả `phases(df)`."""
    ph = phases(df)
    ts = build_timeseries(df)
    fig, (a1, a2, a3) = _hinh(3, 1, (9, 7.5), sharex=True, gridspec_kw=dict(height_ratios=[1.1, 1, 1]))
    for ax in (a1, a2, a3):
        _kieu(ax)
        for ten, w in ph["windows"].items():
            if w is not None:
                ax.axvspan(w[0] - 0.5, w[1] + 0.5, color=MAU_PHA[ten], zorder=0, linewidth=0)
        for k in ("t_m", "t_peak", "t_0", "t_b"):
            if ph[k] is not None:
                ax.axvline(ph[k], color=CHU_PHU, linewidth=0.8, linestyle=(0, (3, 3)), zorder=1)

    a1.plot(ts.index, ts["price"], color=MAU[0], linewidth=2, label="giá bể")
    a1.plot(ts.index, ts["p_ext"], color=MAU[1], linewidth=1.2, linestyle="--", label="giá ngoài $P_e$")
    a1.set_ylabel("giá (token1/token0)")
    a1.legend(frameon=False, fontsize=8, labelcolor=CHU, loc="lower left")
    y_top = a1.get_ylim()[1]
    nhan_moc: dict[int, list[str]] = {}
    for k, nhan in (("t_m", "t_m"), ("t_peak", "t_{peak}"), ("t_0", "t_0"), ("t_b", "t_b")):
        if ph[k] is not None:
            nhan_moc.setdefault(ph[k], []).append(nhan)
    for t, ds in nhan_moc.items():                       # mốc trùng giờ gộp một nhãn, ví dụ t_0 = t_b
        a1.text(t, y_top, "$" + " = ".join(ds) + "$", ha="center", va="bottom", fontsize=8, color=CHU_PHU)
    for ten, w in ph["windows"].items():
        if w is not None and w[1] - w[0] >= 10:
            a1.text((w[0] + w[1]) / 2, a1.get_ylim()[0], ten, ha="center", va="bottom", fontsize=8, color=CHU_PHU)

    # thanh khoản tick tường theo bên, phát lại từng sự kiện rồi lấy giá trị cuối mỗi giờ
    mb = df[df["kind"].isin(["mint", "burn"]) & (df["tick_lower"] == ph["wall_tick_lower"])
            & (df["tick_upper"] == ph["wall_tick_upper"])].sort_values(["t", "seq"])
    mb = mb.assign(dL=np.where(mb["kind"] == "mint", 1.0, -1.0) * mb["liquidity"])
    xs = ts.index
    lop = []
    for vai in ("attacker", "victim"):
        s = mb[mb["role"] == vai].groupby("t")["dL"].sum().reindex(xs, fill_value=0).cumsum().clip(lower=0)
        lop.append((vai, s))
    khac = mb[~mb["role"].isin(["attacker", "victim"])].groupby("t")["dL"].sum().reindex(xs, fill_value=0).cumsum()
    if (khac.abs() > 0).any():
        lop.append(("bg", khac.clip(lower=0)))
    a2.stackplot(xs, *[s.values for _, s in lop], colors=[MAU_VAI[v] for v, _ in lop],
                 labels=[TEN_VAI[v] for v, _ in lop], edgecolor=NEN, linewidth=0.5, step="post")
    a2.set_ylabel("L trên tick tường")
    a2.legend(frameon=False, fontsize=8, labelcolor=CHU, loc="upper left")

    vai_co = [v for v in MAU_VAI if f"vol_{v}" in ts.columns and ts[f"vol_{v}"].sum() > 0]
    day = np.zeros(len(ts))
    for v in vai_co:
        a3.bar(xs, ts[f"vol_{v}"], bottom=day, width=1.0, color=MAU_VAI[v], label=TEN_VAI[v], linewidth=0)
        day = day + ts[f"vol_{v}"].values
    a3.set_ylabel("khối lượng / giờ (token1)")
    a3.set_xlabel("thời gian (giờ)")
    a3.legend(frameon=False, fontsize=8, labelcolor=CHU, ncol=len(vai_co), loc="upper left")
    if tieu_de:
        fig.suptitle(tieu_de, color=CHU, fontsize=11, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path, dpi=160, facecolor=NEN)
    plt.close(fig)
    return ph


def ve_hop_rv(tom_tat: pd.DataFrame, path: str | Path) -> None:
    """Hộp RV theo 4 pha (như Hình 2 bài gốc): hộp = P25–P75, vạch giữa = trung vị, râu = min–max; trục log."""
    fig, ax = _hinh(1, 1, (6, 3.6))
    _kieu(ax)
    data = [pd.to_numeric(tom_tat[f"RV_{p}"], errors="coerce").dropna().clip(lower=1e-4).values for p in PHA]
    bp = ax.boxplot(data, whis=(0, 100), widths=0.45, patch_artist=True, tick_labels=list(PHA),
                    medianprops=dict(color=CHU, linewidth=1.5), whiskerprops=dict(color=CHU_PHU),
                    capprops=dict(color=CHU_PHU), boxprops=dict(edgecolor=CHU_PHU))
    for b in bp["boxes"]:
        b.set_facecolor(MAU[0] + "55")
    for i, d in enumerate(data, start=1):
        ax.text(i + 0.3, np.median(d), f"{np.median(d):.3f}", va="center", fontsize=8, color=CHU_PHU)
    ax.set_yscale("log")
    ax.set_ylabel("RV = √Σr² (r theo Δtick)")
    ax.set_title(f"Biến động theo pha, {len(tom_tat)} vụ mô phỏng", color=CHU, fontsize=10, loc="left")
    fig.tight_layout()
    fig.savefig(path, dpi=160, facecolor=NEN)
    plt.close(fig)


def _cot_cap(ax, nhom: list[str], mo_phong: np.ndarray, bai_goc: np.ndarray, tieu_de: str) -> None:
    """Cột đôi % số vụ theo nhóm: mô phỏng (màu 1) cạnh bài gốc (màu 2), nhãn % trên đầu cột."""
    _kieu(ax)
    x = np.arange(len(nhom))
    w = 0.38
    for dx, y, mau, ten in ((-w / 2 - 0.01, mo_phong, MAU[0], "mô phỏng"), (w / 2 + 0.01, bai_goc, MAU[1], "bài gốc")):
        ax.bar(x + dx, y, width=w, color=mau, label=ten, linewidth=0)
        for xi, yi in zip(x + dx, y):
            if yi > 0:
                ax.text(xi, yi + 1, f"{yi:.0f}", ha="center", va="bottom", fontsize=7, color=CHU_PHU)
    ax.set_xticks(x, nhom)
    ax.set_ylim(0, 105)
    ax.set_title(tieu_de, color=CHU, fontsize=10, loc="left")


def ve_bang4(b4: pd.DataFrame, path: str | Path) -> None:
    """Bảng 4 dạng hình: 3 ô Prep / Attack / Post, % số vụ theo nhóm volume lift, mô phỏng cạnh bài gốc."""
    fig, axs = _hinh(1, 3, (11, 3.4), sharey=True)
    for ax, p in zip(axs, ("Prep", "Attack", "Post")):
        _cot_cap(ax, list(b4.index), b4[f"{p}_mo_phong_%"].values, b4[f"{p}_bai_goc_%"].values, f"Lift {p}")
    axs[0].set_ylabel("% số vụ")
    axs[0].legend(frameon=False, fontsize=8, labelcolor=CHU, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=160, facecolor=NEN)
    plt.close(fig)


def ve_bang7(b7: pd.DataFrame, path: str | Path) -> None:
    """Bảng 7 dạng hình: % số vụ theo độ tụt thanh khoản tick tường tại t_b, mô phỏng cạnh bài gốc."""
    fig, ax = _hinh(1, 1, (6.5, 3.4))
    _cot_cap(ax, list(b7.index), b7["drop_mo_phong_%"].values, b7["drop_bai_goc_%"].values,
             "Độ tụt thanh khoản tick tường tại $t_b$")
    ax.set_ylabel("% số vụ")
    ax.legend(frameon=False, fontsize=8, labelcolor=CHU, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=160, facecolor=NEN)
    plt.close(fig)

"""Biểu đồ RQ1 (matplotlib, PNG cho báo cáo): timeline một vụ (như Hình 1 bài gốc), hộp RV theo pha
(Hình 2), cột chia nhóm Bảng 4 / Bảng 7 mô phỏng cạnh bài gốc. Màu theo bảng màu đã kiểm (dataviz)."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import matplotlib
import matplotlib.collections
import matplotlib.lines

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from matplotlib.ticker import FuncFormatter

from metrics.phases import PHA, label_phases, phases, wall_liquidity
from metrics.timeseries import build_timeseries

# kiểu chung cho mọi hình của bài (RQ1, GĐ2, GĐ3): một họ font, một bộ cỡ chữ, một độ phân giải
DPI = 160
matplotlib.rcParams.update({
    "font.family": ["DejaVu Sans"],                   # DejaVu kèm matplotlib, đủ glyph
    "font.size": 9, "axes.titlesize": 9, "axes.labelsize": 9, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "legend.fontsize": 8, "figure.titlesize": 11, "axes.unicode_minus": True, "hatch.linewidth": 0.8,
})

# "Kiểu in bài báo": hình vẽ đúng khổ in LNCS (rộng ≤ 4,8 in), chữ thật 6,5–8 pt, lưu 300 dpi. Bật bằng `with in_bai():`.
IN = False


@contextmanager
def in_bai():
    """Bật kiểu in bài báo trong khối `with`: chữ trục 8 pt, số trục 7 pt, chú giải 6,5 pt, marker/nét nhỏ; các hàm vẽ
    đọc `hinh.IN` để chọn figsize in thật. Trả rcParams về như cũ khi thoát."""
    global IN
    cu = dict(matplotlib.rcParams)
    IN = True
    matplotlib.rcParams.update({"font.size": 7, "axes.titlesize": 8, "axes.labelsize": 8, "xtick.labelsize": 7,
                                "ytick.labelsize": 7, "legend.fontsize": 6.5, "axes.linewidth": 0.6,
                                "xtick.major.width": 0.5, "ytick.major.width": 0.5, "xtick.major.size": 2.5,
                                "ytick.major.size": 2.5})
    try:
        yield
    finally:
        IN = False
        matplotlib.rcParams.update(cu)


def fs(x: float) -> float:
    """Cỡ chữ: giữ `x` ở khổ lớn, 6,5 pt (nhãn/chú giải) ở kiểu in bài báo."""
    return 6.5 if IN else x


def ms(x: float) -> float:
    """Cỡ marker: nhỏ còn khoảng nửa ở kiểu in bài báo."""
    return 0.5 * x if IN else x


def lw(x: float) -> float:
    """Độ dày nét: nhân 0,6 ở kiểu in bài báo."""
    return 0.6 * x if IN else x


def dpi() -> int:
    """Độ phân giải lưu: 300 khi in bài báo, `DPI` khi khác."""
    return 300 if IN else DPI


# bảng màu phân loại (thứ tự cố định), mặt nền, chữ
MAU = ["#2a78d6", "#eb6834", "#7b57c9", "#eda100", "#e87ba4"]
NEN, CHU, CHU_PHU, LUOI = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
MAU_VAI = {"bg": MAU[0], "farmer": MAU[1], "arb": MAU[2], "attacker": MAU[3], "victim": MAU[4]}
TEN_VAI = {"bg": "background", "farmer": "farmer", "arb": "arbitrageur", "attacker": "attacker", "victim": "victim"}
MAU_PHA = {"Before": "#f1f0ec", "Prep": "#e6eef8", "Attack": "#fbe6dc", "Post": "#eeeeea"}


def so_vn(v: float, nd: int | None = None) -> str:
    """Số theo quy ước tiếng Anh cho nhãn hình: chấm thập phân, phẩy ngăn nghìn, dấu trừ U+2212 (`nd` = số chữ số
    sau chấm; None = tự gọn). Ví dụ 1234.5 → "1,234.5", 0.0025 → "0.0025". (Tên hàm giữ nguyên vì nhiều nơi gọi.)"""
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "–"
    if nd is not None:
        v = round(float(v), nd) + 0.0                     # tránh "−0"
        s = f"{v:,.{nd}f}"
    elif abs(v) >= 1e5 or float(v).is_integer():
        s = f"{v:,.0f}"
    else:
        s = f"{v:,.6g}"
    return s.replace("-", "−")


TRUC_VN = FuncFormatter(lambda v, _: so_vn(round(v, 10)))


def _kieu(ax) -> None:
    """Trục nhạt, lưới ngang mảnh, chữ màu chữ (không dùng màu chuỗi); số trên trục theo kiểu Việt (phẩy thập
    phân). Trục log đặt sau sẽ tự thay formatter."""
    ax.set_facecolor(NEN)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(LUOI)
    ax.tick_params(colors=CHU_PHU, labelsize=7 if IN else 8)
    ax.yaxis.grid(True, color=LUOI, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.xaxis.label.set_color(CHU_PHU)
    ax.yaxis.label.set_color(CHU_PHU)
    ax.xaxis.set_major_formatter(TRUC_VN)
    ax.yaxis.set_major_formatter(TRUC_VN)


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
    fig, (a1, a2, a3) = _hinh(3, 1, (3.9, 4.0) if IN else (9, 7.5), sharex=True, gridspec_kw=dict(height_ratios=[1.1, 1, 1]))
    for ax in (a1, a2, a3):
        _kieu(ax)
        for ten, w in ph["windows"].items():
            if w is not None:
                ax.axvspan(w[0] - 0.5, w[1] + 0.5, color=MAU_PHA[ten], zorder=0, linewidth=0)
        for k in ("t_m", "t_peak", "t_0", "t_b"):
            if ph[k] is not None:
                ax.axvline(ph[k], color=CHU_PHU, linewidth=lw(0.8), linestyle=(0, (3, 3)), zorder=1)

    a1.plot(ts.index, ts["price"], color=MAU[0], linewidth=lw(2), label="pool price")
    a1.plot(ts.index, ts["p_ext"], color=MAU[1], linewidth=lw(1.2), linestyle="--", label="external price $P_e$")
    a1.set_ylabel("price" if IN else "price (token1/token0)")
    a1.legend(frameon=True, facecolor="white", framealpha=1, edgecolor="none", fontsize=fs(8), labelcolor=CHU,
              loc="center left", bbox_to_anchor=(0.10, 0.70))
    y_top = a1.get_ylim()[1]
    nhan_moc: dict[int, list[str]] = {}
    for k, nhan in (("t_m", "t_m"), ("t_peak", "t_{peak}"), ("t_0", "t_0"), ("t_b", "t_b")):
        if ph[k] is not None:
            nhan_moc.setdefault(ph[k], []).append(nhan)
    for t, ds in nhan_moc.items():                       # mốc trùng giờ gộp một nhãn, ví dụ t_0 = t_b
        a1.text(t, y_top, "$" + " = ".join(ds) + "$", ha="center", va="bottom", fontsize=fs(8), color=CHU_PHU)
    for ten, w in ph["windows"].items():
        if w is not None and w[1] - w[0] >= 10:
            y0, y1 = a1.get_ylim()
            a1.text(w[1] - 2 if ten == "Before" else (w[0] + w[1]) / 2, y0 + 0.30 * (y1 - y0), ten,
                    ha="right" if ten == "Before" else "center", va="center", fontsize=fs(8), color=CHU_PHU)

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
    a2.stackplot(xs, *[s.values / 1e8 for _, s in lop], colors=[MAU_VAI[v] for v, _ in lop],
                 labels=[TEN_VAI[v] for v, _ in lop], edgecolor=NEN, linewidth=0.5, step="post")
    a2.set_ylabel("$L$ (×10⁸)" if IN else "L on wall tick (×10⁸)")
    a2.legend(frameon=True, facecolor="white", framealpha=1, edgecolor="none", fontsize=fs(8), labelcolor=CHU,
              loc="upper left")

    vai_co = [v for v in MAU_VAI if f"vol_{v}" in ts.columns and ts[f"vol_{v}"].sum() > 0]
    day = np.zeros(len(ts))
    for v in vai_co:
        a3.bar(xs, ts[f"vol_{v}"], bottom=day, width=1.0, color=MAU_VAI[v], label=TEN_VAI[v], linewidth=0)
        day = day + ts[f"vol_{v}"].values
    a3.set_ylabel("volume (token1/h)" if IN else "volume (token1/hour)")
    a3.set_xlabel("time (hours)")
    a3.legend(frameon=True, facecolor="white", framealpha=1, edgecolor="none", fontsize=fs(8), labelcolor=CHU,
              ncol=len(vai_co), loc="upper left",
              columnspacing=0.8, handlelength=1.2)
    fig.tight_layout(pad=0.4) if IN else fig.tight_layout()
    fig.savefig(path, dpi=dpi(), facecolor=NEN)
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
        ax.text(i + 0.3, np.median(d), so_vn(np.median(d), 3), va="center", fontsize=8, color=CHU_PHU)
    ax.set_yscale("log")
    ax.set_ylabel("RV = √Σr² (log-return, unitless)")
    fig.tight_layout()
    fig.savefig(path, dpi=DPI, facecolor=NEN)
    plt.close(fig)


def _cot_cap(ax, nhom: list[str], mo_phong: np.ndarray, bai_goc: np.ndarray, tieu_de: str) -> None:
    """Cột đôi % số vụ theo nhóm: mô phỏng (màu 1) cạnh bài gốc (màu 2), nhãn % trên đầu cột."""
    _kieu(ax)
    x = np.arange(len(nhom))
    w = 0.38
    for dx, y, mau, ten in ((-w / 2 - 0.01, mo_phong, MAU[0], "simulation"), (w / 2 + 0.01, bai_goc, MAU[1], "original paper")):
        ax.bar(x + dx, y, width=w, color=mau, label=ten, linewidth=0)
        for xi, yi in zip(x + dx, y):
            if yi > 0:
                ax.text(xi, yi + 1, f"{yi:.0f}", ha="center", va="bottom", fontsize=7, color=CHU_PHU)
    ax.set_xticks(x, list(nhom))
    ax.set_ylim(0, 105)
    ax.set_title(tieu_de, color=CHU, fontsize=10, loc="left")


def ve_bang4(b4: pd.DataFrame, path: str | Path) -> None:
    """Bảng 4 dạng hình: 3 ô Prep / Attack / Post, % số vụ theo nhóm volume lift, mô phỏng cạnh bài gốc."""
    fig, axs = _hinh(1, 3, (11, 3.4), sharey=True)
    for ax, p in zip(axs, ("Prep", "Attack", "Post")):
        _cot_cap(ax, list(b4.index), b4[f"{p}_mo_phong_%"].values, b4[f"{p}_bai_goc_%"].values, f"{p} phase")
        ax.set_xlabel("volume lift (× Before level)")
    axs[0].set_ylabel("% of episodes")
    axs[0].legend(frameon=False, fontsize=8, labelcolor=CHU, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=DPI, facecolor=NEN)
    plt.close(fig)


def ve_bang7(b7: pd.DataFrame, path: str | Path) -> None:
    """Bảng 7 dạng hình: % số vụ theo độ tụt thanh khoản tick tường tại t_b, mô phỏng cạnh bài gốc."""
    fig, ax = _hinh(1, 1, (6.5, 3.4))
    _cot_cap(ax, list(b7.index), b7["drop_mo_phong_%"].values, b7["drop_bai_goc_%"].values,
             "")
    ax.set_xlabel(r"wall-tick liquidity drop at $t_b$: $(L_{\max} - L(t_b))/L_{\max}$ (%)")
    ax.set_ylabel("% of episodes")
    ax.legend(frameon=False, fontsize=8, labelcolor=CHU, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=DPI, facecolor=NEN)
    plt.close(fig)


def dat_nhan(fig, ax, items: list[tuple[float, float, str]], fontsize: float = 7.0, gop_px: float = 45.0,
             thu_cong: list | None = None) -> None:
    """Ghi nhãn chữ cho các điểm `(x, y, chữ)` trên `ax` sao cho không đè nhau và không đè điểm: mỗi chữ chỉ ghi một
    lần (hai điểm cùng chữ cách nhau < `gop_px` pixel thì gộp một nhãn ở trung điểm; xa hơn thì ghi từng điểm),
    thử lần lượt 32 vị trí quanh điểm (xa dần) và lấy vị trí đầu tiên không chồng nhãn đã đặt / điểm dữ liệu / mép trục.
    `thu_cong` = danh sách `(chữ, (x, y) điểm, (x, y) vị trí nhãn)` đặt tay (toạ độ dữ liệu) cho cụm có chữ đó và
    chứa điểm cách `(x, y)` < `gop_px` pixel; nhãn đặt tay có đường dẫn mảnh. Gọi SAU `tight_layout`."""
    fig.canvas.draw()
    rd = fig.canvas.get_renderer()
    W, H = fig.bbox.width, fig.bbox.height
    td = ax.transData
    def _goc(t: str) -> str:
        return t.rstrip("0123456789")

    nhom: dict[str, list[tuple[float, float, str]]] = {}
    for x, y, t in items:
        px = td.transform((x, y))
        nhom.setdefault(_goc(t), []).append((float(px[0]), float(px[1]), t))
    diem = [td.transform((x, y)) for x, y, _ in items]
    cho: list = []
    for g, ps in nhom.items():                                # gộp điểm cùng họ gần nhau: "warn15/20/40"
        cum: list[list[tuple[float, float, str]]] = []
        for p in ps:
            for c in cum:
                if min(np.hypot(p[0] - q[0], p[1] - q[1]) for q in c) < gop_px:
                    c.append(p)
                    break
            else:
                cum.append([p])
        for c in cum:
            so = sorted({q[2][len(g):] for q in c}, key=lambda v: (len(v), v))
            t = g + "/".join(so) if len(so) > 1 or so[0] else g
            cho.append((t, float(np.mean([q[0] for q in c])), float(np.mean([q[1] for q in c])),
                        [(q[0], q[1]) for q in c]))
    bb_ax = ax.get_window_extent(rd)
    vat: list = []                                            # điểm mẫu trên đường / thanh sai số (pixel)
    segs = [ln.get_transform().transform(ln.get_xydata()) for ln in ax.lines
            if ln.get_linestyle() not in ("None", "", " ") and len(ln.get_xydata()) > 1]
    for col in ax.collections:
        if isinstance(col, matplotlib.collections.LineCollection):
            segs += [td.transform(np.asarray(sg, dtype=float)) for sg in col.get_segments()]
    for sg in segs:
        sg = sg[np.isfinite(sg).all(axis=1)]
        for u, v in zip(sg[:-1], sg[1:]):
            n = max(2, int(np.hypot(*(v - u)) / 4))
            vat.extend(u + (v - u) * t for t in np.linspace(0, 1, n))
    vat = np.array(vat) if vat else np.zeros((0, 2))
    da: list = []
    huong = [(1, 1), (1, -1), (-1, 1), (-1, -1), (1, 0), (-1, 0), (0, 1), (0, -1)]
    for t, px, py, mem in sorted(cho, key=lambda c: (c[2], c[1])):
        tay = None
        for tc_, pt, lb in thu_cong or []:
            q0 = td.transform(pt)
            if tc_ == t and any(np.hypot(m[0] - q0[0], m[1] - q0[1]) < gop_px for m in mem):
                tay = td.transform(lb)
        if tay is not None:
            fig.text(tay[0] / W, tay[1] / H, t, fontsize=fontsize, color=CHU_PHU, ha="left", va="center",
                     bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8))
            da.append(fig.texts[-1].get_window_extent(rd))
            for m in mem:
                fig.add_artist(matplotlib.lines.Line2D([tay[0] / W, m[0] / W], [tay[1] / H, m[1] / H], color=CHU_PHU,
                                                       linewidth=0.5, alpha=0.7, transform=fig.transFigure))
            continue
        tot, vtot = None, 1e18
        for r in (9, 16, 26, 38, 54, 72):
            for gx, gy in huong:
                tx = fig.text((px + gx * r) / W, (py + gy * r) / H, t, fontsize=fontsize, color=CHU_PHU,
                              ha="left" if gx >= 0 else "right", va="bottom" if gy >= 0 else "top")
                bb = tx.get_window_extent(rd).expanded(1.04, 1.1)
                tx.remove()
                ph = float(sum(bb.overlaps(o) for o in da))
                ph += 0.5 * sum(bb.x0 - 6 < q[0] < bb.x1 + 6 and bb.y0 - 6 < q[1] < bb.y1 + 6 for q in diem)
                if len(vat):
                    ph += 0.4 * min(5, int(((vat[:, 0] > bb.x0) & (vat[:, 0] < bb.x1) & (vat[:, 1] > bb.y0)
                                            & (vat[:, 1] < bb.y1)).sum()))
                if bb.x0 < bb_ax.x0 or bb.x1 > bb_ax.x1 or bb.y0 < bb_ax.y0 or bb.y1 > bb_ax.y1:
                    ph += 0.7
                ph += 0.002 * r
                if ph < vtot:
                    tot, vtot = (px + gx * r, py + gy * r, gx, gy, bb), ph
        qx, qy, gx, gy, bb = tot
        fig.text(qx / W, qy / H, t, fontsize=fontsize, color=CHU_PHU, ha="left" if gx >= 0 else "right",
                 va="bottom" if gy >= 0 else "top",
                 bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8))
        da.append(bb)
        if np.hypot(qx - px, qy - py) > 14:                   # nhãn xa điểm: kẻ đường dẫn tới từng điểm của cụm
            for m in mem:
                fig.add_artist(matplotlib.lines.Line2D([qx / W, m[0] / W], [qy / H, m[1] / H], color=CHU_PHU,
                                                       linewidth=0.5, alpha=0.7, transform=fig.transFigure))


def nhan_tay(ax, ds: list, fontsize: float = 6.5) -> None:
    """Ghi nhãn đặt tay: mỗi phần tử `(chữ, [điểm (x, y), ...], (x, y) vị trí nhãn)` (toạ độ dữ liệu); nền trắng mờ,
    đường dẫn mảnh từ nhãn tới từng điểm (không vẽ nếu nhãn cách điểm < 3 đơn vị trục)."""
    for t, pts, lb in ds:
        ax.annotate(t, xy=pts[0], xytext=lb, textcoords="data", fontsize=fontsize, color=CHU_PHU, ha="center",
                    va="center", zorder=6, bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85),
                    arrowprops=dict(arrowstyle="-", lw=0.4, color=CHU_PHU, shrinkA=0, shrinkB=1.5, alpha=0.8))
        for p in pts[1:]:
            ax.annotate("", xy=p, xytext=lb, textcoords="data", zorder=5,
                        arrowprops=dict(arrowstyle="-", lw=0.4, color=CHU_PHU, shrinkA=0, shrinkB=1.5, alpha=0.8))

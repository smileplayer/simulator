"""Sáu hình minh họa cho mục 2 "Nền tảng CLMM" (Hình 2.1–2.6 trong `ket_qua/ban_nhap/nen_tang_CLMM.md`).

Một lệnh: `python -m plots.ve_nen_tang` (< 5 s) → `ket_qua/nen_tang/hinh_2_{1..6}.png`. Mọi số lấy từ ví dụ đã kiểm
trong bản nháp (phí 0,3% ở 2.1–2.4; kịch bản cơ sở `co_so` seed 0 ở 2.5). Lượng token theo `engine.tick_math`.
"""
from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

from engine.tick_math import amounts_for_liquidity
from plots.hinh import CHU, CHU_PHU, DPI, LUOI, MAU, MAU_VAI, NEN, so_vn

RA = Path("ket_qua/nen_tang")


def _truc(ax) -> None:
    """Kiểu trục chung: nền, lưới mảnh, bỏ viền trên/phải."""
    ax.set_facecolor(NEN)
    ax.grid(color=LUOI, lw=0.6)
    ax.spines[["top", "right"]].set_visible(False)


def _luu(fig, ten: str) -> Path:
    RA.mkdir(parents=True, exist_ok=True)
    f = RA / ten
    fig.savefig(f, dpi=DPI, facecolor=NEN, bbox_inches="tight")
    plt.close(fig)
    return f


def hinh_2_1() -> Path:
    """Đường cong v2 so với đoạn thực của vị thế v3 [0,90; 1,10] (L ≈ 10.219); L theo giá của ba cách đặt 1.000 USDT."""
    L, pa, pb = 10_219.0, 0.90, 1.10
    fig, (a, b) = plt.subplots(1, 2, figsize=(9.6, 3.8), facecolor=NEN)
    _truc(a)
    x = np.linspace(200, 2_500, 400)
    a.plot(x, L**2 / x / 1e3, color=CHU_PHU, ls="--", lw=1.2, label="v2: x·y = L² (toàn trục giá)")
    xa, xb = L * (1 / math.sqrt(pa) - 1 / math.sqrt(pb)), 0.0           # token0 tối đa (giá ở p_a) và 0 (giá ở p_b)
    xs = np.linspace(xb, xa, 200)
    ys = L**2 / (xs + L / math.sqrt(pb)) - L * math.sqrt(pa)
    a.plot(xs, ys, color=MAU[0], lw=2.4, label="v3 [0,90; 1,10]: phần dự trữ thực")
    x0, y0 = 475.6, 524.4
    a.plot([x0], [y0], "o", color=MAU[1], zorder=5)
    a.annotate("P = 1: 475,6 token0 + 524,4 USDT", (x0, y0), (650, 1_400), fontsize=8,
               arrowprops=dict(arrowstyle="-", color=CHU_PHU, lw=0.7))
    a.annotate("giá ≤ 0,90: toàn token0", (xa, 0), (700, 300), fontsize=8, arrowprops=dict(arrowstyle="-", color=CHU_PHU, lw=0.7))
    a.annotate("giá ≥ 1,10: toàn USDT", (0, ys[0]), (150, 1_800), fontsize=8, arrowprops=dict(arrowstyle="-", color=CHU_PHU, lw=0.7))
    a.set_xlim(0, 2_500), a.set_ylim(0, 2_500)
    a.set_xlabel("x (token0)"), a.set_ylabel("y (USDT)")
    a.set_title("Cùng L: v3 chỉ dùng một đoạn của đường cong")
    a.legend(loc="upper right", frameon=False)

    _truc(b)
    p = np.geomspace(0.5, 2.0, 400)
    b.plot(p, np.full_like(p, 500.0), color=CHU_PHU, lw=2, label="v2, 1.000 USDT: L = 500")
    b.fill_between([0.90, 1.10], 19_487 * 0 + 10_219, 1, color=MAU[0], alpha=0.35, step="pre")
    b.plot([0.90, 0.90, 1.10, 1.10], [1, 10_219, 10_219, 1], color=MAU[0], lw=2, label="v3 [0,90; 1,10]: L ≈ 10.219")
    b.plot([0.9999, 0.9999, 1.0, 1.0], [1, 2.0e7, 2.0e7, 1], color=MAU[3], lw=2.4, label="một tick [0,9999; 1]: L ≈ 2·10⁷")
    b.set_xscale("log"), b.set_yscale("log")
    b.set_xlim(0.5, 2.0), b.set_ylim(100, 1e8)
    b.set_xticks([0.5, 0.7, 0.9, 1.0, 1.1, 1.5, 2.0])
    b.set_xticklabels([so_vn(v, 1) if v != 1 else "1" for v in [0.5, 0.7, 0.9, 1.0, 1.1, 1.5, 2.0]])
    b.set_xlabel("giá P (USDT/token0, trục log)"), b.set_ylabel("thanh khoản L (trục log)")
    b.set_title("Cùng 1.000 USDT: dải càng hẹp, L càng lớn")
    b.xaxis.set_minor_formatter(plt.NullFormatter())
    b.legend(loc="center right", frameon=False)
    fig.suptitle("Hình 2.1. Từ x·y = k đến thanh khoản tập trung", x=0.02, ha="left")
    return _luu(fig, "hinh_2_1.png")


def hinh_2_2() -> Path:
    """Thành phần (token0, USDT) của vị thế [0,90; 1,10], L ≈ 10.219 theo giá, và giá trị so với cứ giữ (IL)."""
    L, za, zb = 10_219.0, math.sqrt(0.90), math.sqrt(1.10)
    P = np.linspace(0.7, 1.3, 400)
    xy = np.array([amounts_for_liquidity(math.sqrt(q), za, zb, L) for q in P])
    x, y = xy[:, 0], xy[:, 1]
    gia_tri, giu = x * P + y, 475.6 * P + 524.4
    fig, (a, b) = plt.subplots(1, 2, figsize=(9.6, 3.6), facecolor=NEN)
    for ax in (a, b):
        _truc(ax)
        for q in (0.90, 1.10):
            ax.axvline(q, color=CHU_PHU, lw=0.8, ls=":")
        ax.set_xlabel("giá P (USDT/token0)")
    a.plot(P, x, color=MAU[0], lw=2, label="token0 trong vị thế")
    a.plot(P, y, color=MAU[2], lw=2, label="USDT trong vị thế")
    a.set_ylabel("lượng"), a.set_title("Dưới dải: toàn token0 · trên dải: toàn USDT")
    a.legend(frameon=False, loc="center right")
    b.plot(P, giu, color=CHU_PHU, lw=1.6, ls="--", label="cứ giữ 475,6 token0 + 524,4 USDT")
    b.plot(P, gia_tri, color=MAU[1], lw=2, label="giá trị vị thế LP")
    b.fill_between(P, gia_tri, giu, color=MAU[1], alpha=0.15, label="tổn thất tạm thời (IL)")
    for q, nhan, dx, dy in ((0.8, "P = 0,8: ≈ 822,7", 0.015, -12), (1.2, "P = 1,2: ≈ 1.023,2", -0.06, -45)):
        v = float(np.interp(q, P, gia_tri))
        b.plot([q], [v], "o", color=MAU[1])
        b.text(q + dx, v + dy, nhan, fontsize=8, va="top")
    b.set_ylabel("giá trị (USDT)"), b.set_title("Cả hai chiều LP đều kém cứ giữ")
    b.legend(frameon=False, loc="upper left")
    fig.suptitle("Hình 2.2. Vị thế 1.000 USDT trên dải [0,90; 1,10] khi giá đổi", x=0.02, ha="left")
    return _luu(fig, "hinh_2_2.png")


def hinh_2_3() -> Path:
    """L_active theo tick của ví dụ hai vị thế; bán 600 token0 đi qua tick −5 và dừng ở tick −7."""
    ticks = np.arange(-12, 7)
    L = np.where((ticks >= -5) & (ticks < 5), 2e6, np.where((ticks >= -10) & (ticks < 10), 1e6, 0.0))
    fig, ax = plt.subplots(figsize=(9.6, 3.6), facecolor=NEN)
    _truc(ax)
    mau = [MAU[0] if t >= -7 and t < 0 else "#b9cfe9" for t in ticks]
    ax.bar(ticks + 0.5, L / 1e6, width=0.9, color=mau, edgecolor="none")
    ax.axvline(0, color=CHU, lw=1.2)
    ax.text(0.15, 2.45, "giá ban đầu P = 1 (tick 0)", fontsize=8)
    ax.annotate("", xy=(-6.6, 2.2), xytext=(0, 2.2), arrowprops=dict(arrowstyle="-|>", color=MAU[1], lw=1.8))
    ax.axvline(-5, color=MAU[1], lw=1, ls="--")
    ax.text(-4.8, 1.55, "qua tick −5:\nL −= 10⁶", fontsize=8, color=MAU[1], bbox=dict(fc=NEN, ec="none", pad=1))
    ax.text(-2.6, 2.28, "đoạn 1: L = 2·10⁶, dùng 501,54 token0", fontsize=8, ha="center")
    ax.text(-6.0, 1.15, "đoạn 2: L = 10⁶\ncòn 98,46 token0\ndừng ở P ≈ 0,99930", fontsize=8, ha="center")
    ax.set_xlim(-12.5, 6.5), ax.set_ylim(0, 2.7)
    ax.set_xticks(range(-12, 7, 2))
    ax.set_xlabel("tick"), ax.set_ylabel("L_active (×10⁶)")
    ax.set_title("A trên [−10, 10), B trên [−5, 5), mỗi vị thế L = 10⁶; bán 600 token0, phí 0,3%: nhận 598,02 USDT, "
                 "phí 1,80 token0 (A 1,048, B 0,752)")
    fig.suptitle("Hình 2.3. Swap xuyên tick", x=0.02, ha="left")
    return _luu(fig, "hinh_2_3.png")


def hinh_2_4() -> Path:
    """Sơ đồ feeGrowthOutside: với biên l, u và ba vị trí giá, phần nào của f_g là below / inside / above."""
    fig, axs = plt.subplots(3, 1, figsize=(9.6, 4.6), facecolor=NEN, sharex=True)
    l, u = 3.0, 7.0
    truong_hop = [(1.5, "giá dưới dải (i_c < l)", "f_o(l) = phí phía trên l", "f_o(u) = phí phía trên u"),
                  (5.0, "giá trong dải", "f_o(l) = phí phía dưới l", "f_o(u) = phí phía trên u"),
                  (8.5, "giá trên dải (i_c ≥ u)", "f_o(l) = phí phía dưới l", "f_o(u) = phí phía dưới u")]
    for ax, (gia, ten, cl, cu) in zip(axs, truong_hop):
        ax.set_facecolor(NEN)
        ax.set_yticks([]), ax.set_ylim(0, 1), ax.set_xlim(0, 10)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.add_patch(Rectangle((0, 0.2), l, 0.5, color=MAU[0], alpha=0.18))
        ax.add_patch(Rectangle((l, 0.2), u - l, 0.5, color=MAU[2], alpha=0.35))
        ax.add_patch(Rectangle((u, 0.2), 10 - u, 0.5, color=MAU[3], alpha=0.18))
        ax.text(l / 2, 0.45, "below(l)", ha="center", fontsize=8)
        ax.text((l + u) / 2, 0.45, "inside = f_g − below − above", ha="center", fontsize=8, weight="bold")
        ax.text((u + 10) / 2, 0.45, "above(u)", ha="center", fontsize=8)
        for b_, nhan in ((l, "l"), (u, "u")):
            ax.axvline(b_, color=CHU, lw=1)
            ax.text(b_ + 0.12, 0.76, nhan, ha="left", fontsize=10, weight="bold")
        ax.plot([gia], [0.1], marker="^", color=MAU[1], ms=9)
        ax.text(0.01, 0.92, f"{ten}: {cl}; {cu}", fontsize=8, transform=ax.transAxes, color=CHU_PHU,
                bbox=dict(fc=NEN, ec="none", pad=1))
    axs[-1].set_xticks([])
    axs[-1].set_xlabel("trục tick (▲ = giá hiện tại). Mỗi lần giá qua tick i: f_o(i) ← f_g − f_o(i). "
                       "Phí vị thế = L·(inside bây giờ − inside lúc ghi)")
    fig.suptitle("Hình 2.4. feeGrowth: tách phí trong dải [l, u) chỉ từ hai bộ đếm ở biên", x=0.02, ha="left")
    return _luu(fig, "hinh_2_4.png")


def hinh_2_5() -> Path:
    """Ba pha của tường trên biểu đồ L theo tick, số của `co_so` seed 0 (tường 4·10⁸, nạn nhân 0,62·10⁸, tick −53)."""
    ticks = np.arange(-58, -47)
    nen = 2e5 / 1e8
    pha = [("(a) Dựng tường: giờ 48–72", 4.0, 0.0), ("(b) Nạn nhân vào: giờ 78", 4.0, 0.62),
           ("(c) Rút tường rồi xả: giờ 168–169", 0.0, 0.62)]
    fig, axs = plt.subplots(1, 3, figsize=(10.4, 3.6), facecolor=NEN, sharey=True)
    for ax, (ten, la, lv) in zip(axs, pha):
        _truc(ax)
        ax.bar(ticks, np.full(len(ticks), nen) + 0.02, color=MAU_VAI["bg"], width=0.85)
        ax.bar([-53], [la], color=MAU_VAI["attacker"], width=0.85, label="kẻ tấn công")
        ax.bar([-53], [lv], bottom=[la], color=MAU_VAI["victim"], width=0.85, label="nạn nhân")
        ax.set_title(ten), ax.set_xlabel("tick (tường ở −53, giá ≈ 0,995)")
        ax.set_xticks([-58, -53, -48])
    axs[0].set_ylabel("L trên mỗi tick (×10⁸)")
    axs[0].legend(frameon=False, loc="upper left")
    axs[0].text(-58.3, 0.25, "nền ≈ 2·10⁵ mỗi tick\n(quá mỏng để thấy ở thang này)", fontsize=7.4, color=CHU_PHU)
    axs[1].text(-52.4, 4.3, "tường 87%,\nnạn nhân 13%", fontsize=8)
    ax = axs[2]
    ax.annotate("", xy=(-58.4, 2.2), xytext=(-53, 2.2), arrowprops=dict(arrowstyle="-|>", color=MAU[1], lw=2))
    ax.text(-58.2, 2.45, "giá sập 0,995 → 0,501\n(xuống tick ≈ −6.900)", fontsize=8, color=MAU[1])
    ax.text(-52.4, 0.75, "nạn nhân kẹt lại:\ntoàn token0", fontsize=8, color=MAU_VAI["victim"])
    axs[0].set_ylim(0, 5)
    fig.suptitle("Hình 2.5. Tường thanh khoản một tick qua ba pha (kịch bản cơ sở, seed 0)", x=0.02, ha="left")
    return _luu(fig, "hinh_2_5.png")


def hinh_2_6() -> Path:
    """Sơ đồ khối: tác nhân → lệnh → Pool → EventLog → metrics; nhánh phát lại log về Pool mới."""
    fig, ax = plt.subplots(figsize=(10.4, 3.4), facecolor=NEN)
    ax.set_xlim(0, 100), ax.set_ylim(0, 40), ax.axis("off")

    def hop(x, y, w, h, tieu_de, dong, mau):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.6,rounding_size=1.2", fc=mau, ec=CHU, lw=0.8))
        ax.text(x + w / 2, y + h - 2.6, tieu_de, ha="center", va="top", fontsize=9, weight="bold")
        ax.text(x + w / 2, y + h - 7.4, dong, ha="center", va="top", fontsize=7.6, color=CHU_PHU, linespacing=1.35)

    def mui(x1, y1, x2, y2, nhan="", kieu="-|>", ls="-"):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=kieu, mutation_scale=12, color=CHU, lw=1, ls=ls))
        if nhan:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 1.4, nhan, ha="center", fontsize=7.4)

    hop(1, 14, 16, 22, "Tác nhân (vai C)", "farmer · arb\nnạn nhân (toàn tri /\nthích nghi) · kẻ tấn công\nnền · LP lành mạnh", "#fbe6dc")
    hop(30, 14, 16, 22, "Pool (vai A)", "trạng thái theo tick:\nliquidity_net / gross\nweighted_net (φ)\nfeeGrowthOutside", "#e6eef8")
    hop(57, 14, 16, 22, "EventLog", "mint · burn · collect\nswap · subsidy · step\n(một dòng / sự kiện,\nINTERFACE mục 4)", "#f1f0ec")
    hop(83, 14, 16, 22, "metrics/ (vai B)", "mốc, pha, 4 chỉ số\nkiểm định RQ1\nbảng GĐ2–GĐ3\nplots/ → hình", "#e3f3ec")
    mui(17.6, 25, 29.4, 25, "quote_swap · swap\nmint · burn · collect")
    mui(46.6, 25, 56.4, 25, "ghi")
    mui(73.6, 25, 82.4, 25, "chỉ đọc")
    hop(30, 1, 16, 8, "Pool mới", "", "#e6eef8")
    mui(64, 13.4, 46.6, 5, ls="--")
    ax.text(60, 4, "phát lại log: kiểm định engine,\nphản thực \"bán thẳng\"", fontsize=7.4, va="center")
    fig.suptitle("Hình 2.6. Kiến trúc ba lớp của simulator", x=0.02, ha="left")
    return _luu(fig, "hinh_2_6.png")


def main() -> list[Path]:
    """Vẽ đủ sáu hình, trả danh sách đường dẫn."""
    return [hinh_2_1(), hinh_2_2(), hinh_2_3(), hinh_2_4(), hinh_2_5(), hinh_2_6()]


if __name__ == "__main__":
    for f in main():
        print(f)

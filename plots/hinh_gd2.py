"""Biểu đồ GĐ2 (RQ2): đánh đổi biện pháp (mất khối lượng vs giảm thiệt hại / giảm lợi kẻ tấn công), bản đồ nhiệt
`(σ, Q)` khi không có biện pháp, ngưỡng vào của victim theo trần (Q*). Màu theo bảng màu đã kiểm của `plots.hinh`."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D

from plots.hinh import CHU, CHU_PHU, LUOI, MAU, NEN, _hinh, _kieu

# màu theo họ biện pháp (cố định thứ tự), hình dạng theo loại victim
MAU_HO = {"cap": MAU[0], "delay": MAU[1], "claw": MAU[2]}
TEN_HO = {"cap": "hạ trần Q", "delay": "trả trễ", "claw": "trả trễ + thu hồi"}
DANG_VICTIM = {"omniscient": "o", "adaptive": "s"}
TEN_VICTIM = {"omniscient": "victim toàn tri", "adaptive": "victim thích nghi"}
# thang tuần tự một sắc xanh (ramp 100 → 700 của bảng màu dataviz)
XANH = LinearSegmentedColormap.from_list("xanh", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])


def _ho(bp: str) -> str:
    """Họ biện pháp từ mã: cap75 → cap, delay72 → delay, claw168 → claw."""
    return next(h for h in MAU_HO if bp.startswith(h))


def _diem(dai: pd.DataFrame, chi_so: str) -> pd.DataFrame:
    """Lấy (bp, victim_type) → −pct (giảm, %) và CI cho một chỉ số từ bảng dài `bang_danh_doi`."""
    h = dai[dai["chi_so"] == chi_so].set_index(["victim_type", "bp"])
    return pd.DataFrame({"giam": -h["pct"], "lo": -h["pct_hi"], "hi": -h["pct_lo"]})


def ve_danh_doi_ax(ax_list, dai: pd.DataFrame, chi_so_y=("victim_loss_full", "loi_tan_cong_treo"),
                   nhan_y=("giảm thiệt hại victim (%)", "giảm lợi kẻ tấn công (%)")) -> None:
    """Vẽ lên các trục: x = % mất tổng khối lượng (`vol_tong`), y = % giảm của từng chỉ số trong `chi_so_y`;
    mỗi điểm một (biện pháp, loại victim), thanh = CI 95% bootstrap cặp theo vụ. Nhãn chữ trực tiếp tên bp."""
    x = _diem(dai, "vol_tong")
    for ax, cs, ny in zip(ax_list, chi_so_y, nhan_y):
        _kieu(ax)
        ax.xaxis.grid(True, color=LUOI, linewidth=0.6)
        y = _diem(dai, cs)
        gan_goc = set()
        for (vt, bp), r in y.iterrows():
            if (vt, bp) not in x.index:
                continue
            xr = x.loc[(vt, bp)]
            c = MAU_HO[_ho(bp)]
            ax.errorbar(xr.giam, r.giam, xerr=[[xr.giam - xr.lo], [xr.hi - xr.giam]],
                        yerr=[[r.giam - r.lo], [r.hi - r.giam]], fmt="none", ecolor=c, elinewidth=1, alpha=0.55,
                        zorder=2)
            ax.plot(xr.giam, r.giam, DANG_VICTIM[vt], ms=8, color=c, mec=NEN, mew=2, zorder=3)
            if abs(xr.giam) < 5 and abs(r.giam) < 5:          # điểm sát gốc: gộp một nhãn, tránh chồng chữ
                gan_goc.add(bp)
            else:
                ax.annotate(bp, (xr.giam, r.giam), xytext=(5, 4), textcoords="offset points", fontsize=7,
                            color=CHU_PHU)
        if gan_goc:
            ax.annotate(", ".join(sorted(gan_goc, key=lambda b: (_ho(b), int(b.lstrip("capdelyw"))))) + " (sát gốc)",
                        (0, 0), xytext=(6, 12), textcoords="offset points", fontsize=7, color=CHU_PHU)
        ax.axhline(0, color=CHU_PHU, linewidth=0.8)
        ax.set_xlabel("mất tổng khối lượng (%)")
        ax.set_ylabel(ny)


def _chu_giai(fig, ho: list[str]) -> None:
    """Chú giải chung: màu = họ biện pháp, hình = loại victim."""
    h = [Line2D([], [], marker="o", ls="", color=MAU_HO[k], ms=8, label=TEN_HO[k]) for k in ho]
    h += [Line2D([], [], marker=DANG_VICTIM[v], ls="", color=CHU_PHU, ms=8, label=TEN_VICTIM[v]) for v in DANG_VICTIM]
    fig.legend(handles=h, loc="lower center", ncol=len(h), frameon=False, fontsize=8, labelcolor=CHU)


def ve_danh_doi(dai: pd.DataFrame, path: str | Path, tieu_de: str = "") -> None:
    """Hình đánh đổi một nhóm (bảng `danh_doi.csv`): hai ô — giảm thiệt hại victim, giảm lợi kẻ tấn công
    (excess + farm + treo) — theo % mất khối lượng. Đơn vị: % thay đổi so với `khong` (tỷ số trung bình cặp)."""
    fig, axs = _hinh(1, 2, (11, 4.8))
    ve_danh_doi_ax(axs, dai)
    _chu_giai(fig, sorted({_ho(b) for b in dai["bp"]}, key=list(MAU_HO).index))
    fig.suptitle(tieu_de, color=CHU, fontsize=11)
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    fig.savefig(path, dpi=150, facecolor=NEN)
    plt.close(fig)


def ve_danh_doi_farm(dai: pd.DataFrame, path: str | Path, tieu_de: str = "") -> None:
    """Như `ve_danh_doi` cho bảng `danh_doi_farm.csv`, mỗi hàng một `farm_share` (bội nhỏ, chung thang)."""
    shares = sorted(dai["farm_share"].unique())
    fig, axs = _hinh(len(shares), 2, (11, 4.2 * len(shares)), sharex=True, sharey="col", squeeze=False)
    for i, s in enumerate(shares):
        g = dai[dai["farm_share"] == s]
        # thu hồi không đổi hành vi victim (cùng lượt, cùng thiệt hại với delay) → ô victim chỉ vẽ delay
        ve_danh_doi_ax([axs[i, 0]], g[~g["bp"].str.startswith("claw")], ("victim_loss_full",),
                       ("giảm thiệt hại victim (%)",))
        ve_danh_doi_ax([axs[i, 1]], g, ("loi_tan_cong_treo",), ("giảm lợi kẻ tấn công (%)",))
        axs[i, 0].set_title(f"phần farm của kẻ tấn công = {s:g} (claw trùng delay ở ô này)", loc="left",
                            fontsize=9, color=CHU)
    _chu_giai(fig, sorted({_ho(b) for b in dai["bp"]}, key=list(MAU_HO).index))
    fig.suptitle(tieu_de, color=CHU, fontsize=11)
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    fig.savefig(path, dpi=150, facecolor=NEN)
    plt.close(fig)


def luoi_nhiet(tt: pd.DataFrame, cot: str, victim_type: str, bp: str = "khong") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Bảng σ (hàng) × Q (cột): trung vị `cot` qua mọi vụ + seed của ô (chỉ lượt sập, trợ cấp tuyến tính), và số
    lượt. Đơn vị theo `cot`."""
    g = tt[(tt["bp"] == bp) & (tt["victim_type"] == victim_type) & (tt["breached"] > 0)
           & (tt.get("subsidy_form", "linear") == "linear")]
    gia_tri = g.pivot_table(index="sigma", columns="Q", values=cot, aggfunc="median")
    so = g.pivot_table(index="sigma", columns="Q", values=cot, aggfunc="count")
    return gia_tri, so


def ve_nhiet(tt: pd.DataFrame, path: str | Path, cot=("attacker_profit_excess", "victim_loss_full"),
             nhan=("lợi nhuận tăng thêm (excess, token1)", "thiệt hại victim (token1)"), tieu_de: str = "") -> None:
    """Bản đồ nhiệt (σ, Q) khi không có biện pháp: hàng = loại victim, cột = chỉ số; ô = trung vị (3 vụ × ~10 seed),
    chữ trong ô = giá trị. Mỗi ô một thang riêng (chỉ số khác đơn vị/độ lớn)."""
    vts = ["omniscient", "adaptive"]
    fig, axs = _hinh(len(vts), len(cot), (5.2 * len(cot), 4.0 * len(vts)), squeeze=False)
    for i, vt in enumerate(vts):
        for j, (c, n) in enumerate(zip(cot, nhan)):
            ax = axs[i, j]
            gt, so = luoi_nhiet(tt, c, vt)
            im = ax.imshow(gt.to_numpy(), cmap=XANH, origin="lower", aspect="auto",
                           vmin=min(0.0, np.nanmin(gt.to_numpy())))
            vmax = np.nanmax(gt.to_numpy())
            for a in range(gt.shape[0]):
                for b in range(gt.shape[1]):
                    v = gt.iat[a, b]
                    ax.text(b, a, f"{v:,.0f}\n(n={int(so.iat[a, b])})", ha="center", va="center", fontsize=8,
                            color="white" if v > 0.55 * vmax else CHU)
            ax.set_xticks(range(gt.shape[1]), [f"{q / 1000:g}k" for q in gt.columns])
            ax.set_yticks(range(gt.shape[0]), [f"{s:g}" for s in gt.index])
            ax.set_xlabel("trần Q (token1/farmer/ngày)", color=CHU_PHU)
            ax.set_ylabel("tỷ lệ trợ cấp σ", color=CHU_PHU)
            ax.tick_params(colors=CHU_PHU, labelsize=8)
            for s in ax.spines.values():
                s.set_visible(False)
            ax.set_title(f"{n} — {TEN_VICTIM[vt]}", fontsize=9, color=CHU, loc="left")
            cb = fig.colorbar(im, ax=ax, shrink=0.85)
            cb.ax.tick_params(labelsize=7, colors=CHU_PHU)
            cb.outline.set_visible(False)
    fig.suptitle(tieu_de, color=CHU, fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=150, facecolor=NEN)
    plt.close(fig)


def ve_q_sao(qv: pd.DataFrame, path: str | Path, tieu_de: str = "") -> None:
    """Ngưỡng vào của victim nội suy `r_V` = Q*_V/Q (bảng `q_sao_vu.csv`) theo trần Q, mỗi điểm một vụ; vạch ngang
    = các mức trần đã chạy (lưới cap); vùng dưới 0,25 = ngoại suy. Toàn tri: vạch chấm = k của vụ (Lemma 4)."""
    fig, axs = _hinh(1, 2, (11, 4.4), sharey=True)
    for ax, vt in zip(axs, ["omniscient", "adaptive"]):
        _kieu(ax)
        g = qv[qv["victim_type"] == vt].dropna(subset=["r_V"])
        Qs = sorted(g["Q"].unique())
        rng = np.random.default_rng(0)
        for j, k in enumerate(sorted(g["k"].unique())):
            h = g[g["k"] == k]
            xs = np.array([Qs.index(q) for q in h["Q"]]) + (j - 1) * 0.18 + rng.uniform(-0.04, 0.04, len(h))
            ax.plot(xs, h["r_V"], "o", ms=8, color=MAU[j], mec=NEN, mew=2, label=f"k = {k:g}")
            if vt == "omniscient":
                ax.axhline(k, color=MAU[j], linewidth=1, linestyle=(0, (2, 2)))
        for r in (0.25, 0.5, 0.75, 1.0):
            ax.axhline(r, color=LUOI, linewidth=1.2)
        ax.axhspan(min(-2.0, g["r_V"].min() - 0.1), 0.25, color="#f1f0ec", zorder=0)
        ax.text(len(Qs) - 0.6, 0.27, "lưới cap: 0,25 / 0,5 / 0,75 / 1", fontsize=7, color=CHU_PHU, ha="right",
                va="bottom")
        ax.set_xticks(range(len(Qs)), [f"{q / 1000:g}k" for q in Qs])
        ax.set_xlabel("trần Q gốc (token1/farmer/ngày)")
        ax.set_ylabel("ngưỡng vào victim r_V = Q*_V / Q")
        ax.set_title(TEN_VICTIM[vt], loc="left", fontsize=9, color=CHU)
    h, n = axs[0].get_legend_handles_labels()
    fig.legend(h, n, loc="lower center", ncol=len(h), frameon=False, fontsize=8, labelcolor=CHU)
    fig.suptitle(tieu_de, color=CHU, fontsize=11)
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))
    fig.savefig(path, dpi=150, facecolor=NEN)
    plt.close(fig)

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
MAU_HO = {"cap": MAU[0], "delay": MAU[1], "claw": MAU[2], "warn": MAU[3], "dyncap": MAU[4]}
TEN_HO = {"cap": "hạ trần Q", "delay": "trả trễ", "claw": "trả trễ + thu hồi", "warn": "cảnh báo (c_V×)",
          "dyncap": "trần động"}
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
            ax.annotate(", ".join(sorted(gan_goc)) + " (sát gốc)",
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


def ve_danh_doi_farm(dai: pd.DataFrame, path: str | Path, tieu_de: str = "", cs_loi: str | None = None) -> None:
    """Như `ve_danh_doi` cho bảng `danh_doi_farm.csv`, mỗi hàng một `farm_share` (bội nhỏ, chung thang).
    `cs_loi` = chỉ số lợi kẻ tấn công (mặc định `loi_tang_them_treo` nếu có — v3, không thì `loi_tan_cong_treo`)."""
    if cs_loi is None:
        cs_loi = "loi_tang_them_treo" if (dai["chi_so"] == "loi_tang_them_treo").any() else "loi_tan_cong_treo"
    shares = sorted(dai["farm_share"].unique())
    fig, axs = _hinh(len(shares), 2, (11, 4.2 * len(shares)), sharex=True, sharey="col", squeeze=False)
    for i, s in enumerate(shares):
        g = dai[dai["farm_share"] == s]
        # thu hồi không đổi hành vi victim (cùng lượt, cùng thiệt hại với delay) → ô victim chỉ vẽ delay
        ve_danh_doi_ax([axs[i, 0]], g[~g["bp"].str.startswith("claw")], ("victim_loss_full",),
                       ("giảm thiệt hại victim (%)",))
        ve_danh_doi_ax([axs[i, 1]], g, (cs_loi,), ("giảm lợi kẻ tấn công (%)",))
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


Y_DUOI = -1.5     # cận dưới trục r_V trong `ve_q_sao`


def ve_q_sao(qv: pd.DataFrame, path: str | Path, tieu_de: str = "") -> None:
    """Ngưỡng vào của victim nội suy `r_V` = Q*_V/Q (bảng `q_sao_vu.csv`) theo trần Q, mỗi điểm một vụ; vạch ngang
    = các mức trần đã chạy (lưới cap, đọc từ cột `LV_<mức>`); nền xám = dưới mức thấp nhất (ngoại suy).
    Toàn tri: vạch chấm = k của vụ (Lemma 4)."""
    fig, axs = _hinh(1, 2, (11, 4.4), sharey=True)
    for ax, vt in zip(axs, ["omniscient", "adaptive"]):
        _kieu(ax)
        g = qv[qv["victim_type"] == vt].dropna(subset=["r_V"])
        Qs = sorted(g["Q"].unique())
        rng = np.random.default_rng(0)
        for j, k in enumerate(sorted(g["k"].unique())):
            h = g[g["k"] == k]
            xs = np.array([Qs.index(q) for q in h["Q"]]) + (j - 1) * 0.18 + rng.uniform(-0.04, 0.04, len(h))
            yv = h["r_V"].to_numpy()
            cat = yv < Y_DUOI
            ax.plot(xs[~cat], yv[~cat], "o", ms=8, color=MAU[j], mec=NEN, mew=2, label=f"k = {k:g}")
            if cat.any():                                     # điểm quá thấp: vẽ tam giác ở mép dưới
                ax.plot(xs[cat], np.full(cat.sum(), Y_DUOI + 0.04), "v", ms=8, color=MAU[j], mec=NEN, mew=1.5)
            if vt == "omniscient":
                ax.axhline(k, color=MAU[j], linewidth=1, linestyle=(0, (2, 2)))
        muc = sorted(float(c[3:]) / 100 for c in qv.columns if c.startswith("LV_") and c[3:].isdigit())
        for r in muc:
            ax.axhline(r, color=LUOI, linewidth=1.0)
        ax.axhspan(Y_DUOI, muc[0], color="#f1f0ec", zorder=0)
        ax.set_ylim(Y_DUOI, 1.1)
        ax.text(0.01, muc[0] - 0.03, f"vạch ngang = lưới cap ({len(muc)} mức); nền xám = dưới mức thấp nhất "
                f"(ngoại suy); ▼ = r_V < {Y_DUOI:g}", fontsize=7, color=CHU_PHU, ha="left", va="top",
                transform=ax.get_yaxis_transform())
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


def ve_pareto(bang: dict[str, pd.DataFrame], path: str | Path, tieu_de: str = "",
              cs=("loi_tang_them", "victim_loss_full"),
              nhan=("giảm lợi tăng thêm của kẻ tấn công (%)", "giảm thiệt hại victim (%)")) -> None:
    """Biên đánh đổi: mỗi hàng một vùng tham số (`bang` = {tên: bảng dài `bang_danh_doi`}), mỗi cột một chỉ số;
    x = % mất tổng khối lượng, y = % giảm (so với `khong`, CI 95%). Các mức hạ trần nối thành đường tham chiếu cho
    từng loại victim: biện pháp nằm trên đường cap = tốt hơn hạ trần ở cùng mức mất khối lượng."""
    fig, axs = _hinh(len(bang), len(cs), (6 * len(cs), 4.6 * len(bang)), squeeze=False)
    ho_co = set()
    for i, (ten, dai) in enumerate(bang.items()):
        x = _diem(dai, "vol_tong")
        for j, (c, n) in enumerate(zip(cs, nhan)):
            ax = axs[i, j]
            _kieu(ax)
            ax.xaxis.grid(True, color=LUOI, linewidth=0.6)
            y = _diem(dai, c)
            for vt in DANG_VICTIM:
                cap = [(x.loc[(vt, b)].giam, y.loc[(vt, b)].giam) for b in y.loc[vt].index
                       if b.startswith("cap") and (vt, b) in x.index] if vt in y.index.get_level_values(0) else []
                if cap:
                    cap = sorted(cap + [(0.0, 0.0)])
                    ax.plot(*zip(*cap), color=MAU_HO["cap"], linewidth=1.2,
                            linestyle="-" if vt == "omniscient" else (0, (4, 2)), zorder=1)
            for (vt, bp), r in y.iterrows():
                if (vt, bp) not in x.index:
                    continue
                xr, h = x.loc[(vt, bp)], _ho(bp)
                ho_co.add(h)
                cmau = MAU_HO[h]
                if h != "cap":
                    ax.errorbar(xr.giam, r.giam, xerr=[[xr.giam - xr.lo], [xr.hi - xr.giam]],
                                yerr=[[r.giam - r.lo], [r.hi - r.giam]], fmt="none", ecolor=cmau, elinewidth=1,
                                alpha=0.5, zorder=2)
                    ax.annotate(bp, (xr.giam, r.giam), xytext=(5, 3), textcoords="offset points", fontsize=7,
                                color=CHU_PHU)
                elif bp in ("cap90", "cap50", "cap10", "cap05"):
                    ax.annotate(bp, (xr.giam, r.giam), xytext=(4, -9), textcoords="offset points", fontsize=6.5,
                                color=CHU_PHU)
                ax.plot(xr.giam, r.giam, DANG_VICTIM[vt], ms=7 if h == "cap" else 8, color=cmau, mec=NEN, mew=1.5,
                        zorder=3)
            ax.axhline(0, color=CHU_PHU, linewidth=0.8)
            ax.set_xlabel("mất tổng khối lượng (%)")
            ax.set_ylabel(n)
            ax.set_title(ten, loc="left", fontsize=9, color=CHU)
    _chu_giai(fig, sorted(ho_co, key=list(MAU_HO).index))
    fig.suptitle(tieu_de, color=CHU, fontsize=11)
    fig.tight_layout(rect=(0, 0.05, 1, 0.96))
    fig.savefig(path, dpi=150, facecolor=NEN)
    plt.close(fig)


MAU_VUNG = {"i_khong_KL": "#e4e3df", "ii_an_toan": MAU[2], "iii_co_lai": MAU[1]}
TEN_VUNG = {"i_khong_KL": "(i) không tạo khối lượng", "ii_an_toan": "(ii) có khối lượng, tấn công không lãi",
            "iii_co_lai": "(iii) tấn công có lãi"}


def ve_ba_vung(bv: pd.DataFrame, path: str | Path, tieu_de: str = "") -> None:
    """Bản đồ ba vùng (bảng `ba_vung.csv`): hàng = loại victim, cột = bp (khong, cap50); ô tô theo vùng thực
    nghiệm, chữ = trung vị lợi tăng thêm (token1); ô gạch chéo = ngoài giả định Theorem 3/6 (GĐ1 trần không ràng
    buộc hoặc GĐ2 giá rời tick); dấu ≠ = khác vùng lý thuyết; dấu ! = vùng (i) mà kẻ tấn công vẫn có lãi;
    vạch đứt = ranh giới Lemma 4 Q_eff = c_V·L_A/(f·n)."""
    vts, bps = ["omniscient", "adaptive"], [b for b in ("khong", "cap50") if b in set(bv["bp"])]
    fig, axs = _hinh(len(vts), len(bps), (5.6 * len(bps), 4.2 * len(vts)), squeeze=False)
    for i, vt in enumerate(vts):
        for j, bp in enumerate(bps):
            ax = axs[i, j]
            g = bv[(bv["victim_type"] == vt) & (bv["bp"] == bp)]
            sg, Qs = sorted(g["sigma"].unique()), sorted(g["Q"].unique())
            for _, r in g.iterrows():
                a, b = sg.index(r["sigma"]), Qs.index(r["Q"])
                ngoai = bool(r.get("ngoai_gia_dinh", False))
                ax.add_patch(plt.Rectangle((b - 0.5, a - 0.5), 1, 1, facecolor=MAU_VUNG[r["vung"]], edgecolor=NEN,
                                           linewidth=2, hatch="///" if ngoai else None))
                chu = (f"{r['loi']:,.0f}" + ("" if r["khop_ly_thuyet"] else " ≠")
                       + (" !" if r["vung"] == "i_khong_KL" and r["loi"] > 0 else ""))
                ax.text(b, a, chu, ha="center", va="center", fontsize=8,
                        color=CHU, bbox=dict(facecolor=NEN, edgecolor="none", alpha=0.75, pad=1.2))
            # ranh giới Lemma 4: k_eff = k/r = 1 ⇔ Q = Q_ref·0,75/r, nội suy trên trục log Q
            k0 = g.iloc[0]
            q_nguong = k0["k"] * k0["Q"] / k0["r"]
            xq = np.interp(np.log(q_nguong), np.log(Qs), range(len(Qs)))
            ax.axvline(xq, color=CHU, linewidth=1.2, linestyle=(0, (4, 3)))
            ax.text(xq + 0.05, len(sg) - 0.45, f"Lemma 4: Q_eff = {q_nguong * k0['r'] / 1000:g}k", fontsize=7,
                    color=CHU, va="top")
            ax.axhline(0.5, color=CHU, linewidth=1.0, linestyle=(0, (1, 2)))
            ax.text(len(Qs) - 0.45, 0.52, "σ₀ = f", fontsize=7, color=CHU, ha="right", va="bottom")
            ax.set_xlim(-0.5, len(Qs) - 0.5)
            ax.set_ylim(-0.5, len(sg) - 0.5)
            ax.set_xticks(range(len(Qs)), [f"{q / 1000:g}k" for q in Qs])
            ax.set_yticks(range(len(sg)), [f"{s:g}" for s in sg])
            ax.set_xlabel("trần Q gốc (token1/farmer/24 bước)", color=CHU_PHU)
            ax.set_ylabel("tỷ lệ trợ cấp σ", color=CHU_PHU)
            ax.tick_params(colors=CHU_PHU, labelsize=8)
            for s in ax.spines.values():
                s.set_visible(False)
            ax.set_title(f"{TEN_VICTIM[vt]} — {'không biện pháp' if bp == 'khong' else 'hạ trần 50%'}",
                         loc="left", fontsize=9, color=CHU)
    h = [plt.Rectangle((0, 0), 1, 1, facecolor=MAU_VUNG[k], label=TEN_VUNG[k]) for k in MAU_VUNG]
    h.append(plt.Rectangle((0, 0), 1, 1, facecolor=NEN, edgecolor=CHU_PHU, hatch="///",
                           label="ngoài giả định (GĐ1/GĐ2)"))
    fig.legend(handles=h, loc="lower center", ncol=2, frameon=False, fontsize=8, labelcolor=CHU)
    fig.text(0.5, 0.005, "số trong ô = trung vị lợi tăng thêm của kẻ tấn công (token1); ≠ khác vùng lý thuyết; "
             "! vùng (i) nhưng vẫn có lãi", ha="center", fontsize=7.5, color=CHU_PHU)
    fig.suptitle(tieu_de, color=CHU, fontsize=11)
    fig.tight_layout(rect=(0, 0.09, 1, 0.95))
    fig.savefig(path, dpi=150, facecolor=NEN)
    plt.close(fig)

"""So thanh khoản từng vụ thật với bộ mã bài gốc (Zenodo, `submission/`): tái lập cách bài gốc gán thanh khoản
theo ví gửi giao dịch, rồi đặt cạnh thanh khoản đúng một tick tính thẳng từ sự kiện Mint/Burn của bể.

    python -m metrics.so_bai_goc [--submission ../submission]

Cần `su_kien.csv` và `vi_lenh*.csv` (ví gửi từng lệnh, do `scenarios.tai_vi_vu` tải) trong `ket_qua/that/vu/*`.
Cách bài gốc (đã kiểm khớp từng ví ở vụ 0xa207): mỗi ví cộng L khi gửi lệnh nạp, trừ khi gửi lệnh rút, không cho âm;
chỉ tính vị thế đúng khoảng tường [tick_lower, tick_upper]. Vị thế nạp bằng ví này, rút bằng ví khác làm ví nạp giữ
thanh khoản "ma". Cột `_goc`: số trong JSON bài gốc; `_tl`: tái lập theo ví gửi; `_be`: thật, theo sự kiện của bể.
Đơn vị L: số thô on-chain. k = 1/(1 + L_V/L_A)² (Bổ đề 4). Ghi `ket_qua/that/so_bai_goc.csv`.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from scenarios.tai_vu_that import doc_bang_vu

GOC = Path(__file__).resolve().parents[1]
VU = GOC / "ket_qua" / "that" / "vu"
BANG = GOC.parent / "00_Bai_goc" / "manual-validation-events-table.md"
RA = GOC / "ket_qua" / "that" / "so_bai_goc.csv"


def _so(x) -> int:
    """Chuỗi số nguyên lớn → int (rỗng/NaN → 0)."""
    s = str(x).strip()
    return int(s) if s not in ("", "nan", "None") else 0


def doc_lenh(thu_muc: Path, lo: int, hi: int) -> pd.DataFrame:
    """Mint/Burn đúng khoảng [lo, hi] của một thư mục vụ, kèm ví gửi (`vi`, NaN nếu chưa tra); L là int thô."""
    ev = pd.read_csv(thu_muc / "su_kien.csv", dtype=str)
    ev["kind"] = ev["kind"].str.lower()
    ev = ev[ev["kind"].isin(["mint", "burn"])].copy()
    for c in ("block", "tx_index", "log_index", "tick_lower", "tick_upper"):
        ev[c] = ev[c].astype(int)
    ev = ev[(ev["tick_lower"] == lo) & (ev["tick_upper"] == hi)]
    ev["L"] = [_so(x) for x in ev["liquidity"]]
    vi = pd.concat([pd.read_csv(f, dtype=str) for f in sorted(thu_muc.glob("vi_lenh*.csv"))], ignore_index=True)
    vi = vi.drop_duplicates("tx_hash")[["tx_hash", "from"]].rename(columns={"from": "vi"})
    ev = ev.merge(vi, on="tx_hash", how="left")
    ev["vi"] = ev["vi"].str.lower()
    return ev.sort_values(["block", "tx_index", "log_index"]).reset_index(drop=True)


def doc_lenh_lich_su(thu_muc: Path, lo: int, hi: int) -> pd.DataFrame:
    """Mint/Burn đúng khoảng [lo, hi] trước cửa sổ của thư mục vụ, từ lịch sử đã tải (`scenarios.tai_lich_su_be`); rỗng nếu chưa tải."""
    from scenarios.tai_lich_su_be import doc_lich_su
    b0 = int(pd.read_csv(thu_muc / "su_kien.csv", usecols=["block"])["block"].min())
    h = doc_lich_su(thu_muc.name.split("_")[0], b0, vu=thu_muc.parent)
    if h.empty:
        return h.assign(L=[])
    h["kind"] = h["kind"].str.lower()
    h = h[h["kind"].isin(["mint", "burn"])].copy()
    for c in ("block", "tick_lower", "tick_upper"):
        h[c] = h[c].astype(int)
    h = h[(h["tick_lower"] == lo) & (h["tick_upper"] == hi)]
    h["L"] = [_so(x) for x in h["liquidity"]]
    return h


def theo_vi_gui(ev: pd.DataFrame, den_block: int) -> dict[str, int]:
    """L của từng ví theo cách bài gốc tới hết `den_block`: cộng khi ví gửi lệnh nạp, trừ khi gửi lệnh rút, chặn dưới 0."""
    L: dict[str, int] = {}
    for r in ev[ev["block"] <= den_block].itertuples(index=False):
        L[r.vi] = max(0, L.get(r.vi, 0) + (r.L if r.kind == "mint" else -r.L))
    return L


def theo_be(ev: pd.DataFrame, den_block: int) -> int:
    """Thanh khoản thật của khoảng tường tới hết `den_block`: tổng nạp trừ tổng rút, không phụ thuộc ví."""
    e = ev[ev["block"] <= den_block]
    return int(sum(e.loc[e["kind"] == "mint", "L"]) - sum(e.loc[e["kind"] == "burn", "L"]))


def mot_vu(vu, thu_muc: Path, goc: dict | None) -> dict:
    """Một dòng so sánh cho một vụ của bảng bài gốc (`vu`: pool, tick_lower, tick_upper, t_m, t_b)."""
    ev = doc_lenh(thu_muc, vu.tick_lower, vu.tick_upper)
    ev_ca_cua_so = ev
    ev = ev[ev["block"] >= vu.t_m]                                 # bài gốc phát lại trong [t_m, t_b]
    tl = theo_vi_gui(ev, vu.t_b)
    d = dict(vu_id=vu.vu_id, thu_muc=thu_muc.name, n_lenh=len(ev), thieu_vi=int(ev["vi"].isna().sum()),
             L_tb_tl=sum(tl.values()), n_vi_tb_tl=sum(v > 0 for v in tl.values()), L_tb_be=theo_be(ev, vu.t_b))
    d["L_ma"] = d["L_tb_tl"] - d["L_tb_be"]
    d["ty_le_thua"] = d["L_ma"] / d["L_tb_be"] if d["L_tb_be"] > 0 else (float("inf") if d["L_ma"] > 0 else 0.0)
    ls = doc_lenh_lich_su(thu_muc, vu.tick_lower, vu.tick_upper)   # L_be đủ lịch sử: mọi Mint/Burn đúng khoảng từ lúc tạo bể tới t_b
    toan = pd.concat([ls[["block", "kind", "L"]] if len(ls) else None, ev_ca_cua_so[["block", "kind", "L"]]], ignore_index=True)
    d["L_tb_be_ls"] = theo_be(toan, vu.t_b)                          # cả cửa sổ (từ trước t_m) cộng lịch sử; rỗng thì chỉ cửa sổ
    d["ty_le_thua_ls"] = (d["L_tb_tl"] - d["L_tb_be_ls"]) / d["L_tb_be_ls"] if d["L_tb_be_ls"] > 0 else (float("inf") if d["L_tb_tl"] > 0 else 0.0)
    if goc is not None:
        A, V = goc.get("attacker_details", []), goc.get("victim_details_tb", [])
        LA, LV = sum(int(a["L_u_t0"]) for a in A), sum(int(v["L_u_t0"]) for v in V)
        LVb = sum(int(v["L_u_breach"]) for v in V)
        khop = sum(tl.get(v["address"].lower(), 0) == int(v["L_u_breach"]) for v in V)
        d.update(L_tb_goc=int(goc["pool_liquidity"]["L_pool_tb"] or 0), n_nan_nhan_goc=len(V), khop_tung_vi=khop,
                 LA_goc=LA, LV_goc=LV, LV_breach_goc=LVb,
                 k_goc=1 / (1 + LV / LA) ** 2 if LA > 0 else float("nan"),
                 k_be=1 / (1 + d["L_tb_be"] / LA) ** 2 if LA > 0 else float("nan"))
    return d


def chay(submission: Path, ra: Path = RA) -> pd.DataFrame:
    """So mọi vụ có đủ dữ liệu; ghi CSV `ra`, trả bảng."""
    vu = doc_bang_vu(BANG)
    goc = {}
    for f in (submission / "Part2" / "2-metrics" / "3-Role_dimension" / "1_role_outputs").glob("*.json"):
        r = json.loads(f.read_text(encoding="utf-8"))
        goc[(r["pool"].lower(), int(r["tick_key"].split("_")[0]))] = r
    dong = []
    for v in vu.itertuples(index=False):
        ung = [p for p in sorted(VU.glob(v.pool[:10] + "_*")) if not p.name.endswith("_nhanh")
               and int(p.name.split("_")[1]) <= v.t_m and list(p.glob("vi_lenh*.csv"))]
        ung = [p for p in ung if pd.read_csv(p / "su_kien.csv", usecols=["block"])["block"].max() >= v.t_b]
        if not ung:
            dong.append(dict(vu_id=v.vu_id, thu_muc="THIẾU"))
            continue
        dong.append(mot_vu(v, ung[-1], goc.get((v.pool, v.tick_lower))))
    d = pd.DataFrame(dong)
    ra.parent.mkdir(parents=True, exist_ok=True)
    d.to_csv(ra, index=False, encoding="utf-8")
    return d


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--submission", default=str(GOC.parent / "submission"), help="thư mục submission đã giải nén")
    a = ap.parse_args()
    d = chay(Path(a.submission))
    pd.set_option("display.width", 250, "display.max_columns", 40)
    c = d[d["thu_muc"] != "THIẾU"].copy()
    for k in ("L_tb_goc", "L_tb_tl", "L_tb_be", "L_ma", "LA_goc"):
        c[k] = c[k].astype(float)
    c["tl_khop_goc"] = (c["L_tb_tl"] - c["L_tb_goc"]).abs() <= 1e-9 * c["L_tb_goc"].clip(lower=1)
    print(c[["vu_id", "n_lenh", "thieu_vi", "n_nan_nhan_goc", "khop_tung_vi", "tl_khop_goc", "L_tb_goc", "L_tb_tl",
             "L_tb_be", "ty_le_thua", "k_goc", "k_be"]].to_string(index=False, float_format=lambda x: f"{x:.3g}"))
    print("thiếu dữ liệu:", d.loc[d["thu_muc"] == "THIẾU", "vu_id"].tolist())

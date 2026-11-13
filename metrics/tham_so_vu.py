"""Trích tham số thật của từng vụ trong bảng 29 vụ để dựng kịch bản mô phỏng theo vụ (`scenarios.quet_vu_that`).

    python -m metrics.tham_so_vu            # ghi ket_qua/that/tham_so_vu.csv và tham_so_vu_nen.json

Cần `su_kien.csv`, `swap_day_du.csv` trong `ket_qua/that/vu/*` (và lịch sử bể nếu đã tải), `ket_qua/that/so_bai_goc.csv`.
Mỗi vụ đổi về hệ "token bị xả D / token định giá Qt": p = giá D tính bằng Qt (p giảm khi xả), để soi gương sang
mô phỏng (ở đó token0 bị xả, giá ≈ 1). Đại lượng không thứ nguyên, chia cho L_A:
- `k` = 1/(1 + L_V/L_A)² với L_V = thanh khoản đúng khoảng tường còn lại lúc sập (theo sự kiện bể), L_A của bài gốc
  (thiếu thì lấy đỉnh L khoảng tường trong [t_m, t_b] trừ L_V);
- `nen_xa[i]`, `nen_kia[i]`: thanh khoản nền tương đương (trung bình theo √P của L hoạt động, không tính vị thế đúng
  khoảng tường) trong từng dải khoảng cách tick `MEP` về phía xả và phía kia, lúc t_b;
- `xa` = lượng D ròng vào bể từ mốc trước sập tới t_b + 400 block, nhân √p0 (đơn vị L); `farm_24h` = nửa khối lượng Qt
  mỗi 24 giờ trong đoạn swap đủ trước lúc rút tường, chia √p0 (đơn vị L);
- `sap_400`, `sap_2h`: thay đổi tương đối của p từ mốc trước sập (swap cuối khi giá còn ở tick tường, tìm trong 2 giờ
  trước t_b; không có thì swap cuối trước t_b) tới đáy trước t_b + 400 block, và tới t_b + 2 giờ.
Đơn vị L: số thô on-chain; block BSC 0,75 giây (đọc từ `moc.csv` nếu có).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from engine.tick_math import MAX_TICK, MIN_TICK
from metrics.so_bai_goc import BANG, VU
from metrics.tai_hien_vu import doc_su_kien
from scenarios.tai_vu_that import doc_bang_vu

GOC = Path(__file__).resolve().parents[1]
RA = GOC / "ket_qua" / "that" / "tham_so_vu.csv"
RA_NEN = GOC / "ket_qua" / "that" / "tham_so_vu_nen.json"
MEP = [0, 10, 30, 100, 300, 1000, 3000, 10000, 30000, 100000, MAX_TICK]    # mép dải khoảng cách tick tính từ tick tường
CUA_SO_SAP, CUA_SO_2H, TRUOC_XA, BO_TRUOC_RUT = 400, 9600, 50, 1200


def ban_do(ev: pd.DataFrame, den_block: int, bo: tuple[int, int] | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Bản đồ thanh khoản tới hết `den_block`, bỏ vị thế đúng khoảng `bo`: (mép tick tăng dần, L hoạt động trong
    [mép[i], mép[i+1])). `ev`: Mint/Burn với cột block, kind, tick_lower, tick_upper, L."""
    e = ev[ev["block"] <= den_block]
    if bo is not None:
        e = e[~((e["tick_lower"] == bo[0]) & (e["tick_upper"] == bo[1]))]
    dau = np.where(e["kind"] == "mint", 1.0, -1.0) * e["L"].to_numpy()
    net = pd.concat([pd.Series(dau, index=e["tick_lower"].to_numpy()), pd.Series(-dau, index=e["tick_upper"].to_numpy())])
    net = net.groupby(level=0).sum().sort_index()
    return net.index.to_numpy(dtype=float), np.maximum(net.cumsum().to_numpy(), 0.0)


def l_tuong_duong(mep: np.ndarray, L: np.ndarray, a: float, b: float) -> float:
    """Thanh khoản tương đương của đoạn tick [a, b): trung bình L theo √P (lượng token1 cần để đi hết đoạn chia Δ√P)."""
    if b <= a or len(mep) == 0:
        return 0.0
    diem = np.unique(np.concatenate([[a, b], mep[(mep > a) & (mep < b)]]))
    z = 1.0001 ** ((diem - a) / 2)                               # √P tương đối so với mép a (tránh tràn số)
    chi_so = np.searchsorted(mep, diem[:-1], side="right") - 1
    Ld = np.where(chi_so >= 0, L[np.clip(chi_so, 0, len(L) - 1)], 0.0)
    return float((Ld * np.diff(z)).sum() / (z[-1] - z[0]))


def ho_so_nen(mep: np.ndarray, L: np.ndarray, tick_tuong: int, huong: int) -> tuple[list[float], list[float]]:
    """Hồ sơ nền theo dải `MEP`: (phía xả, phía kia). `huong` = +1 nếu cú xả đẩy tick lên (token1 bị xả), −1 nếu xuống."""
    def dai(i: int, phia: int) -> tuple[float, float]:       # phia = +1: tick lớn hơn tường; −1: nhỏ hơn hoặc bằng
        lo, hi = MEP[i], MEP[i + 1]
        if phia > 0:
            return min(tick_tuong + 1 + lo, MAX_TICK), min(tick_tuong + 1 + hi, MAX_TICK)
        return max(tick_tuong + 1 - hi, MIN_TICK), max(tick_tuong + 1 - lo, MIN_TICK)
    xa = [l_tuong_duong(mep, L, *dai(i, huong)) for i in range(len(MEP) - 1)]
    kia = [l_tuong_duong(mep, L, *dai(i, -huong)) for i in range(len(MEP) - 1)]
    return xa, kia


def mot_vu(d: pd.DataFrame, vu, LA_goc: float, giay_block: float = 0.75) -> dict:
    """Tham số một vụ từ bảng sự kiện `d` của thư mục vụ (`doc_su_kien`) và một dòng bảng vụ (tick_lower, tick_upper, t_m, t_b)."""
    ev, sw = d[d["kind"] != "swap"], d[d["kind"] == "swap"]
    quanh = sw[(sw["block"] >= vu.t_b - CUA_SO_2H) & (sw["block"] <= vu.t_b + CUA_SO_SAP)]
    tai_tuong = quanh[quanh["tick"] == vu.tick_lower]             # mốc trước sập: swap cuối khi giá còn ở tick tường
    b0 = int(tai_tuong["block"].iloc[-1]) if len(tai_tuong) else int(vu.t_b) - 1   # (bài gốc đặt t_b lúc giá đã rời tường ở vài vụ)
    truoc = sw[sw["block"] <= b0]
    sau = sw[(sw["block"] > b0) & (sw["block"] <= vu.t_b + CUA_SO_SAP)]
    sau2 = sw[(sw["block"] > b0) & (sw["block"] <= vu.t_b + CUA_SO_2H)]
    if truoc.empty or sau.empty:
        return dict(vu_id=vu.vu_id, loi="thiếu swap quanh t_b")
    z0, tick0 = float(truoc["sqrtP"].iloc[-1]), int(truoc["tick"].iloc[-1])
    lech = float(sau["tick"].iloc[-1]) - tick0 or float(sau2["tick"].iloc[-1]) - tick0
    huong = 1 if lech > 0 else -1                                 # +1: token1 bị xả, giá token1/token0 tăng
    can_p0 = z0 if huong < 0 else 1 / z0                                # √p0, p = giá token bị xả tính bằng token kia
    p = (lambda s: s["sqrtP"] ** 2 if huong < 0 else 1 / s["sqrtP"] ** 2)
    tuong = ev[(ev["tick_lower"] == vu.tick_lower) & (ev["tick_upper"] == vu.tick_upper)]
    dau = np.where(tuong["kind"] == "mint", 1.0, -1.0) * tuong["L"].to_numpy()
    luy = pd.Series(np.cumsum(dau), index=tuong["block"].to_numpy())
    trong = luy[(luy.index >= vu.t_m) & (luy.index <= vu.t_b)]
    L_dinh = float(trong.max()) if len(trong) else 0.0
    L_V = max(float(luy[luy.index <= vu.t_b].iloc[-1]) if (luy.index <= vu.t_b).any() else 0.0, 0.0)
    L_A = LA_goc if LA_goc and LA_goc > 0 else max(L_dinh - L_V, 0.0)
    mep, L = ban_do(ev, vu.t_b, bo=(vu.tick_lower, vu.tick_upper))
    nen_xa, nen_kia = ho_so_nen(mep, L, int(vu.tick_lower), huong)
    cs = sau
    D_vao = float((cs["a0"] if huong < 0 else cs["a1"]).sum())          # dương: token bị xả vào bể (ròng)
    fm = sw[(sw["block"] >= b0 - CUA_SO_2H) & (sw["block"] < b0 - BO_TRUOC_RUT)]
    gio = (fm["block"].max() - fm["block"].min()) * giay_block / 3600 if len(fm) > 1 else 0.0
    Qt = float((fm["a1"] if huong < 0 else fm["a0"]).abs().sum())
    return dict(vu_id=vu.vu_id, huong=huong, tick_truoc=tick0, block_truoc=b0, block_day=int(sau.loc[p(sau).idxmin(), "block"]), tick_tuong=int(vu.tick_lower),
                gio_tuong=(vu.t_b - vu.t_m) * giay_block / 3600, L_A=L_A, L_A_nguon="bai_goc" if LA_goc and LA_goc > 0 else "dinh",
                L_dinh=L_dinh, L_V=L_V, k=1 / (1 + L_V / L_A) ** 2 if L_A > 0 else float("nan"),
                xa=D_vao * can_p0 / L_A if L_A > 0 else float("nan"),
                farm_24h=(Qt / 2 / gio * 24) / can_p0 / L_A if gio > 0 and L_A > 0 else float("nan"), gio_do_farm=gio,
                sap_400=float(p(sau).min() / p(truoc).iloc[-1] - 1), sap_2h=float(p(sau2).iloc[-1] / p(truoc).iloc[-1] - 1),
                nen_xa=[x / L_A if L_A > 0 else float("nan") for x in nen_xa],
                nen_kia=[x / L_A if L_A > 0 else float("nan") for x in nen_kia])


def chay(ra: Path = RA, ra_nen: Path = RA_NEN) -> pd.DataFrame:
    """Trích mọi vụ có thư mục dữ liệu; ghi bảng CSV (không gồm hồ sơ nền) và JSON hồ sơ nền theo `vu_id`."""
    s = pd.read_csv(GOC / "ket_qua" / "that" / "so_bai_goc.csv")
    vu = doc_bang_vu(BANG).merge(s[["vu_id", "thu_muc", "LA_goc", "n_nan_nhan_goc"]], on="vu_id")
    dong = []
    for th, g in vu[vu["thu_muc"] != "THIẾU"].groupby("thu_muc"):
        d = doc_su_kien(VU / th)
        for v in g.itertuples(index=False):
            r = mot_vu(d, v, float(v.LA_goc) if pd.notna(v.LA_goc) else 0.0)
            dong.append(dict(r, thu_muc=th, n_nan_nhan_goc=int(v.n_nan_nhan_goc)))
            print(f"{v.vu_id}: k = {r.get('k', float('nan')):.3g}, xả {r.get('xa', float('nan')):.3g}, sập 400 block {r.get('sap_400', float('nan')):.1%}", flush=True)
    b = pd.DataFrame(dong)
    ra.parent.mkdir(parents=True, exist_ok=True)
    b.drop(columns=["nen_xa", "nen_kia"], errors="ignore").to_csv(ra, index=False, encoding="utf-8")
    nen = {r["vu_id"]: dict(mep=MEP, nen_xa=r["nen_xa"], nen_kia=r["nen_kia"]) for r in dong if "nen_xa" in r}
    ra_nen.write_text(json.dumps(nen), encoding="utf-8")
    return b


if __name__ == "__main__":
    b = chay()
    pd.set_option("display.width", 250, "display.max_columns", 40)
    print(b[["vu_id", "n_nan_nhan_goc", "huong", "gio_tuong", "L_A_nguon", "k", "xa", "farm_24h", "sap_400", "sap_2h"]]
          .to_string(index=False, float_format=lambda x: f"{x:.3g}"))

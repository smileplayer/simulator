"""Kịch bản mô phỏng đặt tham số theo từng vụ thật (cải tiến "thực tế hơn"): vụ × biện pháp × loại nạn nhân × seed.

    python -m scenarios.quet_vu_that [--seeds 5] [--nhanh] [--out ket_qua/that/kich_ban_vu.csv]

Tham số lấy từ `ket_qua/that/tham_so_vu.csv` và `tham_so_vu_nen.json` (`python -m metrics.tham_so_vu`), soi gương về quy ước
mô phỏng (token0 bị xả, giá ≈ 1, tường ở tick 0) và co về L_A = 4e8:
- phí 0,01% (biến thể `f001`: σ × 0,04); c_V đặt sao cho Bổ đề 4, với đối thủ là tường cộng nền phủ tick tường, cho đúng
  L_V/L_A thật (`k_that` = k thật; cột `k` là k quy đổi dùng cho mô phỏng);
- nền: hồ sơ thanh khoản thật quanh tick tường lúc sập, theo dải khoảng cách tick (`bg_vi_the`);
- cú xả dừng ở đúng mức giá đáy thật (đáy trong 400 block): đặt giá vốn c_A bằng mức giá đó (điều kiện dừng thứ ba của
  Bổ đề 5), kho gấp 5 lần lượng token0 cần để tới đó qua thanh khoản nạn nhân Bổ đề 4 và hồ sơ nền; xả trong 1 bước;
- thời gian giữ tường = số giờ thật từ t_m tới t_b (chặn trong [24, 336] bước); giá ngoài đứng yên trước tường.
Không lấy từ dữ liệu: σ, số farmer (giữ co_so). Mặc định Q cũng giữ co_so: khối lượng cày thật so với tường lớn hơn co_so hàng
trăm lần, bước 1 giờ một lệnh mua không chở nổi. Cờ `--min` bật bước thời gian mịn (`buoc_con` vòng mua–bán mỗi giờ, cấu hình
`scenarios.run`) và đặt Q theo khối lượng cày thật đo trong 2 giờ trước lúc rút tường.
Chỉ chạy vụ có k < `--k_max` (mặc định 0,99: vụ còn nạn nhân lúc sập). Ghi nối từng dòng; chạy lại thì bỏ lượt đã có.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import time
import warnings
from pathlib import Path

import pandas as pd

from engine import MAX_TICK, MIN_TICK
from scenarios.quet_gd2 import BIEN_PHAP, dong_ket_qua

GOC = Path("ket_qua/that")
L_A_MP = 4e8
BP_VU = {k: BIEN_PHAP[k] for k in ("khong", "cap50", "cap25", "cap05", "delay168", "warn15", "warn40", "dyncap")}
KHOA = ["scenario_id", "bp", "victim_type", "seed"]
SAP_MAX = 0.95
SUC_CHUA_VONG = 0.6e-5   # phần L_A mà một farmer mua mỗi vòng: ba farmer ≈ 70% nửa tick (2,5e-5·L_A), không đẩy giá khỏi tick tường
VONG_MAX = 300
DU_KHO = 5.0          # kho dư so với lượng cần: điểm dừng cú xả là mức giá đáy thật (c_A), không phải hết kho


def _z(tick: float) -> float:
    """√P tại mép tick (giá = 1,0001^tick)."""
    return 1.0001 ** (tick / 2)


def vi_the_nen(mep: list[int], nen_xa: list[float], nen_kia: list[float], L_A: float = L_A_MP) -> list[list[float]]:
    """Hồ sơ nền thật → vị thế nền mô phỏng [(tick dưới, tick trên, L)]: phía xả nằm dưới tick 0, phía kia từ tick 0 lên."""
    vt = []
    for i in range(len(mep) - 1):
        lo, hi = mep[i], min(mep[i + 1], MAX_TICK)
        vt.append([max(-hi, MIN_TICK), -lo, nen_xa[i] * L_A])
        vt.append([lo, hi, nen_kia[i] * L_A])
    return [v for v in vt if v[2] > 0 and v[0] < v[1]]


def kho_xa(sap: float, k: float, vt: list[list[float]], L_A: float = L_A_MP) -> float:
    """Lượng token0 đẩy giá từ mép trên tick 0 xuống mức sập `sap` (âm, tỷ lệ) qua nạn nhân Bổ đề 4 (một tick) và nền `vt`."""
    dich = math.log(1 + max(sap, -SAP_MAX)) / math.log(1.0001)          # tick đích (âm)
    doan = [(lo, hi, L) for lo, hi, L in vt] + [(0, 1, L_A * (1 / math.sqrt(k) - 1))]
    tong = 0.0
    for lo, hi, L in doan:
        a, b = max(lo, dich), min(hi, 1.0)
        if b > a:
            tong += L * (1 / _z(a) - 1 / _z(b))
    return tong


def cau_hinh_vu(r, nen: dict, min_: bool = False) -> dict:
    """Ghi đè lên co_so cho một vụ thật (`r`: một dòng `tham_so_vu.csv`; `nen`: hồ sơ nền của vụ đó).

    `min_` (bước thời gian mịn): lấy thêm khối lượng cày thật. Trần Q mỗi farmer = `farm_24h`·L_A/3 (token1 mỗi 24 bước), và
    `buoc_con` = số vòng mua–bán mỗi giờ đủ để mỗi vòng ba farmer mua không quá khoảng nửa sức chứa một tick của tường cộng
    nạn nhân (chặn ở `VONG_MAX`; chạm chặn thì Q hạ theo, `farm_phu` = phần khối lượng thật được chở)."""
    vt = vi_the_nen(nen["mep"], nen["nen_xa"], nen["nen_kia"])
    gan = [(hi - lo, L) for lo, hi, L in vt if -1000 <= lo and hi <= 1000]
    L_gan = sum(w * L for w, L in gan) / max(sum(w for w, _ in gan), 1)
    giu = int(min(max(round(r.gio_tuong), 24), 336))
    b0 = sum(L for lo, hi, L in vt if lo <= 0 < hi) / L_A_MP          # nền phủ tick tường, so với L_A
    lv = 1 / math.sqrt(float(r.k)) - 1                                 # L_V/L_A thật
    k_mp = (1 + b0) / (lv + 1 + b0) ** 2                               # c_V sao cho Bổ đề 4 với đối thủ L_A + nền cho đúng L_V thật
    cfg = {"id": f"VU_{r.vu_id}", "k": k_mp, "k_that": float(r.k), "L_A": L_A_MP, "bg_vi_the": vt, "bg_band": None, "bg_tail": 0.0,
            "bg_size": max(500 * L_gan / 2e5, 1e-3), "vol_pre": 0.0,
            "attacker_inventory": DU_KHO * kho_xa(float(r.sap_400), float(r.k), vt),
            "c_A": 1.0, "c_A_ty_le": (1 + max(float(r.sap_400), -SAP_MAX)) * (1 - 1e-4), "dump_steps": 1,
            "t_m": 48, "wall_schedule": [[48, 1.0]], "t_0": 48 + giu, "steps": 48 + giu + 72,
            "victim_delay": int(min(30, max(1, giu // 4)))}
    if min_ and float(r.farm_24h) > 0:
        Q = float(r.farm_24h) * L_A_MP / 3
        suc_chua = SUC_CHUA_VONG * L_A_MP                                 # token1 mỗi farmer mỗi vòng (lúc chỉ có tường)
        n = int(min(max(math.ceil(Q / 24 / suc_chua), 1), VONG_MAX))
        Q_mp = min(Q, n * 24 * suc_chua)                                  # chạm VONG_MAX thì hạ Q để lệnh mua không vượt tick tường
        cfg.update(Q=Q_mp, buoc_con=n, farm_phu=Q_mp / Q)
    return cfg


def danh_sach_vu(k_max: float = 0.99, min_: bool = False) -> list[dict]:
    """Các vụ thật có nạn nhân lúc sập (k < `k_max`), đã thành ghi đè cấu hình."""
    b = pd.read_csv(GOC / "tham_so_vu.csv")
    nen = json.loads((GOC / "tham_so_vu_nen.json").read_text(encoding="utf-8"))
    b = b[(b["k"] < k_max) & (b["sap_400"] < 0)]
    return [cau_hinh_vu(r, nen[r.vu_id], min_) for r in b.itertuples(index=False)]


def chay(seeds: int, out: Path, nhanh: bool = False, k_max: float = 0.99, min_: bool = False) -> None:
    """Chạy mọi lượt còn thiếu, ghi nối từng dòng; `nhanh`: 2 vụ × 2 biện pháp × 1 seed để đo giờ."""
    warnings.filterwarnings("ignore")
    ds, bps = danh_sach_vu(k_max, min_), list(BP_VU)
    if nhanh:
        ds, bps, seeds = ds[:2], bps[:2], 1
    da_co, cot = set(), None
    if out.exists() and out.stat().st_size > 0:
        with out.open(encoding="utf-8", newline="") as f:
            rd = csv.DictReader(f)
            cot = rd.fieldnames
            da_co = {tuple(row[k] for k in KHOA) for row in rd}
    viec = [(vu, bp, vt, sd) for vu in ds for bp in bps for vt in ("omniscient", "adaptive") for sd in range(seeds)
            if (vu["id"], bp, vt, str(sd)) not in da_co]
    print(f"{len(ds)} vụ; {len(da_co)} lượt đã có, còn {len(viec)} lượt → {out}", flush=True)
    t0 = time.time()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8", newline="") as f:
        w = None
        for i, (vu, bp, vt, sd) in enumerate(viec):
            r = dong_ket_qua(vu, bp, vt, sd, None, BP_VU, "f001")
            r.update(kho=vu["attacker_inventory"], giu_tuong=vu["t_0"] - vu["t_m"], k_that=vu["k_that"], buoc_con=vu.get("buoc_con", 1), farm_phu=vu.get("farm_phu", float("nan")))
            if w is None:
                cot = cot or list(r)
                w = csv.DictWriter(f, fieldnames=cot, extrasaction="ignore")
                if f.tell() == 0:
                    w.writeheader()
            w.writerow(r)
            f.flush()
            if (i + 1) % 20 == 0 or i == len(viec) - 1:
                da = time.time() - t0
                print(f"{i + 1}/{len(viec)} · {da:.0f}s · còn ≈ {da / (i + 1) * (len(viec) - i - 1) / 60:.1f} phút", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--nhanh", action="store_true", help="2 vụ × 2 biện pháp × 1 seed, ghi file _nhanh")
    ap.add_argument("--k_max", type=float, default=0.99, help="chỉ chạy vụ có k nhỏ hơn mức này")
    ap.add_argument("--min", dest="min_", action="store_true", help="bước thời gian mịn: khối lượng cày thật, nhiều vòng mua–bán mỗi giờ; ghi kich_ban_vu_min.csv")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    ten = "kich_ban_vu" + ("_min" if a.min_ else "") + ("_nhanh" if a.nhanh else "") + ".csv"
    chay(a.seeds, Path(a.out or GOC / ten), a.nhanh, a.k_max, a.min_)

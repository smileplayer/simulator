"""Kẻ tấn công phản ứng tốt nhất bằng tìm kiếm hộp đen (thay phép thử F "chọn lại L_A trên lưới 1 chiều").

Với mỗi (vụ, biện pháp, loại nạn nhân), tìm vectơ tham số θ của kẻ tấn công cực đại hóa **trung vị qua seed huấn
luyện** (0–9) của lợi tăng thêm = `dc_excess` + `dc_farm_pnl` (token1, chỉ số chính bảng RQ2), rồi BÁO trên seed kiểm
(10–19) cho cả θ tìm được (`kieu = "tim"`) và kẻ tấn công gốc θ₀ (`kieu = "goc"`). Chỉ dùng khóa cấu hình đã có:

- `m`: hệ số độ dày tường, L_A × m, log-đều trong [0,25; 4]; giữ c_V vật lý của vụ (như F, `_m_LA`);
- `t_0`: giờ rút tường (bước, nguyên) trong [96; 216]; `steps = t_0 + 72` để còn đủ pha xả và Post (như khóa `giu`);
- `ty_le_48`: phần L_A dựng ở giờ 48, phần còn lại dựng ở giờ 72 (`wall_schedule`), trong [0,2; 1];
- `dump_steps` ∈ {1, 2, 4, 8} (bước xả); `so_lat_rut` ∈ {1, 2, 5, 10} (chỉ có tác dụng khi có phạt rút sớm).
`attacker_farm_share` KHÔNG vào vectơ: vùng RQ1 của bảng RQ2 không cho kẻ tấn công tự farm (s = 0).

Gốc θ₀ = (m 1; t_0 168; 0,6; 2; 1) tái tạo đúng lượt RQ2 (`steps` = 240). Thuật toán: thử θ₀ trước, rồi 60% mẫu ngẫu
nhiên toàn miền, 40% nhiễu quanh điểm tốt nhất hiện thời (bước nhiễu thu nhỏ dần); chỉ numpy, bộ sinh số có seed cố
định theo (vụ, biện pháp, loại nạn nhân) nên tái lập được và không phụ thuộc thứ tự chạy.

Chạy (từ `04_Simulator/`): `python -m scenarios.tim_kiem_tan_cong [--n_thu 200] [--vu L27_00,L27_01]
[--bien_phap khong,cap05] [--victim omniscient] [--tien_trinh 4] [--hau_to _a] [--nhanh]`; `--tom_tat` in bảng.
Ghi dần `ket_qua/gd2/tim_kiem/tham_so<hau_to>.csv` (θ tốt nhất + mục tiêu huấn luyện) và `kiem<hau_to>.csv` (lượt
trên seed kiểm, đủ cột như `quet_gd2.dong_ket_qua`). Chạy lại thì bỏ phần đã xong. Biện pháp `khong` phải có trong
cùng lượt chạy (hoặc file khác cùng thư mục) để tính % thay đổi.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import time
import warnings
import zlib
from pathlib import Path

import numpy as np

from scenarios.batch import FILE_TO_HOP, cau_hinh
from scenarios.quet_gd2 import BIEN_PHAP, BIEN_PHAP_PHAT, LOAI_VICTIM, dong_ket_qua, loi_nhuan_dia_chi
from scenarios.run import run_frame

THU_MUC = Path("ket_qua/gd2/tim_kiem")
BANG_TK = {**{k: BIEN_PHAP[k] for k in ("khong", "cap50", "cap05", "dyncap", "delay168", "warn15", "warn40")},
           "phat168": BIEN_PHAP_PHAT["phat168"]}
M_MIN, M_MAX = 0.25, 4.0
T0_MIN, T0_MAX = 96, 216
TL_MIN, TL_MAX = 0.2, 1.0
DUMP = (1, 2, 4, 8)
LAT = (1, 2, 5, 10)
THETA_GOC = {"m": 1.0, "t_0": 168, "ty_le_48": 0.6, "dump_steps": 2, "so_lat_rut": 1}
TEN_THETA = list(THETA_GOC)
SEED_HL = list(range(10))
SEED_KIEM = list(range(10, 20))
SEED_TIM = 20261111
PHAN_NGAU_NHIEN = 0.6
TOL = 1e-6                                   # token1: chỉ nhận θ mới khi hơn hẳn (hòa → giữ θ₀, tránh nhiễu số)
KHOA_TS = ["scenario_id", "bp", "victim_type"]
KHOA_KIEM = ["scenario_id", "bp", "victim_type", "kieu", "seed"]


# ---------------------------------------------------------------- vectơ tham số → cấu hình

def vu_tham_so(vu: dict, theta: dict) -> dict:
    """Ghi đè vụ theo θ (m: lần L_A; t_0, steps: bước; ty_le_48: phần L_A ở giờ 48; dump_steps, so_lat_rut).
    Dùng cho `quet_gd2.dong_ket_qua` (khóa `_m_LA` giữ c_V vật lý)."""
    a = float(theta["ty_le_48"])
    lich = [[48, a]] + ([[72, 1.0 - a]] if 1.0 - a > 1e-9 else [])
    t0 = int(theta["t_0"])
    return dict(vu, _m_LA=float(theta["m"]), wall_schedule=lich, t_0=t0, steps=t0 + 72,
                dump_steps=int(theta["dump_steps"]), so_lat_rut=int(theta["so_lat_rut"]))


def cau_hinh_luot(vu: dict, bp: str, victim: str, theta: dict) -> dict:
    """Config đầy đủ của một lượt (vụ, biện pháp, loại nạn nhân, θ), dựng y như `dong_ket_qua` (farm_share = 0)."""
    v = vu_tham_so(vu, theta)
    cfg = cau_hinh(v)
    cfg["L_A"] = cfg["L_A"] * float(v["_m_LA"])              # c_V đã tính với L_A gốc → giữ
    bp_cfg = dict(BANG_TK[bp] or {})
    bp_cfg.pop("_cfg", None)
    cfg.update(defense=bp_cfg if bp_cfg.get("name") else None, victim_type=victim, attacker_farm_share=0.0)
    return cfg


def loi_tang_them(vu: dict, bp: str, victim: str, theta: dict, seed: int) -> float:
    """Lợi tăng thêm của kẻ tấn công (token1) = dc_excess + dc_farm_pnl của một lượt; NaN nếu không có cú xả."""
    r = loi_nhuan_dia_chi(run_frame(cau_hinh_luot(vu, bp, victim, theta), seed))
    return r["dc_excess"] + r["dc_farm_pnl"]


def muc_tieu(vu: dict, bp: str, victim: str, theta: dict, seeds=SEED_HL) -> float:
    """Trung vị qua `seeds` của lợi tăng thêm (token1), bỏ NaN; toàn NaN → −inf."""
    x = np.array([loi_tang_them(vu, bp, victim, theta, s) for s in seeds], dtype=float)
    return float(np.nanmedian(x)) if np.isfinite(x).any() else -math.inf


# ---------------------------------------------------------------- tìm kiếm

def _rng(vu_id: str, bp: str, victim: str, seed: int = SEED_TIM) -> np.random.Generator:
    ma = [seed] + [zlib.crc32(s.encode("utf-8")) for s in (vu_id, bp, victim)]
    return np.random.default_rng(np.random.SeedSequence(ma))


def mau_ngau_nhien(rng: np.random.Generator) -> dict:
    """Một θ ngẫu nhiên toàn miền (m log-đều, t_0 nguyên đều, ty_le_48 đều, hai biến rời rạc đều)."""
    return {"m": float(math.exp(rng.uniform(math.log(M_MIN), math.log(M_MAX)))),
            "t_0": int(rng.integers(T0_MIN, T0_MAX + 1)),
            "ty_le_48": float(rng.uniform(TL_MIN, TL_MAX)),
            "dump_steps": int(rng.choice(DUMP)), "so_lat_rut": int(rng.choice(LAT))}


def _buoc_roi_rac(rng, ds: tuple, x: int, p: float) -> int:
    i = ds.index(x)
    if rng.random() < p:
        i = int(np.clip(i + rng.choice((-1, 1)), 0, len(ds) - 1))
    return int(ds[i])


def mau_lan_can(rng: np.random.Generator, tot: dict, ty: float) -> dict:
    """θ nhiễu quanh `tot`; `ty` ∈ (0, 1] co bước nhiễu (log m ± 0,35·ty, t_0 ± 15·ty bước, ty_le_48 ± 0,12·ty)."""
    lm = math.log(tot["m"]) + rng.normal(0.0, 0.35 * ty)
    return {"m": float(math.exp(np.clip(lm, math.log(M_MIN), math.log(M_MAX)))),
            "t_0": int(np.clip(round(tot["t_0"] + rng.normal(0.0, 15.0 * ty)), T0_MIN, T0_MAX)),
            "ty_le_48": float(np.clip(tot["ty_le_48"] + rng.normal(0.0, 0.12 * ty), TL_MIN, TL_MAX)),
            "dump_steps": _buoc_roi_rac(rng, DUMP, tot["dump_steps"], 0.3 * ty + 0.1),
            "so_lat_rut": _buoc_roi_rac(rng, LAT, tot["so_lat_rut"], 0.3 * ty + 0.1)}


def tim_kiem(vu: dict, bp: str, victim: str, n_thu: int, seeds=SEED_HL, seed_tim: int = SEED_TIM) -> dict:
    """Tìm θ cực đại `muc_tieu` với `n_thu` lượt thử (lượt 0 = θ₀); trả θ tốt nhất, `obj_tot`, `obj_goc` (token1)."""
    rng = _rng(vu["id"], bp, victim, seed_tim)
    n_nn = max(int(round(PHAN_NGAU_NHIEN * (n_thu - 1))), 0)
    da_thu: dict[tuple, float] = {}
    tot, obj_tot = dict(THETA_GOC), -math.inf
    obj_goc = math.nan
    for i in range(n_thu):
        if i == 0:
            th = dict(THETA_GOC)
        elif i <= n_nn:
            th = mau_ngau_nhien(rng)
        else:
            ty = 1.0 - 0.7 * (i - n_nn - 1) / max(n_thu - n_nn - 1, 1)
            th = mau_lan_can(rng, tot, ty)
        ma = (round(th["m"], 6), th["t_0"], round(th["ty_le_48"], 6), th["dump_steps"], th["so_lat_rut"])
        if ma in da_thu:
            continue
        o = muc_tieu(vu, bp, victim, th, seeds)
        da_thu[ma] = o
        if i == 0:
            obj_goc = o
        if o > obj_tot + TOL or (i == 0 and o > obj_tot):
            tot, obj_tot = th, o
    return {**tot, "obj_tot": obj_tot, "obj_goc": obj_goc, "n_danh_gia": len(da_thu)}


# ---------------------------------------------------------------- một việc (vụ, bp, victim) + ghi dần

def _doc_khoa(p: Path, khoa: list[str]) -> set[tuple]:
    if not p.exists() or p.stat().st_size == 0:
        return set()
    with p.open(encoding="utf-8", newline="") as f:
        return {tuple(r[k] for k in khoa) for r in csv.DictReader(f)}


def _doc_theta(p: Path) -> dict[tuple, dict]:
    if not p.exists() or p.stat().st_size == 0:
        return {}
    with p.open(encoding="utf-8", newline="") as f:
        return {tuple(r[k] for k in KHOA_TS): {"m": float(r["m"]), "t_0": int(r["t_0"]),
                                               "ty_le_48": float(r["ty_le_48"]),
                                               "dump_steps": int(r["dump_steps"]), "so_lat_rut": int(r["so_lat_rut"])}
                for r in csv.DictReader(f)}


def lam_viec(vu: dict, bp: str, victim: str, n_thu: int, seed_hl, seed_kiem, theta_co: dict | None,
             kiem_xong: set) -> dict:
    """Tìm θ (nếu chưa có) rồi chạy các lượt kiểm còn thiếu; trả {"ts": dòng tham_so hoặc None, "kiem": [dòng]}."""
    warnings.filterwarnings("ignore")
    t0 = time.time()
    ts = None
    if theta_co is None:
        kq = tim_kiem(vu, bp, victim, n_thu, seed_hl)
        ts = {"scenario_id": vu["id"], "bp": bp, "victim_type": victim, **{k: kq[k] for k in TEN_THETA},
              "obj_tot": kq["obj_tot"], "obj_goc": kq["obj_goc"], "n_thu": n_thu, "n_danh_gia": kq["n_danh_gia"],
              "seed_hl": " ".join(map(str, seed_hl)), "giay": round(time.time() - t0, 1)}
        theta = {k: kq[k] for k in TEN_THETA}
    else:
        theta = theta_co
    dong = []
    for kieu, th in (("goc", THETA_GOC), ("tim", theta)):
        for sd in seed_kiem:
            if (vu["id"], bp, victim, kieu, str(sd)) in kiem_xong:
                continue
            r = dong_ket_qua(vu_tham_so(vu, th), bp, victim, sd, bang=BANG_TK)
            r = {"kieu": kieu, **{f"th_{k}": th[k] for k in TEN_THETA}, **r}
            r["loi_tang_them"] = r["dc_excess"] + r["dc_farm_pnl"]
            dong.append(r)
    return {"ts": ts, "kiem": dong}


class _GhiCSV:
    """Ghi nối CSV, giữ thứ tự cột của file đã có, flush sau mỗi dòng."""

    def __init__(self, p: Path):
        self.p, self.f, self.w = p, None, None
        self.cot = None
        if p.exists() and p.stat().st_size > 0:
            with p.open(encoding="utf-8", newline="") as f:
                self.cot = csv.DictReader(f).fieldnames

    def ghi(self, r: dict) -> None:
        if self.f is None:
            self.f = self.p.open("a", encoding="utf-8", newline="")
            self.cot = self.cot or list(r)
            self.w = csv.DictWriter(self.f, fieldnames=self.cot, extrasaction="ignore")
            if self.f.tell() == 0:
                self.w.writeheader()
        self.w.writerow(r)
        self.f.flush()

    def dong(self) -> None:
        if self.f is not None:
            self.f.close()


def _goi(args):
    return lam_viec(*args)


def chay(n_thu: int = 200, thu_muc: Path = THU_MUC, hau_to: str = "", vu_chon=None, bp_chon=None,
         victim_chon=None, seed_hl=SEED_HL, seed_kiem=SEED_KIEM, tien_trinh: int = 1, ds_vu: list | None = None) -> None:
    """Chạy mọi (vụ, biện pháp, loại nạn nhân) còn thiếu, ghi dần `tham_so<hau_to>.csv` và `kiem<hau_to>.csv`."""
    warnings.filterwarnings("ignore")
    thu_muc.mkdir(parents=True, exist_ok=True)
    p_ts, p_kiem = thu_muc / f"tham_so{hau_to}.csv", thu_muc / f"kiem{hau_to}.csv"
    ds = ds_vu if ds_vu is not None else json.loads(FILE_TO_HOP.read_text(encoding="utf-8"))
    if vu_chon:
        ds = [v for v in ds if v["id"] in vu_chon]
    bps = [b for b in BANG_TK if not bp_chon or b in bp_chon]
    vts = [v for v in LOAI_VICTIM if not victim_chon or v in victim_chon]
    theta_co, kiem_xong = _doc_theta(p_ts), _doc_khoa(p_kiem, KHOA_KIEM)
    viec = []
    for vu in ds:
        for bp in bps:
            for vt in vts:
                th = theta_co.get((vu["id"], bp, vt))
                con = [(k, s) for k in ("goc", "tim") for s in seed_kiem
                       if (vu["id"], bp, vt, k, str(s)) not in kiem_xong]
                if th is None or con:
                    xong = {x for x in kiem_xong if x[:3] == (vu["id"], bp, vt)}
                    viec.append((vu, bp, vt, n_thu, list(seed_hl), list(seed_kiem), th, xong))
    print(f"[tim_kiem] {len(viec)} việc (vụ × biện pháp × nạn nhân) còn thiếu, n_thu = {n_thu}, "
          f"{tien_trinh} tiến trình → {p_ts}, {p_kiem}")
    g_ts, g_kiem = _GhiCSV(p_ts), _GhiCSV(p_kiem)
    t0 = time.time()

    def nhan(i, kq):
        if kq["ts"] is not None:
            g_ts.ghi(kq["ts"])
        for r in kq["kiem"]:
            g_kiem.ghi(r)
        da = time.time() - t0
        print(f"{i + 1}/{len(viec)} · {da:.0f}s · còn ≈ {da / (i + 1) * (len(viec) - i - 1) / 60:.1f} phút", flush=True)

    try:
        if tien_trinh > 1 and len(viec) > 1:
            from multiprocessing import get_context
            with get_context("spawn").Pool(tien_trinh) as pool:
                for i, kq in enumerate(pool.imap_unordered(_goi, viec)):
                    nhan(i, kq)
        else:
            for i, v in enumerate(viec):
                nhan(i, lam_viec(*v))
    finally:
        g_ts.dong()
        g_kiem.dong()
    print(f"Xong → {thu_muc}")


# ---------------------------------------------------------------- tóm tắt

def _pct(a: np.ndarray, b: np.ndarray) -> float:
    """% thay đổi như bảng RQ2: 100·(TB a − TB b)/|TB b| trên các cặp đủ số."""
    ok = np.isfinite(a) & np.isfinite(b)
    if not ok.any() or np.mean(b[ok]) == 0:
        return math.nan
    return float(100 * (np.mean(a[ok]) - np.mean(b[ok])) / abs(np.mean(b[ok])))


def tom_tat(thu_muc: Path = THU_MUC, nhanh: bool = False):
    """Bảng trên seed kiểm: mỗi biện pháp × loại nạn nhân, % thay đổi lợi tăng thêm so với `khong` của kẻ tấn công
    gốc và tìm kiếm (cặp phản thực cùng vụ + seed; tìm kiếm so với θ tìm cho `khong`), hiệu tìm − gốc cùng biện pháp
    (token1), trung vị θ chọn. Đọc mọi `kiem*.csv`, `tham_so*.csv` trong `thu_muc` (chỉ bản `_nhanh` nếu `nhanh`)."""
    import pandas as pd

    def doc(ten):
        ds = [p for p in sorted(thu_muc.glob(f"{ten}*.csv")) if ("_nhanh" in p.name) == nhanh]
        return pd.concat([pd.read_csv(p) for p in ds], ignore_index=True)
    kiem, ts = doc("kiem"), doc("tham_so")
    kiem = kiem.drop_duplicates(KHOA_KIEM)
    ts = ts.drop_duplicates(KHOA_TS)
    kiem["loi_tang_them"] = kiem["dc_excess"] + kiem["dc_farm_pnl"]
    k = ["scenario_id", "victim_type", "kieu", "seed"]
    goc = kiem[kiem.bp == "khong"][k + ["loi_tang_them"]].rename(columns={"loi_tang_them": "loi_khong"})
    d = kiem.merge(goc, on=k, how="inner")
    out = []
    for (bp, vt), g in d.groupby(["bp", "victim_type"], sort=False):
        a, b = g[g.kieu == "goc"], g[g.kieu == "tim"]
        ab = a.merge(b[["scenario_id", "seed", "loi_tang_them"]], on=["scenario_id", "seed"], suffixes=("", "_tim"))
        t = ts[(ts.bp == bp) & (ts.victim_type == vt)]
        out.append({"bp": bp, "victim_type": vt, "n_cap": len(ab),
                    "goc_%": _pct(a.loi_tang_them.to_numpy(float), a.loi_khong.to_numpy(float)),
                    "tim_%": _pct(b.loi_tang_them.to_numpy(float), b.loi_khong.to_numpy(float)),
                    "goc_tv": a.loi_tang_them.median(), "tim_tv": b.loi_tang_them.median(),
                    "tim_tru_goc_tv": (ab.loi_tang_them_tim - ab.loi_tang_them).median(),
                    "ty_le_tim_thang": float((ab.loi_tang_them_tim > ab.loi_tang_them + 1e-9).mean()) if len(ab) else math.nan,
                    "hl_tot_tru_goc_tv": (t.obj_tot - t.obj_goc).median(),
                    **{f"{c}_tv": t[c].median() for c in TEN_THETA}})
    bang = pd.DataFrame(out)
    with pd.option_context("display.width", 200, "display.max_columns", 30, "display.float_format", "{:.3g}".format):
        print("Seed kiểm. goc_% / tim_% = % thay đổi lợi tăng thêm so với 'khong' (như bảng RQ2, tỷ số trung bình "
              "trên cặp cùng vụ + seed); *_tv = trung vị (token1); ty_le_tim_thang = phần cặp tìm > gốc cùng biện pháp;"
              " hl_tot_tru_goc_tv = cải thiện trên seed huấn luyện; m..so_lat_rut_tv = trung vị θ chọn.")
        print(bang.to_string(index=False))
    return bang


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_thu", type=int, default=200, help="số lượt thử θ mỗi (vụ, biện pháp, nạn nhân)")
    ap.add_argument("--vu", default=None, help="mã vụ, phân cách dấu phẩy (mặc định cả 30 vụ RQ1)")
    ap.add_argument("--bien_phap", default=None, help=f"biện pháp, phân cách dấu phẩy, trong {list(BANG_TK)}")
    ap.add_argument("--victim", default=None, help="omniscient,adaptive")
    ap.add_argument("--tien_trinh", type=int, default=1, help="số tiến trình song song trong một lệnh")
    ap.add_argument("--hau_to", default="", help="hậu tố file khi chạy nhiều lệnh song song (vd _a)")
    ap.add_argument("--thu_muc", default=str(THU_MUC))
    ap.add_argument("--nhanh", action="store_true", help="2 vụ × {khong, cap05} × n_thu 20 × 3 seed HL + 3 seed kiểm")
    ap.add_argument("--tom_tat", action="store_true", help="chỉ in bảng tóm tắt từ các file đã có")
    a = ap.parse_args()
    tach = (lambda s: [x.strip() for x in s.split(",") if x.strip()] if s else None)
    tm = Path(a.thu_muc)
    if a.tom_tat:
        tom_tat(tm, a.nhanh)
    elif a.nhanh:
        ds = json.loads(FILE_TO_HOP.read_text(encoding="utf-8"))[:2]
        chay(a.n_thu if a.n_thu != 200 else 20, tm, "_nhanh" + a.hau_to, [v["id"] for v in ds],
             tach(a.bien_phap) or ["khong", "cap05"], tach(a.victim), SEED_HL[:3], SEED_KIEM[:3], a.tien_trinh)
    else:
        chay(a.n_thu, tm, a.hau_to, tach(a.vu), tach(a.bien_phap), tach(a.victim), SEED_HL, SEED_KIEM, a.tien_trinh)

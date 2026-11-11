"""Kẻ tấn công tìm kiếm hộp đen (scenarios.tim_kiem_tan_cong): θ → config, θ₀ = lượt gốc, tái lập, chạy tiếp."""
import csv
import json

import numpy as np
import pytest

import scenarios.tim_kiem_tan_cong as tk
from scenarios.batch import FILE_TO_HOP, cau_hinh
from scenarios.quet_gd2 import dong_ket_qua

VU = json.loads(FILE_TO_HOP.read_text(encoding="utf-8"))[0]


def test_theta_thanh_cau_hinh_hop_le():
    rng = np.random.default_rng(0)
    goc = cau_hinh(VU)
    for _ in range(50):
        th = tk.mau_ngau_nhien(rng)
        cfg = tk.cau_hinh_luot(VU, "phat168", "adaptive", th)
        assert tk.M_MIN <= th["m"] <= tk.M_MAX
        assert cfg["L_A"] == pytest.approx(goc["L_A"] * th["m"])
        assert cfg["c_V"] == pytest.approx(goc["c_V"])              # giữ c_V vật lý
        assert tk.T0_MIN <= cfg["t_0"] <= tk.T0_MAX and cfg["steps"] == cfg["t_0"] + 72
        assert sum(r for _, r in cfg["wall_schedule"]) == pytest.approx(1.0)
        assert all(r > 0 for _, r in cfg["wall_schedule"])
        assert max(t for t, _ in cfg["wall_schedule"]) < cfg["t_0"]
        assert cfg["dump_steps"] in tk.DUMP and cfg["so_lat_rut"] in tk.LAT
        assert cfg["defense"]["name"] == "phat" and cfg["attacker_farm_share"] == 0.0
    th = dict(tk.THETA_GOC, ty_le_48=1.0)
    assert tk.cau_hinh_luot(VU, "khong", "omniscient", th)["wall_schedule"] == [[48, 1.0]]
    lan_can = tk.mau_lan_can(rng, tk.THETA_GOC, 1.0)
    assert set(lan_can) == set(tk.THETA_GOC)


def test_theta_goc_tai_tao_luot_goc():
    cfg = tk.cau_hinh_luot(VU, "cap05", "omniscient", tk.THETA_GOC)
    goc = cau_hinh(VU)
    for k in ("L_A", "c_V", "t_0", "steps", "wall_schedule", "dump_steps"):
        assert cfg[k] == goc[k], k
    for bp, vt in (("khong", "omniscient"), ("cap05", "adaptive"), ("phat168", "omniscient")):
        bang = tk.BANG_TK if bp == "phat168" else None
        r0 = dong_ket_qua(VU, bp, vt, 1, bang=bang)
        x = tk.loi_tang_them(VU, bp, vt, tk.THETA_GOC, 1)
        assert x == pytest.approx(r0["dc_excess"] + r0["dc_farm_pnl"], rel=1e-12, abs=1e-9)
        r1 = dong_ket_qua(tk.vu_tham_so(VU, tk.THETA_GOC), bp, vt, 1, bang=tk.BANG_TK)
        assert r1["dc_excess"] == pytest.approx(r0["dc_excess"], rel=1e-12, abs=1e-9)


def test_duong_nhe_khop_dong_ket_qua():
    th = {"m": 2.3, "t_0": 130, "ty_le_48": 0.35, "dump_steps": 4, "so_lat_rut": 5}
    r = dong_ket_qua(tk.vu_tham_so(VU, th), "phat168", "adaptive", 2, bang=tk.BANG_TK)
    assert r["t_0"] == 130 and r["steps"] == 202 and r["so_lat_rut"] == 5
    assert tk.loi_tang_them(VU, "phat168", "adaptive", th, 2) == pytest.approx(
        r["dc_excess"] + r["dc_farm_pnl"], rel=1e-12, abs=1e-9)


def test_tim_kiem_tai_lap(monkeypatch):
    # mục tiêu giả (nhanh) để kiểm riêng thuật toán: tái lập và không thua θ₀
    def gia(vu, bp, victim, th, seeds=None):
        return -(np.log(th["m"]) - 0.7) ** 2 - ((th["t_0"] - 120) / 50) ** 2 + 0.1 * th["dump_steps"]
    monkeypatch.setattr(tk, "muc_tieu", gia)
    a = tk.tim_kiem(VU, "cap05", "adaptive", 60)
    b = tk.tim_kiem(VU, "cap05", "adaptive", 60)
    c = tk.tim_kiem(VU, "cap50", "adaptive", 60)
    assert a == b
    assert a != c
    assert a["obj_tot"] >= a["obj_goc"]
    assert a["obj_goc"] == pytest.approx(gia(None, None, None, tk.THETA_GOC))


def test_tim_kiem_that_tai_lap_va_khong_thua_goc():
    a = tk.tim_kiem(VU, "cap05", "omniscient", 4, seeds=[0])
    b = tk.tim_kiem(VU, "cap05", "omniscient", 4, seeds=[0])
    assert a == b and a["obj_tot"] >= a["obj_goc"]


def test_chay_tiep_khong_lam_lai(tmp_path, monkeypatch):
    dem = {"tim": 0, "kiem": 0}
    goc_tim, goc_dkq = tk.tim_kiem, tk.dong_ket_qua

    def tim(*a, **k):
        dem["tim"] += 1
        return goc_tim(*a, **k)

    def dkq(*a, **k):
        dem["kiem"] += 1
        return goc_dkq(*a, **k)
    monkeypatch.setattr(tk, "tim_kiem", tim)
    monkeypatch.setattr(tk, "dong_ket_qua", dkq)
    tham = dict(n_thu=2, thu_muc=tmp_path, ds_vu=[VU], bp_chon=["khong", "cap05"], victim_chon=["omniscient"],
                seed_hl=[0], seed_kiem=[10])
    tk.chay(**tham)
    assert dem == {"tim": 2, "kiem": 4}                     # 2 bp × (goc + tim) × 1 seed kiểm
    with (tmp_path / "kiem.csv").open(encoding="utf-8") as f:
        dong = list(csv.DictReader(f))
    assert {(r["bp"], r["kieu"], r["seed"]) for r in dong} == {
        (b, k, "10") for b in ("khong", "cap05") for k in ("goc", "tim")}
    tk.chay(**tham)
    assert dem == {"tim": 2, "kiem": 4}                     # chạy lại: không làm gì
    tk.chay(**dict(tham, seed_kiem=[10, 11]))               # thêm seed kiểm: chỉ chạy phần mới, không tìm lại
    assert dem == {"tim": 2, "kiem": 8}
    with (tmp_path / "tham_so.csv").open(encoding="utf-8") as f:
        assert len(list(csv.DictReader(f))) == 2
    bang = tk.tom_tat(tmp_path)
    assert set(bang.bp) == {"khong", "cap05"} and (bang.n_cap == 2).all()

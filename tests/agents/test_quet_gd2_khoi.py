"""Test khói cho 4 chế độ quét GĐ2 (mặc định "chinh", farm, k_nho, luoi): danh sách việc + 1 lượt đủ cột chính."""
import math

import pytest

from scenarios.quet_gd2 import danh_sach_viec, dong_ket_qua


@pytest.mark.parametrize("che_do", ["chinh", "farm", "k_nho", "luoi"])
def test_che_do_chay_duoc_mot_luot(che_do):
    viec = danh_sach_viec(che_do, seeds=1, nhanh=True)
    assert len(viec) > 0
    vu, bp, vt, sd, fs, bang = viec[0]
    r = dong_ket_qua(vu, bp, vt, sd, fs, bang)
    assert {"dc_excess", "bp", "victim_type", "scenario_id", "seed"} <= set(r)
    assert r["bp"] == bp and r["victim_type"] == vt
    assert isinstance(r["dc_excess"], float) and not math.isinf(r["dc_excess"])

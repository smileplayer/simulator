"""Đánh giá luật báo động của trần động (`defenses.tran_dong.TranDong`) như một bộ phát hiện tường, chỉ từ log.

Luật: cuối mỗi bước, L của tick chứa giá > m × trung vị L của N bước bình thường gần nhất → báo động. Module này
phát lại đúng luật đó trên dòng `step` của log không biện pháp (nên không đổi hành vi tác nhân) và đo: có báo trước
khi tường rút không, báo sớm hơn lần rút và lần nạn nhân vào bao nhiêu giờ, có báo nhầm trước khi có tường không.
`ne_tu_tu` tính số giờ kẻ tấn công cần để dựng tường từng nấc mà không chạm ngưỡng (cách né).
"""
from __future__ import annotations

import math
import statistics

import pandas as pd

from defenses.tran_dong import TranDong


def chuoi_L(df: pd.DataFrame) -> pd.Series:
    """Thanh khoản hoạt động cuối mỗi bước (đơn vị L), chỉ số = bước, lấy từ dòng `step`."""
    s = df[df["kind"] == "step"].sort_values(["t", "seq"]).groupby("t").last()
    return s["liquidity_active_after"].astype(float)


def cac_buoc_bao(L: pd.Series, m: float = 3.0, N: int = 24) -> list[int]:
    """Các bước có tín hiệu khi phát lại luật trần động (bội số `m`, đường nền `N` bước) trên chuỗi `L`."""
    td = TranDong(Q=1.0, m=m, N=N)
    return [int(t) for t, x in L.items() if td.quan_sat(int(t), float(x))]


def danh_gia(df: pd.DataFrame, m: float = 3.0, N: int = 24) -> dict:
    """Một dòng đánh giá cho một log: mốc (bước), độ sớm (giờ), số lần báo nhầm trước tường, tỷ số tín hiệu.

    `som_hon_rut` = t_rut − bước báo đầu (từ lúc có tường); `som_hon_victim` = bước nạn nhân mint đầu − bước báo đầu
    (NaN nếu không có nạn nhân); `bao_nham` = số bước báo trước t_m trên `gio_nen` = t_m − N bước xét được;
    `ty_so` = L cuối bước t_m / trung vị L của N bước trước đó.
    """
    meta = df.attrs["meta"]
    t_m, t_rut = int(meta["t_m"]), meta.get("t_rut")
    L = chuoi_L(df)
    bao = cac_buoc_bao(L, m, N)
    sau = [t for t in bao if t >= t_m]
    t_bao = sau[0] if sau else None
    vm = df[(df["kind"] == "mint") & (df["role"] == "victim")]["t"]
    t_victim = int(vm.min()) if len(vm) else None
    nen = statistics.median(L.loc[max(0, t_m - N):t_m - 1])
    co_rut = t_rut is not None
    bat = t_bao is not None and (not co_rut or t_bao < int(t_rut))
    return dict(
        t_m=t_m, t_rut=t_rut, t_bao=t_bao, t_victim=t_victim, bat_truoc_rut=bool(bat),
        som_hon_rut=float(int(t_rut) - t_bao) if bat and co_rut else math.nan,
        som_hon_victim=float(t_victim - t_bao) if bat and t_victim is not None else math.nan,
        bao_nham=sum(t < t_m for t in bao), gio_nen=max(0, t_m - N),
        ty_so=float(L.loc[t_m]) / nen if nen > 0 else math.inf,
    )


def ne_tu_tu(ty_so: float, m: float = 3.0, N: int = 24, an_toan: float = 0.999) -> int:
    """Số bước ít nhất để nâng L của tick từ nền lên `ty_so` lần nền mà luật (m, N) không báo lần nào.

    Kẻ tấn công mỗi bước đặt L = an_toan·m·trung vị đường nền hiện tại (không vượt đích); đường nền tự cập nhật vì
    không có báo động. Hàm phát lại bằng chính `TranDong` nên kết quả đúng theo luật đang cài.
    """
    if ty_so <= 1:
        return 0
    td = TranDong(Q=1.0, m=m, N=N)
    for t in range(N):
        td.quan_sat(t, 1.0)
    t, L = N, 1.0
    while L < ty_so:
        L = min(ty_so, an_toan * m * statistics.median(td._nen))
        if td.quan_sat(t, L):
            raise RuntimeError("đường dựng từng nấc chạm ngưỡng")
        t += 1
        if t > N + 100_000:
            raise RuntimeError("không hội tụ")
    return t - N

"""Kẻ tấn công: dựng tường w tick quanh giá, chờ nạn nhân vào, rút toàn bộ tường rồi xả token0 tới z₂.

Lemma 5 bài gốc: z₂ = max{z_floor, z_Ā, z̄} — dừng khi hết thanh khoản (engine tự dừng), hết kho token0,
hoặc khi giá bán biên P·(1−f) chạm giá vốn c_A, tức z̄ = √(c_A/(1−f)).
Phải rút tường TRƯỚC khi xả, nếu không một phần lượng bán đi vào chính vị thế của kẻ tấn công.
"""
from __future__ import annotations

import math
from typing import Any

from agents.base import Market, khoang_quanh_gia


class Attacker:
    """Tường dựng theo lịch `dung_tuong`, rút ở `t_0` cố định hoặc khi L nạn nhân đạt `nguong_victim·L_A`."""

    def __init__(self, owner: str, L_A: float, t_m: int, kho_token0: float, c_A: float,
                 w: int = 1, dung_tuong: list[tuple[int, float]] | None = None,
                 t_0: int | None = None, nguong_victim: float | None = None, so_buoc_xa: int = 1):
        """`L_A`: tổng L của tường; `t_m`: bước dựng tường đầu tiên; `kho_token0`: lượng token0 sẵn để xả;
        `c_A`: giá vốn token0 (token1/token0); `w`: độ rộng tường (tick, làm tròn lên bội số tick_spacing);
        `dung_tuong`: [(bước, tỷ lệ của L_A)], mặc định dựng hết ở t_m;
        `t_0`: bước rút cố định; `nguong_victim`: rút khi L nạn nhân trong tick ≥ nguong_victim·L_A
        (phải cho ít nhất một trong hai); `so_buoc_xa`: chia kho xả đều qua bấy nhiêu bước."""
        if t_0 is None and nguong_victim is None:
            raise ValueError("cần t_0 hoặc nguong_victim")
        self.owner = owner
        self.L_A, self.w, self.c_A = L_A, w, c_A
        self.kho = kho_token0
        self.lich = dung_tuong if dung_tuong is not None else [(t_m, 1.0)]
        self.t_0, self.nguong_victim = t_0, nguong_victim
        self.so_buoc_xa = so_buoc_xa
        self.tick_lower: int | None = None
        self.tick_upper: int | None = None
        self.tuong: list[int] = []
        self.t_rut: int | None = None          # bước đã rút (t_0 thực tế)
        self._luot_xa = 0

    def z_dung(self, pool: Any) -> float:
        """z̄ = √(c_A/(1−f)): giá bán biên sau phí bằng giá vốn."""
        return math.sqrt(self.c_A / (1 - pool.fee)) if self.c_A > 0 else 0.0

    def dang_xa(self, t: int) -> bool:
        """True nếu bước t thuộc pha xả (bộ chạy dùng để tắt arb)."""
        return self.t_rut is not None and self.t_rut <= t < self.t_rut + self.so_buoc_xa

    def _L_victim(self, pool: Any) -> float:
        # vị thế nạn nhân phủ tick tường (GĐ3: dải rộng căn giữa; w = 1 thì đúng tick tường như trước)
        return sum(p.liquidity for p in pool.positions()
                   if p.owner.startswith("victim:") and p.tick_lower <= self.tick_lower < p.tick_upper)

    def _den_luc_rut(self, t: int, pool: Any) -> bool:
        if self.t_0 is not None and t >= self.t_0:
            return True
        return (self.nguong_victim is not None and self.tuong
                and self._L_victim(pool) >= self.nguong_victim * self.L_A)

    def act(self, t: int, pool: Any, market: Market) -> None:
        """Dựng tường theo lịch; tới lúc rút thì burn + collect toàn bộ tường rồi bắt đầu xả."""
        if self.t_rut is None:
            for t_dung, ty_le in self.lich:
                if t == t_dung:
                    if self.tick_lower is None:          # tick chứa giá, căn theo tick_spacing
                        self.tick_lower, self.tick_upper = khoang_quanh_gia(pool, self.w)
                    pid, _, _ = pool.mint(self.owner, self.tick_lower, self.tick_upper, ty_le * self.L_A)
                    self.tuong.append(pid)
            if self.tuong and self._den_luc_rut(t, pool):
                for pid in self.tuong:
                    pool.burn(pid)
                    pool.collect(pid)
                self.t_rut = t
        if self.dang_xa(t) and self.kho > 0:
            con_lai = self.so_buoc_xa - self._luot_xa
            luong = self.kho / con_lai
            self._luot_xa += 1
            z_dung = self.z_dung(pool)
            if pool.sqrt_price <= z_dung:
                return
            r = pool.swap(self.owner, zero_for_one=True, amount_in=luong,
                          sqrt_price_limit=z_dung if z_dung > 0 else None)
            self.kho -= r.amount_in

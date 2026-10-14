"""LP nạn nhân. Loại toàn tri chơi đúng Lemma 4 bài gốc: L_V* = max{0, √(f·V·L_A/c_V) − L_A}.

Lợi nhuận một cửa sổ: Π_V(L_V) = f·V·L_V/(L_A + L_V) − c_V·L_V, với V = khối lượng (token1) mỗi cửa sổ
đi qua tick, c_V = chi phí hiệu dụng (token1) cho mỗi đơn vị L mỗi cửa sổ — đã gồm vốn, IL, rủi ro sập.
"""
from __future__ import annotations

import math
from typing import Any

from agents.base import Market


def l_v_sao(f: float, V: float, L_A: float, c_V: float) -> float:
    """Lemma 4: thanh khoản tối ưu của nạn nhân (đơn vị L) khi đã có L_A thanh khoản khác trong tick."""
    if L_A <= 0:
        return 0.0                       # mô hình không xác định khi tick trống; nạn nhân không vào
    return max(0.0, math.sqrt(f * V * L_A / c_V) - L_A)


class VictimToanTri:
    """Biết V (khối lượng được trợ cấp mỗi cửa sổ); mỗi bước chỉnh L trong tick về L_V* nếu lệch > nguong."""

    def __init__(self, owner: str, V: float, c_V: float, w: int = 1, t_vao: int = 0,
                 nguong: float = 0.01):
        """`V`: token1 mỗi cửa sổ; `c_V`: token1 mỗi đơn vị L mỗi cửa sổ; `w`: độ rộng (tick);
        `t_vao`: bước sớm nhất được vào; `nguong`: lệch tương đối tối thiểu để chỉnh vị thế."""
        self.owner = owner
        self.V, self.c_V, self.w = V, c_V, w
        self.t_vao, self.nguong = t_vao, nguong
        self.tick_lower: int | None = None
        self.vi_the: list[int] = []      # position_id, mint sau nằm cuối

    def L_hien_tai(self, pool: Any) -> float:
        """Tổng L nạn nhân đang giữ."""
        return sum(p.liquidity for p in pool.positions(self.owner) if p.id in self.vi_the)

    def act(self, t: int, pool: Any, market: Market) -> None:
        """Vào tick chứa giá hiện tại; chỉ chỉnh khi giá còn trong khoảng của mình (ra ngoài thì giữ nguyên)."""
        if t < self.t_vao:
            return
        if self.tick_lower is None:
            self.tick_lower = pool.tick
        if not self.tick_lower <= pool.tick < self.tick_lower + self.w:
            return
        L_minh = self.L_hien_tai(pool)
        L_khac = pool.liquidity - L_minh
        muc_tieu = l_v_sao(pool.fee, self.V, L_khac, self.c_V)
        if muc_tieu > L_minh * (1 + self.nguong) and muc_tieu - L_minh > 0:
            pid, _, _ = pool.mint(self.owner, self.tick_lower, self.tick_lower + self.w, muc_tieu - L_minh)
            self.vi_the.append(pid)
        elif muc_tieu < L_minh * (1 - self.nguong):
            can_rut = L_minh - muc_tieu
            for pid in reversed(list(self.vi_the)):
                if can_rut <= 0:
                    break
                L_p = next(p.liquidity for p in pool.positions(self.owner) if p.id == pid)
                rut = min(L_p, can_rut)
                pool.burn(pid, None if rut >= L_p else rut)
                can_rut -= rut
                if rut >= L_p:
                    self.vi_the.remove(pid)

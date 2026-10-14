"""Giao thức chung cho tác nhân và thị trường ngoài (INTERFACE mục 3)."""
from __future__ import annotations

from typing import Any, Protocol


class Market(Protocol):
    def external_price(self, t: int) -> float:
        """Giá ngoài sàn P_e(t), token1 trên mỗi token0, tại bước t."""
        ...


class Agent(Protocol):
    owner: str

    def act(self, t: int, pool: Any, market: Market) -> None:
        """Hành động trong bước t: gọi mint/burn/collect/swap trên pool (engine ghi log)."""
        ...


class ThiTruongCoDinh:
    """Thị trường ngoài có giá P_e không đổi (token1/token0) — dùng cho test và kịch bản đơn giản."""

    def __init__(self, gia: float):
        self.gia = gia

    def external_price(self, t: int) -> float:
        """Trả giá P_e cố định, token1/token0."""
        return self.gia


def role(owner: str) -> str:
    """Vai của chủ sở hữu: phần trước dấu ':' (ví dụ 'farmer:3' → 'farmer')."""
    return owner.split(":", 1)[0]

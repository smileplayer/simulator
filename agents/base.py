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


def tick_chua_gia(pool: Any) -> int:
    """Tick (đơn vị tick) chứa giá theo nghĩa [P(i), P(i+1)): như `pool.tick`, trừ khi giá nằm đúng biên trên
    `P(pool.tick + 1)` (quy ước v3 sau khi đi xuống chạm biên) thì trả `pool.tick + 1`."""
    from engine import sqrt_price_at_tick
    if pool.sqrt_price >= sqrt_price_at_tick(pool.tick + 1):
        return pool.tick + 1
    return pool.tick


def khoang_quanh_gia(pool: Any, w: int, vi_tri: str = "tren") -> tuple[int, int]:
    """Khoảng [tick_lower, tick_upper) căn theo `pool.tick_spacing`, chứa giá hiện tại (xem `tick_chua_gia`);
    độ rộng = w tick làm tròn lên bội số của tick_spacing (spacing 1 → đúng w).

    `vi_tri` (GĐ3): "tren" = tick chứa giá là tick dưới cùng, dải đi lên (mặc định GĐ1/2); "giua" = dải căn giữa,
    lùi ⌊n/2⌋ ô spacing xuống (n = số ô); "duoi" = tick chứa giá là tick trên cùng, dải đi xuống. w = 1: cả ba như nhau."""
    s = getattr(pool, "tick_spacing", 1)
    tl = tick_chua_gia(pool)
    tl -= tl % s
    n = -(-w // s)
    lui = {"tren": 0, "giua": n // 2, "duoi": n - 1}[vi_tri] * s
    return tl - lui, tl - lui + n * s

"""Log sự kiện đúng định dạng INTERFACE mục 4. Engine ghi mint/burn/collect/swap;
bộ chạy kịch bản (vai C) ghi thêm dòng `subsidy`, `step` bằng `append`.
"""
from __future__ import annotations

import math

import pandas as pd

COLUMNS = [
    "t", "seq", "kind", "owner", "role", "position_id", "tick_lower", "tick_upper", "liquidity",
    "amount0", "amount1", "fee0", "fee1", "sqrt_price_after", "tick_after",
    "liquidity_active_after", "external_price",
]
KINDS = {"mint", "burn", "collect", "swap", "subsidy", "step"}


class EventLog:
    """Danh sách dòng sự kiện; `seq` tự tăng trong cùng bước `t`, đặt lại khi sang bước mới."""

    def __init__(self) -> None:
        self.rows: list[dict] = []
        self._t: int | None = None
        self._seq = 0

    def append(self, t: int, kind: str, owner: str, **fields) -> dict:
        """Thêm một dòng. Cột không truyền: NaN, riêng amount*/fee* mặc định 0."""
        if kind not in KINDS:
            raise ValueError(f"kind không hợp lệ: {kind}")
        if t != self._t:
            self._t, self._seq = t, 0
        unknown = set(fields) - set(COLUMNS)
        if unknown:
            raise ValueError(f"cột lạ: {sorted(unknown)}")
        row = dict.fromkeys(COLUMNS, math.nan)
        row.update(amount0=0.0, amount1=0.0, fee0=0.0, fee1=0.0)
        row.update(fields)
        row.update(t=t, seq=self._seq, kind=kind, owner=owner, role=owner.split(":")[0])
        self._seq += 1
        self.rows.append(row)
        return row

    def __len__(self) -> int:
        return len(self.rows)

    def to_frame(self) -> pd.DataFrame:
        """DataFrame với đúng thứ tự cột của INTERFACE mục 4."""
        return pd.DataFrame(self.rows, columns=COLUMNS)

    def to_csv(self, path) -> None:
        """Ghi log ra CSV."""
        self.to_frame().to_csv(path, index=False)

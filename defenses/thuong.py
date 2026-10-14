"""Biện pháp trên luật trợ cấp (GĐ2): hạ trần Q (§7.1 bài gốc) và trả thưởng trễ (§7.2).

Config: `defense = null` | `{"name": "cap", "ty_le": r}` (Q_eff = r·Q) hoặc `{"name": "cap", "Q_cap": x}`
| `{"name": "delay", "D": số bước, "don_vi": "token1" | "token0", "chiet_khau": δ mỗi bước,
"clawback": ngưỡng sập (tùy chọn, ví dụ 0.10)}`.

Giả định của trả trễ (cần nêu khi báo cáo): thưởng chốt cuối mỗi cửa sổ, trả sau D bước. Farmer quy về hiện tại
bằng δ^D (thiếu kiên nhẫn / rủi ro nền tảng) và không dự báo giá. Với `don_vi = "token0"`, thưởng đổi ra token0
theo giá lúc chốt, nên chi phí thật của nền tảng (token1) = lượng token0 × giá lúc trả: giá sập trước hạn thì
nền tảng trả ít đi, farmer nhận ít đi. Thưởng chưa tới hạn khi kịch bản kết thúc không tính vào chi phí.

Thu hồi (`clawback`, biến thể (a) của CH-6): khoản còn treo bị hủy nếu giá bể sập ≥ ngưỡng so với giá lúc chốt,
**chỉ** với owner từng có vị thế LP trong bể khi khoản đó còn treo (nền tảng thấy được ví farmer cũng là LP) —
farmer thuần không bị phạt.
"""
from __future__ import annotations

from collections import deque

TEN_HOP_LE = {None, "cap", "delay"}


def ten_bien_phap(defense: dict | None) -> str | None:
    """Tên biện pháp; báo lỗi nếu chưa cài."""
    ten = defense.get("name") if defense else None
    if ten not in TEN_HOP_LE:
        raise NotImplementedError(f"biện pháp chưa cài: {ten}")
    return ten


def Q_hieu_luc(Q: float, defense: dict | None) -> float:
    """Trần trợ cấp sau biện pháp (token1 mỗi cửa sổ): cap → min(Q, Q_cap) hoặc ty_le·Q; khác → Q."""
    if ten_bien_phap(defense) != "cap":
        return Q
    if "Q_cap" in defense:
        return min(Q, float(defense["Q_cap"]))
    return float(defense["ty_le"]) * Q


class LichTraThuong:
    """Hàng đợi trả thưởng: chốt ở cuối cửa sổ, tới hạn sau D bước. D = 0 → trả ngay bằng token1 (mặc định)."""

    def __init__(self, D: int = 0, don_vi: str = "token1", chiet_khau: float = 1.0,
                 clawback: float | None = None):
        if don_vi not in ("token1", "token0"):
            raise ValueError("don_vi phải là token1 hoặc token0")
        self.D, self.don_vi, self.chiet_khau = int(D), don_vi, float(chiet_khau)
        self.clawback = clawback
        self.da_thu_hoi = 0.0                                 # token1, theo giá lúc hủy
        # mỗi khoản: [bước tới hạn, owner, lượng theo don_vi, giá lúc chốt, owner đã từng là LP khi còn treo]
        self._hang: deque[list] = deque()

    @classmethod
    def tu_defense(cls, defense: dict | None) -> "LichTraThuong":
        """Dựng lịch từ config biện pháp; không phải delay → trả ngay."""
        if ten_bien_phap(defense) != "delay":
            return cls()
        return cls(defense["D"], defense.get("don_vi", "token1"), defense.get("chiet_khau", 1.0),
                   defense.get("clawback"))

    @property
    def he_so_cam_nhan(self) -> float:
        """Farmer nhân thưởng với δ^D khi quyết định khối lượng."""
        return self.chiet_khau ** self.D

    def chot(self, t: int, owner: str, thuong_token1: float, gia: float) -> None:
        """Chốt thưởng (token1) ở bước t, giá P = gia (token1/token0)."""
        luong = thuong_token1 / gia if self.don_vi == "token0" else thuong_token1
        self._hang.append([t + self.D, owner, luong, gia, False])

    def thu_hoi(self, gia: float, chu_lp: set[str]) -> list[tuple[str, float]]:
        """Gọi mỗi bước sau `chot`, trước `den_han`: đánh dấu khoản của owner đang là LP (`chu_lp`), hủy khoản
        đã đánh dấu khi giá P = gia ≤ (1 − clawback)·giá lúc chốt. Trả [(owner, giá trị token1 bị hủy)]."""
        if self.clawback is None:
            return []
        huy, giu = [], deque()
        for k in self._hang:
            k[4] = k[4] or k[1] in chu_lp
            if k[4] and gia <= (1 - self.clawback) * k[3]:
                huy.append((k[1], k[2] * gia if self.don_vi == "token0" else k[2]))
            else:
                giu.append(k)
        self._hang = giu
        self.da_thu_hoi += sum(v for _, v in huy)
        return huy

    def den_han(self, t: int, gia: float) -> list[tuple[str, float]]:
        """Lấy các khoản tới hạn ở bước t, trả [(owner, giá trị token1 lúc trả)]."""
        ra = []
        while self._hang and self._hang[0][0] <= t:
            _, owner, luong, _, _ = self._hang.popleft()
            ra.append((owner, luong * gia if self.don_vi == "token0" else luong))
        return ra

    def con_treo(self, gia: float, owner: str | None = None) -> float:
        """Tổng giá trị (token1, theo giá hiện tại) các khoản chưa tới hạn; `owner` khác None → chỉ của owner đó."""
        return sum(k[2] * gia if self.don_vi == "token0" else k[2] for k in self._hang
                   if owner is None or k[1] == owner)

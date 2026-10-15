"""Biện pháp §7.3 (cảnh báo rủi ro) và §7.4 (trần động) của bài gốc.

Config:
- `{"name": "warn", "he_so": h}` — nền tảng công bố rủi ro khi LP mint dải hẹp → chi phí hiệu dụng của victim
  tăng `c_V → h·c_V` (Lemma 4: L_V* = √(fV·L_A/c_V) − L_A giảm). Chỉ đụng victim; farmer, kẻ tấn công giữ nguyên.
- `{"name": "dyncap", "ty_le": r, "m": m, "N": N, "H": H}` (hoặc `"Q_dyn"` thay `ty_le`) — trần động: cuối mỗi
  bước, nền tảng đọc thanh khoản L của tick chứa giá; nếu L > m × trung vị L của N bước "bình thường" gần nhất
  (bước không trong báo động) thì báo động. Trong H bước sau lần báo gần nhất, trần mỗi cửa sổ là Q_dyn = r·Q
  (thay vì Q). Đường nền đóng băng trong lúc báo động, nên tường còn đứng thì tín hiệu còn, báo động kéo dài tới
  H bước sau khi tường (hoặc khối thanh khoản lạ) biến mất. Tín hiệu bắt chước cách bài gốc dò tường (thanh khoản
  ròng của tick tăng bất thường, ngưỡng kiểu 3σ), nhưng theo bước giờ thay vì theo ngày.

Giả định của trần động (nêu khi báo cáo): luật được công bố, farmer và victim toàn tri thấy trần hiện hành
ngay (farmer tối ưu theo trần hiện hành; victim toàn tri dùng V = số tài khoản × trần hiện hành); thưởng mỗi
cửa sổ tính theo trần tại lúc chốt (cuối cửa sổ). Victim thích nghi tự thấy qua phí.
"""
from __future__ import annotations

import statistics
from collections import deque


def c_V_hieu_luc(c_V: float, defense: dict | None) -> float:
    """Chi phí hiệu dụng của victim (token1 mỗi đơn vị L mỗi cửa sổ) sau cảnh báo rủi ro: warn → he_so·c_V."""
    if defense and defense.get("name") == "warn":
        return float(defense["he_so"]) * c_V
    return c_V


class TranDong:
    """Trần trợ cấp động: báo động khi L tick chứa giá > m × trung vị N bước bình thường; trần Q_dyn trong H bước."""

    def __init__(self, Q: float, ty_le: float = 0.25, m: float = 3.0, N: int = 24, H: int = 24,
                 Q_dyn: float | None = None):
        """`Q`: trần gốc (token1 mỗi cửa sổ); `ty_le`: Q_dyn = ty_le·Q (bỏ qua nếu cho `Q_dyn`);
        `m`: bội số ngưỡng; `N`: số bước đường nền; `H`: số bước giữ trần thấp sau lần báo cuối."""
        if m <= 1 or N < 1 or H < 1:
            raise ValueError("cần m > 1, N ≥ 1, H ≥ 1")
        self.Q = float(Q)
        self.Q_dyn = float(Q_dyn) if Q_dyn is not None else float(ty_le) * self.Q
        self.m, self.N, self.H = float(m), int(N), int(H)
        self._nen: deque[float] = deque(maxlen=self.N)   # L của các bước không báo động
        self.t_bao: int | None = None                    # bước gần nhất có tín hiệu
        self.t_bao_dau: int | None = None                # bước có tín hiệu đầu tiên
        self.so_buoc_bat = 0                             # số bước trần thấp đã áp

    @classmethod
    def tu_defense(cls, defense: dict | None, Q: float) -> "TranDong | None":
        """Dựng từ config biện pháp; không phải dyncap → None."""
        if not defense or defense.get("name") != "dyncap":
            return None
        return cls(Q, defense.get("ty_le", 0.25), defense.get("m", 3.0), defense.get("N", 24),
                   defense.get("H", 24), defense.get("Q_dyn"))

    def dang_bat(self, t: int) -> bool:
        """True nếu bước t nằm trong báo động: t_bao < t ≤ t_bao + H (trần thấp áp từ bước sau tín hiệu)."""
        return self.t_bao is not None and 0 < t - self.t_bao <= self.H

    def Q_hien_tai(self, t: int) -> float:
        """Trần áp ở bước t (token1 mỗi cửa sổ); gọi một lần mỗi bước, đầu bước."""
        if self.dang_bat(t):
            self.so_buoc_bat += 1
            return self.Q_dyn
        return self.Q

    def quan_sat(self, t: int, L: float) -> bool:
        """Cuối bước t: L = thanh khoản tick chứa giá (đơn vị L). Trả True nếu có tín hiệu dựng tường."""
        tin_hieu = len(self._nen) == self.N and L > 0 and L > self.m * statistics.median(self._nen)
        if tin_hieu:
            self.t_bao = t
            if self.t_bao_dau is None:
                self.t_bao_dau = t
        elif not self.dang_bat(t):
            self._nen.append(L)
        return tin_hieu

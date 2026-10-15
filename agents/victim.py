"""LP nạn nhân. Loại toàn tri chơi đúng Lemma 4 bài gốc: L_V* = max{0, √(f·V·L_A/c_V) − L_A}.

Lợi nhuận một cửa sổ: Π_V(L_V) = f·V·L_V/(L_A + L_V) − c_V·L_V, với V = khối lượng (token1) mỗi cửa sổ
đi qua tick, c_V = chi phí hiệu dụng (token1) cho mỗi đơn vị L mỗi cửa sổ — đã gồm vốn, IL, rủi ro sập.
"""
from __future__ import annotations

import math
from collections import deque
from typing import Any

from agents.base import Market, khoang_quanh_gia, tick_chua_gia


def l_v_sao(f: float, V: float, L_A: float, c_V: float) -> float:
    """Lemma 4: thanh khoản tối ưu của nạn nhân (đơn vị L) khi đã có L_A thanh khoản khác trong tick."""
    if L_A <= 0:
        return 0.0                       # mô hình không xác định khi tick trống; nạn nhân không vào
    return max(0.0, math.sqrt(f * V * L_A / c_V) - L_A)


class VictimToanTri:
    """Biết V (khối lượng được trợ cấp mỗi cửa sổ); mỗi bước chỉnh L trong tick về L_V* nếu lệch > nguong.

    Trong bộ chạy, V = (n_farmers + m)·Q_eff gồm cả khối lượng farm của kẻ tấn công (m tài khoản ảo, CH-6): phí
    từ khối lượng đó là thật (cơ chế pressure trader của bài gốc), nên `attacker_farm_share` lớn kéo victim vào
    nhiều hơn — đúng ý đồ, không phải lỗi.

    Giả định của bài gốc mà loại này dựa vào (giữ nguyên để kiểm lý thuyết): **Giả định 1 (cap-binding)** — mọi
    farmer giao dịch tới trần nên V = số tài khoản × Q_eff; **Giả định 2 (tick feasibility)** — Q ≤ L_A(z_U − z₀)/(1−f),
    mọi khối lượng được trợ cấp nằm trong một tick. Khi trần không ràng buộc (σ thấp: farmer dừng trước Q) hoặc Q lớn
    so với L_A (khối lượng tràn ra ngoài tick), V thật < V giả định → victim toàn tri định giá sai (vào quá nhiều);
    kết quả ở các ô đó thuộc vùng "ngoài giả định", không dùng để kiểm Lemma 4/Theorem 6."""

    def __init__(self, owner: str, V: float, c_V: float, w: int = 1, t_vao: int = 0,
                 nguong: float = 0.01):
        """`V`: token1 mỗi cửa sổ; `c_V`: token1 mỗi đơn vị L mỗi cửa sổ; `w`: độ rộng (tick);
        `t_vao`: bước sớm nhất được vào; `nguong`: lệch tương đối tối thiểu để chỉnh vị thế."""
        self.owner = owner
        self.V, self.c_V, self.w = V, c_V, w
        self.t_vao, self.nguong = t_vao, nguong
        self.tick_lower: int | None = None
        self.tick_upper: int | None = None
        self.vi_the: list[int] = []      # position_id, mint sau nằm cuối

    def L_hien_tai(self, pool: Any) -> float:
        """Tổng L nạn nhân đang giữ."""
        return sum(p.liquidity for p in pool.positions(self.owner) if p.id in self.vi_the)

    def uoc_V(self, t: int, pool: Any) -> float | None:
        """Khối lượng mỗi cửa sổ (token1) nạn nhân tin là có; None = chưa đủ thông tin để quyết."""
        return self.V

    def quan_sat(self, t: int, pool: Any) -> None:
        """Gọi đầu mỗi bước, kể cả trước t_vao (loại thích nghi dùng để ghi lịch sử)."""

    def act(self, t: int, pool: Any, market: Market) -> None:
        """Vào tick chứa giá hiện tại; chỉ chỉnh khi giá còn trong khoảng của mình (ra ngoài thì giữ nguyên)."""
        self.quan_sat(t, pool)
        if t < self.t_vao:
            return
        V = self.uoc_V(t, pool)
        if V is None:
            return
        if self.tick_lower is None:                      # tick chứa giá, căn theo tick_spacing
            self.tick_lower, self.tick_upper = khoang_quanh_gia(pool, self.w)
        tick = tick_chua_gia(pool)
        if not self.tick_lower <= tick < self.tick_upper:
            return
        L_minh = self.L_hien_tai(pool)
        # giá ở đúng biên trên của pool.tick: L hoạt động của bể là của tick dưới → đọc L của tick chứa giá
        L_khac = (pool.liquidity if tick == pool.tick else pool.liquidity_at(tick)) - L_minh
        muc_tieu = l_v_sao(pool.fee, V, L_khac, self.c_V)
        if muc_tieu > L_minh * (1 + self.nguong) and muc_tieu - L_minh > 0:
            pid, _, _ = pool.mint(self.owner, self.tick_lower, self.tick_upper, muc_tieu - L_minh)
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


class VictimThichNghi(VictimToanTri):
    """Không biết V hay Q: ước V từ phí cả bể trong H bước gần nhất (dữ liệu on-chain công khai), rồi tối ưu
    như Lemma 4. Không phân biệt khối lượng được trợ cấp với khối lượng nền/arb, và phản ứng trễ H bước."""

    def __init__(self, owner: str, c_V: float, window: int = 24, H: int = 24, w: int = 1, t_vao: int = 0,
                 nguong: float = 0.10):
        """`window`: số bước một cửa sổ (đơn vị của V và c_V); `H`: số bước lịch sử dùng để ước V;
        `nguong` mặc định 10% (V̂ nhiễu theo từng bước, ngưỡng 1% làm vị thế bị chỉnh liên tục)."""
        super().__init__(owner, V=float("nan"), c_V=c_V, w=w, t_vao=t_vao, nguong=nguong)
        self.window, self.H = window, H
        self._doc_den = 0                                # chỉ số dòng log đã đọc
        self._phi_buoc: deque[tuple[int, float]] = deque()   # (bước, phí token1 cả bể trong bước đó)
        self.V_uoc: float | None = None

    def quan_sat(self, t: int, pool: Any) -> None:
        """Đọc các dòng swap mới của các bước đã xong (< t), cộng phí quy ra token1 theo giá sau swap."""
        rows = pool.log.rows
        while self._doc_den < len(rows) and rows[self._doc_den]["t"] < t:
            r = rows[self._doc_den]
            self._doc_den += 1
            if r["kind"] != "swap":
                continue
            phi = r["fee1"] + r["fee0"] * r["sqrt_price_after"] ** 2
            if self._phi_buoc and self._phi_buoc[-1][0] == r["t"]:
                self._phi_buoc[-1] = (r["t"], self._phi_buoc[-1][1] + phi)
            else:
                self._phi_buoc.append((r["t"], phi))
        while self._phi_buoc and self._phi_buoc[0][0] < t - self.H:
            self._phi_buoc.popleft()

    def uoc_V(self, t: int, pool: Any) -> float | None:
        """V̂ = (phí H bước gần nhất / f) × window/H (token1 mỗi cửa sổ); None khi lịch sử chưa đủ H bước."""
        if t < self.H or pool.fee <= 0:
            return None
        tong = sum(phi for _, phi in self._phi_buoc)
        self.V_uoc = tong / pool.fee * self.window / self.H
        return self.V_uoc

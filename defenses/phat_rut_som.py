"""Cải tiến G (22/10/2026): phạt phí khi rút thanh khoản sớm, phần phạt chia cho LP đang trong dải.

Theo OpenZeppelin `LiquidityPenaltyHook` (uniswap-hooks v1.3.0, MIT, `src/general/LiquidityPenaltyHook.sol`
dòng 137–171, 242–268): rút vị thế khi mới giữ `giu` < `cua_so` thì mất (1 − giu/cua_so) phí đang treo, phần
đó `donate` cho thanh khoản đang hoạt động sau khi rút. Ý tưởng phí hai tầng theo thời gian giữ: Capponi–Jia–Zhu
(preprint, arXiv 2311.18164). Đồ án chỉ đánh giá nó trước tấn công do khuyến khích; không nhận là phát minh.

Config: `{"name": "phat", "cua_so": số bước}`. Cơ chế nằm trong engine (`Pool(phat_rut_som=...)`) vì phải chạy
ở mọi lần burn của mọi tác nhân. Khác hook OZ: thời gian giữ đo từ lần mint của từng vị thế (engine không có
"thêm thanh khoản vào vị thế cũ"), đơn vị là bước (giờ) thay vì block; không ai trong dải thì phần phạt mất
thay vì revert.
"""
from __future__ import annotations


def cua_so_phat(defense: dict | None) -> int | None:
    """Cửa sổ phạt (bước) nếu biện pháp là `phat`, không thì None."""
    if not defense or defense.get("name") != "phat":
        return None
    return int(defense["cua_so"])

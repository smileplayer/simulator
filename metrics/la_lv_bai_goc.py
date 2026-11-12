"""L_A, L_V thật của từng vụ từ bộ mã của bài gốc (Zenodo 20440752, `submission.zip`), và k suy ra từ Bổ đề 4.

    python -m metrics.la_lv_bai_goc --vao <thư mục submission đã giải nén>

Đọc `Part2/2-metrics/3-Role_dimension/1_role_outputs/*.json` (chỉ đọc JSON, không chạy mã của bài gốc). Với mỗi vụ:
L_A = tổng `L_u_t0` của các địa chỉ bài gốc xếp là kẻ tấn công, L_V = tổng `L_u_t0` của nạn nhân tại t_b (đơn vị L thô,
lúc tường bắt đầu rút t_0). Bổ đề 4: L_V* = L_A(1/√k − 1) ⇒ k = 1/(1 + L_V/L_A)², cùng định nghĩa k = c_V·L_A/(f·V)
của `scenarios.batch.ap_k`. Ghi `ket_qua/that/LA_LV_bai_goc.csv`.
Giới hạn: vai trò theo định nghĩa của bài gốc (kẻ tấn công = người cấp tường có lãi); L đo tại t_0, khi kẻ tấn công có
thể đã rút bớt; σ, Q không có trong bộ mã.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

RA = Path(__file__).resolve().parents[1] / "ket_qua" / "that" / "LA_LV_bai_goc.csv"
LUOI_K = ((0.64, 0.95), (0.10, 0.45))   # vùng RQ1 và vùng k nhỏ GĐ2


def mot_vu(r: dict) -> dict:
    """Một dòng từ một file role_outputs: số kẻ tấn công/nạn nhân, L_A, L_V (L thô), tỷ phần trong bể, L_V/L_A, k suy ra."""
    A, V = r.get("attacker_details", []), r.get("victim_details_tb", [])
    LA = float(sum(a["L_u_t0"] for a in A))
    LV = float(sum(v["L_u_t0"] for v in V))
    Lp = float(r["pool_liquidity"]["L_pool_t0"] or 0)
    ty = LV / LA if LA > 0 else float("nan")
    return dict(pool=r["pool"], tick=int(r["tick_key"].split("_")[0]), n_attacker=len(A), n_victim=len(V),
                n_wall=len(r.get("wall_providers", [])), LA_t0=LA, LV_t0=LV, L_pool_t0=Lp,
                ty_phan_A=LA / Lp if Lp else float("nan"), ty_phan_V=LV / Lp if Lp else float("nan"),
                LV_chia_LA=ty, k_suy=1.0 / (1.0 + ty) ** 2 if ty == ty else float("nan"))


def chay(vao: Path, ra: Path = RA) -> pd.DataFrame:
    """Đọc mọi file role_outputs trong `vao`, ghi CSV `ra`, trả bảng."""
    tep = sorted((vao / "Part2" / "2-metrics" / "3-Role_dimension" / "1_role_outputs").glob("*.json"))
    if not tep:
        raise SystemExit(f"Không thấy role_outputs trong {vao}")
    d = pd.DataFrame([mot_vu(json.loads(t.read_text(encoding="utf-8"))) for t in tep])
    d["trong_luoi"] = d["k_suy"].apply(lambda k: any(a <= k <= b for a, b in LUOI_K))
    ra.parent.mkdir(parents=True, exist_ok=True)
    d.to_csv(ra, index=False, encoding="utf-8")
    return d


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--vao", required=True, help="thư mục submission đã giải nén")
    a = ap.parse_args()
    d = chay(Path(a.vao))
    co = d[(d.n_victim > 0) & (d.LA_t0 > 0)]
    print(f"{len(d)} vụ; có cả kẻ tấn công và nạn nhân: {len(co)}; k suy ra trung vị {co.k_suy.median():.3f} "
          f"(min {co.k_suy.min():.3f}, max {co.k_suy.max():.3f}); trong lưới k: {int(co.trong_luoi.sum())}")
    print(co[["pool", "tick", "n_attacker", "n_victim", "LV_chia_LA", "k_suy", "trong_luoi"]].round(3).to_string(index=False))

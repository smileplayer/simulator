"""Bảng kiểm độ bền RQ3 (victim tính rủi ro theo khoảng) bằng một lệnh: `python -m metrics.chay_ruiro [--vao ...] [--B 2000]`.

Đọc `ket_qua/gd3/tomtat_ruiro.csv` (`scenarios.quet_gd3 --rui_ro`), ghi `ket_qua/gd3/bang_ruiro/` (file vào `_nhanh` → `bang_ruiro_nhanh/`): `phi_theo_vu.csv`,
`phi_gop.csv` (φ so với pro-rata cùng λ), `lam_theo_vu.csv`, `lam_gop.csv` (λ so với λ = 0 ở pro-rata), `lua_chon.csv`
(tỷ lệ w ≥ 500 và vị trí victim chọn theo λ, φ, victim), `ket_luan.json` (R1/R2/R3, ngưỡng ghi trước khi chạy).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from metrics.gd3 import bang_ruiro, ket_luan_ruiro


def main(vao: str = "ket_qua/gd3/tomtat_ruiro.csv", B: int = 2000) -> dict:
    """Tính mọi bảng kiểm độ bền RQ3, ghi ra `bang_ruiro/` cạnh file vào, trả dict kết luận."""
    df = pd.read_csv(vao)
    ra = Path(vao).parent / ("bang_ruiro_nhanh" if Path(vao).stem.endswith("_nhanh") else "bang_ruiro")
    ra.mkdir(parents=True, exist_ok=True)
    bang = bang_ruiro(df, B=B)
    for ten, tep in (("phi", "phi_theo_vu"), ("phi_gop", "phi_gop"), ("lam", "lam_theo_vu"), ("lam_gop", "lam_gop")):
        bang[ten].to_csv(ra / f"{tep}.csv", index=False)
    chon = (df.assign(w_lon=df["w_victim"] >= 500)
            .groupby(["lam", "alpha", "w0", "victim_type"])
            .agg(n=("seed", "size"), ty_le_w_lon=("w_lon", "mean"), w_trung_vi=("w_victim", "median"),
                 vi_tri=("vi_tri_victim", lambda s: "/".join(sorted(set(s)))))
            .reset_index())
    chon.to_csv(ra / "lua_chon.csv", index=False)
    kl = ket_luan_ruiro(bang) | dict(n_luot=len(df))
    (ra / "ket_luan.json").write_text(json.dumps(kl, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"R1 = {kl['R1']}, R2 = {kl['R2']}, R3 = {kl['R3']} ({len(df)} lượt) → {ra}")
    return kl


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--vao", default="ket_qua/gd3/tomtat_ruiro.csv")
    ap.add_argument("--B", type=int, default=2000)
    a = ap.parse_args()
    main(a.vao, a.B)

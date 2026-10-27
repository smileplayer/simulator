# Simulator — tấn công thanh khoản do khuyến khích trong CLMM

Git repo của phần mã nguồn. Thiết kế: `../03_Ghi_chu_nghien_cuu/03_Ke_hoach_simulator.md`. Phân công: `../03_Ghi_chu_nghien_cuu/05_Phan_cong.md`. Luật làm việc cho Claude Code (vai, git, lệnh chạy lâu): mục "Simulator" trong `../CLAUDE.md`. Kết quả và mọi lỗi đã sửa: `TONG_KET_DU_AN.md`.

| File | Để làm gì |
|---|---|
| `INTERFACE.md` | Hợp đồng giữa engine, tác nhân và đo lường (chỉ vai C sửa) |
| `SYNC.md` | Tiến độ và yêu cầu qua lại giữa ba vai + Chỉ huy, nhật ký |
| `TONG_KET_DU_AN.md` | Tổng kết: dòng thời gian, lỗi đã sửa, kết quả RQ1–RQ3, việc tiếp theo |
| `.claude/commands/vai.md`, `chot.md` | Lệnh `/vai A|B|C` (nhận vai) và `/chot` (test, commit, cập nhật SYNC) |

```
engine/      A — Pool, Position, swap cross-tick, phí          tests/engine/
agents/      C — Farmer, Victim (toàn tri / thích nghi), Attacker
scenarios/   C — cấu hình, bộ chạy, log giả                    tests/agents/
defenses/    C — trần, trả trễ, cảnh báo, trần động, range-aware
metrics/     B — mốc/pha, 4 chỉ số, kiểm định RQ1               tests/metrics/
plots/       B — biểu đồ
ket_qua/     B — CSV, PNG sinh ra
```

Chạy test: `python -m pytest -q` (320 test, khoảng 1–2 phút). Đã kiểm trên pandas 2.2.3 và 3.0.6 (27/10).

Sinh lại số liệu và hình: `python -m metrics.chay_rq1`, `metrics.chay_gd2`, `metrics.chay_gd3`; `python -m plots.ve_rq1`, `ve_gd2`, `ve_gd3`. Quét: `python -m scenarios.batch --seeds 10` (RQ1), `scenarios.quet_gd2` (GĐ2), `scenarios.quet_gd3 [--w_A] [--w0 …]` (GĐ3). Trên PowerShell đặt `$env:PYTHONIOENCODING="utf-8"` trước để in được tiếng Việt.

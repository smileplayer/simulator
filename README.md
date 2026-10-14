# Simulator — tấn công thanh khoản do khuyến khích trong CLMM

Git repo của phần mã nguồn. Thiết kế: `tai_lieu_do_an/03_Ghi_chu_nghien_cuu/03_Ke_hoach_simulator.md`. Phân công: `tai_lieu_do_an/03_Ghi_chu_nghien_cuu/05_Phan_cong.md`.

| File | Để làm gì |
|---|---|
| `CLAUDE.md` | Luật cho 3 phiên Claude: vai nào sửa thư mục nào, git, quyết định đã chốt |
| `INTERFACE.md` | Hợp đồng giữa engine, tác nhân và đo lường (chỉ vai C sửa) |
| `SYNC.md` | Tiến độ và yêu cầu qua lại giữa ba vai |
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

Chạy test: `python -m pytest -q`

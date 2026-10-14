# Simulator — luật làm việc cho 3 vai

Thư mục này là **git repo của simulator**. Đức chạy **3 phiên Claude Code riêng**, mỗi phiên đóng một vai. Ba phiên dùng chung thư mục này (không dùng worktree) và đồng bộ qua file + git. Bối cảnh đồ án ở `../CLAUDE.md` (tự nạp); ghi chú nghiên cứu ở `../03_Ghi_chu_nghien_cuu/`.

## Bắt đầu phiên: gõ `/vai A`, `/vai B` hoặc `/vai C`. Trước khi dừng: gõ `/chot`.

Khi chưa biết mình là vai nào (chưa có lệnh `/vai`), **hỏi Đức trước khi sửa bất kỳ file nào**.

## Ba vai và quyền sửa

| Vai | Tên phiên | Được sửa | Chỉ đọc |
|---|---|---|---|
| **A — Engine** | `A-engine` | `engine/`, `tests/engine/` | mọi thứ còn lại |
| **B — Đo lường, kiểm định** | `B-metrics` | `metrics/`, `plots/`, `tests/metrics/`, `ket_qua/` | mọi thứ còn lại |
| **C — Tác nhân, thí nghiệm** | `C-agents` | `agents/`, `scenarios/`, `defenses/`, `tests/agents/`, **`INTERFACE.md`** | mọi thứ còn lại |
| Cả ba | — | **chỉ mục của vai mình** trong `SYNC.md` | — |

- Cần vai khác sửa gì → ghi vào mục "Cần từ vai khác" của **vai mình** trong `SYNC.md`. Không tự sửa thư mục của vai khác.
- `INTERFACE.md` là hợp đồng. Chỉ vai C sửa. A, B muốn đổi → ghi đề nghị vào `SYNC.md`. Khi C đổi interface, C ghi dòng "ĐỔI INTERFACE" vào nhật ký kèm mô tả.
- Trước khi sửa `SYNC.md`: đọc lại file (vai khác có thể vừa ghi), rồi chỉ thay đúng mục của mình bằng Edit — không ghi đè cả file.

## Git

- Commit sau **mỗi việc nhỏ** xong và test qua. Chỉ `git add` thư mục của vai mình + `SYNC.md` (+ `INTERFACE.md` nếu là C). **Không** `git add -A` / `git add .`.
- Thông điệp commit bắt đầu bằng `[A]`, `[B]` hoặc `[C]`, viết tiếng Việt, ngắn.
- Gặp lỗi `index.lock` (phiên khác đang commit) → đợi vài giây rồi thử lại, **không** xóa file lock.
- Không `git push`, `git reset --hard`, `git checkout -- .`, `git clean` khi Đức chưa đồng ý.

## Code

- Python 3.11+, `numpy`, `pandas`, `matplotlib`, `pytest`. Chạy test: `python -m pytest -q` (cả repo) hoặc `python -m pytest tests/engine -q`.
- Số thực `float` thường, không mô phỏng số nguyên Q64.96 của Solidity.
- Mỗi hàm công khai có docstring tiếng Việt một-hai dòng, ghi đơn vị (token0/token1, tick, bước thời gian).
- Kết quả chạy (CSV, PNG) để trong `ket_qua/`; file lớn > 5 MB không commit.

## Quyết định đã chốt — không đi ngược khi chưa hỏi Đức

Xem mục "Quyết định kỹ thuật đã chốt" trong `../CLAUDE.md` (cross-tick ngay từ đầu; `w` là tham số tác nhân; victim tối ưu theo Lemma 4; `MC(v)` từ bể thật; range-aware = chia lại phí có trọng số; thử cả trợ cấp tuyến tính và log). Công thức, checklist, tiêu chuẩn kiểm định: `../03_Ghi_chu_nghien_cuu/03_Ke_hoach_simulator.md`. Việc + yêu cầu cần đạt + hạn của từng vai: `../03_Ghi_chu_nghien_cuu/05_Phan_cong.md`.

## Tiết kiệm lượt dùng

- Đọc file theo đoạn cần thiết, không mở lại PDF khi đã có phiếu đọc trong `../03_Ghi_chu_nghien_cuu/06_Phieu_doc/`.
- Mỗi lượt làm **một việc nhỏ trọn vẹn** rồi commit + cập nhật `SYNC.md`. Nếu bị ngắt vì hết hạn mức, phiên sau đọc `SYNC.md` là làm tiếp được.

## Trả lời Đức

Tiếng Việt, giải thích có ví dụ số khi là chỗ khó. **Cuối mỗi lần xong việc, nói rõ bước tiếp theo nên làm.**

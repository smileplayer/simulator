# Simulator — luật làm việc cho 3 vai + Chỉ huy

Thư mục này là **git repo của simulator** (`smileplayer/simulator`). Đức làm việc với **một phiên Chỉ huy trên cloud**; Chỉ huy gọi **A, B, C làm subagent** trong cùng container (cùng thư mục, thấy thay đổi của nhau ngay, không cần push/pull giữa các vai). Tài liệu đồ án nằm trong `tai_lieu_do_an/` (không cần đọc `tai_lieu_do_an/CLAUDE.md`, `README.md`); ghi chú nghiên cứu ở `tai_lieu_do_an/03_Ghi_chu_nghien_cuu/`, bài gốc ở `tai_lieu_do_an/00_Bai_goc/`, tài liệu tham khảo ở `tai_lieu_do_an/01_Tai_lieu_tham_khao/`.

## Chốt: Đức gõ `/chot` → test, commit, push. (`/vai` chỉ dùng khi Đức mở riêng một phiên cho một vai.)

Khi chưa biết mình là vai nào (chưa có lệnh `/vai`), **hỏi Đức trước khi sửa bất kỳ file nào**.

## Ba vai và quyền sửa

| Vai | Tên phiên | Được sửa | Chỉ đọc |
|---|---|---|---|
| **A — Engine** | `A-engine` | `engine/`, `tests/engine/` | mọi thứ còn lại |
| **B — Đo lường, kiểm định** | `B-metrics` | `metrics/`, `plots/`, `tests/metrics/`, `ket_qua/` | mọi thứ còn lại |
| **C — Tác nhân, thí nghiệm** | `C-agents` | `agents/`, `scenarios/`, `defenses/`, `tests/agents/`, **`INTERFACE.md`** | mọi thứ còn lại |
| **Chỉ huy** | `CH` | mục "Chỉ huy" trong `SYNC.md`; hạ tầng chung (`CLAUDE.md`, `README.md`, `.gitignore`, `.claude/`) | mọi code của A, B, C |
| Cả bốn | — | **chỉ mục của vai mình** trong `SYNC.md` | — |

**Chỉ huy:** rà kết quả và code của các vai, chạy test toàn repo; khi thấy lỗi, xung đột hoặc số bất thường thì tìm giải pháp (ghi chú nghiên cứu, bài gốc, tài liệu tham khảo, web), ghi vấn đề + bằng chứng + phương án vào mục "Chỉ huy" của `SYNC.md`, giao cho đúng vai. **Đầu mỗi phiên, A/B/C đọc mục "Chỉ huy" trước** và trả lời việc được giao trong mục của mình. Chỉ huy không sửa code của vai khác; việc đụng "Quyết định đã chốt" thì đưa Đức quyết.

- Cần vai khác sửa gì → ghi vào mục "Cần từ vai khác" của **vai mình** trong `SYNC.md`. Không tự sửa thư mục của vai khác.
- `INTERFACE.md` là hợp đồng. Chỉ vai C sửa. A, B muốn đổi → ghi đề nghị vào `SYNC.md`. Khi C đổi interface, C ghi dòng "ĐỔI INTERFACE" vào nhật ký kèm mô tả.
- Trước khi sửa `SYNC.md`: đọc lại file (vai khác có thể vừa ghi), rồi chỉ thay đúng mục của mình bằng Edit — không ghi đè cả file.

## Git

- Nhánh chung là `main`. **Không commit, không push giữa chừng**, trừ một ngoại lệ (Đức cho phép 15/10): **khi cần Đức chạy một lệnh** (lệnh dài > 5 phút), Chỉ huy tự chạy test, commit + push ngay để Đức `git pull` là chạy được. Ngoài ra chỉ khi Đức gõ `/chot`: Chỉ huy chạy test toàn repo, commit theo từng vai (mỗi vai một commit, chỉ `git add` thư mục của vai đó + `SYNC.md`), rồi `git pull --rebase origin main && git push origin HEAD:main`.
- Subagent A/B/C **không chạy git commit/push**; xong việc trả báo cáo cho Chỉ huy. Chỉ huy ghi `SYNC.md` (subagent không sửa `SYNC.md` để tránh ghi đè nhau).
- Thông điệp commit bắt đầu bằng `[A]`, `[B]`, `[C]` hoặc `[CH]`, viết tiếng Việt, ngắn. **Không** `git add -A` / `git add .`.
- Không `git push --force`, `git reset --hard`, `git checkout -- .`, `git clean` khi Đức chưa đồng ý.

## Code

- Python 3.11+, `numpy`, `pandas`, `matplotlib`, `pytest`. Chạy test: `python -m pytest -q` (cả repo) hoặc `python -m pytest tests/engine -q`.
- Số thực `float` thường, không mô phỏng số nguyên Q64.96 của Solidity.
- Mỗi hàm công khai có docstring tiếng Việt một-hai dòng, ghi đơn vị (token0/token1, tick, bước thời gian).
- Kết quả chạy (CSV, PNG) để trong `ket_qua/`; file > 50 MB không commit (giới hạn GitHub 100 MB/file).

## Lệnh chạy lâu — Đức tự chạy, không để Claude chạy

- **Trước khi chạy** một lệnh có thể lâu (quét tham số, nhiều seed, benchmark lớn, kịch bản dài): chạy bản nhỏ trước (ít bước / ít seed / `--nhanh`), đo thời gian, rồi **ước lượng thời gian bản đầy đủ**.
- Nếu ước lượng **> 5 phút**: **không chạy**. Dừng lại và báo Đức đúng 4 dòng: lệnh chạy (copy-dán được, chạy từ gốc repo), thời gian ước lượng, kết quả ghi vào file nào, và cách chạy tiếp nếu bị ngắt. Đồng thời ghi một dòng **"Chờ Đức chạy: …"** vào mục của vai mình trong `SYNC.md`.
- Script chạy lâu phải: ghi kết quả **dần dần** (mỗi ô xong ghi ngay một dòng CSV vào `ket_qua/`), **chạy lại thì bỏ qua phần đã xong**, in tiến độ ngắn gọn (vài dòng), có tùy chọn `--nhanh` để thử.
- Không dùng lệnh chạy nền rồi kiểm tra đi kiểm tra lại để chờ việc dài; không tự đặt `/loop` hay lịch hẹn giờ khi Đức chưa yêu cầu.
- Khi Đức báo đã chạy xong, đọc **file kết quả** (tóm tắt bằng pandas), không in toàn bộ file vào hội thoại.

## Quyết định đã chốt — không đi ngược khi chưa hỏi Đức

1. Engine cross-tick ngay từ GĐ1. 2. Độ rộng `w` là tham số tác nhân (GĐ1 đặt 1), không hardcode một tick. 3. Victim tối ưu theo Lemma 4; hai loại toàn tri và thích nghi. 4. `MC(v)` của farmer tính từ bể thật. 5. `c_V` tính theo vốn khi sang GĐ3. 6. Range-aware = chia lại phí có trọng số `L_i·φ(w_i)/Σ L_j·φ(w_j)`, tổng phí giữ nguyên. 7. Range-aware vô hiệu ở một tick → chỉ đánh giá ở GĐ3. 8. Thử cả trợ cấp `σ·min{v,Q}` và dạng log. Công thức, checklist, tiêu chuẩn kiểm định: `tai_lieu_do_an/03_Ghi_chu_nghien_cuu/03_Ke_hoach_simulator.md`. Việc + yêu cầu cần đạt + hạn của từng vai: `tai_lieu_do_an/03_Ghi_chu_nghien_cuu/05_Phan_cong.md`.

## Tiết kiệm lượt dùng

- Đọc file theo đoạn cần thiết, không mở lại PDF khi đã có phiếu đọc trong `tai_lieu_do_an/03_Ghi_chu_nghien_cuu/06_Phieu_doc/`.
- Mỗi lượt làm **một việc nhỏ trọn vẹn** rồi commit + cập nhật `SYNC.md`. Nếu bị ngắt vì hết hạn mức, phiên sau đọc `SYNC.md` là làm tiếp được.

## Trả lời Đức

Tiếng Việt, giải thích có ví dụ số khi là chỗ khó. **Cuối mỗi lần xong việc, nói rõ bước tiếp theo nên làm.**

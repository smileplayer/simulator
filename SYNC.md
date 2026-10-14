# SYNC — bảng đồng bộ giữa ba vai

Mỗi phiên **chỉ sửa mục của vai mình** (đọc lại file trước khi sửa). Nhật ký: thêm dòng mới **lên đầu**.

## Mục tiêu gần nhất

- **18/10:** C chốt `INTERFACE.md` + viết `scenarios/fake_log.py`.
- **25/10:** A có engine qua test cơ bản; B có metrics chạy trên log giả.
- **01/11:** GĐ1 chạy trọn vẹn trên engine thật.

---

## Vai A — Engine
- **Trạng thái:** chưa bắt đầu
- **Đang làm:** —
- **Cần từ vai khác:** —

## Vai B — Đo lường, kiểm định
- **Trạng thái:** chưa bắt đầu phần code. (Related Work đã có bản nháp trong Claude Docs, xem `../CLAUDE.md`.)
- **Đang làm:** —
- **Cần từ vai khác:** C — `scenarios/fake_log.py` để có log giả.

## Vai C — Tác nhân, thí nghiệm
- **Trạng thái:** đã nhận vai, chưa sửa code. Có đề xuất trả lời 4 câu hỏi mở (mục 7 `INTERFACE.md`) đang chờ Đức duyệt: 1 bước = 1 giờ; có `arb:0` kéo giá về `P_e` mỗi bước; farmer mua rồi bán ngay trong cùng bước để giá vẫn trong tick; trợ cấp trả theo cửa sổ 24 bước.
- **Đang làm:** chốt `INTERFACE.md` (chưa sửa file). Sau đó viết `scenarios/fake_log.py` cho B. Hạn cả hai: 18/10.
- **Cần từ vai khác:** —

---

## Nhật ký (mới nhất ở trên)

| Thời gian | Vai | Việc | Test |
|---|---|---|---|
| 14/10/2026 18:50 | C | Nhận vai, rà INTERFACE, đề xuất đáp án 4 câu hỏi mở (chờ Đức duyệt) | toàn repo 6 qua; tests/agents chưa có test |
| 14/10/2026 | — | Dựng khung repo, CLAUDE.md, INTERFACE.md (dự thảo), SYNC.md, lệnh /vai và /chot | `tests/test_khung.py` |

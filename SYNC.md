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
- **Trạng thái:** chưa bắt đầu
- **Đang làm:** —
- **Cần từ vai khác:** —

---

## Nhật ký (mới nhất ở trên)

| Thời gian | Vai | Việc | Test |
|---|---|---|---|
| 14/10/2026 | — | Dựng khung repo, CLAUDE.md, INTERFACE.md (dự thảo), SYNC.md, lệnh /vai và /chot | `tests/test_khung.py` |

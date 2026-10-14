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
- **Trạng thái:** `INTERFACE.md` **ĐÃ CHỐT 14/10** (1 bước = 1 giờ; `arb:0` kéo giá về `P_e` cuối mỗi bước; farmer khứ hồi trong cùng bước; trợ cấp theo cửa sổ `subsidy_window` = 24 bước). `scenarios/fake_log.py` đã xong: `make_fake_log(seed)` trả DataFrame đúng mục 4, mốc thật ở `df.attrs["meta"]` (`t_m`=48, `t_0`=144, `wall_tick`, …). Trong log giả: Prep ≈ 1,05–1,2× khối lượng nền, Attack > 10×, Post < nền; giá giảm ≈ 30% trong 2 bước sau `t_0`. Dòng `step` có `owner="platform"`.
- **Đang làm:** chưa mở việc mới. Việc kế: khung tác nhân (`agents/base.py`: Protocol `Agent`, `Market`) + farmer tối ưu `U_T` với `MC(v)` từ `quote_swap`. Viết trên bể giả `_BeGia` trước, chờ engine của A thì đổi sang.
- **Cần từ vai khác:** A — `Pool.quote_swap` sớm (farmer cần để tính `MC(v)`).

---

## Nhật ký (mới nhất ở trên)

| Thời gian | Vai | Việc | Test |
|---|---|---|---|
| 14/10/2026 18:56 | C | **ĐỔI INTERFACE → ĐÃ CHỐT** (trả lời 4 câu hỏi mở, thêm thứ tự trong bước, `subsidy_window`, quy ước dấu cho collect/subsidy/step, phí luôn ≥ 0). Thêm `scenarios/fake_log.py` cho B | toàn repo 13 qua (tests/agents 7 qua) |
| 14/10/2026 18:50 | C | Nhận vai, rà INTERFACE, đề xuất đáp án 4 câu hỏi mở (chờ Đức duyệt) | toàn repo 6 qua; tests/agents chưa có test |
| 14/10/2026 | — | Dựng khung repo, CLAUDE.md, INTERFACE.md (dự thảo), SYNC.md, lệnh /vai và /chot | `tests/test_khung.py` |

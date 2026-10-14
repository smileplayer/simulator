# SYNC — bảng đồng bộ giữa ba vai

Mỗi phiên **chỉ sửa mục của vai mình** (đọc lại file trước khi sửa). Nhật ký: thêm dòng mới **lên đầu**.

## Mục tiêu gần nhất

- **18/10:** C chốt `INTERFACE.md` + viết `scenarios/fake_log.py`.
- **25/10:** A có engine qua test cơ bản; B có metrics chạy trên log giả.
- **01/11:** GĐ1 chạy trọn vẹn trên engine thật.

---

## Vai A — Engine
- **Trạng thái:** đã nhận vai 14/10, chưa có code (`engine/` chỉ có `__init__.py`, `tests/engine/` trống).
- **Đang làm:** chưa mở việc. Việc kế: `engine/pool.py` lõi một khoảng — `Position`, `SwapResult`, `Pool` đúng chữ ký INTERFACE mục 2; hàm toán tick↔`√P`, `amount0/amount1` theo `L`; `mint`, `position_amounts`, `liquidity_at` + test (1.000 USDT một tick dưới `P₀=1` → `L ≈ 20.000.000`; `(x, y)` đúng ba trạng thái). Sau đó: `swap`/`quote_swap` cross-tick + `feeGrowth` (ưu tiên vì C cần `quote_swap`).
- **Cần từ vai khác:** —

## Vai B — Đo lường, kiểm định
- **Trạng thái:** có `metrics/timeseries.py`: `step_frame` (giá, tick, `L_active`, `p_ext` từ dòng `step`), `swap_volume` (khối lượng mỗi bước theo `role`, đo bằng |amount1| token1), `build_timeseries` (gộp + `vol_total`, `vol_trade` = bỏ arb, `n_swap`, `ret` log-return, `abs_ret`, `rv` std trượt 24 bước). Test `tests/metrics/test_timeseries.py` (5) trên `make_fake_log`. Related Work đã có bản nháp trong Claude Docs.
- **Đang làm:** chưa mở việc. Việc kế: `metrics/phases.py` — `phases(df)` tìm `t_m`, `t_50`, `t_peak`, `t_0`, `t_oot`, `t_b` (giá −10%) và ranh giới Prep/Attack/Post; test đối chiếu `df.attrs["meta"]` (`t_m`=48, `t_0`=144).
- **Cần từ vai khác:** —

## Vai C — Tác nhân, thí nghiệm
- **Trạng thái:** `INTERFACE.md` **ĐÃ CHỐT 14/10** (1 bước = 1 giờ; `arb:0` kéo giá về `P_e` cuối mỗi bước; farmer khứ hồi trong cùng bước; trợ cấp theo cửa sổ `subsidy_window` = 24 bước). `scenarios/fake_log.py` đã xong: `make_fake_log(seed)` trả DataFrame đúng mục 4, mốc thật ở `df.attrs["meta"]` (`t_m`=48, `t_0`=144, `wall_tick`, …). Trong log giả: Prep ≈ 1,05–1,2× khối lượng nền, Attack > 10×, Post < nền; giá giảm ≈ 30% trong 2 bước sau `t_0`. Dòng `step` có `owner="platform"`.
- **Đang làm:** chưa mở việc mới. Việc kế: khung tác nhân (`agents/base.py`: Protocol `Agent`, `Market`) + farmer tối ưu `U_T` với `MC(v)` từ `quote_swap`. Viết trên bể giả `_BeGia` trước, chờ engine của A thì đổi sang.
- **Cần từ vai khác:** A — `Pool.quote_swap` sớm (farmer cần để tính `MC(v)`).

---

## Nhật ký (mới nhất ở trên)

| Thời gian | Vai | Việc | Test |
|---|---|---|---|
| 14/10/2026 19:10 | B | Thêm `metrics/timeseries.py` (chuỗi thời gian theo bước: giá, `L_active`, khối lượng theo role, log-return, biến động trượt) + test | toàn repo 18 qua (tests/metrics 5 qua) |
| 14/10/2026 19:09 | A | Nhận vai, rà SYNC/INTERFACE/phân công; chưa viết code | toàn repo 13 qua; tests/engine chưa có test |
| 14/10/2026 19:09 | B | Nhận vai, rà SYNC/INTERFACE/phân công; chưa viết code | toàn repo 13 qua; tests/metrics chưa có test |
| 14/10/2026 18:56 | C | **ĐỔI INTERFACE → ĐÃ CHỐT** (trả lời 4 câu hỏi mở, thêm thứ tự trong bước, `subsidy_window`, quy ước dấu cho collect/subsidy/step, phí luôn ≥ 0). Thêm `scenarios/fake_log.py` cho B | toàn repo 13 qua (tests/agents 7 qua) |
| 14/10/2026 18:50 | C | Nhận vai, rà INTERFACE, đề xuất đáp án 4 câu hỏi mở (chờ Đức duyệt) | toàn repo 6 qua; tests/agents chưa có test |
| 14/10/2026 | — | Dựng khung repo, CLAUDE.md, INTERFACE.md (dự thảo), SYNC.md, lệnh /vai và /chot | `tests/test_khung.py` |

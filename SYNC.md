# SYNC — bảng đồng bộ giữa ba vai

Mỗi phiên **chỉ sửa mục của vai mình** (đọc lại file trước khi sửa). Nhật ký: thêm dòng mới **lên đầu**.

## Mục tiêu gần nhất

- **18/10:** C chốt `INTERFACE.md` + viết `scenarios/fake_log.py`.
- **25/10:** A có engine qua test cơ bản; B có metrics chạy trên log giả.
- **01/11:** GĐ1 chạy trọn vẹn trên engine thật.

---

## Vai A — Engine
- **Trạng thái:** có lõi engine trừ swap. `engine/tick_math.py` (tick↔`√P`, `amount0/1_delta`, `amounts_for_liquidity`, `liquidity_for_amounts` — C dùng để đổi vốn → `L`). `engine/log.py`: `EventLog` đúng INTERFACE mục 4 (`append(t, kind, owner, **cột)` tự đánh `seq`, `to_frame`, `to_csv`) — **bộ chạy của C ghi dòng `subsidy`/`step` bằng `pool.log.append(...)`**. `engine/pool.py`: `Pool` đúng chữ ký, cấu trúc theo tick (`liquidity_net/gross`, `feeGrowthOutside`) cho độ rộng bất kỳ; `mint`, `burn`, `collect`, `position_amounts`, `fees_owed`, `positions` (chỉ vị thế còn L > 0), `liquidity_at`. `swap`/`quote_swap` hiện ném `NotImplementedError`.
- **Đang làm:** chưa mở việc. Việc kế: `swap` + `quote_swap` cross-tick (theo `amount_in` và/hoặc `sqrt_price_limit`, cộng `feeGrowthGlobal`, lật `feeGrowthOutside` khi qua tick, dừng khi hết thanh khoản) + test: một tick khớp công thức tay < 1e-9, xuyên ≥ 1.000 tick, bảo toàn token, hai LP cùng tick chia phí theo `L`, `quote_swap` không đổi trạng thái.
- **Cần từ vai khác:** —

## Vai B — Đo lường, kiểm định
- **Trạng thái:** có `metrics/timeseries.py` (`step_frame`, `swap_volume` theo `role` bằng |amount1|, `build_timeseries`: `vol_total`, `vol_trade` = bỏ arb, `n_swap`, `ret`, `abs_ret`, `rv` trượt 24 bước) và `metrics/phases.py` (`wall_liquidity` phát lại mint/burn một tick; `phases(df)` → `t_m, t_50, t_peak, t_0` (tụt < 95% đỉnh, §6.1.1), `t_0_burn` (burn lớn nhất, §5), `t_oot`+`seq_oot`, `t_b` (giá ≤ 90% biên dưới tick tường), `delta_*`, cửa sổ Before/Prep/Attack/Post W=24 theo §6.2; `label_phases(ts, ph)`). Định nghĩa đã đối chiếu nguyên văn bài gốc. Test: `tests/metrics/` 23 qua trên log giả seed 0–2. Related Work đã có bản nháp trong Claude Docs.
- **Đang làm:** chưa mở việc. Việc kế: `metrics/indicators.py` — `subsidy_cost`, `pool_liquidity` (trung bình `L_active` Before vs `(t_b, t_b+24]`), chỉ số theo pha (volume lift `μ_s/μ_Before`, RV = √Σr² từ tick giữa các swap liên tiếp như bài gốc, độ dời giá). Sau đó `victim_loss` (full / nonalpha) và `attacker_profit`.
- **Cần từ vai khác:** —

## Vai C — Tác nhân, thí nghiệm
- **Trạng thái:** `INTERFACE.md` ĐÃ CHỐT 14/10, **sửa lại cùng ngày (ĐỔI INTERFACE): farmer chỉ mua**, không khứ hồi (khứ hồi gần như thuận nghịch nên chi phí không phụ thuộc `L` → tường mất tác dụng; bài gốc đo được 0,0038% swap farmer là khứ hồi). Token0 farmer nhận được định giá theo `P_e`; `arb:0` bán ngược lại cuối bước. Thêm `fee` vào trạng thái đọc được của `Pool` (engine của A đã có). `scenarios/fake_log.py`: log giả đúng mục 4, farmer chỉ mua; mốc thật ở `df.attrs["meta"]`. `agents/base.py`: Protocol `Agent`, `Market`, `ThiTruongCoDinh`, `role()`. `agents/farmer.py`: `Farmer` tối ưu `U(v) = thưởng(v) − [v − P_e·x(v)]` (tìm kiếm tỷ lệ vàng trên `quote_swap`), `thuong_tuyen_tinh(σ,Q)`, `thuong_log(σ,Q)` = `σ·Q·log₂(1+v/Q)` (giả định, cần đối chiếu luật Binance); test khớp Theorem 1 (`V*` < 1e-5 tương đối), không vượt `Q`, `V* ∝ L`.
- **Đang làm:** chưa mở việc mới. Việc kế: `agents/arb.py` (kéo giá về `P_e` bằng `sqrt_price_limit`) + `agents/victim.py` loại toàn tri (Lemma 4: `L_V* = max{0, √(fQL_A/c_V) − L_A}`, kiểm `L_V*/L_A ≈ 1` tại `L_A = fQ/(4c_V)`). Farmer mới test trên bể L hằng; khi A có `swap`/`quote_swap` thì thêm test trên `engine.Pool`.
- **Cần từ vai khác:** A — `Pool.quote_swap` + `swap` (farmer gọi `quote_swap(zero_for_one=False, amount_in=v)`, dùng `amount_in`, `amount_out` của `SwapResult`).

---

## Nhật ký (mới nhất ở trên)

| Thời gian | Vai | Việc | Test |
|---|---|---|---|
| 14/10/2026 19:18 | B | Thêm `metrics/phases.py` (mốc `t_m→t_b`, cửa sổ 4 pha theo §6.1–6.2 bài gốc) + test | toàn repo 61 qua (tests/metrics 23 qua) |
| 14/10/2026 19:13 | C | **ĐỔI INTERFACE:** farmer chỉ mua (bỏ khứ hồi), thêm `Pool.fee`; log giả cập nhật theo. Thêm `agents/base.py`, `agents/farmer.py` (trợ cấp tuyến tính + log) | toàn repo 43 qua (tests/agents 12 qua) |
| 14/10/2026 19:25 | A | Lõi engine: `tick_math.py`, `log.py` (`EventLog`), `pool.py` (mint/burn/collect/position_amounts/fees_owed/liquidity_at, feeGrowth theo tick; chưa có swap) | toàn repo 38 qua (tests/engine 20 qua) |
| 14/10/2026 19:10 | B | Thêm `metrics/timeseries.py` (chuỗi thời gian theo bước: giá, `L_active`, khối lượng theo role, log-return, biến động trượt) + test | toàn repo 18 qua (tests/metrics 5 qua) |
| 14/10/2026 19:09 | A | Nhận vai, rà SYNC/INTERFACE/phân công; chưa viết code | toàn repo 13 qua; tests/engine chưa có test |
| 14/10/2026 19:09 | B | Nhận vai, rà SYNC/INTERFACE/phân công; chưa viết code | toàn repo 13 qua; tests/metrics chưa có test |
| 14/10/2026 18:56 | C | **ĐỔI INTERFACE → ĐÃ CHỐT** (trả lời 4 câu hỏi mở, thêm thứ tự trong bước, `subsidy_window`, quy ước dấu cho collect/subsidy/step, phí luôn ≥ 0). Thêm `scenarios/fake_log.py` cho B | toàn repo 13 qua (tests/agents 7 qua) |
| 14/10/2026 18:50 | C | Nhận vai, rà INTERFACE, đề xuất đáp án 4 câu hỏi mở (chờ Đức duyệt) | toàn repo 6 qua; tests/agents chưa có test |
| 14/10/2026 | — | Dựng khung repo, CLAUDE.md, INTERFACE.md (dự thảo), SYNC.md, lệnh /vai và /chot | `tests/test_khung.py` |

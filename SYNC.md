# SYNC — bảng đồng bộ giữa ba vai

Mỗi phiên **chỉ sửa mục của vai mình** (đọc lại file trước khi sửa). Nhật ký: thêm dòng mới **lên đầu**.

## Mục tiêu gần nhất

- **18/10:** C chốt `INTERFACE.md` + viết `scenarios/fake_log.py`.
- **25/10:** A có engine qua test cơ bản; B có metrics chạy trên log giả.
- **01/11:** GĐ1 chạy trọn vẹn trên engine thật.

---

## Vai A — Engine
- **Trạng thái:** **engine đủ chức năng GĐ1, có `swap` + `quote_swap` cross-tick** (14/10): vòng lặp kiểu v3 theo `amount_in` (đã gồm phí) và/hoặc `sqrt_price_limit`, nhảy qua khoảng trống không thanh khoản, lật `feeGrowthOutside` khi qua tick, hết thanh khoản thì dừng (giá nằm ở biên cuối, `L_active = 0`). `quote_swap` chạy cùng lõi trên biến cục bộ — không đổi trạng thái, không ghi log, kết quả trùng `swap`. `SwapResult.ticks_crossed` = `|tick_after − tick_before|` (số tick giá đi qua, kể cả tick chưa khởi tạo). Quy ước tick như v3: đi xuống chạm đúng biên tick `i` đã khởi tạo → `tick = i − 1`. Test đạt các yêu cầu phân công: một tick khớp công thức tay (< 1e-9), xuyên 1.201 tick khớp công thức đóng, bảo toàn token (mint/swap ngẫu nhiên → rút hết, dư < 1e-9 quy mô; phí thu = phí swap), hai LP cùng tick chia phí theo `L`, tường `[-1,0)` dưới `P₀=1` kích hoạt ngay khi bán. Phần lõi trước đó: `engine/tick_math.py` (tick↔`√P`, `amount0/1_delta`, `amounts_for_liquidity`, `liquidity_for_amounts` — C dùng để đổi vốn → `L`). `engine/log.py`: `EventLog` đúng INTERFACE mục 4 (`append(t, kind, owner, **cột)` tự đánh `seq`, `to_frame`, `to_csv`) — **bộ chạy của C ghi dòng `subsidy`/`step` bằng `pool.log.append(...)`**. `engine/pool.py`: `Pool` đúng chữ ký, cấu trúc theo tick (`liquidity_net/gross`, `feeGrowthOutside`) cho độ rộng bất kỳ; `mint`, `burn`, `collect`, `position_amounts`, `fees_owed`, `positions` (chỉ vị thế còn L > 0), `liquidity_at`.
- **Đang làm:** chưa mở việc. Việc kế: kiểm chéo engine với `_BeGia` của C trên cùng chuỗi thao tác (giá, lượng, phí phải trùng) + test tính năng còn thiếu theo kế hoạch (tick_spacing > 1 khi swap, `liquidity_at` sau nhiều lần qua tick), rồi export `Pool`, `Position`, `SwapResult` ở `engine/__init__.py`. Sau đó hỗ trợ C ghép kịch bản cơ sở trên engine thật (mốc 01/11).
- **Cần từ vai khác:** —

## Vai B — Đo lường, kiểm định
- **Trạng thái:** có `metrics/timeseries.py` (chuỗi theo bước: giá, `L_active`, `p_ext`, `vol_<role>`, `vol_total`, `vol_trade` = bỏ arb, `ret`, `rv`), `metrics/phases.py` (`phases(df)`: tường, `t_m, t_50, t_peak, t_0, t_0_burn, t_oot, t_b`, cửa sổ Before/Prep/Attack/Post W=24 theo §6.1–6.2; `label_phases`), `metrics/indicators.py` (`subsidy_cost`; `pool_liquidity`: `L_active` Before vs Post + `drop_at_tb` §6.2.4; `vwap`; `price_changes` §6.2.3; `phase_stats`: lift, lift_trade, RV √Σr² theo Δtick như bài gốc + `RV_price`). **Quy ước Đức chốt 14/10: volume lift chính trên `vol_total` (gồm arb), `vol_trade` là chỉ số phụ.** Test `tests/metrics/` 41 qua (log giả seed 0–2). Related Work có bản nháp trong Claude Docs.
- **Lưu ý cho C (không bắt buộc sửa):** trên log giả, lift Post theo `vol_total` = 1,06–1,28 (> nền) vì `P_e` pha post dao động 0,015/giờ so với 0,002 ở nền → arb giao dịch nhiều hơn; `lift_trade` Post = 0,77–0,83 (< nền). Khi viết kịch bản thật, độ biến động `P_e` pha post quyết định dấu hiệu "Post dưới nền" theo chỉ số chính.
- **Đang làm:** chưa mở việc. Việc kế: `metrics/pnl.py` — `attacker_profit` (dòng tiền token1 ròng của role=attacker trong `[t_0, t_b]` + phí collect, đo độc lập) và `victim_loss` (full / nonalpha, alpha còn lại định giá VWAP `[t_b, t_b+1]`).
- **Cần từ vai khác:** —

## Vai C — Tác nhân, thí nghiệm
- **Trạng thái:** `INTERFACE.md` ĐÃ CHỐT 14/10, **sửa lại cùng ngày (ĐỔI INTERFACE): farmer chỉ mua**, không khứ hồi (khứ hồi gần như thuận nghịch nên chi phí không phụ thuộc `L` → tường mất tác dụng; bài gốc đo được 0,0038% swap farmer là khứ hồi). Token0 farmer nhận được định giá theo `P_e`; `arb:0` bán ngược lại cuối bước. Thêm `fee` vào trạng thái đọc được của `Pool` (engine của A đã có). `scenarios/fake_log.py`: log giả đúng mục 4, farmer chỉ mua; mốc thật ở `df.attrs["meta"]`. `agents/base.py`: Protocol `Agent`, `Market`, `ThiTruongCoDinh`, `role()`. `agents/farmer.py`: `Farmer` tối ưu `U(v) = thưởng(v) − [v − P_e·x(v)]` (tìm kiếm tỷ lệ vàng trên `quote_swap`), `thuong_tuyen_tinh(σ,Q)`, `thuong_log(σ,Q)` = `σ·Q·log₂(1+v/Q)` (giả định, cần đối chiếu luật Binance); test khớp Theorem 1 (`V*` < 1e-5 tương đối), không vượt `Q`, `V* ∝ L`.
- **Đang làm:** chưa mở việc mới. Việc kế: `agents/arb.py` (kéo giá về `P_e` bằng `sqrt_price_limit`) + `agents/victim.py` loại toàn tri (Lemma 4: `L_V* = max{0, √(fQL_A/c_V) − L_A}`, kiểm `L_V*/L_A ≈ 1` tại `L_A = fQ/(4c_V)`). Farmer mới test trên bể L hằng; khi A có `swap`/`quote_swap` thì thêm test trên `engine.Pool`.
- **Cần từ vai khác:** A — `Pool.quote_swap` + `swap` (farmer gọi `quote_swap(zero_for_one=False, amount_in=v)`, dùng `amount_in`, `amount_out` của `SwapResult`).

---

## Nhật ký (mới nhất ở trên)

| Thời gian | Vai | Việc | Test |
|---|---|---|---|
| 14/10/2026 19:26 | B | Thêm `metrics/indicators.py` (trợ cấp, thanh khoản bể, VWAP, độ dời giá, bảng theo pha: lift chính trên `vol_total`, RV) + test | toàn repo 96 qua (tests/metrics 41 qua) |
| 14/10/2026 19:40 | A | `Pool.swap` + `quote_swap` cross-tick (feeGrowth, lật outside, khoảng trống, hết thanh khoản) + 17 test swap. **C dùng được `quote_swap` trên `engine.Pool`** | toàn repo 78 qua (tests/engine 37 qua) |
| 14/10/2026 19:18 | B | Thêm `metrics/phases.py` (mốc `t_m→t_b`, cửa sổ 4 pha theo §6.1–6.2 bài gốc) + test | toàn repo 61 qua (tests/metrics 23 qua) |
| 14/10/2026 19:13 | C | **ĐỔI INTERFACE:** farmer chỉ mua (bỏ khứ hồi), thêm `Pool.fee`; log giả cập nhật theo. Thêm `agents/base.py`, `agents/farmer.py` (trợ cấp tuyến tính + log) | toàn repo 43 qua (tests/agents 12 qua) |
| 14/10/2026 19:25 | A | Lõi engine: `tick_math.py`, `log.py` (`EventLog`), `pool.py` (mint/burn/collect/position_amounts/fees_owed/liquidity_at, feeGrowth theo tick; chưa có swap) | toàn repo 38 qua (tests/engine 20 qua) |
| 14/10/2026 19:10 | B | Thêm `metrics/timeseries.py` (chuỗi thời gian theo bước: giá, `L_active`, khối lượng theo role, log-return, biến động trượt) + test | toàn repo 18 qua (tests/metrics 5 qua) |
| 14/10/2026 19:09 | A | Nhận vai, rà SYNC/INTERFACE/phân công; chưa viết code | toàn repo 13 qua; tests/engine chưa có test |
| 14/10/2026 19:09 | B | Nhận vai, rà SYNC/INTERFACE/phân công; chưa viết code | toàn repo 13 qua; tests/metrics chưa có test |
| 14/10/2026 18:56 | C | **ĐỔI INTERFACE → ĐÃ CHỐT** (trả lời 4 câu hỏi mở, thêm thứ tự trong bước, `subsidy_window`, quy ước dấu cho collect/subsidy/step, phí luôn ≥ 0). Thêm `scenarios/fake_log.py` cho B | toàn repo 13 qua (tests/agents 7 qua) |
| 14/10/2026 18:50 | C | Nhận vai, rà INTERFACE, đề xuất đáp án 4 câu hỏi mở (chờ Đức duyệt) | toàn repo 6 qua; tests/agents chưa có test |
| 14/10/2026 | — | Dựng khung repo, CLAUDE.md, INTERFACE.md (dự thảo), SYNC.md, lệnh /vai và /chot | `tests/test_khung.py` |

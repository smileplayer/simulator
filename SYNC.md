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
- **Trạng thái:** có `metrics/timeseries.py` (chuỗi theo bước: giá, `L_active`, `p_ext`, `vol_<role>`, `vol_total`, `vol_trade` = bỏ arb, `ret`, `rv`), `metrics/phases.py` (`phases(df)`: tường, `t_m, t_50, t_peak, t_0, t_0_burn, t_oot, t_b`, cửa sổ Before/Prep/Attack/Post W=24 theo §6.1–6.2; `label_phases`), `metrics/indicators.py` (`subsidy_cost`; `pool_liquidity`: `L_active` Before vs Post + `drop_at_tb` §6.2.4; `vwap`; `price_changes` §6.2.3; `phase_stats`: lift, lift_trade, RV √Σr² theo Δtick như bài gốc + `RV_price`). **Quy ước Đức chốt 14/10: volume lift chính trên `vol_total` (gồm arb), `vol_trade` là chỉ số phụ.** `metrics/pnl.py` (`identify_roles` suy vai như §5 bài gốc — victim/wall provider/pressure trader/attacker/main attacker, không dùng nhãn `role`; `victim_loss` bản `nonalpha` (bài gốc) + `full` (so với ôm, định giá VWAP [t_b, t_b+1]), phí tách riêng; `attacker_profit`: `paper` = token1 từ swap chiều sập trong [t_0, t_end], `net_cash1`, `full` = + Δtoken0 × `alpha_cost` (mặc định giá trước khi rút)). Cả hai mốc kết thúc `t_b`/`t_oot`. Test `tests/metrics/` 56 qua (log giả seed 0–2). Related Work có bản nháp trong Claude Docs.
- **Lưu ý cho C (không bắt buộc sửa):** trên log giả, lift Post theo `vol_total` = 1,06–1,28 (> nền) vì `P_e` pha post dao động 0,015/giờ so với 0,002 ở nền → arb giao dịch nhiều hơn; `lift_trade` Post = 0,77–0,83 (< nền). Khi viết kịch bản thật, độ biến động `P_e` pha post quyết định dấu hiệu "Post dưới nền" theo chỉ số chính.
- **Đang làm:** chưa mở việc. Đủ 4 chỉ số + dẫn xuất còn thiếu `derived` (hiệu quả chi tiêu, tỷ lệ rò rỉ). Việc kế: `metrics/derived.py` + `metrics/report.py` (một hàm `summarize(df)` gom mọi chỉ số một vụ thành một dict/dòng), rồi `validate_rq1`.
- **Cần từ vai khác:** C — (1) cuối kịch bản cho victim/attacker `collect` để phí LP hiện trong log (phí chưa collect không đọc được từ log); (2) ghi giá vốn alpha của attacker `c_A` vào `df.attrs["meta"]` hoặc config để `attacker_profit(..., alpha_cost=c_A)` dùng thay mặc định.

## Vai C — Tác nhân, thí nghiệm
- **Trạng thái:** `INTERFACE.md` ĐÃ CHỐT 14/10, sửa cùng ngày (ĐỔI INTERFACE): **farmer chỉ mua**, `arb:0` bán ngược lại cuối bước; thêm `Pool.fee`. Đã có:
  - `scenarios/fake_log.py` — log giả đúng mục 4, mốc thật ở `df.attrs["meta"]`.
  - `agents/base.py` — Protocol `Agent`, `Market`, `ThiTruongCoDinh`, `role()`.
  - `agents/farmer.py` — `Farmer` tối ưu `U(v) = thưởng(v) − [v − P_e·x(v)]` bằng **chia đôi trên `U'(v)`** (giá biên từ `sqrt_price_after`, chính xác ~1e-8, đúng cả khi xuyên tick); `thuong_tuyen_tinh`, `thuong_log` (`σ·Q·log₂(1+v/Q)` — giả định, cần đối chiếu Binance).
  - `agents/arb.py` — `Arbitrageur` kéo giá về `P_e` bằng `sqrt_price_limit`, có cờ `bat` để tắt ở pha Attack.
  - `agents/victim.py` — `l_v_sao` (Lemma 4) + `VictimToanTri`: vào tick chứa giá, mỗi bước chỉnh L về `L_V*` (lệch > 1%), `L_A` = mọi thanh khoản khác đang hoạt động; giá ra ngoài khoảng thì giữ nguyên.
  - Test trên **engine thật**: farmer khớp Theorem 1 (sai 1e-8), victim đạt `L_V*/L_A = 1` tại `L_A = fQ/(4c_V)`, arb về đúng `P_e`.
- **Đang làm:** chưa mở việc mới. Việc kế: `agents/attacker.py` (dựng tường, rút toàn bộ, xả tới `z₂` — Lemma 5) rồi `scenarios/run.py` + config JSON cơ sở (trả thưởng theo cửa sổ, ghi `subsidy`/`step` bằng `pool.log.append`). Đáp ứng yêu cầu của B trong bộ chạy: `collect` cuối kịch bản cho mọi LP; ghi `c_A` vào config/meta. Sau đó: victim thích nghi.
- **Cần từ vai khác:** —

---

## Nhật ký (mới nhất ở trên)

| Thời gian | Vai | Việc | Test |
|---|---|---|---|
| 14/10/2026 19:31 | C | Thêm `agents/arb.py`, `agents/victim.py` (toàn tri, Lemma 4); farmer đổi sang chia đôi trên đạo hàm; test arb/victim/farmer trên engine thật | toàn repo 122 qua (tests/agents 23 qua) |
| 14/10/2026 19:31 | B | Thêm `metrics/pnl.py` (suy vai như bài gốc, thiệt hại nạn nhân nonalpha/full, lợi nhuận kẻ tấn công paper/net/full) + test | toàn repo 122 qua (tests/metrics 56 qua) |
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

# SYNC — bảng đồng bộ giữa ba vai

Mỗi phiên **chỉ sửa mục của vai mình** (đọc lại file trước khi sửa). Nhật ký: thêm dòng mới **lên đầu**.

## Mục tiêu gần nhất

- **18/10:** C chốt `INTERFACE.md` + viết `scenarios/fake_log.py`.
- **25/10:** A có engine qua test cơ bản; B có metrics chạy trên log giả.
- **01/11:** GĐ1 chạy trọn vẹn trên engine thật.

---

## Vai A — Engine
- **Trạng thái:** **engine đủ chức năng GĐ1, có `swap` + `quote_swap` cross-tick** (14/10): vòng lặp kiểu v3 theo `amount_in` (đã gồm phí) và/hoặc `sqrt_price_limit`, nhảy qua khoảng trống không thanh khoản, lật `feeGrowthOutside` khi qua tick, hết thanh khoản thì dừng (giá nằm ở biên cuối, `L_active = 0`). `quote_swap` chạy cùng lõi trên biến cục bộ — không đổi trạng thái, không ghi log, kết quả trùng `swap`. `SwapResult.ticks_crossed` = `|tick_after − tick_before|` (số tick giá đi qua, kể cả tick chưa khởi tạo). Quy ước tick như v3: đi xuống chạm đúng biên tick `i` đã khởi tạo → `tick = i − 1`. Test đạt các yêu cầu phân công: một tick khớp công thức tay (< 1e-9), xuyên 1.201 tick khớp công thức đóng, bảo toàn token (mint/swap ngẫu nhiên → rút hết, dư < 1e-9 quy mô; phí thu = phí swap), hai LP cùng tick chia phí theo `L`, tường `[-1,0)` dưới `P₀=1` kích hoạt ngay khi bán. Đã kiểm chéo với `_BeGia` của C (4 seed × 200 swap: giá, tick, lượng vào/ra, phí từng vị thế trùng < 1e-8; khác biệt duy nhất: chạm biên thanh khoản rồi đổi chiều thì `_BeGia` kẹt, engine đi tiếp như v3); swap với `tick_spacing=10`; `L_active` = `liquidity_at(tick)` sau 100 lần qua lại. **Import gọn: `from engine import Pool, Position, SwapResult, EventLog, sqrt_price_at_tick, liquidity_for_amounts, …`.** **Móc GĐ3 `Pool(..., fee_weight=φ)`** (14/10): phí chia theo `L_i·φ(w_i)/Σ L_j·φ(w_j)` trong vị thế đang hoạt động, tổng phí giữ nguyên (quyết định chốt 6); cài bằng feeGrowth trên mỗi đơn vị `L·φ(w)` (thêm `weighted_net` mỗi tick, `pool.liquidity_weighted`); giá/lượng swap không đổi theo φ; φ hằng số ⇔ pro-rata (đúng quyết định 7: vô hiệu ở một tick); `φ(w) ≤ 0` → `ValueError`. **Tốc độ** (đo 14/10): 1.000 bước × (10 farmer × 40 `quote_swap` + swap) = 412.000 lệnh trong 2,8 s (~7 µs/lệnh); xả qua 2.900 tick 5 ms → quét `(σ, Q)` × 10 seed × 4 biện pháp chạy được trong vài giờ một lõi, nhanh hơn nếu chạy song song. Phần lõi trước đó: `engine/tick_math.py` (tick↔`√P`, `amount0/1_delta`, `amounts_for_liquidity`, `liquidity_for_amounts` — C dùng để đổi vốn → `L`). `engine/log.py`: `EventLog` đúng INTERFACE mục 4 (`append(t, kind, owner, **cột)` tự đánh `seq`, `to_frame`, `to_csv`) — **bộ chạy của C ghi dòng `subsidy`/`step` bằng `pool.log.append(...)`**. `engine/pool.py`: `Pool` đúng chữ ký, cấu trúc theo tick (`liquidity_net/gross`, `feeGrowthOutside`) cho độ rộng bất kỳ; `mint`, `burn`, `collect`, `position_amounts`, `fees_owed`, `positions` (chỉ vị thế còn L > 0), `liquidity_at`.
- **Đang làm:** chưa mở việc. Engine đã đủ cho GĐ1–GĐ3. Việc kế: (1) đọc `agents/` của C xem có chỗ nào gọi engine sai quy ước (dấu, `amount_in` gồm phí, tick khi chạm biên) — báo trong SYNC, không sửa; (2) khi C có `scenarios/run.py`: chạy kịch bản cơ sở, kiểm log engine ghi đúng cột/dấu với `metrics/` của B (đối chiếu `fake_log`), báo lệch. Song song: bắt đầu dàn ý báo cáo nền tảng CLMM (hạn 15/11).
- **Cần từ vai khác:** —

## Vai B — Đo lường, kiểm định
- **Trạng thái:** có `metrics/timeseries.py` (chuỗi theo bước: giá, `L_active`, `p_ext`, `vol_<role>`, `vol_total`, `vol_trade` = bỏ arb, `ret`, `rv`), `metrics/phases.py` (`phases(df)`: tường, `t_m, t_50, t_peak, t_0, t_0_burn, t_oot, t_b`, cửa sổ Before/Prep/Attack/Post W=24 theo §6.1–6.2; `label_phases`), `metrics/indicators.py` (`subsidy_cost`; `pool_liquidity`: `L_active` Before vs Post + `drop_at_tb` §6.2.4; `vwap`; `price_changes` §6.2.3; `phase_stats`: lift, lift_trade, RV √Σr² theo Δtick như bài gốc + `RV_price`). **Quy ước Đức chốt 14/10: volume lift chính trên `vol_total` (gồm arb), `vol_trade` là chỉ số phụ.** `metrics/pnl.py` (`identify_roles` suy vai như §5 bài gốc — victim/wall provider/pressure trader/attacker/main attacker, không dùng nhãn `role`; `victim_loss` bản `nonalpha` (bài gốc) + `full` (so với ôm, định giá VWAP [t_b, t_b+1]), phí tách riêng; `attacker_profit`: `paper` = token1 từ swap chiều sập trong [t_0, t_end], `net_cash1`, `full` = + Δtoken0 × `alpha_cost` (mặc định giá trước khi rút)). Cả hai mốc kết thúc `t_b`/`t_oot`. `metrics/report.py` (`derived`: `eff_L` = L_active Post / trợ cấp, `eff_gain` = (Post − Before) / trợ cấp, `leak_paper`/`leak_full` = lợi nhuận kẻ tấn công / trợ cấp; `summarize(df)` → dict phẳng ~60 chỉ số một vụ; `summarize_many(dfs)` → DataFrame). Test `tests/metrics/` 60 qua (log giả seed 0–2). Related Work có bản nháp trong Claude Docs.
- **Lưu ý cho C (không bắt buộc sửa):** trên log giả, lift Post theo `vol_total` = 1,06–1,28 (> nền) vì `P_e` pha post dao động 0,015/giờ so với 0,002 ở nền → arb giao dịch nhiều hơn; `lift_trade` Post = 0,77–0,83 (< nền). Khi viết kịch bản thật, độ biến động `P_e` pha post quyết định dấu hiệu "Post dưới nền" theo chỉ số chính.
- **Đang làm:** chưa mở việc. Việc kế: `metrics/validate.py` — `validate_rq1(dfs)` bảng Đạt/Không đạt theo mục 6 kế hoạch (thời gian chuẩn bị theo ngày/thu hoạch theo giờ, lift Prep 1–1,5×, Attack có vụ > 5×, Post < 1 (chính `vol_total`, phụ `vol_trade`), RV Prep < Attack < Post, giá quanh `t_m` ≈ 0 và sau rút âm lớn, cạn thanh khoản tại `t_b`).
- **Cần từ vai khác:** C — (1) cuối kịch bản cho victim/attacker `collect` để phí LP hiện trong log (phí chưa collect không đọc được từ log); (2) ghi giá vốn alpha của attacker `c_A` vào `df.attrs["meta"]` hoặc config để `attacker_profit(..., alpha_cost=c_A)` dùng thay mặc định.

## Vai C — Tác nhân, thí nghiệm
- **Trạng thái:** `INTERFACE.md` ĐÃ CHỐT 14/10, sửa cùng ngày (ĐỔI INTERFACE): **farmer chỉ mua**, `arb:0` bán ngược lại cuối bước; thêm `Pool.fee`. Đã có:
  - `scenarios/fake_log.py` — log giả đúng mục 4, mốc thật ở `df.attrs["meta"]`.
  - `agents/base.py` — Protocol `Agent`, `Market`, `ThiTruongCoDinh`, `role()`.
  - `agents/farmer.py` — `Farmer` tối ưu `U(v) = thưởng(v) − [v − P_e·x(v)]` bằng **chia đôi trên `U'(v)`** (giá biên từ `sqrt_price_after`, chính xác ~1e-8, đúng cả khi xuyên tick); `thuong_tuyen_tinh`, `thuong_log` (`σ·Q·log₂(1+v/Q)` — giả định, cần đối chiếu Binance).
  - `agents/arb.py` — `Arbitrageur` kéo giá về `P_e` bằng `sqrt_price_limit`, có cờ `bat` để tắt ở pha Attack.
  - `agents/victim.py` — `l_v_sao` (Lemma 4) + `VictimToanTri`: vào tick chứa giá, mỗi bước chỉnh L về `L_V*` (lệch > 1%), `L_A` = mọi thanh khoản khác đang hoạt động; giá ra ngoài khoảng thì giữ nguyên.
  - `agents/attacker.py` — `Attacker`: dựng tường theo lịch `[(bước, tỷ lệ)]` ở tick chứa giá, rút (burn + collect) ở `t_0` hoặc khi L nạn nhân ≥ `nguong_victim·L_A`, xả token0 qua `so_buoc_xa` bước tới `z₂` (dừng ở `z̄ = √(c_A/(1−f))`, hết kho, hoặc hết thanh khoản); `dang_xa(t)` để bộ chạy tắt arb.
  - `scenarios/run.py` — `run(config, seed) -> EventLog` (meta ở `log.meta`), `run_frame(...)` → DataFrame có `df.attrs["meta"]` (gồm cả config: `c_A`, `t_m`, `t_rut`, `wall_tick`…), `nap_config("co_so")`. Config cơ sở `scenarios/configs/co_so.json` (240 bước, tường 4e8 dựng 48/72, rút 168, xả 2 bước). **Đã đáp ứng 2 yêu cầu của B**: collect mọi vị thế có phí ở bước cuối; `c_A` có trong meta. Giá ngoài `ThiTruongKichBan`: neo giữa tick tường khi Prep (vol 0), đi theo bể khi xả, vol 1%/h sau đó.
  - **Kết quả cơ sở seed 0 (đo bằng `metrics.report.summarize`):** victim mint đúng `L_V = L_A = 4e8` ✓; farmer đạt trần 72k/ngày khi có tường, ~27k/ngày khi không ✓; lift Prep 1,78 (trade 1,38), Attack 7,1; RV Prep 0,02 < Before 0,09 < Post 0,28 ✓; giá −34% sau 2 bước; victim lỗ 1.879, phí victim nhận 937. **Chưa đạt: lift Post 1,08 (bài gốc: dưới nền)** — trong mô hình nền và farmer trở về như trước tường; cần cơ chế (LP nền rút / trader rời đi sau sập) — để bàn với Đức.
  - Test trên **engine thật**: farmer khớp Theorem 1 (sai 1e-8), victim đạt `L_V*/L_A = 1` tại `L_A = fQ/(4c_V)`, arb về đúng `P_e`.
- **Đang làm:** chưa mở việc mới. Việc kế: victim thích nghi (`VictimThichNghi`: ước lượng lợi suất phí từ quá khứ, tối ưu như Lemma 4 với V ước lượng), rồi bộ chạy nhiều seed (`scenarios/batch.py`) và các biện pháp GĐ2 trong `defenses/`.
- **Cần từ vai khác:** —

---

## Nhật ký (mới nhất ở trên)

| Thời gian | Vai | Việc | Test |
|---|---|---|---|
| 14/10/2026 19:50 | C | Thêm `scenarios/run.py` + `configs/co_so.json`: **GĐ1 chạy trọn trên engine thật** (đủ 5 loại tác nhân, trợ cấp, collect cuối, meta có `c_A`). B: dùng `run_frame(nap_config("co_so"), seed)` | toàn repo 154 qua (tests/agents 36 qua) |
| 14/10/2026 20:05 | A | Móc GĐ3 `fee_weight = φ(w)` (feeGrowth trên L·φ, tổng phí giữ nguyên) + 7 test; đo tốc độ engine (~7 µs/lệnh) | toàn repo 147 qua (tests/engine 52 qua) |
| 14/10/2026 19:50 | A | Kiểm chéo engine với `_BeGia` (trùng < 1e-8), test `tick_spacing=10`, `liquidity_at` sau nhiều lần qua tick, chạm biên rồi đổi chiều; export gói `engine` | toàn repo 134 qua (tests/engine 45 qua) |
| 14/10/2026 19:39 | C | Thêm `agents/attacker.py` (Lemma 5: ba điều kiện dừng, rút theo `t_0` hoặc ngưỡng victim, xả nhiều bước) + 6 test trên engine | toàn repo 140 qua (tests/agents 29 qua) |
| 14/10/2026 19:38 | B | Thêm `metrics/report.py` (`derived`: hiệu quả chi tiêu, tỷ lệ rò rỉ; `summarize`, `summarize_many`) + test | toàn repo 133 qua (tests/metrics 60 qua) |
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

# Tổng kết dự án simulator — từ đầu tới nay

> Cập nhật: 15/10/2026 (Chỉ huy). Nguồn: nhật ký `SYNC.md`, `ket_qua/rq1/NHAT_KY_HIEU_CHINH.md`, git log, báo cáo các vai.
> Đồ án: tái lập và mở rộng **Lu et al., USENIX Security 2026** — *Liquidity Mining as an Attack Surface* (tấn công "tường thanh khoản một tick" trên CLMM kiểu Uniswap v3 khi có trợ cấp theo khối lượng).

---

## 1. Mục tiêu và cách tổ chức

| Câu hỏi | Nội dung | Giai đoạn |
|---|---|---|
| **RQ1** | Simulator có tái tạo được các dấu hiệu thực nghiệm của 29 vụ trong bài gốc không (khối lượng theo pha, biến động, độ sập giá, tường cạn)? | GĐ1 |
| **RQ2** | Các biện pháp bài gốc đề xuất (§7: hạ trần `Q`, trả thưởng trễ, cảnh báo rủi ro, trần động) có hiệu quả không, đánh đổi gì? | GĐ2 |
| **RQ3** | Range-aware (chia lại phí theo độ rộng vị thế) ở nhiều tick | GĐ3 |

**Ba vai + Chỉ huy:**

| Vai | Phụ trách | Thư mục |
|---|---|---|
| A — Engine | Bể CLMM: tick, swap xuyên tick, phí, log sự kiện | `engine/`, `tests/engine/` |
| B — Đo lường | Chỉ số theo pha, lợi nhuận/thiệt hại, kiểm định, hình | `metrics/`, `plots/`, `tests/metrics/`, `ket_qua/` |
| C — Tác nhân, thí nghiệm | Farmer, arb, victim, attacker, kịch bản, biện pháp; giữ hợp đồng `INTERFACE.md` | `agents/`, `scenarios/`, `defenses/`, `tests/agents/` |
| Chỉ huy | Rà chéo, tìm lỗi, quyết phương án, điều phối, ghi `SYNC.md`, commit khi `/chot` | hạ tầng chung |

**Cách làm việc (đổi theo thời gian):**
1. 14/10: 3 phiên Claude trên máy Đức, chung một thư mục, đồng bộ bằng file + git local.
2. 14/10 tối: chuyển lên cloud, 4 phiên riêng, đồng bộ qua GitHub nhánh `main` (push sau mỗi việc).
3. **15/10 (hiện tại):** một phiên Chỉ huy gọi A/B/C làm **subagent** trong cùng container → không push/pull giữa các vai; **chỉ commit + push khi Đức gõ `/chot`**.

**8 quyết định kỹ thuật đã chốt** (không đi ngược khi chưa hỏi Đức): engine cross-tick từ GĐ1; độ rộng `w` là tham số tác nhân; victim tối ưu theo Lemma 4 (hai loại toàn tri / thích nghi); `MC(v)` của farmer tính từ bể thật; `c_V` theo vốn ở GĐ3; range-aware = chia lại phí có trọng số `L_i·φ(w_i)/Σ L_j·φ(w_j)`; range-aware vô hiệu ở một tick; thử cả trợ cấp tuyến tính và log.

---

## 2. Dòng thời gian việc đã làm

### 14/10/2026 — Dựng khung và GĐ1

| Giờ | Vai | Việc |
|---|---|---|
| sáng | — | Khung repo, `CLAUDE.md`, `INTERFACE.md` dự thảo, `SYNC.md`, lệnh `/vai`, `/chot` |
| 18:50–18:56 | C | Chốt `INTERFACE.md` (4 câu hỏi mở, thứ tự trong bước, `subsidy_window`, quy ước dấu); `scenarios/fake_log.py` (log giả cho B làm trước) |
| 19:10–19:38 | B | `metrics/timeseries.py` → `phases.py` (mốc `t_m…t_b`, 4 pha) → `indicators.py` (lift, RV, VWAP, độ dời giá) → `pnl.py` (suy vai như §5 bài gốc, thiệt hại nạn nhân, lợi nhuận kẻ tấn công) → `report.py` (`summarize`) |
| 19:13 | C | **ĐỔI INTERFACE:** farmer chỉ mua; `agents/base.py`, `farmer.py` (trợ cấp tuyến tính + log) |
| 19:25–19:40 | A | `tick_math.py`, `log.py` (`EventLog`), `pool.py` (mint/burn/collect, feeGrowth theo tick) → `swap` + `quote_swap` xuyên tick |
| 19:31–19:39 | C | `arb.py`, `victim.py` (Lemma 4), `attacker.py` (Lemma 5: dựng tường, rút, xả) |
| 19:50 | A | Kiểm chéo engine với bể mẫu của C (trùng < 1e-8), `tick_spacing=10` |
| 19:50 | C | `scenarios/run.py` + `co_so.json` → **GĐ1 chạy trọn trên engine thật** |
| 19:53 | B | `validate.py`; RQ1 lần đầu trên co_so 5 seed: **Đạt 8/13** |
| 20:05 | A | Móc GĐ3 `fee_weight = φ(w)`; đo tốc độ ~7 µs/lệnh |
| 20:06–20:20 | C | Hiệu chỉnh môi trường (mục 3 dưới), bộ tổ hợp 30 vụ L27, `scenarios/batch.py` |
| 20:16 | B | Kiểm định theo phân phối (Đức chốt), Bảng 4/6/7 cạnh bài gốc → **RQ1 Đạt 13/13** trên 150 log; tag `rq1-v1` |
| 20:25 | B | Hình: timeline, hộp RV, Bảng 4/7 (`plots/`) |
| 20:30 | C | `NHAT_KY_HIEU_CHINH.md`; `VictimThichNghi`; `defenses/thuong.py` (cap, delay); `scenarios/quet_gd2.py` |
| 20:32–20:42 | Đức | Chạy quét GĐ2 → `ket_qua/gd2/tomtat.csv` (4.200 dòng) |
| tối | Đức + CH | Đưa tài liệu đồ án (`tai_lieu_do_an/`, 118 MB) lên repo; chuyển lên cloud; thêm vai Chỉ huy |

### 14/10 tối – 15/10 — Chỉ huy điều phối

| Việc | Vai | Kết quả |
|---|---|---|
| Hạ tầng cloud: `.gitignore` chỉ còn cache Python, luật git mới, sửa đường dẫn, quyền push | CH + Đức | Push lên `main` được |
| Chốt 3 việc chờ Đức (Đức giao CH quyết) | CH | 10 seed + bootstrap; trả trễ mô hình (b) + clawback (a); lift Prep giữ (mục 5) |
| CH-5: RQ1 lên 10 seed | C | 300 log |
| CH-6: kẻ tấn công cũng farm (`attacker_farm_share`) + clawback | C | Đức chạy `quet_gd2 --farm` → `tomtat_farm.csv` (10.800 dòng) |
| CH-4: rà cách agents gọi engine, kiểm bảo toàn | A (subagent) | Engine đúng; +7 test phát lại log |
| CH-1/2/5/7: lợi nhuận tăng thêm, trợ cấp treo, bootstrap, bản nháp | B (subagent) | 13/13 Đạt trên 300 log, có CI |
| CH-8: dòng ngẫu nhiên theo vụ + nguồn, sửa tick, clawback theo lịch sử + mốc đầu cửa sổ | C (subagent) | Xong, 208 test qua; RQ1 300 log chạy lại |

---

## 3. Hiệu chỉnh mô hình cho RQ1 (lỗi "dấu hiệu" và cách sửa)

Chỉ chạm **môi trường**, không chạm hành vi tối ưu của tác nhân hay engine. Chi tiết: `ket_qua/rq1/NHAT_KY_HIEU_CHINH.md`.

| # | Vấn đề | Nguyên nhân | Cách sửa | Hệ quả |
|---|---|---|---|---|
| 1 | **lift Post 1,15 > 1** (bài gốc: Post dưới nền) | Thanh khoản nền phủ ±20.000 tick, sau sập mọi thứ quay lại như cũ | Nền hữu hạn ±`bg_band` (5 vị thế lồng nhau) | Post 0,195 (quá tay), độ sập kẹt ở mép dải ≈ 10% |
| 2 | **Tường chỉ chiếm 50%** (bài gốc ≥ 80% ở 25/29 vụ) | `c_V` đặt ở mốc `L_A = fV/(4c_V)` (điểm làm `L_V*` lớn nhất, chỉ để kiểm engine) | `c_V = k·fV/L_A`, `k ∈ [0,64; 1)` ⟺ `L_V*/L_A ≤ 0,25`; co_so k = 0,75 → tường 87% | Đạt tường cạn ≥ 80% |
| 3 | **Độ sập luôn ≈ band hoặc luôn −50%** | Không có thanh khoản xa giá; kho 60k luôn xả tới giá vốn `z̄` | Đuôi nền mỏng toàn dải `bg_tail = 7,5%`; kho kẻ tấn công thành yếu tố {15k, 25k, 40k}; `bg_band` ∈ {0,15; 0,25; 0,40} | Độ sập −11…−50% (trung vị −37%), Post 0,86, RV Post cao nhất 95% |

Tiêu chuẩn kiểm định cũng đổi (Đức chốt 14/10): kiểm theo **phân phối** (tỷ lệ vụ thỏa, so x/29 bài gốc, Đạt khi ≥ 50%) thay vì trung vị; bỏ tiêu chuẩn Prep 1–1,5×; lift chính tính trên tổng khối lượng (gồm arb), bỏ arb là chỉ số phụ.

---

## 4. Lỗi tìm được và cách sửa (theo thời gian)

| # | Ngày | Ai tìm | Lỗi | Ảnh hưởng | Sửa | Ai sửa |
|---|---|---|---|---|---|---|
| 1 | 14/10 | C | Test cap hỏng: đo L của victim sau khi rút tường | 1 test sai | Đo L ròng trước khi rút | C |
| 2 | 14/10 | C | Bể mẫu `_BeGia` kẹt khi chạm biên thanh khoản rồi đổi chiều | Chỉ bể mẫu, engine đúng | Dùng engine thật | A/C |
| 3 | 14/10 | C | `attacker_profit_paper` ≈ 9.600 cả khi **không có nạn nhân** | Lợi nhuận tấn công bị thổi phồng | Chỉ số mới `attacker_profit_excess` = paper − bán thẳng kho (Theorem 6) — CH-1 | B |
| 4 | 14/10 | C | `subsidy_cost` bỏ sót khoản trả trễ chưa tới hạn | Biện pháp trả trễ trông rẻ giả tạo | Cộng `subsidy_pending`; clawback báo riêng — CH-2 | B |
| 5 | 14/10 | C | Trả trễ gần như **không tác dụng** lên victim | Biện pháp §7.2 không đánh giá được | Mô hình (b): kẻ tấn công cũng farm (pressure trader) + biến thể (a) clawback — CH-6 | C |
| 6 | 15/10 | CH | Kẻ tấn công farm → lợi nhuận tăng 17,7k → 19k; nghi đếm nhầm | — | Đưa B kiểm → đúng là lỗi (mục 7) | B |
| 7 | 15/10 | B | `attacker_profit` trừ cả khối lượng mua farm của kẻ tấn công: `full` = **−245k** | Sai lợi nhuận ở mọi lượt farm | Tách `farm_pnl` (khối lượng, chi phí, thưởng, treo); `full` = phần tấn công + `farm_pnl` | B |
| 8 | 15/10 | B, CH kiểm lại | **Seed là yếu tố chéo:** mọi vụ dùng chung chuỗi ngẫu nhiên `default_rng(seed)` → seed 5 chỉ 30% vụ Post<1, seed 0/8 100%; seed 5–9 kém hơn 0–4 ở 17/30 vụ (p < 0,001) | CI bootstrap hẹp giả | B thêm CI chéo; C: `default_rng([seed, crc32(mã vụ)])` — CH-8 | B, C |
| 9 | 15/10 | A | `tick_lower = pool.tick` (attacker.py, victim.py) sai khi `tick_spacing > 1` (ValueError) hoặc giá dừng đúng biên tick (tường đặt lệch, farmer mua xuyên) | Thấp ở GĐ1 (arb giữ giá giữa tick), quan trọng ở GĐ3 | Căn theo spacing, xử lý biên trên — CH-8 | C |
| 10 | 15/10 | A | Clawback chỉ thu hồi owner **đang** có LP → thưởng chốt sau khi rút tường lọt | Kẻ tấn công né clawback bằng cách rút trước | Thu hồi theo lịch sử địa chỉ: owner từng có LP trong cửa sổ D | C |
| 11 | 15/10 | C | Cặp phản thực (có/không biện pháp) chỉ khớp ngẫu nhiên tới khi trạng thái bể tách nhau (bể cạn thì bỏ lượt rút số) | Hiệu biện pháp lẫn nhiễu | Tách bộ sinh số theo nguồn, mỗi bước luôn rút đủ số | C ✓ |
| 12 | 15/10 | C | Clawback so với giá **lúc chốt** → thưởng chốt sau cú sập có mốc đã thấp | Kẻ tấn công vẫn né được | Mốc = giá đầu cửa sổ tích lũy thưởng | C ✓ |
| 13 | 15/10 | B | `ket_qua/gd2/tomtat*.csv` tính bằng metrics cũ (chưa có excess, farm sai) | Không dùng được cho RQ2 | Chạy lại bản `_v2` sau khi C xong | **Đức chạy** |

**Hạ tầng:**
- `.claude/settings.json` cấm `git push` → Đức sửa.
- Claude chưa có quyền ghi GitHub (403) → Đức kết nối lại GitHub App.
- `.gitignore` bỏ qua log/bản nháp → bỏ hết, chỉ giữ cache Python.

---

## 5. Quyết định đã chốt trong quá trình

| Ngày | Ai quyết | Quyết định | Căn cứ |
|---|---|---|---|
| 14/10 | Đức | Kiểm định RQ1 theo phân phối, bỏ tiêu chuẩn Prep 1–1,5×; lift chính trên tổng khối lượng | — |
| 14/10 | Đức | Bản nháp bài báo của B để trong `ket_qua/ban_nhap/` | — |
| 14/10 | CH (Đức giao) | **10 seed/cấu hình + bootstrap phân cụm, CI 95%** | Phần phương sai do seed 5–36%; 13/30 vụ kết luận Post<1 lẫn lộn giữa 5 seed; 30 vụ → sai số tỷ lệ ±18 điểm % |
| 14/10 | CH | **Trả trễ: (b) kẻ tấn công cũng farm là chính, (a) clawback là biến thể** | §7.2 nhắm "xây chậm, rút nhanh"; bài gốc có vai pressure trader |
| 14/10 | CH | **Lift Prep 1,77 giữ, ghi là khác biệt** | Tăng theo Q (1,31/1,78/2,93) đúng Theorem 1; ép < 1 cần nhiễu ngoại sinh vô căn cứ |
| 15/10 | CH | Victim toàn tri tính V gồm khối lượng farm của kẻ tấn công là **đúng ý đồ** | Phí từ khối lượng đó là thật |
| 15/10 | CH | Sửa ghép cặp ngẫu nhiên + mốc clawback **trước** khi chạy lại GĐ2 | Tránh chạy lại 1 giờ |
| 15/10 | Đức | Làm việc bằng subagent, commit khi `/chot` | Tiết kiệm token |

---

## 6. Kết quả hiện có

### RQ1 (300 log = 30 vụ × 10 seed, sau CH-8) — **Đạt 13/13**

| Tiêu chí | Mô phỏng | CI 95% | Bài gốc | Lần trước CH-8 |
|---|---|---|---|---|
| Sập ≥ 10% | 98% | 96–100 | 100% | 99% |
| Δbuild ≥ 1 ngày | 100% | — | 55% | 100% |
| Δextract < 24 h | 99% | 97–100 | 62% | 99% |
| Attack ≥ 1× | 100% | 99–100 | 59% | 100% |
| Attack > 5× | 25% | 12–40 | 14% | 20% |
| Post < 1× | **80%** | 71–88 | 79% | 74% |
| RV Prep < RV Attack | 97% | 90–100 | — | 97% |
| RV Post cao nhất | 96% | 91–100 | — | 97% |
| Giá ghim quanh t_m | 100% | — | 79% | 100% |
| **Giá sập < −10% (VWAP)** | **52%** | **38–67 — mong manh** | 69% | 59% |
| Giá sập (phụ, mốc trước burn) | 79% | 67–91 | — | 82% |
| Tường cạn ≥ 80% | 100% | — | 86% | 100% |

Trung vị lift: Prep 1,79 · Attack 3,65 · Post 0,855. Lift Prep theo Q 12k/24k/48k: 1,37 / 1,84 / 3,06.
Yếu tố seed chéo **đã hết** (hoán vị seed 0–4 vs 5–9: p = 0,66, trước CH-8 p < 0,001).
**Khác biệt ghi nhận:** Prep không vụ nào < 1× (bài gốc 9/29); Post dồn < 1,5×; tường cạn dồn 80–99% (bài gốc 18/29 ở 100%); **giá sập theo VWAP chỉ 52%, CI vắt qua ngưỡng 50%** → trong bài báo ghi "đạt điểm, chưa chắc thống kê", không hiệu chỉnh thêm (tránh ép mô hình khớp số); chỉ số phụ mốc trước burn chắc ở 79%.

### Phát hiện quan trọng nhất cho RQ2

**Lợi nhuận tăng thêm thật của tấn công rất nhỏ trong bộ RQ1:** `excess` trung vị 299 (CI 146–602), dương ở 277/295 lượt, ≈ 2% lợi nhuận "paper" (14.532); tỷ lệ rò rỉ trợ cấp 0,057× thay vì 3,2×. Phần lớn "lợi nhuận" là bán kho vào thanh khoản nền. Lý do: bộ RQ1 chọn `k` để tường ≥ 80% → nạn nhân nhỏ (`L_V/L_A ≈ 0,15`).
→ RQ2 phải báo `attacker_profit_excess`, không báo `paper`. Cần xét thêm vùng `k` nhỏ (nạn nhân lớn) để thấy khi nào tấn công thật sự có lãi (Theorem 6).

### GĐ2 (bản cũ, chỉ để tham khảo — sẽ thay bằng `_v2`)
- Hạ trần 75/50/25%: victim thích nghi `L_V/L_A` 0,73/0,53/0,34, thiệt hại giảm 3.300 → 700; victim toàn tri về 0 ngay từ cap 75%.
- Trả trễ với farmer thuần: không tác dụng lên victim, chỉ giảm chi phí trợ cấp.
- Kẻ tấn công farm 60% (trung vị lãi farm): +2.199 (không biện pháp) → +1.797 (delay72) → +101 (clawback72) → −634 (clawback168).

---

## 7. Việc tiếp theo

### Ngay bây giờ (cập nhật 15/10 chiều)
- ✓ RQ1 chạy lại sau CH-8 (13/13 Đạt). ✓ GĐ2 v2 đã chạy + B làm bảng đánh đổi, Q*, hình, bản nháp mục 7.
- ✓ C chuẩn bị v3: lợi nhuận theo địa chỉ thật + phản thực phát lại log (excess = 0 khi không victim), vùng k nhỏ, cảnh báo rủi ro (warn), trần động (dyncap), lưới cap mịn, lưới (σ, Q).
1. **Đức:** `/chot` → `git pull` → chạy `python -m scenarios.quet_gd2 --luoi` (~5 phút), `python -m scenarios.quet_gd2` (~43 phút), `python -m scenarios.quet_gd2 --k_nho` (~29 phút); `--farm` không bắt buộc (~54 phút). Đẩy file `ket_qua/gd2/*_v3.csv` lên.
2. **B:** bảng đánh đổi v3 dùng `dc_excess` (phản thực phát lại), Q* theo lưới cap mịn, bản đồ nhiệt (σ, Q) ba vùng thiết kế, vùng k nhỏ; cập nhật mục 7.

### Kết quả GĐ2 v2 đáng chú ý
- Hạ trần: toàn tri cap50 → thiệt hại −100%, lợi kẻ tấn công −94%, mất khối lượng −26%; thích nghi chỉ −40%/−43%. **Q\* toàn tri khớp Lemma 4/Theorem 6** (ngưỡng = k ở 28/30 vụ).
- Trả trễ 24–72 không tác dụng; 168 = hạ σ trá hình. Clawback 168 (attacker farm 0,6) cắt lợi kẻ tấn công −74…−77% nhưng không bảo vệ victim.
- Không biện pháp nào làm giá thôi sập. Victim thích nghi khó bảo vệ (ước V từ phí cả bể, gồm nền + arb).
- Vùng k nhỏ (victim lớn): lợi nhuận tăng thêm ~8.500 (RQ1 ~300); cap25, warn40, dyncap cắt còn ~2.200–3.000.

### Xa hơn
9. **GĐ3 / RQ3:** range-aware nhiều tick (engine đã có `fee_weight`); `c_V` theo vốn; tường nhiều tick.
10. **A:** dàn ý báo cáo nền tảng CLMM (hạn 15/11).
11. **B:** hoàn thiện mục 5–6 bài báo; mục 7 (RQ2) khi có số.

### Mốc hạn
- 01/11: GĐ1 trọn vẹn (**đã đạt sớm**).
- 15/11: báo cáo nền tảng CLMM (A).

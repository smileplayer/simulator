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
3. **15/10:** một phiên Chỉ huy gọi A/B/C làm **subagent** trong cùng container → không push/pull giữa các vai; **chỉ commit + push khi Đức gõ `/chot`**.
4. **16–17/10 (hiện tại):** làm việc trên máy Đức từ phiên mở ở thư mục gốc đồ án. Luật của `04_Simulator/CLAUDE.md` gộp vào `../CLAUDE.md` (mục "Simulator"); xóa bản chép `tai_lieu_do_an/` (118 MB) và bộ kết quả GĐ2 v2.

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
| 13 | 15/10 | B | `ket_qua/gd2/tomtat*.csv` tính bằng metrics cũ (chưa có excess, farm sai) | Không dùng được cho RQ2 | Chạy lại bản `_v2` | Đức chạy ✓ |
| 14 | 15/10 | B | 969 lượt không sập → lợi nhuận NaN (suy vai theo bài gốc cần có sập) | Bỏ NaN làm lệch so sánh | Lợi nhuận theo địa chỉ thật `attacker:0` (cột `dc_*`), báo tỷ lệ sập riêng | C ✓ |
| 15 | 15/10 | C | Phản thực "bán thẳng" bán cả kho một lần → excess +370 khi không có victim | Lớn hơn cả tín hiệu ở RQ1 (~300) | Phản thực phát lại log (bỏ tường + victim) → 0 đúng khi không victim | C ✓ |
| 16 | 15/10 | B | Định giá chi phí farm khác nhau giữa B và C (lệch 136) | Bảng không nhất quán | Thống nhất theo `metrics.pnl.farm_pnl` | C ✓ |
| 17 | 15/10 | B | Lợi tăng thêm không đơn điệu theo trần (L27_25 thích nghi: 2.586 → 4.493 ở cap75) | Trái Theorem 6 | Lỗi phản thực: phát lại nguyên lượng mua farmer (lấy từ đường giá có victim đỡ) → farmer phản thực tối ưu lại trên bể phản thực | C ✓, **cần chạy lại v4** |
| 18 | 15/10 | Đức | `python -m scenarios.quet_gd2 --luoi` lỗi NameError: hàm `to_hop_luoi` bị xóa nhầm khi sửa #17; test không bao phủ chế độ `--luoi` | Không chạy được lưới σ×Q | Khôi phục hàm từ commit trước; thêm 4 test khói cho mọi chế độ quét | CH + C ✓ |
| 19 | 15/10 | A | Engine: khi giá rời tường lớn, L·φ còn lại < 1e-9 lần tường bị `_clean` làm tròn về 0 và kéo L về 0 → bể coi như rỗng, mất phí vị thế nhỏ (chỉ khi có φ, tức GĐ3) | Sai phân bổ phí GĐ3 | Bỏ `_clean`, cộng lại trực tiếp các vị thế đang hoạt động khi phép trừ gần triệt tiêu; +25 test; GĐ1/GĐ2 lệch ≤ 1,8e-12 | A ✓ |
| 20 | 15/10 | A, CH kiểm | Mô hình dùng f = 0,25% với tickSpacing 1; trên PancakeSwap v3 (`PancakeV3Factory.sol`) tier 0,01/0,05/0,25/1% đi với spacing 1/10/50/200 → "tường một tick" theo nghĩa đen chỉ có ở tier 0,01%; bài gốc không nêu tier của 29 vụ | Con số tuyệt đối (lợi nhuận, độ sâu) phụ thuộc cặp (f, spacing); kết quả qua k và σ/f thì không | Ghi là giới hạn trong mục 2 + mục 9; đề xuất chạy độ nhạy f = 0,01% (chưa làm) | mở |
| 21 | 15/10 | C, CH đo | 3 vụ L27_02/04/06 (L_A = 2e8, Q = 48k) vi phạm Giả định 2: 34–37% lệnh farmer trong pha tường đẩy giá ra khỏi tick tường (các vụ khác 1–4%) → Lemma 4 của victim toàn tri dựa trên V sai | Kết quả các vụ này lệch lý thuyết | Giữ trong RQ1, đánh dấu "ngoài Giả định 2", B thêm phân tích độ nhạy loại 3 vụ | B ✓ (27 vụ vẫn 13/13) |
| 22 | 26/10 | Hoàng (ngoài nhóm), CH kiểm | Cải tiến G: `collect` trả hết phí và không phạt, nên thu phí trước rồi mới `burn` lấy lại 100% phí, không có dòng `donate` | Biện pháp G bị vô hiệu bằng một lệnh; bài báo bỏ sót cách né rẻ nhất | `collect` giữ phí chưa xét phạt tới khi vị thế đủ tuổi hoặc bị burn; `meta["fee_balances"]`, cột `victim_net_cash`, `victim_fees_locked` (commit `ecf0a9f`). Kẻ tấn công trong mô phỏng luôn burn trước nên số G không đổi | ✓ |

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

*Ghi chú 18/10 (bài báo):* 13/13 theo ước lượng điểm; 12/13 nếu đòi CI nằm trên 50% (giá sập VWAP 52%, CI 38–67 → "chưa phân định"). "Lift Attack > 5×" là tiêu chí tồn tại (bài gốc 4/29). Gắn nhãn: 9 tiêu chí nảy sinh, 4 áp đặt (chuẩn bị ≥ 1 ngày, thu hoạch < 24 giờ, tường cạn do lịch kịch bản; RV Prep < RV Attack do neo giá).

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

### Độ nhạy RQ1 (15/10, `ket_qua/do_nhay/so_sanh.csv`)
| Dấu hiệu | Gốc | Bỏ neo giá pha tường | Phí 0,01% | Nhận xét |
|---|---|---|---|---|
| Giá ghim quanh t_m, tường cạn ≥ 80%, Δbuild/Δextract | 99–100% | 97–100% | 99–100% | vững |
| Giá sập < −10% (VWAP) | 52% | 59% | 64% | vững (tăng) |
| RV Prep < RV Attack | 97% | 51% | 100% | do giả định giá ghim |
| RV Post cao nhất | 96% | 79% | 95% | vững |
| Post < 1× | 80% | 81% | 42% (Không đạt) | phụ thuộc mức phí |

**Điều kiện cần của tấn công: giá bị ghim.** Khi có giá ngoài + arb, tường một tick không giữ được giá (giá nằm trên tick tường 1,2% số bước; arb vượt tường chỉ cần ~20k token1; 75% lượt victim vào sai tick, trung vị cách tường 105 tick) → thiệt hại và lợi tăng thêm về 0. Baseline giá ghim có căn cứ: token Alpha giao dịch chủ yếu trên chính bể, bài gốc thấy giá ghim ở 79% vụ. Hệ quả cho thảo luận: **neo giá ngoài** (niêm yết/oracle sớm) là hướng phòng thủ bài gốc chưa nêu (suy luận, chưa đánh giá đánh đổi).

### Phát hiện quan trọng nhất cho RQ2

**Lợi nhuận tăng thêm thật của tấn công rất nhỏ trong bộ RQ1:** `excess` trung vị 299 (CI 146–602), dương ở 277/295 lượt, ≈ 2% lợi nhuận "paper" (14.532); tỷ lệ rò rỉ trợ cấp 0,057× thay vì 3,2×. Phần lớn "lợi nhuận" là bán kho vào thanh khoản nền. Lý do: bộ RQ1 chọn `k` để tường ≥ 80% → nạn nhân nhỏ (`L_V/L_A ≈ 0,15`).
→ RQ2 phải báo `attacker_profit_excess`, không báo `paper`. Cần xét thêm vùng `k` nhỏ (nạn nhân lớn) để thấy khi nào tấn công thật sự có lãi (Theorem 6).

### GĐ2 bản đầu (lịch sử, đã thay bằng v4; số cuối ở mục 7)
- Hạ trần 75/50/25%: victim thích nghi `L_V/L_A` 0,73/0,53/0,34, thiệt hại giảm 3.300 → 700; victim toàn tri về 0 ngay từ cap 75%.
- Trả trễ với farmer thuần: không tác dụng lên victim, chỉ giảm chi phí trợ cấp.
- Kẻ tấn công farm 60% (trung vị lãi farm): +2.199 (không biện pháp) → +1.797 (delay72) → +101 (clawback72) → −634 (clawback168).

---

## 7. Việc tiếp theo

### GĐ2 v4 — số cuối của RQ2 (15/10)
Bảng: `ket_qua/gd2/bang/`, hình: `ket_qua/gd2/hinh/`, bản nháp: `ket_qua/ban_nhap/muc7_ket_qua_RQ2.md`.

| Nhóm biện pháp | Vùng RQ1: % giảm lợi kẻ tấn công (toàn tri \| thích nghi) | Vùng k nhỏ (victim lớn) | Mất khối lượng |
|---|---|---|---|
| Hạ trần cap50 → cap05 | 100 \| 31–65 | 25–81 \| 4–30 | 26–54% |
| Trần động | 100 \| 56 | 62 \| 19 | 36–42% |
| Cảnh báo rủi ro warn15/20/40 | 94–100 \| 27/50/94 | 9/18/43 \| 2/4/18 | < 2,3% |
| Trả trễ delay72 / 168 | ≈ 0 / 4 \| ≈ 0 / 19 | 5–6 | 3% / 19% |
| Thu hồi claw72 / 168 (attacker farm 0,6) | 50 / 72 \| 46 / 76 (victim không đổi) | 20–22 | 3,6% / 25% |

**Kết luận RQ2:**
1. Ngưỡng hạ trần Q\* của Theorem 6 khớp thực nghiệm khi victim định giá theo trần: **Q\*/Q = k** (28/30 vụ RQ1, 30/30 k nhỏ). Hạ dưới ngưỡng xóa hết lợi, đổi lấy mất 20–26% khối lượng.
2. **Victim thích nghi (nhìn phí lịch sử) khó bảo vệ:** hạ trần/trần động chỉ cắt 31–65% (RQ1), 4–30% (victim lớn), mất tới nửa khối lượng; 21/30 vụ vẫn còn victim ở cap05. Lý do: victim ước khối lượng từ phí cả bể (gồm nền + arb).
3. **Cảnh báo rủi ro giữ khối lượng tốt nhất** (mất < 2,3% khối lượng) (sửa 20/10: chỉ đúng trên trục khối lượng; cảnh báo gần như không tiết kiệm trợ cấp, hạ trần tiết kiệm 44–94%; warn40 làm L_active Post giảm 49% với nạn nhân thích nghi, do cú sập sâu hơn (22/10: bỏ vị thế nạn nhân và kẻ tấn công cho cùng số ở mọi lượt có sập); thứ hạng tùy mục tiêu của nền tảng). Thu hồi thưởng là bổ sung rẻ nhưng chỉ cắt lãi farm.
   - Bản v5 (22/10): nghi vấn W11 sai: L_khac_mean_post = L_mean_post ở cả 9.270 lượt có sập; warn40 giảm L Post vì cú sập sâu hơn (độ sập trung vị −18% → −40% với nạn nhân thích nghi). Nạn nhân lỗ ròng (tính cả phí) ở 57% lượt toàn tri, 66% thích nghi (trung vị −20 / −275 token1). Bậc phí 0,01%: % thay đổi lệch ≤ 7 điểm (lợi tăng thêm ≤ 1,2), thứ tự biện pháp giữ nguyên; tỷ số lợi tăng thêm / trợ cấp thành 2,7× / 14× (vì trợ cấp ∝ σ, giữ σ/f).
4. **Không biện pháp nào chặn được cú sập giá.**
5. Bản đồ ba vùng (toàn tri) khớp lý thuyết 25/25 ô; vùng 4 "ngoài giả định" ở σ = f và Q lớn so với L_A.

**Giới hạn mô hình cần ghi trong bài:** (a) lợi của phương án bán thẳng phụ thuộc Q (farmer mua đỡ cú bán) — Theorem 6 coi không đổi → vài vụ Q nhỏ có "lợi tăng thêm" tăng nhẹ khi hạ trần; (b) victim toàn tri tin V = n·Q kể cả khi trần không ràng buộc; (c) giá sập theo VWAP chỉ 52% (CI 38–67).

### GĐ3 (RQ3) — kết quả (15/10)
Bảng: `ket_qua/gd3/bang/`, hình: `ket_qua/gd3/hinh/`, bản nháp: `ket_qua/ban_nhap/muc8_ket_qua_RQ3.md`.
- **Victim chọn độ rộng** theo g(w) = φ(w)·ℓ(w): w* nhảy 1 → w₀; ngưỡng **α\* ≈ 1** (mô phỏng: α = 0,5 → w = 1, α ≥ 1 → w = w₀ ở mọi lượt) ⇒ φ phải tăng nhanh hơn tuyến tính (α > 1; α = 1 lợi chỉ 0,01–0,25%) — **xác nhận giả thuyết của đồ án**.
- **Trải rộng không cắt được phần vốn trên đường sập** (0,50–0,55 ở mọi φ): sập sâu 600–5.000 tick ≫ w/2.
- **Kênh tác động thật = lượng vốn victim** (tường 1 tick bị phạt nhường phí cho victim). Giải tích khớp mô phỏng 89/90 ô (sai số trung vị 0,15%). Tường 1 tick, α ≥ 1,5, toàn tri:

| k | Vốn victim (× pro-rata) | Lợi kẻ tấn công |
|---|---|---|
| 0,10 | 0,17–0,68 | −6…−75% |
| 0,95 | 4,5–10,4 | +277…+736% |

  Victim thích nghi luôn giảm vốn (0,15–0,90×).
- **Khi kẻ tấn công được nới tường (số đầy đủ `tomtat_wA.csv`, chọn w_A tối ưu theo trung vị 10 seed; thường w₀/4–w₀/2):**

| k | Victim | Vốn victim: tường 1 tick → tối ưu | Lợi kẻ tấn công: tường 1 tick → tối ưu |
|---|---|---|---|
| 0,10 | toàn tri | 0,17–0,68 → 0,71–1,01 | −75…−6% → −28…−3% |
| 0,25 | cả hai | 0,16–0,81 → 0,56–1,02 | → +8…+22% |
| 0,64 | toàn tri | → 1,47–1,57 (giải tích 1,56) | → −3…+20% |
| 0,80 | toàn tri | → 2,40–2,70 (giải tích 2,63) | → +79…+111% |
| 0,95 | toàn tri | → 10,1–10,6 (giải tích 9,9) | → +610…+740% |

  Khớp giải tích 46/54 ô (36/36 ở k ≥ 0,45). Victim thích nghi chỉ được bảo vệ không nhất quán theo k.
- **Kết luận RQ3:** range-aware đổi được cách victim chọn độ rộng (α\* ≈ 1) nhưng (1) không giảm phần vốn bị cú sập quét qua (≈ 0,5), (2) tác dụng duy nhất là phạt tường một tick — kẻ tấn công vô hiệu hóa bằng cách nới tường, (3) ở vùng RQ1 còn hút victim vào nhiều hơn, (4) LP dải hẹp cố định mất 50–100% phí. ⇒ **φ dạng lũy thừa không phải biện pháp phòng thủ đáng tin cậy; cảnh báo rủi ro (GĐ2) tốt hơn hẳn.**
- **w₀ lớn (17/10, `tomtat_w0lon.csv`, `tomtat_wA_w0lon.csv`):** phần vốn trên đường sập chỉ giảm (0,11–0,37) ở vụ sập nông 2–6%; sập sâu vẫn 0,5. Kẻ tấn công thường giữ tường một tick (37/72). α ≥ 1,5: lợi kẻ tấn công −6…−32% ở k = 0,45–0,64, nhưng k = 0,80/0,95 toàn tri vẫn bị hút 2,5–8,7×. Kết luận không đổi.
- **Cái giá:** LP dải cố định 10 tick mất 51–100% phí khi w₀ ≥ 50; LP tự chọn w thu thêm 44–77%; khi giá bị ghim, độ sâu trên mỗi đơn vị vốn còn ≈ 1/w₀.
- **Giới hạn mô hình:** luật chọn w bỏ qua biến động; victim toàn tri rút giữa hai bước xả (phần bị lấy bị chặn bởi lượng xả mỗi bước); trượt giá `lp*_truot` là của cả bể, đo trước tường.

### Ngay bây giờ (cập nhật 17/10)
- ✓ RQ1, RQ2, RQ3 đều đã có số liệu cuối (15/10).
- ✓ Bài báo ghép đủ mục 1–10 ở `../02_Bao_cao_va_trinh_bay/bai_bao.tex` (LNCS), biên dịch được (16/10).
- ✓ 16–17/10: tùy chọn `--w0` cho `scenarios/quet_gd3.py`; Đức chạy xong; quét w₀ ∈ {1.000; 2.000} (17/10, `ket_qua/gd3/tomtat_w0lon.csv`, `tomtat_wA_w0lon.csv`): nạn nhân chọn đúng w₀; phần vốn trên đường sập chỉ giảm (0,11–0,37) ở vụ sập nông 2–6% (~200–600 tick < w/2), sập sâu 9–50% vẫn 0,5; kẻ tấn công thường giữ tường một tick (37/72 cấu hình) vì nới hàng trăm tick làm tường loãng; α ≥ 1,5: lợi kẻ tấn công −6…−32% ở k = 0,45–0,64 và với nạn nhân thích nghi ở k ≥ 0,45, nhưng k = 0,80/0,95 toàn tri vẫn bị hút 2,5–8,7× (lợi kẻ tấn công tới +60%/+472%) → kết luận RQ3 không đổi. Đã viết vào bài báo (mục RQ3). Commit + push 17/10.
- ✓ 17/10: sáu hình nền tảng CLMM (`python -m plots.ve_nen_tang` → `ket_qua/nen_tang/`), gắn vào `nen_tang_CLMM.md`; Hình 2.5 đưa vào bài báo. Bài báo lọc preprint (giữ 5 bài quan trọng).
1. Bản thảo: điền tác giả, soát Hình 6.1. Đã dọn 17/10: xóa bộ GĐ2 v1, v3 và chế độ `--phien v3`.
2. Slide: kịch bản 10 phút ở `../02_Bao_cao_va_trinh_bay/Kich_ban_slide_10_phut.md` (17/10); dựng bằng `../ppt-master/` theo khung `../L01_Nhap_mon_Blockchain_Mat_ma.pdf`.

### Cải tiến tùy chọn (đề xuất 17/10)
- A: chạy lại GĐ2 ở f = 0,01% (phần w₀ lớn đã xong 17/10).
- B: bộ phát hiện sớm tường (khoảng trống D): sinh dữ liệu có nhãn, so dò theo ngày (3σ, bài gốc) với theo giờ, đo thời gian báo trước `t_0` và báo động giả; nối với cảnh báo/trần động.
- C: LP cũng nhận điểm (Binance Alpha Earn Hub) → `c_V` hiệu dụng giảm.
- D: giá tham chiếu ngoài như một biện pháp (độ sâu tối thiểu làm tấn công thất bại).
- E: kiểm chứng trên log BSC thật của 1–2 vụ.
- G (thêm 22/10, từ tổng quan tài liệu `../review/trung_huong_RQ123/ap_dung.md`): phạt rút thanh khoản sớm, phần phạt chia cho LP còn trong dải (theo OpenZeppelin `LiquidityPenaltyHook`, mã MIT). Ước thô: phí của tường cùng bậc `attacker_profit_excess`; tường sống ~120 bước nên cửa sổ phải cỡ 5–7 ngày. Chưa cài, chờ Đức quyết.

### Mốc hạn
- 01/11: GĐ1 trọn vẹn (**đã đạt sớm**).
- 15/11: báo cáo nền tảng CLMM (A).

### Cải tiến F và G (22/10/2026)

Bộ quét: `quet_gd2 --F --phien v5` (21.000 lượt) và `--phat --phien v5` (3.600 lượt); bảng `ket_qua/gd2/bang_GF/` (`python -m metrics.chay_GF`). G (phạt rút sớm, D = 168): không đổi lợi tăng thêm, khối lượng, trợ cấp, độ sập; trích của tường trung vị 810 / 589 token1 (toàn tri / thích nghi, 3–4% lãi tổng); lợi ròng nạn nhân +471 / +309 (toàn tri −20 → +341, thích nghi −275 → 0); D = 336: trích 1.827 / 1.283. Né: rút 10 lát → phần nạn nhân nhận thêm còn 132 / 222; giữ tường đủ 168 giờ → không bị phạt, lãi tổng còn +6–10% (không tính chi phí vốn), nền tảng trả thêm 46–47% trợ cấp. Cách né thứ ba, thu phí (`collect`) trước khi `burn`, từng lấy lại 100% phí (Hoàng báo 26/10); engine đã chặn (26/10) bằng cách giữ phí chưa xét phạt tới khi vị thế đủ tuổi; kẻ tấn công trong mô phỏng luôn burn trước nên mọi số G trên không đổi, lợi ròng nạn nhân là quyền nhận phí (một phần còn bị giữ lúc kết thúc). F (cận trên, chọn m theo trung vị lợi tăng thêm): không biện pháp, tường mỏng hơn đưa lợi toàn tri 361 → 898; dưới biện pháp kẻ tấn công chủ yếu chọn m = 0,25–0,5; toàn tri: warn15 −94 → −41%, cap50 −100 → −50%, warn40 −100 → −91%, cap05 vẫn −100%; thích nghi: warn40 −94 → −72%, cap05 −65 → −51%; thứ tự gần như giữ (warn40, cap05 đầu; trả trễ cuối); warn40 giờ mất 7–11% khối lượng. Chọn theo lãi tổng: m = 4 ở 5–13/30 vụ (không tính chi phí vốn) → không dùng.


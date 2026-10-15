# 8. Phân bổ phí theo độ rộng (RQ3) — bản nháp

> Bản nháp của B, 15/10/2026.
>
> **Dữ liệu:** `ket_qua/gd3/tomtat.csv`, 1.920 lượt:
> - 16 mức φ: α = 0 (pro-rata) + α ∈ {0,5; 1; 1,5; 2; 3} × w₀ ∈ {10, 50, 200} tick, với φ(w) = min(1, (w/w₀)^α).
> - 6 vụ: L27_10/22/16 (k = 0,64 / 0,80 / 0,95) và KN_L27_10/22/16 (k = 0,10 / 0,25 / 0,45).
> - 2 loại victim × 10 seed.
>
> Victim chi phí **theo vốn**, tự chọn w* = argmax φ(w)·ℓ(w) trên lưới {1, …, 200}, dải căn giữa tick tường. Hai LP lành mạnh vốn 1.000 token1 ở pha bình thường: `lp:0` tự chọn w, `lp:1` cố định 10 tick.
>
> **Lệnh:** bảng `python -m metrics.chay_gd3` (≈ 15 s) → `ket_qua/gd3/bang/`; hình `python -m plots.ve_gd3` → `ket_qua/gd3/hinh/`.
>
> **So sánh:** mỗi mức φ ghép cặp với pro-rata cùng vụ + seed + loại victim; CI 95% bootstrap theo seed (mỗi nhóm một vụ). Tỷ lệ vốn C_RA/C_PR là tỷ số trung bình cặp của `von_victim`. Thiệt hại `vl_loss_full` chỉ so trên cặp cùng sập (290/1.920 lượt không sập, chủ yếu L27_22/KN_L27_22 sập nông). Lãi/lỗ victim chính dùng `vl_lai_tien` (= nhận lại + phí − nạp), đo được cả khi không sập.

## 8.1 Kết quả chính (tường một tick — trước khi kẻ tấn công nới tường, xem 8.3)

1. **Victim chọn độ rộng đúng như giải tích.**
   - α = 0,5: victim ở lại một tick.
   - α ≥ 1: victim nhảy thẳng tới w* = w₀ ở mọi lượt (`w_victim` = w₀).
   - Ngưỡng α* ≈ 1 của C được xác nhận: φ phải ít nhất tuyến tính.
2. **Range-aware KHÔNG cắt được phần vốn victim nằm trên đường sập.** Phần vốn bị cú sập quét qua là 0,50–0,55 ở mọi w ≤ 200, giống pro-rata (0,50), vì cú sập sâu hàng trăm–nghìn tick ≫ w/2.
3. **Kênh tác động thật là lượng vốn victim bỏ vào** (bảng `gon.csv`, hình `ban_do_vung.png`). Ở α ≥ 1,5:

| k (vụ) | C_RA/C_PR toàn tri | C_RA/C_PR thích nghi | % đổi dc_excess toàn tri | % đổi dc_excess thích nghi |
|---|---|---|---|---|
| 0,10 (KN_L27_10) | 0,17–0,68 | 0,15–0,63 | −6 … −75 | +3 … −61 |
| 0,25 (KN_L27_22) | 0,21–0,81 | 0,16–0,67 | +15 … −27 | +2 … +21 |
| 0,45 (KN_L27_16) | 0,35–1,07 | 0,20–0,73 | +1 … −64 | −3 … −66 |
| 0,64 (L27_10) | 0,56–1,56 | 0,24–0,83 | +20 … −57 | −27 … −79 |
| 0,80 (L27_22) | 0,98–2,70 | 0,24–0,89 | +111 … −8 | +10 … −36 |
| 0,95 (L27_16) | **4,5–10,4** | 0,28–0,90 | **+277 … +736** | −11 … −69 |

   - **Victim toàn tri ở vùng RQ1 (k ≥ 0,64): range-aware hút victim vào nhiều hơn**, gấp tới 10 lần ở k = 0,95. Lý do: tường một tick bị phạt φ(1) = w₀^(−α) nên nhường phí cho victim, mà victim dải rộng không bị phạt. Lợi kẻ tấn công tăng theo, từ 78 lên 300–650 token1.
   - **Vùng victim lớn (k ≤ 0,45): range-aware giảm vốn victim 20–85%** và giảm lợi kẻ tấn công tới 75%.
   - **Victim thích nghi luôn giảm vốn** (0,15–0,90×), vì V̂ ước từ phí thực nhận, mà phí này co lại khi victim trải rộng.
   - α = 1 là trường hợp biên: tỷ lệ 0,80–1,04 ở mọi vụ, riêng k = 0,95, w₀ = 200 thì victim rút hẳn (tỷ lệ 0).
4. **Lãi/lỗ victim** (hình `theo_alpha.png`):
   - Victim nhìn chung đỡ lỗ hơn ở α ≥ 2: +500…+7.800 token1, nhiều nhất k = 0,64 thích nghi.
   - Ngoại lệ k = 0,10 toàn tri, α = 1,5: victim lỗ thêm 1.900–4.100. Vốn victim giảm thì cú sập sâu hơn (độ sập từ −22% xuống −50%, chạm sàn z̄), nên phần vốn còn lại mất nhiều hơn.
5. **Cái giá với LP lành mạnh** (hình `lp_lanh_manh.png`; trung vị qua 6 vụ × 2 victim):
   - LP tự chọn w: phí/vốn −18…−24% ở α = 0,5 (bị phạt khi ở một tick), +5% (w₀ = 10) tới +44…+77% (w₀ = 50/200) ở α ≥ 1.
   - LP dải cố định 10 tick: −4% với w₀ = 10, nhưng −51…−100% với w₀ = 50/200 — mất gần hết phí.
   - Trượt giá của lệnh mua 1.000 token1 giảm nhẹ (−1,6…−8%). Tổng khối lượng gần như không đổi (|Δ| < 1%).

## 8.2 Đối chiếu giải tích (`doi_chieu_giai_tich.csv`)

Công thức của C (`agents.do_rong.ty_le_von`): C_RA/C_PR = (√(u/k) − u)/(1/√k − 1), với

u = [ℓ(1)/(φ(w*)·ℓ(w*))]·[(L_A·φ(1) + B)/(L_A + B)]

trong đó ℓ là L trên mỗi token1 vốn, theo hình học CLMM thật. B = 215.000 là L của LP nền phủ tick tường, đo từ log (`nen_tuong.csv`). Với w* = w₀ thì u trùng công thức gọn u ≈ w₀^(1−α) + w₀·B/L_A (lệch < 0,4%).

- **Victim toàn tri, 90 ô (6 vụ × 15 mức φ):**
  - Hướng thay đổi (giảm / không đổi / tăng, ngưỡng ±1%) khớp **89/90**.
  - Sai số tương đối của tỷ lệ vốn: trung vị **0,15%**, lớn nhất **4,3%** (L27_16, k = 0,95, α = 1,5, tỷ lệ ≈ 10). Ở k sát 1, mẫu số 1/√k − 1 nhỏ nên rất nhạy.
  - Ô lệch duy nhất: L27_22, α = 3, w₀ = 50. Giải tích cho 0,997 ("không đổi"), mô phỏng 1,020 ("tăng") — sát biên.
- **Vùng giảm vốn:** u < (1/√k − 1)² hoặc u > 1. Với k < 1/4, mọi u < 1 đều thỏa, nên range-aware gần như luôn giảm vốn victim. Với k ≥ 0,64, ngưỡng (1/√k − 1)² ≤ 0,06, nên cần α đủ lớn (α = 3, w₀ = 10: u = 0,015) mới giảm; α = 1,5–2 rơi vào vùng tăng.
- **Victim thích nghi** không có công thức (V̂ phụ thuộc phí thực nhận); mô phỏng luôn giảm vốn.

## 8.3 Kẻ tấn công nới tường (phản ứng tối ưu)

**Dữ liệu và cách chọn w_A.** `tomtat_wA.csv` có 4.440 lượt: α ∈ {1,5; 2; 3} × w₀ × w_A ∈ {1, w₀/4, w₀/2, w₀} × 6 vụ × 2 victim × 10 seed, cộng pro-rata. Với mỗi (vụ, α, w₀, victim), kẻ tấn công chọn **một** w_A có trung vị `dc_excess` qua 10 seed lớn nhất (`wA_toi_uu.csv`, `gon_wA.csv`). Chọn riêng từng seed (`*_theo_seed.csv`) thiên lệch lên không đáng kể: % đổi `dc_excess` cao hơn trung vị 0,2 điểm (lớn nhất 10 điểm); tỷ lệ vốn lệch trung vị 0,013.

Hình: `theo_wA.png` (vốn victim và `dc_excess` theo w_A/w₀, α = 2), `so_sanh_wA.png` (tường 1 tick so với tường tối ưu). Bảng: `so_sanh_wA.csv`.

**w_A tối ưu thường là w₀/4–w₀/2, không phải w₀.** Nới hết cỡ (w_A = w₀) thì né được phạt φ nhưng làm tường loãng, nên cú xả kém hiệu quả. Ở k = 0,95 với w₀ = 200, nới hết cỡ còn đuổi victim đi hẳn (tỷ lệ vốn 0,01).

**Bảng 8.2 — tường 1 tick so với tường tối ưu** (α ≥ 1,5; 9 mức φ mỗi ô; "đáng kể" = CI 95% bootstrap cặp với pro-rata không chứa 0 hoặc 1). Hiệu lãi victim tính bằng token1; dương là victim đỡ lỗ.

| k | Victim | Vốn: tường 1 tick | Vốn: tường tối ưu | dc_excess: tường 1 tick | dc_excess: tường tối ưu (giảm/tăng đáng kể) | Lãi victim, tường tối ưu (tốt/xấu đáng kể) |
|---|---|---|---|---|---|---|
| 0,10 | toàn tri | 0,17–0,68 | 0,71–1,01 | −75…−6% | −28…−3% (8/0) | −14.235…+133 (0/8) |
| 0,10 | thích nghi | 0,15–0,63 | 0,58–0,83 | −61…+3% | −1…+10% (0/7) | +271…+4.134 (7/0) |
| 0,25 | toàn tri | 0,21–0,81 | 0,75–1,00 | −27…+15% | +8…+20% (0/9) | +534…+1.448 (9/0) |
| 0,25 | thích nghi | 0,16–0,67 | 0,56–1,02 | +2…+21% | +13…+22% (0/9) | +1.435…+2.892 (8/0) |
| 0,45 | toàn tri | 0,35–1,07 | 1,02–1,13 | −64…+1% | −15…+4% (7/0) | −440…+459 (2/2) |
| 0,45 | thích nghi | 0,20–0,73 | 0,81–1,00 | −66…−3% | −7…0% (5/0) | −2.291…+561 (2/7) |
| 0,64 | toàn tri | 0,56–1,56 | 1,47–1,57 | −57…+20% | −3…+20% (1/6) | −708…−247 (0/9) |
| 0,64 | thích nghi | 0,24–0,83 | 0,80–1,01 | −79…−27% | −43…−24% (9/0) | −115…+2.329 (8/1) |
| 0,80 | toàn tri | 0,98–2,70 | 2,40–2,70 | −8…+111% | +79…+111% (0/9) | +199…+755 (5/0) |
| 0,80 | thích nghi | 0,24–0,89 | 0,82–1,03 | −36…+10% | +6…+17% (0/9) | +239…+1.267 (8/0) |
| 0,95 | toàn tri | 4,5–10,4 | 10,1–10,6 | +277…+736% | +610…+740% (0/9) | −435…−143 (0/0) |
| 0,95 | thích nghi | 0,28–0,90 | 0,95–1,02 | −69…−11% | −26…−5% (9/0) | −482…+359 (2/3) |

Mức gốc pro-rata (trung vị): `dc_excess` = 9.318 / 737 / 1.175 / 1.949 / 347 / 78 token1 (toàn tri, k tăng dần).

**Đối chiếu giải tích của C cho tường tối ưu.** Công thức: C_RA/C_PR = 1/(4k(1/√k − 1)) khi k ≥ 1/4, và ≈ 1 khi k < 1/4.
- Victim toàn tri khớp trong ±10% ở **46/54 ô**.
  - k ≥ 0,45: khớp 36/36. Sai số tương đối trung vị: k = 0,45 → 0,0%; 0,64 → −1,7%; 0,80 → +1,1%; 0,95 → +2,8%. Ví dụ k = 0,64 cho 1,47–1,57 so với giải tích 1,56.
  - k = 0,25: khớp 7/9. k = 0,10: chỉ 3/9; mô phỏng 0,71–1,01, giải tích 1, sai số trung vị −14%, lớn nhất −29%.
- Lý do lệch ở k nhỏ: giải tích giả định kẻ tấn công né hết phạt (w_A = w₀). Kẻ tấn công thật tối đa `dc_excess` nên dừng ở w_A < w₀, vẫn chịu một phần phạt.

**Trả lời câu hỏi then chốt.**
- **Vùng k nhỏ:** tác dụng của range-aware gần như mất hết khi kẻ tấn công nới tường tối ưu.
  - k = 0,10, toàn tri: vốn victim chỉ còn giảm 0–29% (từ 32–83% khi tường 1 tick). `dc_excess` giảm 3–28% (đáng kể 8/9 ô). Nhưng victim **lỗ thêm** 3–14 nghìn token1 (đáng kể 8/9), vì cú sập sâu hơn 8–26 điểm %.
  - k = 0,10, thích nghi: vốn giảm 17–42% và victim đỡ lỗ, nhưng `dc_excess` không giảm (−1…+10%).
  - k = 0,25: `dc_excess` **tăng** 8–22% ở cả hai loại victim (đáng kể 18/18 ô), dù victim cũng đỡ lỗ.
- **Vùng RQ1, victim toàn tri:** range-aware **vẫn hút victim** đúng mức giải tích (1,5× / 2,6× / 10× ở k = 0,64 / 0,80 / 0,95; tăng đáng kể 27/27 ô). `dc_excess` tăng +79…+111% ở k = 0,80 và +610…+740% ở k = 0,95.
- **Victim thích nghi:** khi tường tối ưu, vốn gần như về mức pro-rata (0,80–1,03 ở k ≥ 0,45). `dc_excess` giảm đáng kể ở k = 0,64 (−24…−43%, 9/9 ô) và k = 0,95 (−5…−26%, 9/9 ô), nhưng tăng ở k = 0,25 và 0,80 (+6…+22%).

## 8.4 Kết luận RQ3

- **Range-aware đổi được cách victim chọn độ rộng (α* ≈ 1), nhưng không đổi được rủi ro của victim.** Phần vốn victim bị cú sập quét qua vẫn ≈ 0,5, vì cú sập sâu hơn nhiều so với dải.
- **Tác dụng duy nhất là qua phí tường bị phạt, và kẻ tấn công vô hiệu hóa được bằng cách nới tường.**
  - Khi kẻ tấn công nới tường tối ưu (w₀/4–w₀/2), vùng victim lớn mất gần hết lợi ích. Vốn victim chỉ còn giảm ≤ 30%, và lợi tăng thêm của kẻ tấn công không giảm ổn định: −28% ở k = 0,10 toàn tri, +8…+22% ở k = 0,25.
  - Vùng tường chiếm ưu thế (k ≥ 0,64) thì vẫn bị hút victim vào đúng như giải tích (tới 10×), lợi kẻ tấn công tăng tới 7–8 lần.
- **Victim thích nghi được bảo vệ phần nào ở k = 0,64 và 0,95** (lợi kẻ tấn công −5…−43%), nhưng không nhất quán theo k.
- **Cái giá không nhỏ:** LP dải hẹp cố định mất 50–100% phí khi w₀ ≥ 50.
- **Kết luận:** range-aware với φ dạng lũy thừa không phải biện pháp chống tấn công tường thanh khoản đáng tin cậy. Ở GĐ2, cảnh báo rủi ro (tăng c_V) có biên đánh đổi tốt hơn hẳn.

## 8.5 Giới hạn

- **Cú sập ≫ w:** w₀ ≤ 200 tick quá nhỏ so với cú sập 600–5.000 tick. Muốn cắt phần vốn trên đường sập cần w₀ ≳ 1.000 tick; chưa quét.
- **Luật chọn w bỏ qua biến động:** victim và LP chọn w* = argmax φ·ℓ, không tính rủi ro giá ra khỏi dải hay thời gian trong dải. LP thật sẽ chọn hẹp hơn khi biến động thấp, nên mức trải rộng (và cái giá với LP) có thể bị ước cao.
- **Victim toàn tri rút giữa hai bước xả:** victim chỉnh L mỗi bước, nên có thể rút ngay sau bước xả đầu. Thiệt hại khi đó phụ thuộc lịch xả 2 bước, và có thể khác nếu kẻ tấn công xả trong một bước.
- **Trượt giá LP (`lp*_truot`) là của cả bể, đo ở pha bình thường trước khi có tường.** Nó không đo thanh khoản lúc tấn công. Mức giảm 2–8% chỉ phản ánh LP lành mạnh trải rộng hơn trong bể nền.
- **Khối lượng farmer không đổi theo độ sâu thanh khoản**, vì trần Q ràng buộc (farmer mua tới trần bất kể L). Range-aware không có kênh làm đổi khối lượng: tổng khối lượng |Δ| < 1%.
- **Chỉ 6 vụ, lưới w_A 4 mức.** CI chỉ phản ánh biến thiên theo seed. Tỷ lệ 0,01 ở L27_16 khi w_A = w₀ = 200 là victim rút hẳn.
- **KN_L27_22 (k = 0,25, sập nông): vốn victim giảm mà `dc_excess` lại tăng 2–22% — đã kiểm log, không phải lỗi.** C xác nhận phản thực bán thẳng đúng: `dc_ban_thang` trùng tới từng số giữa α = 0 và α = 2/w₀ = 50 (seed 0–3: 14.347 / 14.085 / 13.880 / 13.946). Cơ chế: kẻ tấn công xả 2 bước × 7.500 token0. Sau khi tường rút, victim toàn tri chỉ còn thấy nền nên mục tiêu L ≈ 0, và rút phần còn lại ở t_rut + 1. Vì vậy phần victim bị lấy bị chặn bởi lượng xả mỗi bước, không bởi vốn victim. Với cú sập nông và kho nhỏ, `dc_excess` gần như không đổi theo vốn victim. Mức +2…+22% là nhiễu cộng với chênh giá nhỏ của dải rộng: trong 25 tick chênh giá chỉ ≈ 0,25%, nên giả thuyết "nửa dải dưới bán được giá cao" chỉ đúng một phần. Hệ quả: ở vụ sập nông, vốn victim không phải biến quyết định lợi kẻ tấn công.

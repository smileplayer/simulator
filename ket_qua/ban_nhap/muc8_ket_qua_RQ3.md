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

## 8.1 Kết quả chính

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

## 8.3 Kết luận RQ3

- Range-aware làm victim trải rộng như kỳ vọng (α* ≈ 1), nhưng **không** giảm được phần vốn bị cú sập quét qua, vì cú sập sâu hơn nhiều so với độ rộng dải. Tác động thật đi qua lượng vốn victim bỏ vào.
- Với victim định giá đúng theo trần, range-aware chỉ có lợi ở vùng victim lớn (k < 1/4: vốn −20…−85%, lợi kẻ tấn công giảm tới 75%). Ở vùng tường chiếm ưu thế (k ≥ 0,64), phạt tường một tick lại nhường phí cho victim, hút victim vào nhiều hơn (tới 10×) và làm lợi kẻ tấn công tăng tới 8 lần.
- Victim ước khối lượng từ phí thực nhận thì luôn bỏ ít vốn hơn.
- Cái giá chính đổ lên LP lành mạnh dải hẹp cố định: mất 50–100% phí khi w₀ ≥ 50.
- Kết luận phụ thuộc mạnh vào k, nên muốn dùng range-aware phải biết bể nằm ở vùng nào.

## 8.4 Giới hạn

- **Cú sập ≫ w:** w₀ ≤ 200 tick quá nhỏ so với cú sập 600–5.000 tick. Muốn cắt phần vốn trên đường sập cần w₀ ≳ 1.000; chưa quét.
- **Luật chọn w bỏ qua biến động:** victim chọn w* = argmax φ·ℓ, không tính rủi ro giá ra khỏi dải và thời gian trong dải. LP thật sẽ chọn hẹp hơn khi biến động thấp.
- **Kẻ tấn công chưa được nới tường** trong `tomtat.csv`: tường vẫn một tick, chịu phạt φ(1). Phản ứng tối ưu tự nhiên là nới tường để né phạt. C đang chạy `tomtat_wA.csv` (w_A ∈ {1, w₀/4, w₀/2, w₀}). `metrics.chay_gd3` đã có sẵn bước chọn w_A tối ưu theo `dc_excess` → `wA_toi_uu.csv`, `gon_wA.csv`, đối chiếu giải tích của C: C_RA/C_PR = 1/(4k(1/√k − 1)) khi k ≥ 1/4 (k = 0,64 → 1,56×; 0,80 → 2,63×; 0,95 → 9,9×), ≈ 1 khi k < 1/4.
- **Chỉ 6 vụ.** CI chỉ phản ánh biến thiên theo seed, không theo vụ.
- **Bất thường chưa giải thích hết:** ở KN_L27_22 (k = 0,25, sập nông) vốn victim giảm 19–84% mà `dc_excess` lại tăng 2–21%. Giả thuyết: victim dải rộng có nửa dải dưới (token1) nằm ngay dưới giá, nên cú xả bán được nhiều token1 ở giá cao hơn so với khi victim dồn trong một tick. Cần xem log.

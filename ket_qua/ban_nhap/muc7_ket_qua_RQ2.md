# 7. Đánh giá biện pháp giảm thiểu (RQ2) — bản nháp

> Bản nháp của B, 15/10/2026. Số liệu: `ket_qua/gd2/tomtat_v2.csv` (4.200 lượt = 30 cấu hình × 7 biện pháp × 2 loại victim × 10 seed) và `ket_qua/gd2/tomtat_farm_v2.csv` (10.800 lượt, kẻ tấn công farm 0 / 0,3 / 0,6 khối lượng farmer). Bảng: `python -m metrics.chay_gd2` (≈ 75 s) → `ket_qua/gd2/bang/`; hình: `python -m plots.ve_gd2` (≈ 3 s) → `ket_qua/gd2/hinh/`.
>
> **Phương pháp so sánh.** Mỗi lượt có biện pháp được ghép với lượt `khong` cùng cấu hình + seed + loại victim (+ phần farm). Hai lượt dùng chung chuỗi ngẫu nhiên (CH-8), nên hiệu cặp chỉ còn tác động của biện pháp. Báo hai số: (i) **trung vị hiệu cặp** (đơn vị gốc); (ii) **% thay đổi** = (TB có biện pháp − TB gốc)/|TB gốc| trên cùng tập cặp. CI 95% = bootstrap cặp phân cụm theo cấu hình (2.000 lần). **Cặp không sập:** lợi nhuận, thiệt hại và thanh khoản Post chỉ đo được khi giá sập ≥ 10% (suy vai theo §5 bài gốc). Vì vậy các chỉ số này so trên cặp **cả hai cùng sập**, và số cặp bị loại ghi cạnh từng bảng. Tỷ lệ sập được báo riêng.
>
> **Lợi của kẻ tấn công** = `excess` (lợi nhuận trừ phương án bán thẳng kho, Theorem 6) + lãi farm đã nhận (`farm_pnl`) + thưởng treo chưa tới hạn (`farm_pending`, cùng quy ước với chi phí trợ cấp CH-2). Bản không tính phần treo nằm ở cột `loi_tan_cong`. Bản này chỉ khác đáng kể ở biện pháp trả trễ 168 bước.

## 7.1 Kết quả chính

1. **Hạ trần `Q` là biện pháp duy nhất cắt được thiệt hại, nhưng phải trả bằng khối lượng gần như tương ứng.** Victim toàn tri: hạ trần còn 75% đã giảm 80% thiệt hại và 75% lợi kẻ tấn công, đổi lại mất 13% khối lượng. Từ trần 50% trở xuống, thiệt hại về 0 (victim không vào). Victim thích nghi: giảm ít hơn hẳn với cùng mức mất khối lượng (cap75: −10% thiệt hại, CI vắt qua 0; cap25: −59% thiệt hại, mất 40% khối lượng).
2. **Trả trễ với farmer thuần gần như vô tác dụng lên tấn công.** delay24/72 làm thiệt hại thay đổi +0,6…+3,5% và lợi kẻ tấn công ≈ 0%. Tác dụng duy nhất là giảm chi phí trợ cấp 6–21%. Riêng delay168 với victim thích nghi giảm thiệt hại 24% (CI −49…−1%). Hiệu này nằm trọn ở các cấu hình σ = 0,005: chiết khấu 0,995¹⁶⁸ = 0,43 kéo σ hiệu dụng xuống dưới ngưỡng σ₀, farmer gần như ngừng giao dịch (khối lượng farmer còn 7–21%). Đây là **hạ σ trá hình**, không phải cơ chế nhắm vào kẻ tấn công. Trung vị hiệu cặp là 0.
3. **Khi kẻ tấn công cũng farm (mô hình pressure trader), trả trễ + thu hồi cắt mạnh lợi kẻ tấn công mà tốn rất ít khối lượng.** Với phần farm 0,6: claw72 giảm lợi kẻ tấn công 48–52% và chỉ mất 3,6% khối lượng; claw168 giảm 74–77% nhưng mất 25% khối lượng. delay72 không thu hồi chỉ giảm 10–12%. Thu hồi **không** đổi thiệt hại victim, vì victim quyết theo phí chứ không theo thưởng. Thiệt hại victim của claw = delay ở mọi cặp.
4. **Không biện pháp nào làm giá thôi sập.** Hạ trần còn làm tỷ lệ sập ≥ 10% *tăng* (victim thích nghi 88% → 92/94/96% ở cap75/50/25), vì thanh khoản trong tick tường mỏng hơn. Độ sập trung bình cũng sâu hơn 1–3 điểm %.

**Bảng 7.1.** % thay đổi so với không biện pháp [CI 95%], trợ cấp tuyến tính + log (`ket_qua/gd2/bang/gon.csv`). Thiệt hại và lợi so trên cặp cả hai sập: toàn tri 295 cặp (loại 5), thích nghi 265 (loại 35).

| Victim | Biện pháp | Thiệt hại victim | Lợi kẻ tấn công | Sập (điểm %) | Khối lượng | L Post | Trợ cấp |
|---|---|---|---|---|---|---|---|
| toàn tri | cap75 | −79,8 [−91; −72] | −74,9 [−85; −66] | +1,7 [0; +4] | −12,7 | −11,1 | −21,0 |
| toàn tri | cap50 | −100 | −93,7 [−99; −89] | +1,7 | −25,8 | −14,9 | −43,7 |
| toàn tri | cap25 | −100 | −96,4 [−102; −92] | +1,7 | −38,9 | −18,4 | −69,4 |
| toàn tri | delay24 | +0,6 [+0,2; +1,1] | −0,2 | 0 | −1,0 | −1,6 | −7,3 |
| toàn tri | delay72 | +2,0 [+0,9; +3,5] | −0,7 | 0 | −2,7 | −3,6 | −21,4 |
| toàn tri | delay168 | −2,4 [−8; +3] | −6,2 [−11; −3] | +1,0 | −18,1 | −7,0 | −45,4 |
| thích nghi | cap75 | −10,5 [−26; +8] | −15,5 [−25; −4] | +3,7 [+0,3; +7,7] | −12,9 | −8,2 | −21,2 |
| thích nghi | cap50 | −40,0 [−55; −18] | −42,6 [−57; −26] | +5,3 [+0,7; +10] | −26,2 | −15,2 | −44,2 |
| thích nghi | cap25 | −59,4 [−74; −39] | −61,4 [−75; −44] | +7,3 [+1,7; +13] | −39,6 | −24,1 | −70,0 |
| thích nghi | delay24 | +1,4 [+0,5; +2,3] | +0,2 | 0 | −1,1 | −1,2 | −5,8 |
| thích nghi | delay72 | +3,5 [+1,1; +7,2] | +0,1 | 0 | −3,0 | −2,9 | −17,0 |
| thích nghi | delay168 | −24,3 [−49; −1] | −22,2 [−43; −6] | +4,7 [+0,7; +9,3] | −18,7 | −9,2 | −38,1 |

Mức gốc (trung vị, không biện pháp): thiệt hại victim 171 (toàn tri) / 1.022 (thích nghi) token1; `excess` 299 / 2.503; lợi nhuận "paper" 14.532 / 23.645 (phần lớn là bán kho vào nền, không phải bóc victim — mục 6); trợ cấp 4.678 / 4.807; tổng khối lượng ≈ 1,5 triệu token1.

**Bảng 7.2.** Trả trễ khi kẻ tấn công farm 60% khối lượng farmer (`gon_farm.csv`). Lợi = excess + farm + treo, so với `khong` cùng phần farm (gốc: 4.939 toàn tri / 6.022 thích nghi; lãi farm gốc ≈ 2.515).

| Victim | Biện pháp | Lợi kẻ tấn công | Lãi farm (token1, trung vị hiệu) | Thu hồi (token1) | Khối lượng | Trợ cấp | Thiệt hại victim |
|---|---|---|---|---|---|---|---|
| toàn tri | delay72 | −11,9% [−17; −9] | −698 | 0 | −3,6% | −17,3% | +6,8% |
| toàn tri | claw72 | −52,0% [−59; −45] | −2.254 | 1.452 | −3,6% | −37,6% | +6,8% |
| toàn tri | delay168 | −19,6% [−27; −13] | −2.531 (treo 2.025) | 0 | −24,5% | −37,7% | +15,5% [−8; +57] |
| toàn tri | claw168 | −73,9% [−83; −61] | −2.888 | 2.283 | −24,5% | −65,4% | +15,5% |
| thích nghi | claw72 | −47,6% [−55; −40] | −2.264 | 1.454 | −3,6% | −37,3% | +3,8% |
| thích nghi | claw168 | −77,0% [−84; −67] | −2.891 | 2.300 | −24,7% | −65,1% | −22,2% |

Với phần farm 0,3, thứ tự giữ nguyên nhưng mức nhỏ hơn: claw72 −40% (toàn tri) / −24% (thích nghi); claw168 −61% / −50%.

**Tách theo dạng trợ cấp** (`gon_theo_dang.csv`; log chỉ có 3 cấu hình × 10 seed nên CI rộng): kết luận không đổi. Trợ cấp log làm hạ trần mạnh hơn một chút về lợi kẻ tấn công (cap50 thích nghi −58% so với −41% tuyến tính), và trả trễ 168 với log gần như không tác dụng (−1%). Ba cấu hình log đều có σ ≥ 0,005 nhưng chỉ một ở 0,005, nên hiệu "hạ σ trá hình" yếu hơn.

## 7.2 `Q*` thực nghiệm (đối chiếu Theorem 6)

Theorem 6: tấn công có lợi hơn bán thẳng ⇔ `Q ≥ Q*`, và Π_A không giảm theo Q. Bài gốc không cho công thức đóng của `Q*`. Lemma 4 cho ngưỡng vào của victim: `Q_eff > c_V·L_A/(f·n)`, tức theo tỷ lệ trần `r = Q_eff/Q` thì victim toàn tri vào ⇔ `r > k`. Trong mô hình, khi không có victim thì không có lợi tăng thêm, nên `Q*/Q` ≥ ngưỡng vào của victim.

Với mỗi cấu hình × loại victim, mỗi mức trần r ∈ {1; 0,75; 0,5; 0,25}, lấy trung vị qua seed (chỉ lượt sập). Một mức được coi là "an toàn" khi thiệt hại victim ≤ 1 token1 (tiêu chí V) hoặc lợi kẻ tấn công ≤ 0 (tiêu chí A). `Q*/Q` nằm trong khoảng (mức an toàn cao nhất mà mọi mức thấp hơn cũng an toàn; mức kế trên]. Ngoài ra nội suy ngưỡng vào `r_V` từ `(1 + L_V/L_A)²`, đại lượng này tuyến tính theo r theo Lemma 4 (`q_sao_vu.csv`, `q_sao_tomtat.csv`, hình `q_sao.png`).

- **Victim toàn tri — khớp lý thuyết.** Khoảng `Q*_V/Q` chứa k ở **28/30** cấu hình: k = 0,64 → (0,5; 0,75] (10 cấu hình), k = 0,80/0,95 → (0,75; 1] (18 cấu hình). `r_V` nội suy = k, đúng tới 2 chữ số. Hai ngoại lệ (L27_04, L27_06: Q = 48k, σ ≤ 0,01) có thiệt hại 0 ngay khi không hạ trần, vì trần không ràng buộc (σ < σ_cap, vi phạm Giả định 1 của Theorem 6): farmer không đạt Q nên victim vào rất ít.
- **Victim thích nghi — lưới cap quá thô, và hạ trần nhiều khi không đủ.** 26/30 cấu hình vẫn có thiệt hại ở cap25 → `Q*/Q < 0,25`, 4 cấu hình ở (0,25; 0,5]. `r_V` nội suy tăng theo Q: Q = 12k → âm (−1,1…−0,7), 24k → −0,25…+0,06, 48k → 0,08…0,30. **18/30 cấu hình có `r_V ≤ 0`**: victim thích nghi ước lượng V̂ từ phí của *cả bể* (gồm arb + nền, không co theo trần), nên dù trần về 0 vẫn còn đủ phí để vào. Theorem 6 giả định victim biết V = Q; khi victim nhìn phí lịch sử, hạ trần không đóng được kênh nạp thanh khoản ở bể có khối lượng nền lớn so với Q.
- **Tiêu chí A (lợi ≤ 0) kém tin cậy hơn tiêu chí V.** `excess` còn nhiễu khi không có victim: trên 791 lượt toàn tri có L_V = 0, trung vị 0, tứ phân vị [0; 2,7], nhưng trải từ −961 tới +651 token1. Ở các cấu hình kho 15k, trung vị dương 10–360 token1, vì kẻ tấn công bán hết kho qua 2 bước có nhiễu giá/nền, còn phương án bán thẳng là tức thời. Vì vậy 10/30 cấu hình toàn tri có `Q*_A/Q` "dưới lưới" dù victim đã không vào từ cap50. Kết luận `Q*` dựa trên tiêu chí V (và tiêu chí gộp V hoặc A, trùng với V).
- **Tính đơn điệu (Theorem 6: Π_A không giảm theo Q):** lợi kẻ tấn công đơn điệu theo trần ở 27/30 cấu hình toàn tri, nhưng chỉ 21/30 thích nghi. Ngoại lệ thích nghi hầu hết ở Q = 12k (L27_00, 11, 13, 21, 26: lợi *tăng* nhẹ khi hạ trần), cùng nhóm có `r_V` âm.

**Đề xuất lưới mịn hơn:** victim toàn tri: r ∈ {k − 0,05; k; k + 0,05} quanh từng k (đã biết lý thuyết, chỉ cần xác nhận). Victim thích nghi: r ∈ {0,20; 0,15; 0,10; 0,05; 0} cho các cấu hình Q = 24k/48k, và cho Q = 12k thử cả "trần 0" để kiểm xem victim còn vào không.

## 7.3 Bản đồ `(σ, Q)` không biện pháp (`nhiet_sigma_Q.png`)

Mỗi ô 3×3 gộp 3 cấu hình của mảng trực giao L27 × 10 seed (trợ cấp tuyến tính, chỉ lượt sập). Không thấy xu hướng đơn điệu rõ theo σ hay Q. Ví dụ victim toàn tri: thiệt hại cao nhất ở (σ = 0,02; Q = 24k) = 451 nhưng thấp nhất ở (0,02; 48k) = 42. Lý do: trong L27, mỗi ô (σ, Q) đi kèm một tổ hợp riêng của L_A, k, kho, bg_band, và các yếu tố này lấn át. **Bản đồ này chưa phải bản đồ ba vùng thiết kế của bài gốc.** Muốn có, cần lưới (σ, Q) đầy đủ với các yếu tố khác cố định (xem 7.5).

## 7.4 Hình

- `ket_qua/gd2/hinh/danh_doi.png` — trục x: % mất khối lượng; trục y: % giảm thiệt hại victim (trái), % giảm lợi kẻ tấn công (phải). Màu = họ biện pháp, hình = loại victim, thanh = CI 95%.
- `ket_qua/gd2/hinh/danh_doi_farm.png` — như trên cho phần farm 0,3 / 0,6, thêm thu hồi.
- `ket_qua/gd2/hinh/nhiet_sigma_Q.png` — bản đồ nhiệt (σ, Q) của excess và thiệt hại victim, không biện pháp.
- `ket_qua/gd2/hinh/q_sao.png` — ngưỡng vào `r_V` theo Q, so với k (toàn tri) và lưới cap.

## 7.5 Giới hạn

- **Cặp không sập bị loại:** 5/300 (toàn tri) và 35/300 (thích nghi) cặp gốc không sập ≥ 10%. Các chỉ số lợi nhuận/thiệt hại chỉ so trên cặp cả hai sập. Biện pháp làm *tăng* tỷ lệ sập (hạ trần), nên tập cặp so sánh nghiêng về các lượt sập ở cả hai phía. Các lượt chỉ sập khi có biện pháp (thích nghi: 11/16/22 lượt ở cap75/50/25, 14 ở delay168; không có chiều ngược lại) không vào phép so lợi nhuận, nên % giảm thiệt hại của cap với victim thích nghi có thể bị ước *cao* một chút.
- **% thay đổi là tỷ số trung bình,** nhạy với cấu hình có giá trị lớn. Ở delay168 trung vị hiệu cặp = 0 trong khi % = −24%. Cả hai số đều có trong `danh_doi.csv` (cột `hieu`, `pct`).
- **`excess` nhiễu khi không có victim** (±vài trăm token1, xem 7.2). Phương án bán thẳng là `quote_swap` tức thời trên bể dựng lại, không phải một lượt chạy phản thực cùng seed.
- **Định nghĩa lãi farm khác của C:** `attacker_farm_pnl` (B) định giá lệnh mua ở bước xả theo P_e(t−1), còn `chi_phi_farm_att` (C) dùng P_e cùng bước, đã bị neo theo giá sau xả. Chi phí của C cao hơn trung vị 136 token1. Bảng này dùng bản B.
- Lưới cap 4 mức chỉ cho khoảng của `Q*`. Biện pháp cảnh báo (tăng c_V) và trần động chưa có trong dữ liệu `_v2`.

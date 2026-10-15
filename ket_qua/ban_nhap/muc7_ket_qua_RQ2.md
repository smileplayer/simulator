# 7. Đánh giá biện pháp giảm thiểu (RQ2) — bản nháp (v3)

> Bản nháp của B, 15/10/2026 (thay bản v2 cùng ngày). Dữ liệu `ket_qua/gd2/`:
> - `tomtat_v3.csv`: 9.600 lượt = 30 cấu hình vùng RQ1 (k ∈ {0,64; 0,80; 0,95}, victim nhỏ) × 16 biện pháp × 2 loại victim × 10 seed.
> - `tomtat_knho_v3.csv`: 6.000 lượt, vùng k nhỏ (k ∈ {0,10; 0,25; 0,45}, victim lớn, kẻ tấn công farm 30% khối lượng farmer) × 10 biện pháp.
> - `tomtat_farm_v3.csv`: 10.800 lượt, trả trễ/thu hồi × phần farm {0; 0,3; 0,6}.
> - `tomtat_luoi_v3.csv`: 1.000 lượt, lưới σ ∈ {0,0025 … 0,04} × Q ∈ {6k … 96k} quanh `co_so` (c_V cố định), không biện pháp + hạ trần 50%.
>
> Lệnh: bảng `python -m metrics.chay_gd2` (≈ 2 phút) → `ket_qua/gd2/bang/`; hình `python -m plots.ve_gd2` → `ket_qua/gd2/hinh/`. Bản v2 vẫn tái lập được: `--phien v2` → `bang_v2/`, `hinh_v2/`.
>
> **Phương pháp so sánh.** Mỗi lượt có biện pháp được ghép với lượt `khong` cùng cấu hình + seed + loại victim (+ phần farm). Hai lượt dùng chung chuỗi ngẫu nhiên. Báo hai số: (i) trung vị hiệu cặp; (ii) **% thay đổi** = (TB có biện pháp − TB gốc)/|TB gốc| trên cùng tập cặp. CI 95% = bootstrap cặp phân cụm theo cấu hình (2.000 lần).
>
> **Chỉ số lợi kẻ tấn công (v3) đo theo địa chỉ thật** của kẻ tấn công nên có cả khi giá không sập:
> - `dc_excess`: lợi nhuận tăng thêm so với phát lại log khi không có victim. Bằng 0 đúng khi không có victim; thay cho `excess` của v2, vốn nhiễu ±vài trăm token1.
> - `loi_tang_them` = `dc_excess` + lãi farm (`dc_farm_pnl`); bản `_treo` cộng thêm thưởng treo chưa tới hạn.
> - `dc_lai_tong` (gồm cả giá trị bán kho theo c_A) chỉ ghi trong bảng, không dùng làm chỉ số chính vì phần bán kho lấn át.
> - Thiệt hại victim (`victim_loss_full`) vẫn chỉ đo được khi sập ≥ 10%: so trên cặp cả hai cùng sập, loại 5/300 cặp (toàn tri) và 35/300 (thích nghi). Tỷ lệ sập báo riêng.

## 7.1 Kết quả chính

1. **Cảnh báo rủi ro (warn: c_V × 1,5/2/4) có biên đánh đổi tốt nhất.** Mất khối lượng chỉ 0,4–2,7%, mà vùng RQ1 cắt 94–100% lợi kẻ tấn công với victim toàn tri và 25/48/94% với victim thích nghi. Để đạt mức giảm tương đương, hạ trần phải mất 20–50% khối lượng. Ở vùng k nhỏ (victim lớn), warn40 vẫn giảm thiệt hại victim 43–65%, nhưng lợi kẻ tấn công chỉ giảm 13–37%.
2. **Hạ trần Q và trần động** nằm trên cùng một đường đánh đổi: trần động ≈ hạ trần cố định ở cùng mức mất khối lượng (~36–43%). Victim toàn tri: hạ trần tới r ≤ k thì lợi tăng thêm về 0, đúng Lemma 4. Victim thích nghi: cap05 (mất 49% khối lượng) chỉ giảm 62% lợi và 69% thiệt hại. Ở vùng k nhỏ, hạ trần với victim thích nghi gần như vô hiệu (cap50: lợi +4%, thiệt hại −12%).
3. **Trả trễ không thu hồi gần như vô tác dụng** (delay24/72: lợi kẻ tấn công +0,5…+1,9%, thiệt hại +0,6…+3,5%). Riêng delay168 với victim thích nghi giảm 18–24%, nhưng đó là "hạ σ trá hình": chiết khấu 0,995¹⁶⁸ = 0,43 làm farmer ở các cấu hình σ = 0,005 ngừng giao dịch.
4. **Trả trễ + thu hồi chỉ cắt phần lãi farm của kẻ tấn công.** Ở phần farm 0,6: claw72 giảm 52–54% lợi, chỉ mất 3,6% khối lượng; claw168 giảm 77–83% nhưng mất 25% khối lượng. Ở vùng k nhỏ: claw72 giảm 22–24%. Thu hồi không đổi hành vi victim: thiệt hại claw = delay, +2…+7%.
5. **Không biện pháp nào làm giá thôi sập.** Biện pháp nào làm victim nhỏ đi đều làm tỷ lệ sập ≥ 10% *tăng* (thích nghi: cap05 +10 điểm %, warn40 +11 điểm %), vì tick tường mỏng hơn.

**Bảng 7.1 — vùng RQ1** (`gon.csv`): % thay đổi so với không biện pháp [CI 95%]. Mức gốc (trung vị): lợi tăng thêm 347 (toàn tri) / 1.913 (thích nghi) token1; thiệt hại 171 / 1.022; khối lượng ≈ 1,5 triệu; trợ cấp ≈ 4.700.

| Nhóm | Biện pháp | Lợi tăng thêm: toàn tri | Lợi tăng thêm: thích nghi | Thiệt hại: toàn tri | Thiệt hại: thích nghi | Sập (điểm %, thích nghi) | Khối lượng | Trợ cấp |
|---|---|---|---|---|---|---|---|---|
| hạ trần | cap90 | −38 [−48; −31] | −2 [−5; +2] | −39 | −4 | +0,7 | −5 | −8 |
| | cap75 | −80 [−90; −71] | −8 [−15; +3] | −80 | −11 | +3,7 | −13 | −21 |
| | cap50 | −100 | −27 [−38; −13] | −100 | −40 | +5,3 | −26 | −44 |
| | cap25 | −100 | −51 [−67; −31] | −100 | −59 | +7,3 | −40 | −70 |
| | cap05 | −100 | −62 [−79; −41] | −100 | −69 | +10,3 | −49 | −94 |
| trả trễ | delay72 | +1,2 | +1,9 | +2,0 | +3,5 | 0 | −3 | −17 |
| | delay168 | −3 [−8; +1] | −18 [−39; −1] | −2 | −24 | +4,7 | −19 | −38 |
| cảnh báo | warn15 | −94 [−97; −92] | −25 [−32; −15] | −95 | −34 | +3,7 | −0,6 | −1 |
| | warn20 | −99 | −48 [−57; −37] | −100 | −54 | +7,0 | −1,2 | −2 |
| | warn40 | −100 | −94 [−98; −88] | −100 | −95 | +11,3 | −2,3 | −3 |
| trần động | dyncap | −100 | −53 [−68; −33] | −100 | −60 | +7,3 | −36 | −60 |

**Bảng 7.2 — vùng k nhỏ, kẻ tấn công farm 0,3** (`gon_knho.csv`; tách theo k: `gon_knho_theo_k.csv`). Mức gốc: lợi tăng thêm 3.051 / 3.190; thiệt hại 1.219 / 1.985.

| Biện pháp | Lợi: toàn tri | Lợi: thích nghi | Thiệt hại: toàn tri | Thiệt hại: thích nghi | Khối lượng |
|---|---|---|---|---|---|
| cap50 | −17 [−31; 0] | +4 [−5; +16] | −32 | −12 | −28 |
| cap25 | −51 [−63; −35] | −3 [−14; +11] | −66 | −20 | −45 |
| cap10 | −78 [−83; −71] | −19 [−32; −5] | −94 | −29 | −54 |
| dyncap | −57 [−69; −43] | −8 [−19; +5] | −66 | −20 | −42 |
| delay72 | −5 | −5 | +3 | +2 | −3 |
| claw72 | −24 [−29; −18] | −22 [−28; −16] | +3 | +2 | −3 |
| warn15/20/40 | −8 / −13 / −37 | −2 / −3 / −13 | −21 / −36 / −65 | −13 / −20 / −43 | −0,4…−2 |

**Bảng 7.3 — trả trễ khi kẻ tấn công farm 0,6** (`gon_farm.csv`, lợi tính cả treo): delay72 −11%, claw72 −52…−54%, delay168 −18…−26% (−71…−78% nếu không tính treo, vì thưởng chỉ bị hoãn), claw168 −77…−83%. Khối lượng mất lần lượt −3,6 / −3,6 / −25 / −25%.

**Hình 7.1** `ket_qua/gd2/hinh/pareto.png`: biên đánh đổi, hàng = vùng RQ1 / k nhỏ, cột = giảm lợi tăng thêm / giảm thiệt hại. Đường xanh nối các mức hạ trần (liền: toàn tri; đứt: thích nghi); biện pháp nằm trên đường này tốt hơn hạ trần ở cùng mức mất khối lượng. **Hình 7.2** `danh_doi_farm.png`.

## 7.2 `Q*` thực nghiệm (lưới 9 mức trần, đối chiếu Lemma 4 và Theorem 6)

Nguồn: `q_sao_vu.csv`, `q_sao_tomtat.csv`, `*_knho.csv`; hình `q_sao.png`, `q_sao_knho.png`.

Một mức r = Q_eff/Q được coi là **an toàn theo tiêu chí V** khi victim không vào (L_V/L_A ≤ 0,001). **Tiêu chí A**: `dc_excess` ≤ 0 (Theorem 6 so tấn công với bán thẳng, nên không tính lãi farm). Q*/Q nằm trong (mức an toàn cao nhất mà mọi mức thấp hơn cũng an toàn; mức kế trên]. Ngưỡng nội suy `r_V` lấy từ (1 + L_V/L_A)² = (V̂/(n·Q))/k: toàn tri khớp đường qua gốc, thích nghi khớp đường thẳng.

- **Victim toàn tri khớp Lemma 4 tới 2–3 chữ số.** Vùng RQ1: khoảng Q*/Q chứa k ở 28/30 cấu hình (k = 0,64 → (0,6; 0,75]; 0,80 → (0,75; 0,9]; 0,95 → (0,9; 1]). Tiêu chí A cho cùng khoảng (`dc_excess` = 0 khi victim rút), và `r_V` = k. Vùng k nhỏ: 30/30 cấu hình khớp **k hiệu dụng = k·(1 − 0,3)** (`r_V` = 0,07 / 0,175 / 0,315), vì victim toàn tri tính V gồm cả khối lượng farm của kẻ tấn công. Hai ngoại lệ vùng RQ1 (L27_04, L27_06: Q = 48k, L_A = 2·10⁸) vi phạm Giả định 2 (xem 7.3): victim đã gần như không vào ngay khi không hạ trần.
- **Victim thích nghi: hạ trần nhiều khi không đuổi được.** Vùng RQ1: 21/30 cấu hình victim vẫn còn ở cap05; `r_V` ≤ 0 ở 20/30 cấu hình (toàn bộ nhóm Q = 12k và 24k). Nhóm Q = 48k có Q*/Q ∈ (0,05; 0,5]. Vùng k nhỏ: 30/30 vẫn còn victim ở cap10. Giải thích bằng V̂ ngầm định = k·(1 + L_V/L_A)² (đơn vị n·Q): ở cap05, V̂ = 0,66–2,44, trong khi trần chỉ còn 0,05. Victim ước V từ phí của *cả bể* trong 24 bước (gồm arb và giao dịch nền), mà phần này không co theo trần. Muốn đuổi victim thích nghi phải tác động vào c_V (cảnh báo), không phải vào Q.
- **Tính đơn điệu (Theorem 6: Π_A không giảm theo Q), có cho phép nhiễu 5%:** đúng ở 29/30 cấu hình toàn tri vùng RQ1, nhưng chỉ 18/30 thích nghi; vùng k nhỏ 10/30 và 4/30. Có hai kiểu vi phạm:
  - (a) Q = 48k, L_A = 2·10⁸ (L27_02/04/06): ở trần cao, lệnh farmer đẩy giá ra khỏi tick tường (40% lệnh ở L27_02 khi không hạ trần, 6% ở cap50), victim không nạp được. Hạ trần đưa bể về vùng thỏa Giả định 2 và **làm tăng lợi kẻ tấn công** (L27_02 toàn tri: 130 → 373 ở cap75).
  - (b) victim thích nghi ở Q = 12k (L27_13, 21, 26): lợi tăng nhẹ khi hạ trần (789 → 1.199). L27_25 (Q = 48k, L_A = 8·10⁸, không vi phạm Giả định 2) có lợi đỉnh ở cap75 (4.493 so với 2.586) — chưa giải thích được, cần xem log.

## 7.3 Bản đồ ba vùng thiết kế (lưới σ × Q, `ba_vung.csv`, hình `ba_vung.png`)

Mỗi ô (σ, Q) có 10 seed. Ba vùng thực nghiệm:
- **(i) không tạo khối lượng:** khối lượng farmer < 50% mức lớn nhất theo σ ở cùng Q.
- **(ii) có khối lượng nhưng tấn công không lãi:** victim không vào, hoặc `loi_tang_them` ≤ 0.
- **(iii) tấn công có lãi.**

Vùng lý thuyết: (i) σ ≤ σ₀ = f = 0,0025 (Theorem 1 với P_e = P₀); (ii) Q_eff ≤ c_V·L_A/(f·n) = 18k (Lemma 4); (iii) còn lại. Giả định của Theorem 3/6 được kiểm trực tiếp bằng cách chạy lại lượt trong pha Prep (`luoi_gia_dinh.csv`):
- **GĐ1** (trần ràng buộc): mức lấp đầy trần mỗi bước ≥ 0,8.
- **GĐ2** (mọi giao dịch được trợ cấp nằm trong một tick): tỷ lệ lệnh farmer làm giá rời tick tường ≤ 5%.

Kết quả:
- **Victim toàn tri, không biện pháp — khớp lý thuyết 25/25 ô:**
  - (i) ở σ = 0,0025 (lấp đầy trần 0–0,06).
  - (ii) ở σ ≥ 0,005 và Q ≤ 12k.
  - (iii) ở σ ≥ 0,005 và Q ≥ 24k: lợi 962–1.104 ở 24k, 4.125–4.513 ở 48k.
  - Ranh giới đúng tại Q_eff = 18k. Hạ trần 50% dời ranh giới sang Q = 36k (khớp 24/25 ô).
- **Ô ngoài giả định (vùng thứ 4, gạch chéo trên hình):**
  - (a) **σ = 0,0025, mọi Q — vi phạm GĐ1:** trần không ràng buộc, farmer chỉ đạt 0–11% trần. Nhưng victim toàn tri vẫn tin V = n·Q và nạp đúng L_V*, nên kẻ tấn công **vẫn có lãi trong vùng (i)** khi Q ≥ 24k: 810 / 3.321 / 1.667 ở 24k/48k/96k. "Không tạo khối lượng" chỉ an toàn nếu victim nhìn thấy khối lượng thật.
  - (b) **Q = 96k, σ ≥ 0,005 — vi phạm GĐ2:** 35–37% lệnh farmer đẩy giá rời tick tường, lấp đầy trần 0,86–1. Victim chỉ nạp được L_V/L_A ≈ 0,05, so với lý thuyết 1,31, nên lợi tụt còn 54–516 (từ 4.125–4.513 ở 48k), giảm dần khi σ tăng. Đây là chỗ Chỉ huy thấy lợi "tụt" ở Q = 96k. Nghịch lý: **hạ trần 50% đưa Q = 96k về vùng thỏa GĐ2** (tỷ lệ rời tick 3–4%), nên lợi kẻ tấn công *tăng* lên 4.256–4.510.
- **Victim thích nghi — vùng (ii) biến mất:**
  - Tấn công có lãi ở **mọi ô σ ≥ 0,005, kể cả Q = 6k**: 1.700–2.100 ở 6k, 3.260–5.472 ở 12–48k. Không biện pháp chỉ khớp lý thuyết 17/25 ô, cap50 chỉ 12/25 ô.
  - Ở σ = 0,0025 (vùng i, farmer gần như không giao dịch), lợi vẫn 898–1.165 ở mọi Q. Victim vẫn vào với L_V/L_A = 0,17–0,22, vì V̂ ước từ phí của khối lượng nền + arb.
  - **Kết luận: với victim nhìn phí lịch sử, cả vùng (i) lẫn ranh giới Q* đều không bảo vệ được.** Ranh giới thực do khối lượng không trợ cấp của bể quyết định, không do σ hay Q.

## 7.4 Kết luận RQ2

Trong mô hình, Q* của Theorem 6 tồn tại và đo được chính xác **chỉ khi victim định giá đúng theo trần** (toàn tri: Q*/Q = k, sai số < 0,01). Hạ trần đủ sâu khi đó loại bỏ hoàn toàn lợi tăng thêm, với giá mất 20–26% khối lượng ở vùng RQ1. Khi victim ước khối lượng từ phí lịch sử, hạ trần — kể cả trần động — chỉ cắt được 27–62% lợi ở vùng RQ1 và gần như 0 ở vùng victim lớn, trong khi mất tới một nửa khối lượng. Ngược lại, cảnh báo rủi ro (tăng c_V) cắt lợi kẻ tấn công mạnh nhất trên mỗi điểm khối lượng mất, với cả hai loại victim. Thu hồi thưởng là bổ sung rẻ (mất < 4% khối lượng) nhưng chỉ nhắm vào lãi farm của kẻ tấn công. Không biện pháp nào ngăn được giá sập; mọi biện pháp thu nhỏ victim còn làm tỷ lệ sập tăng.

## 7.5 Giới hạn

- **% thay đổi là tỷ số trung bình,** nhạy với cấu hình có giá trị lớn. Ở delay168 trung vị hiệu cặp ≈ 0 trong khi % = −18…−24%. Cả hai số đều có trong `danh_doi*.csv`.
- **Thiệt hại victim chỉ so trên cặp cả hai cùng sập.** Biện pháp làm tăng tỷ lệ sập, nên các lượt chỉ sập khi có biện pháp không vào phép so. Lợi kẻ tấn công v3 không bị giới hạn này.
- Victim "toàn tri" trong mô hình là victim tin V = n·Q_eff. Nó không toàn tri khi trần không ràng buộc (vi phạm GĐ1), nên bị lỗ ở vùng (i).
- Kiểm giả định chỉ chạy lại 3 seed/ô. Ngưỡng GĐ1 (0,8) và GĐ2 (5%) là lựa chọn của B.
- L27_25 thích nghi (lợi đỉnh ở cap75, không vi phạm GĐ2) chưa giải thích được.

### Lần chạy trước (v2, giữ để đối chiếu)
v2 dùng `excess` suy vai (nhiễu khi không có victim) và lưới cap 4 mức. Kết luận định tính giống v3: hạ trần hiệu quả với victim toàn tri, kém với victim thích nghi; trả trễ chỉ tác dụng khi có thu hồi và kẻ tấn công farm. v2 chưa có warn và dyncap. Bảng/hình: `ket_qua/gd2/bang_v2/`, `ket_qua/gd2/hinh_v2/`.

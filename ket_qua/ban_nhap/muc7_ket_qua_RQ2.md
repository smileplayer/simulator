# 7. Đánh giá biện pháp giảm thiểu (RQ2) — bản nháp (v4)

> Bản nháp của B, 15/10/2026. Bản v4 thay bản v3 cùng ngày. v4 sửa phản thực "bán thẳng": ở bước xả thứ hai, farmer tối ưu lại trên bể phản thực, không phát lại lượng mua lấy từ đường giá thật có victim đỡ. Hành vi thật (victim, khối lượng, sập) giữ nguyên, chỉ `dc_excess` đổi.
>
> **Dữ liệu** (`ket_qua/gd2/`):
> - `tomtat_v4.csv`: 9.600 lượt = 30 cấu hình vùng RQ1 (k ∈ {0,64; 0,80; 0,95}, victim nhỏ) × 16 biện pháp × 2 loại victim × 10 seed.
> - `tomtat_knho_v4.csv`: 6.000 lượt, vùng k nhỏ (k ∈ {0,10; 0,25; 0,45}, victim lớn, kẻ tấn công farm 30% khối lượng farmer) × 10 biện pháp.
> - `tomtat_farm_v4.csv`: 10.800 lượt, trả trễ/thu hồi × phần farm {0; 0,3; 0,6}.
> - `tomtat_luoi_v4.csv`: 1.000 lượt, lưới σ ∈ {0,0025 … 0,04} × Q ∈ {6k … 96k} quanh `co_so` (c_V cố định), không biện pháp + hạ trần 50%.
>
> **Lệnh:** bảng `python -m metrics.chay_gd2` (≈ 2 phút) → `ket_qua/gd2/bang/`; hình `python -m plots.ve_gd2` → `ket_qua/gd2/hinh/`. Các lần trước: `--phien v3` → `bang_v3/`, `hinh_v3/`; `--phien v2` → `bang_v2/`, `hinh_v2/`.
>
> **Phương pháp.** Mỗi lượt có biện pháp được ghép với lượt `khong` cùng cấu hình + seed + loại victim (+ phần farm); hai lượt dùng chung chuỗi ngẫu nhiên. Báo hai số: trung vị hiệu cặp, và **% thay đổi** = (TB có biện pháp − TB gốc)/|TB gốc| trên cùng tập cặp. CI 95% = bootstrap cặp phân cụm theo cấu hình (2.000 lần).
>
> **Chỉ số.**
> - **Lợi tăng thêm của kẻ tấn công** `loi_tang_them` = `dc_excess` + `dc_farm_pnl`, đo theo địa chỉ thật (có cả khi không sập). `dc_excess` = lợi nhuận so với phát lại log không victim, bằng 0 đúng khi không có victim. Bản `_treo` cộng thêm thưởng chưa tới hạn. `dc_lai_tong` (gồm cả bán kho theo c_A) chỉ để tham khảo.
> - **Thiệt hại victim** chỉ đo được khi giá sập ≥ 10%, nên so trên cặp cả hai cùng sập: loại 5/300 cặp (toàn tri), 35/300 cặp (thích nghi). Tỷ lệ sập được báo riêng.

## 7.1 Kết quả chính

1. **Cảnh báo rủi ro (warn: c_V × 1,5/2/4) giữ khối lượng tốt nhất.** (sửa 20/10: chỉ đúng trên trục khối lượng; cảnh báo gần như không tiết kiệm trợ cấp, hạ trần tiết kiệm 44–94%; warn40 làm L_active Post giảm 49% với nạn nhân thích nghi, do cú sập sâu hơn (22/10: bỏ vị thế nạn nhân và kẻ tấn công cho cùng số ở mọi lượt có sập); thứ hạng tùy mục tiêu của nền tảng)
   - Mất khối lượng chỉ 0,4–2,3%.
   - Vùng RQ1: cắt 94–100% lợi kẻ tấn công với victim toàn tri, 27/50/94% với victim thích nghi. Để đạt mức giảm tương đương, hạ trần phải mất 20–49% khối lượng.
   - Vùng k nhỏ: warn40 giảm thiệt hại victim 43–65%, nhưng lợi kẻ tấn công chỉ giảm 18–43%.
2. **Hạ trần Q và trần động nằm trên cùng một đường đánh đổi.**
   - Victim toàn tri: lợi tăng thêm về 0 khi r ≤ k, đúng Lemma 4. Mất 20–26% khối lượng.
   - Victim thích nghi, vùng RQ1: cap05 mất 49% khối lượng mà chỉ giảm 65% lợi và 69% thiệt hại.
   - Victim thích nghi, vùng k nhỏ: gần như vô hiệu — cap50 giảm 4% lợi, 12% thiệt hại.
3. **Trả trễ không thu hồi gần như vô tác dụng** (delay24/72: lợi +0,4…+0,9%). delay168 với victim thích nghi giảm 19–24%, nhưng là "hạ σ trá hình": chiết khấu 0,995¹⁶⁸ = 0,43 làm farmer ở các cấu hình σ = 0,005 ngừng giao dịch.
4. **Thu hồi chỉ cắt phần lãi farm của kẻ tấn công.**
   - Phần farm 0,6: claw72 giảm 46–50% lợi, mất 3,6% khối lượng; claw168 giảm 72–76%, mất 25% khối lượng.
   - Vùng k nhỏ: claw72 giảm 20–22%.
   - Thiệt hại victim không đổi (claw = delay).
5. **Không biện pháp nào làm giá thôi sập.** Biện pháp làm victim nhỏ đi còn làm tỷ lệ sập ≥ 10% *tăng*: victim thích nghi 88% → 99% ở cap05 và ở warn40.

**Bảng 7.1 — vùng RQ1** (`gon.csv`): % thay đổi [CI 95%]. Mức gốc (trung vị): lợi tăng thêm 361 (toàn tri) / 2.071 (thích nghi) token1; thiệt hại 171 / 1.022; khối lượng ≈ 1,5 triệu; trợ cấp ≈ 4.700.

| Nhóm | Biện pháp | Lợi: toàn tri | Lợi: thích nghi | Thiệt hại: toàn tri | Thiệt hại: thích nghi | Sập (điểm %, thích nghi) | Khối lượng | Trợ cấp |
|---|---|---|---|---|---|---|---|---|
| hạ trần | cap90 | −38 [−48; −31] | −4 [−6; 0] | −39 | −4 | +0,7 | −5 | −8 |
| | cap75 | −80 [−90; −71] | −11 [−17; −3] | −80 | −11 | +3,7 | −13 | −21 |
| | cap50 | −100 | −31 [−41; −18] | −100 | −40 | +5,3 | −26 | −44 |
| | cap25 | −100 | −55 [−70; −35] | −100 | −59 | +7,3 | −40 | −70 |
| | cap05 | −100 | −65 [−81; −45] | −100 | −69 | +10,3 | −49 | −94 |
| trả trễ | delay72 | +0,7 | +0,9 | +2,0 | +3,5 | 0 | −3 | −17 |
| | delay168 | −4 [−10; 0] | −19 [−39; −4] | −2 | −24 | +4,7 | −19 | −38 |
| cảnh báo | warn15 | −94 [−97; −92] | −27 [−33; −20] | −95 | −34 | +3,7 | −0,6 | −1 |
| | warn20 | −99 | −50 [−58; −40] | −100 | −54 | +7,0 | −1,2 | −2 |
| | warn40 | −100 | −94 [−98; −89] | −100 | −95 | +11,3 | −2,3 | −3 |
| trần động | dyncap | −100 | −56 [−70; −37] | −100 | −60 | +7,3 | −36 | −60 |

**Bảng 7.2 — vùng k nhỏ, kẻ tấn công farm 0,3** (`gon_knho.csv`; tách theo k: `gon_knho_theo_k.csv`). Mức gốc: lợi tăng thêm 3.504 / 3.832; thiệt hại 1.219 / 1.985.

| Biện pháp | Lợi: toàn tri | Lợi: thích nghi | Thiệt hại: toàn tri | Thiệt hại: thích nghi | Khối lượng |
|---|---|---|---|---|---|
| cap50 | −25 [−36; −9] | −4 [−12; +9] | −32 | −12 | −28 |
| cap25 | −56 [−67; −42] | −14 [−23; −1] | −66 | −20 | −45 |
| cap10 | −81 [−85; −75] | −30 [−40; −17] | −94 | −29 | −54 |
| dyncap | −62 [−73; −49] | −19 [−28; −6] | −66 | −20 | −42 |
| delay72 | −6 | −5 | +3 | +2 | −3 |
| claw72 | −22 [−27; −17] | −20 [−25; −15] | +3 | +2 | −3 |
| warn15/20/40 | −9 / −18 / −43 | −2 / −4 / −18 | −21 / −36 / −65 | −13 / −20 / −43 | −0,4…−2 |

**Bảng 7.3 — trả trễ khi kẻ tấn công farm** (`gon_farm.csv`, lợi tính cả thưởng treo):

| Phần farm | delay72 | claw72 | delay168 | claw168 |
|---|---|---|---|---|
| 0,6 | −10…−11% | −46…−50% | −19…−26% | −72…−76% |
| 0,3 | −5…−12% | −22…−37% | −21…−23% | −47…−56% |

Ở delay168, nếu không tính thưởng treo thì mức giảm là −66…−71%, vì thưởng chỉ bị hoãn chứ không mất. Khối lượng mất: −3,6% ở D = 72, −25% ở D = 168.

**Hình 7.1** `ket_qua/gd2/hinh/pareto.png`: biên đánh đổi, hàng = vùng RQ1 / vùng k nhỏ, cột = giảm lợi tăng thêm / giảm thiệt hại. Đường xanh nối các mức hạ trần (liền: toàn tri; đứt: thích nghi). **Hình 7.2** `danh_doi_farm.png`.

## 7.2 `Q*` thực nghiệm (lưới 9 mức trần; đối chiếu Lemma 4 và Theorem 6)

Nguồn: `q_sao_vu*.csv`, `q_sao_tomtat*.csv`; hình `q_sao.png`, `q_sao_knho.png`.

Một mức r = Q_eff/Q được coi là an toàn theo **tiêu chí V** khi victim không vào (L_V/L_A ≤ 0,001), theo **tiêu chí A** khi `dc_excess` ≤ 0 (Theorem 6 so với bán thẳng nên không tính lãi farm). Ngưỡng nội suy `r_V` lấy từ (1 + L_V/L_A)² = (V̂/(n·Q))/k.

- **Victim toàn tri khớp Lemma 4.**
  - Vùng RQ1: khoảng Q*/Q chứa k ở 28/30 cấu hình; tiêu chí A cho cùng khoảng; `r_V` = k.
  - Vùng k nhỏ: 30/30 khớp k hiệu dụng = k·(1 − 0,3), vì victim toàn tri tính V gồm cả khối lượng farm của kẻ tấn công.
  - Hai ngoại lệ (L27_04, L27_06: Q = 48k, L_A = 2·10⁸) vi phạm Giả định 2 (mục 7.4).
- **Victim thích nghi: hạ trần không đuổi được.**
  - Vùng RQ1: 21/30 cấu hình vẫn còn victim ở cap05; `r_V` ≤ 0 ở 20/30 (toàn bộ nhóm Q = 12k và 24k).
  - Vùng k nhỏ: 30/30 vẫn còn victim ở cap10.
  - V̂ ngầm định ở cap05 bằng 0,66–2,44·n·Q, trong khi trần chỉ còn 0,05: victim ước V từ phí của *cả bể* (gồm arb + nền), không co theo trần.

## 7.3 Kiểm tính đơn điệu theo trần (Theorem 6: Π_A không giảm theo Q)

Nguồn: `don_dieu_gop*.csv`, `don_dieu_vu*.csv`. Hiệu cặp cùng vụ + seed giữa hai mức trần liền kề: d = lợi(trần thấp) − lợi(trần cao), lợi = `loi_tang_them`.

- **Gộp 30 vụ: không có bước hạ trần nào làm lợi tăng có ý nghĩa.**
  - Victim thích nghi: TB d âm ở mọi bước. khong→cap90: −102 [−198; +6]; cap90→cap75: −212 [−374; −46]; cap75→cap60: −315 [−478; −151].
  - Victim toàn tri: d ≤ 0 ở mọi bước.
  - Dãy trung vị "1.863 → 1.817 → 2.048 (cap75)" mà Chỉ huy thấy là trung vị *cắt ngang* qua các vụ, không phải hiệu cặp. Trung vị hiệu cặp ở cap90→cap75 là −101.
- **Theo từng vụ (CI bootstrap theo seed, ngưỡng tăng > 50 token1):**
  - Vùng RQ1: 11/240 phép so tăng có ý nghĩa, rơi vào 5 vụ thích nghi; toàn tri 0.
  - Vùng k nhỏ: 12/120 phép so (thích nghi 6, toàn tri 6), gần hết ở bước khong→cap50 của các vụ Q = 48k, L_A = 2·10⁸.
- **Cơ chế 1 — phương án bán thẳng xấu đi khi hạ trần** (vụ Q = 12k, kho 15k, victim thích nghi: L27_11, 13, 21, 26; mỗi bước +53…+147 token1, ≈ 4–12%).
  - Ví dụ L27_26, khong → cap05: L_V/L_A giảm chậm 0,99 → 0,59 (V̂ chủ yếu từ nền + arb); thiệt hại victim gần như không đổi (858 → 899).
  - Tiền thu thật khi xả (`dc_paper`) chỉ giảm 216 (14.933 → 14.717), nhưng giá trị bán thẳng phản thực giảm 745 (13.857 → 13.112). Lý do: trong phản thực không có tường/victim, cú bán thẳng được đỡ bởi lượng mua của farmer, mà lượng này co theo trần.
  - Nghĩa là lợi *tăng thêm* tăng vì phương án ngoài xấu đi, không phải vì tấn công lời hơn. Theorem 6 coi Π_direct không phụ thuộc Q; trong mô hình có farmer, giả định này không đúng.
- **Cơ chế 2 — trần cao vi phạm Giả định 2** (Q = 48k, L_A = 2·10⁸: L27_02 thích nghi cap90→cap75 +1.033; vùng k nhỏ KN_L27_02/04/06 khong→cap50 +840…+5.834).
  - Ở trần cao, lệnh farmer đẩy giá ra khỏi tick tường (40% lệnh ở L27_02), nên victim không nạp được.
  - Hạ trần đưa bể về vùng một tick, victim vào và kẻ tấn công lời hơn. Đây là ngoài phạm vi Theorem 6, không phải phản ví dụ.
- **v3 → v4:** số vụ không đơn điệu (ngưỡng 5%) giảm. Vùng RQ1 thích nghi: 12 → 6/30. Vùng k nhỏ thích nghi: 26 → 10/30; toàn tri: 20 → 7/30. Phần lớn "tăng khi hạ trần" ở v3 là do lỗi phản thực.

## 7.4 Bản đồ ba vùng thiết kế (`ba_vung.csv`, hình `ba_vung.png`)

**Cách phân vùng.** Mỗi ô (σ, Q) có 10 seed. Ba vùng thực nghiệm:
- (i) không tạo khối lượng: khối lượng farmer < 50% mức lớn nhất theo σ ở cùng Q;
- (ii) có khối lượng nhưng tấn công không lãi: victim không vào, hoặc `loi_tang_them` ≤ 0;
- (iii) tấn công có lãi.

Vùng lý thuyết: (i) σ ≤ σ₀ = f = 0,0025; (ii) Q_eff ≤ c_V·L_A/(f·n) = 18k (Lemma 4); (iii) còn lại.

Giả định được kiểm bằng cách chạy lại pha Prep (`luoi_gia_dinh.csv`, 3 seed/ô):
- **GĐ1** (trần ràng buộc): mức lấp đầy trần mỗi bước ≥ 0,8.
- **GĐ2** (giao dịch được trợ cấp nằm trong một tick): ≤ 5% lệnh farmer làm giá rời tick tường.

**Kết quả.**
- **Victim toàn tri, không biện pháp: khớp lý thuyết 25/25 ô.**
  - (i) ở σ = 0,0025.
  - (ii) ở σ ≥ 0,005 và Q ≤ 12k.
  - (iii) ở σ ≥ 0,005 và Q ≥ 24k: lợi 967–1.141 ở 24k, 4.557–5.777 ở 48k.
  - Ranh giới đúng tại Q_eff = 18k. Hạ trần 50% dời ranh giới sang Q = 36k (khớp 24/25 ô).
- **Vùng ngoài giả định (gạch chéo trên hình).**
  - (a) **σ = 0,0025, vi phạm GĐ1:** farmer chỉ đạt 0–11% trần. Nhưng victim toàn tri tin V = n·Q và vẫn nạp đủ, nên kẻ tấn công vẫn có lãi trong vùng (i): 831 / 3.353 / 6.328 ở Q = 24k / 48k / 96k.
  - (b) **Q = 96k và σ ≥ 0,005, vi phạm GĐ2:** 35–37% lệnh farmer rời tick tường; victim chỉ nạp L_V/L_A ≈ 0,05 so với lý thuyết 1,31; lợi còn 77–524. Hạ trần 50% đưa ô này về thỏa GĐ2 (tỷ lệ rời tick 3–4%), và lợi *tăng* lên 4.462–5.720.
- **Victim thích nghi: vùng (ii) biến mất.**
  - Lợi dương ở mọi ô σ ≥ 0,005, kể cả Q = 6k: 1.700–2.100 ở 6k, 2.888–6.383 ở 12–48k. Khớp lý thuyết 17/25 ô (không biện pháp), 12/25 ô (cap50).
  - Ở σ = 0,0025, lợi vẫn 930–1.166 ở mọi Q: victim vẫn vào với L_V/L_A 0,17–0,22, vì V̂ ước từ phí nền + arb.
  - Vùng (i) và ranh giới Q* đều không bảo vệ được victim nhìn phí lịch sử.

## 7.5 Kết luận RQ2

- **Q* của Theorem 6 chỉ đo được chính xác khi victim định giá theo trần.** Với victim toàn tri, Q*/Q = k (sai số < 0,01), và hạ trần đủ sâu xóa hết lợi tăng thêm với giá mất 20–26% khối lượng ở vùng RQ1.
- **Khi victim ước khối lượng từ phí lịch sử, hạ trần kém hiệu quả.** Kể cả trần động, chỉ cắt 31–65% lợi ở vùng RQ1 và 4–30% ở vùng victim lớn, trong khi mất tới một nửa khối lượng.
- **Cảnh báo rủi ro (tăng c_V) giữ khối lượng tốt nhất** với cả hai loại victim (sửa 20/10: chỉ đúng trên trục khối lượng; cảnh báo gần như không tiết kiệm trợ cấp, hạ trần tiết kiệm 44–94%; warn40 làm L_active Post giảm 49% với nạn nhân thích nghi, do cú sập sâu hơn (22/10: bỏ vị thế nạn nhân và kẻ tấn công cho cùng số ở mọi lượt có sập); thứ hạng tùy mục tiêu của nền tảng). Thu hồi thưởng là bổ sung rẻ (mất < 4% khối lượng), nhưng chỉ nhắm vào lãi farm của kẻ tấn công.
- **Không biện pháp nào ngăn được giá sập.**
- **Về tính đơn điệu:** gộp lại thì không có bước hạ trần nào làm lợi tăng có ý nghĩa. Các ngoại lệ theo vụ có hai nguồn: (1) phương án bán thẳng phụ thuộc Q, trong khi lý thuyết coi nó cố định; (2) vi phạm giả định một tick.

## 7.6 Giới hạn

- **% thay đổi là tỷ số trung bình**, nhạy với cấu hình có giá trị lớn. Ví dụ delay168: trung vị hiệu cặp ≈ 0, nhưng % = −19…−24%. Cả hai số đều có trong `danh_doi*.csv`.
- **Thiệt hại victim chỉ so trên cặp cả hai cùng sập.** Biện pháp làm tăng tỷ lệ sập.
- **Victim "toàn tri" là victim tin V = n·Q_eff**, nên bị lỗ khi trần không ràng buộc (vùng i).
- **Kiểm giả định chỉ chạy 3 seed/ô.** Ngưỡng GĐ1 (0,8), GĐ2 (5%) và ngưỡng "tăng > 50 token1" là lựa chọn của B. Kiểm đơn điệu theo vụ gồm 240 phép so nên có thể có vài dương tính giả; các vụ nêu ở 7.3 tăng nhất quán qua nhiều bước liền nhau.

### Bản v5 (22/10/2026): CH-9 và bậc phí 0,01% (cải tiến A)

Đức chạy `python -m scenarios.quet_gd2 --phien v5` và `--phien v5 --bien_the f001` (mỗi bộ 9.600 lượt, vùng RQ1). Bảng: `ket_qua/gd2/bang_v5/`, `bang_f001_v5/`. Bộ v5 ở phí 0,25% khớp v4 ở mọi cột cũ.

- **Thanh khoản Post (W11):** bỏ vị thế nạn nhân và kẻ tấn công (`L_khac_mean_post`) cho đúng bằng `L_mean_post` ở cả 9.270 lượt có sập. Nghi vấn "warn40 làm mất thanh khoản chỉ vì nạn nhân vào ít" sai. Mức giảm 49% (nạn nhân thích nghi) đến từ cú sập sâu hơn: trung vị độ sập −18% → −40%, giá rơi ra khỏi dải LP nền; LP nền trong mô hình không đặt lại vị thế.
- **Lợi nhuận ròng nạn nhân** (`victim_net` = phí cả kịch bản − E_full), lượt không biện pháp có nạn nhân và có sập: lỗ ròng ở 57% lượt toàn tri, 66% lượt thích nghi; trung vị −20 và −275 token1 (phí 159 và 754 token1 không bù được thiệt hại 171 và 1.022). Theo k (toàn tri): −69 / −26 / 0 ở k = 0,64 / 0,80 / 0,95.
- **Bậc phí 0,01% (giữ k và σ/f):** % thay đổi của lợi tăng thêm lệch ≤ 1,2 điểm so với 0,25%; khối lượng, trợ cấp, L Post lệch tới 4, 6, 7 điểm (lớn nhất: delay168 mất 14% khối lượng thay vì 18%; cap05 toàn tri L Post −16% thay vì −22%). Thứ tự biện pháp trên từng trục không đổi; tỷ lệ sập gần như không đổi; nạn nhân thích nghi vẫn còn ở 21/30 vụ dưới cap05.
- **Tỷ số lợi tăng thêm / trợ cấp phụ thuộc bậc phí:** trợ cấp tỷ lệ với σ (giữ σ/f nên σ × 0,04) giảm từ ~4.700 xuống 171 token1, còn lợi tăng thêm gần như không đổi (365 và 2.230 token1) → tỷ số 2,7× (toàn tri) và 14× (thích nghi), so với 10% và 49% ở bậc 0,25%.

### Các lần chạy trước
- **v3:** cùng thiết kế; phản thực đỡ giá cho cú bán thẳng.
  - v3 → v4, cùng xếp hạng biện pháp, Q* và phân vùng; chỉ % giảm lợi kẻ tấn công đổi vài điểm %: vùng k nhỏ hạ trần mạnh hơn (thích nghi cap10 −19 → −30%, toàn tri cap50 −17 → −25%), claw72 farm 0,6 yếu hơn (−52…−54 → −46…−50%).
  - File kết quả v3 đã xóa ngày 17/10/2026 (còn trong lịch sử git).
- **v2:** lợi nhuận suy vai, lưới cap 4 mức, chưa có warn và dyncap. File kết quả đã xóa ngày 17/10/2026 (còn trong lịch sử git).

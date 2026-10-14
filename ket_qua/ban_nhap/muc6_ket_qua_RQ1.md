# 6. Kết quả tái lập (RQ1) — bản nháp

> Bản nháp của B, 14/10/2026. **Không commit lên git.** Số liệu từ `ket_qua/rq1/` (sinh lại: `python -m metrics.chay_rq1`, hình: `python -m plots.ve_rq1`). Bộ dữ liệu: 30 cấu hình × 5 seed = 150 vụ mô phỏng trên engine cross-tick, có đuôi thanh khoản nền toàn dải (`bg_tail` = 0,075). Bài gốc: 29 vụ thật trên BSC.

**Simulator tái lập được cả mười một dấu hiệu thực nghiệm chính của bài gốc** (Bảng 6.1): tường ghim giá, khối lượng sau sập rơi dưới nền ở 81% vụ (bài gốc 79%), biến động thấp nhất lúc chuẩn bị và cao nhất sau sập, tường cạn tại thời điểm sập. Phân phối khớp sát nhất ở khối lượng Post; lệch rõ nhất ở khối lượng Prep và Attack (mục 6.3).

## 6.1 Bảng kiểm định

**Bảng 6.1.** Tỷ lệ vụ thỏa từng phát biểu của bài gốc. Đạt khi tỷ lệ mô phỏng ≥ 50% (riêng "Attack > 5×": có ít nhất một vụ).

| Dấu hiệu | Phát biểu | Mô phỏng | Bài gốc | Kết quả |
|---|---|---|---|---|
| Sập | giá ≤ 90% tick tường | 99% (149/150) | 100% | Đạt |
| Chuẩn bị theo ngày | Δbuild ≥ 1 ngày | 100% | 55% | Đạt* |
| Thu hoạch theo giờ | Δextract < 24 giờ | 97% | 62% | Đạt |
| Khối lượng Attack | lift ≥ 1× | 100% | 59% | Đạt |
| | có vụ lift > 5× | 17% | 14% | Đạt |
| **Khối lượng Post** | **lift < 1×** | **81%** | **79%** | **Đạt** |
| | (phụ, bỏ arbitrageur) | 77% | — | Đạt |
| Biến động | RV Prep < RV Attack | 98% | — | Đạt |
| | RV Post cao nhất | 95% | — | Đạt |
| Giá ghim quanh `t_m` | \|độ dời\| < 10% | 100% | 79% | Đạt |
| Giá sập sau rút | độ dời < −10% (VWAP) | 59% | 69% | Đạt |
| | (phụ, mốc trước burn) | 79% | — | Đạt |
| Tường cạn | drop tại `t_b` ≥ 80% | 100% | 86% | Đạt |
| Victim khớp lý thuyết | `L_V*/L_A ≈ 1` tại `L_A = fQ/(4c_V)` | kiểm ở lớp cơ học | — | Đạt (test) |

\* Δbuild = 120 giờ ở mọi vụ vì lịch dựng và rút tường là tham số kịch bản (`t_m` = 48, `t_0` = 168), không phải kết quả nội sinh. Dòng này chỉ xác nhận thiết kế kịch bản nằm trong miền bài gốc quan sát.

## 6.2 Diễn biến một vụ và động lực theo pha

![Timeline một vụ](../rq1/hinh/timeline_co_so.png)

**Hình 6.1.** Một vụ trong kịch bản cơ sở (seed 0). Trên: giá bể và giá ngoài. Giữa: thanh khoản tick tường của kẻ tấn công và nạn nhân. Dưới: khối lượng swap mỗi giờ theo vai.

Hình 6.1 cho thấy đủ trình tự bài gốc mô tả. Kẻ tấn công dựng tường 2,4·10⁸ L ở giờ 48, nâng lên 4·10⁸ ở giờ 72; nạn nhân toàn tri vào ở giờ 78 với phần nhỏ hơn tường. Suốt 120 giờ Prep, giá đứng yên trong một tick trong khi farmer và arbitrageur giao dịch đều. Ở giờ 168 kẻ tấn công rút toàn bộ tường rồi xả; giá rơi từ 1,0 xuống 0,5 trong cùng giờ, nên `t_0 = t_b`. Sau đó chỉ còn phần của nạn nhân kẹt trên tick, và khối lượng mỗi giờ thấp hơn trước khi có tường.

![Biến động theo pha](../rq1/hinh/hop_rv.png)

**Hình 6.2.** Biến động thực hiện theo pha, 150 vụ (trục log; râu = min–max).

Trung vị RV theo pha là 0,092 (Before), 0,017 (Prep), 0,187 (Attack) và 1,147 (Post). Prep yên hơn cả Before vì tường hấp thụ dòng lệnh mà không đổi tick. Post cao nhất vì sau sập giá ra khỏi dải thanh khoản nền, chỉ còn đuôi mỏng: `L_active` trung vị giảm từ 215.000 (Before) xuống 15.000 (Post), tức còn 7%.

## 6.3 Phân phối so với bài gốc

![Bảng 4 dạng hình](../rq1/hinh/bang4_lift.png)

**Hình 6.3 (Bảng 4 bài gốc).** Phân bố volume lift theo nhóm, % số vụ.

| Nhóm | Prep MP | Prep BG | Attack MP | Attack BG | Post MP | Post BG |
|---|---|---|---|---|---|---|
| < 1× | 0 | 9 | 0 | 12 | 121 | 23 |
| 1–1,5× | 58 | 11 | 6 | 9 | 28 | 1 |
| 1,5–2× | 31 | 4 | 13 | 3 | 0 | 1 |
| 2–5× | 61 | 2 | 104 | 1 | 0 | 2 |
| > 5× | 0 | 3 | 26 | 4 | 0 | 2 |

MP = mô phỏng (149 vụ có sập), BG = bài gốc (29 vụ). Post khớp gần như tuyệt đối về tỷ lệ dưới nền. Hai chỗ lệch cần nói rõ:

- **Prep không vụ nào dưới nền** (bài gốc 9/29). Trong mô phỏng, farmer luôn tối ưu đúng theo Theorem 1 nên tường luôn hút thêm khối lượng; trên thực tế có tường không hút được ai. Lift Prep tăng theo trần trợ cấp `Q`: trung vị 1,31 / 1,78 / 2,93 với `Q` = 12k / 24k / 48k, tức `Q` nhỏ khớp bài gốc hơn.
- **Attack dồn vào 2–5×** (70% vụ; bài gốc 41% dưới nền). Trong mô phỏng toàn bộ cú xả đi qua đúng bể bị tấn công; trên chuỗi thật kẻ tấn công có thể bán qua nhiều bể và sàn, nên khối lượng trong bể không bùng đều như vậy.

![Bảng 7 dạng hình](../rq1/hinh/bang7_drop.png)

**Hình 6.4 (Bảng 7 bài gốc).** Độ tụt thanh khoản tick tường tại `t_b`.

Mọi vụ mô phỏng cạn ≥ 80% (bài gốc 25/29), nhưng 90% rơi vào nhóm 80–99% thay vì 100% (bài gốc 18/29 ở 100%). Lý do: nạn nhân toàn tri không rút trước khi sập, phần của họ vẫn nằm trên tick. Ở bài gốc, `L(t_b) = 0` thường xuyên hơn, gợi ý nạn nhân thật nhỏ hơn hoặc một phần đã rút.

**Độ dời giá (Bảng 6 bài gốc).** Quanh `t_m`: 120/150 vụ trong 0–10%, 30 vụ trong −10–0% (bài gốc 16 và 7). Sau rút, theo VWAP: 22 vụ −50…−20%, 66 vụ −20…−10%, 61 vụ −10…0% (bài gốc 10 / 10 / 8). Mốc VWAP giờ `t_0` đã gồm cú xả nên ước thấp độ sập; với mốc trước burn tường, trung vị độ dời là −14,8% thay vì −10,4%, và 79% vụ dưới −10%.

## 6.4 Bốn chỉ số

| Chỉ số (token1) | P10 | Trung vị | P90 |
|---|---|---|---|
| Thiệt hại nạn nhân, bản đầy đủ | 14 | 180 | 664 |
| Thiệt hại nạn nhân, bản bài gốc (non-alpha) | 0 | 0 | 0 |
| Lợi nhuận kẻ tấn công, bản bài gốc | 11.823 | 14.416 | 19.937 |
| Lợi nhuận kẻ tấn công, bản đầy đủ (`c_A` = 0,5) | 5.082 | 8.988 | 12.262 |
| Chi phí trợ cấp | 1.235 | 4.706 | 16.590 |
| Tỷ lệ rò rỉ (bản bài gốc) | 1,1× | 3,1× | 11,2× |
| Tỷ lệ rò rỉ (bản đầy đủ) | 0,6× | 1,7× | 5,7× |

Kẻ tấn công có lãi theo bản đầy đủ ở 149/150 vụ. Lợi nhuận kẻ tấn công gấp hàng chục lần thiệt hại nạn nhân, đúng nhận xét của bài gốc rằng hai đại lượng không phải tổng bằng không: phần lớn tiền xả đến từ thanh khoản nền bên dưới tick, không từ nạn nhân. Hiệu quả chi tiêu âm ở mọi vụ (`eff_gain` trung vị −35 L mỗi token1): thanh khoản sau tấn công thấp hơn trước khi có trợ cấp.

Thiệt hại nạn nhân bản bài gốc gần như luôn bằng 0 (chỉ 7% vụ dương), vì cách tính này trừ toàn bộ alpha nhận lại, kể cả alpha nạn nhân tự nạp. Bản đầy đủ dương ở 89% vụ. Thiệt hại giảm khi chi phí tham gia của nạn nhân tăng (`k` = 0,64 / 0,80 / 0,95 cho trung vị 548 / 219 / 47), vì nạn nhân góp ít hơn. Có 15/149 vụ không xác định được nạn nhân (không ai còn thanh khoản trên tick tại `t_b`), chia đều 5 vụ cho mỗi mức `k`; cần xem log để biết nạn nhân không vào hay đã rút.

## 6.5 Giới hạn

- Năm seed mỗi cấu hình, chưa có khoảng tin cậy (mục 5.5 chờ quyết).
- Lịch dựng và rút tường cố định nên dấu hiệu thời gian chỉ là kiểm tra thiết kế, không phải kết quả.
- Nạn nhân toàn tri là cận trên của khả năng phản ứng; nạn nhân thích nghi (vai C đang làm) có thể làm Bảng 7 gần bài gốc hơn.

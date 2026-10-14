# Nhật ký hiệu chỉnh RQ1

Đóng băng ở tag **`rq1-v1`** (14/10/2026): bảng kiểm định `kiemdinh.csv` đạt **13/13** tiêu chí đo được, trên 150 log (30 vụ × 5 seed). Victim toàn tri khớp lý thuyết được kiểm riêng trong `tests/agents/`.

Ba thay đổi dưới đây chỉ chạm **môi trường**: thanh khoản nền, tham số chi phí của nạn nhân, kho của kẻ tấn công. Không thay đổi nào chạm hành vi tối ưu của tác nhân (farmer theo Theorem 1, victim theo Lemma 4, attacker theo Lemma 5) hay engine. Mỗi thay đổi được đưa vào để sửa một dấu hiệu cụ thể bị hỏng, và có lý do kinh tế độc lập với việc "cho qua kiểm định".

Tái lập bảng 1: `python -m scenarios.hieu_chinh` (≈ 2 s, ghi `hieu_chinh_truoc_sau.csv`). Tái lập bảng kiểm định cuối: `python -m scenarios.batch --seeds 5` (≈ 12 s) rồi `python -m metrics.chay_rq1`.

---

## Thay đổi 1 — Thanh khoản nền hữu hạn (`bg_band`)

**Trước:** một vị thế nền phủ đều ±20.000 tick (giá ×/÷ 7,4).
**Sau:** 5 vị thế `bg:1..5` lồng nhau trong ±`bg_band` quanh giá đầu (mặc định 10%). Khoảng thứ k phủ ±`bg_band·k/5`, mỗi khoảng `L_bg/5`, nên mật độ dày nhất ở giữa. Trader nền bỏ lệnh khi bể cạn.

**Lý do.** Ở bản gốc, khối lượng Post trên nền (1,15×), trái dấu hiệu quan trọng nhất của bài gốc là "Post dưới nền". Nguyên nhân: sau cú sập, giao dịch nền và farmer quay lại y như trước tường, vì thanh khoản nền vẫn còn nguyên ở mọi mức giá. Trên bể thật, LP thụ động tập trung quanh giá hiện hành chứ không phủ tới giá ×7. Khi giá rơi khỏi vùng đó, độ sâu cạn và dòng lệnh giảm theo. Đây đúng là cơ chế bài gốc giải thích: dòng lệnh phụ thuộc vào thanh khoản.

**Hệ quả phụ, dẫn tới thay đổi 3:** ngoài dải thì `L = 0`, nên cú xả dừng đúng ở mép dải (sàn `z_floor` của Lemma 5). Độ sập luôn ≈ `bg_band` trừ độ trôi giá trước tường, ra 9–11%. Post tụt gần 0 (0,195) vì bể cạn hẳn, và RV Post không còn cao nhất.

## Thay đổi 2 — Tường chiếm phần lớn tick: `L_A ∈ [0,64 ; 1)·fV/c_V`

**Trước:** `c_V` đặt ở mốc `L_A = fV/(4c_V)` (V = n_farmers·Q), nên `L_V* = L_A` và tường chỉ chiếm 50% thanh khoản tick.
**Sau:** `c_V = k·fV/L_A` với `k ∈ [0,64; 1)`; co_so dùng `k = 0,75`.

**Lý do.** Lemma 4 cho `L_V*/L_A = 1/√k − 1`. Do đó `k ∈ [0,64; 1)` ⟺ `L_V*/L_A ∈ (0; 0,25]` ⟺ tường chiếm ≥ 80%, khớp Bảng 7 bài gốc: tường cạn ≥ 80% tại `t_b` ở 25/29 vụ. Mốc `fV/(4c_V)` là điểm làm **`L_V*` lớn nhất**, dùng để kiểm định engine, chứ không phải điểm kẻ tấn công thực sự chọn. Mốc này vẫn được giữ trong test (`test_victim_moc_LA_bang_fV_chia_4cV`).

Ví dụ số, co_so: `f = 0,25%`, `V = 3 × 24.000 = 72.000`, `L_A = 4·10⁸`, `k = 0,75`. Khi đó `c_V = 3,375·10⁻⁷` và `L_V* = (1/√0,75 − 1)·L_A ≈ 0,155·L_A = 6,2·10⁷`, nên tường chiếm `1/1,155 ≈ 87%`.

## Thay đổi 3 — Đuôi nền mỏng toàn dải (`bg_tail`) + kho kẻ tấn công là yếu tố quét

**Trước:** ngoài ±`bg_band` thì `L = 0`; kho kẻ tấn công cố định 60.000 token0.
**Sau:** thêm vị thế `bg:6` toàn dải `[MIN_TICK, MAX_TICK]` với `L = bg_tail·L_bg`, co_so `bg_tail = 0,075` (Đức giao 5–10%). Kho kẻ tấn công thành yếu tố thứ 6 của mảng L27, nhận các mức {15k, 25k, 40k}; co_so dùng 25k.

**Lý do.** Bể thật luôn có một ít thanh khoản rải rác ở xa giá (vị thế toàn dải kiểu v2, LP quên chỉnh), nên giá không dừng cứng ở mép một dải. Có đuôi thì cú xả đi tiếp qua vùng mỏng: Post còn giao dịch (dưới nền nhưng không ≈ 0), và biến động sau sập cao nhất.

Chỉ thêm đuôi thì chưa đủ. Với kho 60k, **mọi vụ** đều dừng ở `z̄ = √(c_A/(1−f))`, tức giá bằng giá vốn `c_A = 0,5`, nên độ sập luôn −50% và không có phân phối. Kho phải là ràng buộc chặn trước thì độ sập mới trải rộng như 29 vụ của bài gốc. Đo trên co_so (seed 0, đuôi 7,5%):

| bg_band | kho 8k | kho 15k | kho 25k | kho 40k |
|---|---|---|---|---|
| 0,15 | −5% | −17% | −50% | −50% |
| 0,25 | −5% | −12% | −36% | −50% |
| 0,40 | −5% | −11% | −20% | −42% |

Ngoài ra, mức `bg_band` của bộ tổ hợp đổi từ {0,05; 0,10; 0,20} sang **{0,15; 0,25; 0,40}**. Với sàn −5%, không vụ nào sập được ≥ 10%, trong khi bài gốc chọn 29 vụ đúng theo điều kiện "sập ≥ 10% trong 2 giờ".

---

## Bảng 1 — co_so qua từng giai đoạn (trung vị 5 seed, `hieu_chinh_truoc_sau.csv`)

| Chỉ số | 0 ban đầu | 1 nền hữu hạn | 2 L_A = 0,75·fV/c_V | 3 đuôi + kho 25k |
|---|---|---|---|---|
| Độ sập (giá step, trước rút → cuối xả) | −34,4% | −10,2% | −10,2% | −50,0% |
| Giá sập sau rút (VWAP, bài gốc) | −10,4% | −4,5% | −4,2% | −15,5% |
| lift Prep | 1,82 | 1,82 | 1,82 | 1,78 |
| **lift Post** | **1,15** | 0,195 | 0,195 | **0,78** |
| RV Prep | 0,016 | 0,017 | 0,017 | 0,016 |
| RV Attack | 0,178 | 0,113 | 0,113 | 0,480 |
| **RV Post** | 0,282 | 0,117 | 0,117 | **1,503** |
| **Tường cạn tại t_b** | **50%** | 50% | 86,6% | **86,6%** |
| L_V / L_A | 1,00 | 1,00 | 0,154 | 0,154 |
| Thiệt hại nạn nhân (full) | 1.879 | 747 | 124 | 385 |
| Lợi nhuận kẻ tấn công (paper) | 28.399 | 18.227 | 8.813 | 11.370 |
| Chi phí trợ cấp | 4.729 | 4.234 | 4.234 | 4.445 |

Đọc bảng:
- Thay đổi 1 kéo Post xuống dưới nền nhưng quá tay (≈ 0,2), và làm độ sập kẹt ở mép dải.
- Thay đổi 2 chỉ dời tỷ trọng tường từ 50% lên 87%. Nó không động tới khối lượng hay giá, đúng như kỳ vọng vì farmer chỉ nhìn tổng `L` trong tick.
- Thay đổi 3 trả lại một Post vừa phải (0,78) và đưa RV Post lên cao nhất.

Lợi nhuận kẻ tấn công giảm từ 28k xuống 11k chủ yếu do kho nhỏ đi (60k → 25k) và nạn nhân nhỏ đi (`L_V/L_A` từ 1 xuống 0,15).

## Bảng 2 — bộ tổ hợp 150 log, trước/sau thay đổi 3

| Dấu hiệu (tỷ lệ vụ, trừ khi ghi trung vị) | Trước thay đổi 3 (band 0,15–0,40, không đuôi, kho 60k) | Sau, `rq1-v1` | Bài gốc (x/29) |
|---|---|---|---|
| Sập ≥ 10% | 100% | 99% | 100% |
| lift Post < 1× | 100% (trung vị 0,19) | **81%** (trung vị 0,855) | 79% |
| RV Post cao nhất | 17% | **95%** | — |
| Giá sập < −10% (VWAP) | 41% (trung vị −9,5%) | 59% (trung vị −10,4%) | 69% |
| Giá sập < −10% (mốc trước burn, phụ) | — | 79% | — |
| Tường cạn ≥ 80% | 100% | 100% | 86% |
| Độ sập (giá step) trung vị, P10–P90 | ≈ −band (dừng ở mép dải) | −37%, −50% … −11% | — |

Nguồn cột "trước": các lần chạy ghi trong nhật ký `SYNC.md` ngày 14/10/2026, trước commit `415f8ae`, tính theo tiêu chí kiểm định cũ (trung vị). Cột "sau": `kiemdinh.csv` ở `rq1-v1`, tiêu chí theo phân phối mà Đức chốt.

## Khác biệt còn lại so với bài gốc (ghi trung thực, không hiệu chỉnh tiếp)

- **Prep:** không vụ nào có lift < 1× (bài gốc 9/29); trung vị 1,77×. Farmer được trợ cấp luôn có mặt từ đầu, và tường luôn hút thêm khối lượng. Prep tăng theo Q: trung vị 1,31 / 1,81 / 2,94 ứng với Q = 12k / 24k / 48k.
- **Post:** dồn vào hai khoảng < 1× và 1–1,5×; bài gốc có đuôi > 2×.
- **Tường cạn:** dồn vào 80–99%; bài gốc 18/29 vụ ở đúng 100% (nạn nhân còn kẹt). Victim toàn tri luôn giữ một phần nhỏ `L_V*`, nên phần không phải tường không bao giờ bằng 0.
- **Sập ≥ 10%:** 1/150 log không đạt (L27_18 seed 1: kho 15k, bg_band 0,40, L_A 8·10⁸ — kho nhỏ nhất gặp tường dày và dải rộng nhất).

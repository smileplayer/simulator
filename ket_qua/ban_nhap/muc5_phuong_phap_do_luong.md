# 5. Phương pháp đo lường (bản sửa cho khớp code, 15/10/2026)

> Bản nháp của B, viết thay mục 5 trong tài liệu chung. Code tương ứng: `metrics/` (`phases.py`, `indicators.py`, `pnl.py`, `report.py`, `validate.py`).

Mọi chỉ số tính **chỉ từ log sự kiện** của simulator (mint, burn, collect, swap, subsidy, step; INTERFACE mục 4) và meta của lượt chạy; ngoại lệ duy nhất là phản thực "bán thẳng" (dưới đây) dựng lại bể từ log rồi hỏi giá bằng `quote_swap` của engine. Cách đo theo §5–§6 bài gốc, kể cả khi bài gốc có lựa chọn khác hợp lý hơn; chỗ nào chúng tôi thêm biến thể, biến thể được ghi là chỉ số phụ. Đơn vị: tiền tính bằng token định giá (token1, USDT), thời gian tính bằng bước 1 giờ.

## 5.1 Mốc thời gian và pha

Tường là khoảng một tick có thanh khoản (cộng mọi địa chỉ) đạt đỉnh lớn nhất; mốc được tìm bằng cách phát lại mint/burn trên khoảng đó, không dùng nhãn vai trò của simulator.

| Mốc | Định nghĩa (theo bài gốc) |
|---|---|
| `t_m` | mint đầu tiên vào tick tường |
| `t_50` | lần đầu thanh khoản tick tường ≥ 50% đỉnh |
| `t_peak` | lần đầu chạm đỉnh |
| `t_0` | lần đầu sau đỉnh tụt dưới 95% đỉnh (§6.1.1); đối chiếu thêm burn lớn nhất trên tick tường (§5) |
| `t_oot` | swap đầu tiên từ `t_0` đưa giá ra khỏi tick tường |
| `t_b` | giờ đầu tiên từ `t_0` có giá ≤ 90% giá biên dưới tick tường |

Bốn pha với `W = 24` giờ: Before `[t_m − W, t_m)`, Prep `[t_m, t_0)`, Attack `[t_0, t_b]`, Post `(t_b, t_b + W]`. Vụ không sập đủ 10% không có Attack/Post và bị loại khỏi các chỉ số sau `t_0`.

## 5.2 Bốn chỉ số chính

**Vai trò** được suy như bài gốc từ hành vi: *nạn nhân* còn thanh khoản trên tick tường tại `t_end`; *wall provider* vừa mint vừa burn trên tick tường trong `[t_m, t_end]`; *pressure trader* có swap bán alpha lấy token1 trong `[t_0, t_end]`; *kẻ tấn công* thỏa cả hai vai sau. `t_end ∈ {t_b, t_oot}`, mặc định `t_b`.

| Chỉ số | Định nghĩa | Ghi chú |
|---|---|---|
| Thiệt hại nạn nhân | `E_full = (y_dep + p̂·x_dep) − (y_back + p̂·x_back)`, thiệt hại = `max{0, E}`; `x, y` = alpha, token1 nạp vào và nhận lại (burn tới `t_end` + phần còn kẹt theo giá cuối `t_end`); `p̂` = trung bình VWAP giờ `t_b` và `t_b + 1` | **Phí LP tách riêng, không trừ** — bài gốc chỉ đo phần thiệt hại do cú sập. Bản bài gốc `E_nonalpha = y_dep − y_back − p̂·x_back` chỉ đếm non-alpha, trừ toàn bộ alpha nhận lại (kể cả alpha tự nạp), nên luôn ≤ bản đầy đủ; hai bản chênh đúng `p̂·x_dep` |
| Lợi nhuận kẻ tấn công | Chính (bài gốc, `paper`): token1 thu từ swap chiều sập trong `[t_0, t_end]`. **Tăng thêm** (`excess`, Theorem 6): `paper` trừ giá trị khi bán thẳng cùng lượng alpha đó vào bể đã bỏ tường và nạn nhân, dựng lại từ log ngay trước burn tường đầu tiên, dừng ở giá vốn `z̄ = √(c_A/(1−f))` (phần không bán được tính theo `c_A`). Đầy đủ (`full`): dòng token1 ròng của phần tấn công trong `[t_m, t_end]` (mint, burn, swap bán, phí collect) + thay đổi kho alpha × `c_A` + lãi săn trợ cấp | Đo từ dòng tiền, không suy từ thiệt hại nạn nhân. `paper` gồm cả tiền xả vào thanh khoản nền nên dương cả khi không có nạn nhân; `excess` = 0 đúng khi không có nạn nhân (test). Khi kẻ tấn công cũng săn trợ cấp, lệnh mua của nó được tách thành **lãi farm** = thưởng đã nhận − Σ(v − P_e·x), không vào `paper`, `excess`; thưởng còn treo báo riêng |
| Chi phí trợ cấp | tổng `amount1` của các dòng `subsidy` **cộng khoản trả trễ đã chốt chưa tới hạn** khi hết kịch bản (`meta.subsidy_pending`); khoản bị thu hồi (clawback) báo riêng, không cộng; tách phần trả cho kẻ tấn công | Bài gốc không đo; dạng tuyến tính `σ·min{v, Q}` và dạng log. Không cộng khoản treo thì "trả trễ" trông rẻ giả tạo |
| Thanh khoản bể | `L_active` theo giờ; trung bình Before so với Post; độ tụt tick tường tại `t_b`: `drop = (L_max − L(t_b)) / L_max` (§6.2.4) | `L(t)` cộng mọi địa chỉ trên tick tường, nên phần nạn nhân còn kẹt làm `drop` < 100% |

Các chỉ số thị trường theo pha (§6.2): **volume lift** `Lift_s = μ_s / max(μ_Before, ε)`, `μ` = khối lượng token1 trung bình mỗi giờ. Chỉ số chính tính trên **mọi swap** (gồm arbitrageur, như bài gốc đếm mọi dòng non-alpha on-chain); chỉ số phụ bỏ arbitrageur. **Biến động** `RV = √Σ r_i²`, `r_i = ln(1,0001)·(tick_i − tick_{i−1})` qua các swap liên tiếp trong pha. **Độ dời giá** theo VWAP giờ: `before = (P(t_m) − P(t_m − 1)) / P(t_m)`, `attack = (P̄(t_b) − P(t_0)) / P(t_0)`. Biến thể phụ của `attack` lấy mốc là giá bể ngay trước burn tường đầu tiên, vì VWAP giờ `t_0` đã gồm cú xả nên ước thấp độ sập.

## 5.3 Hai chỉ số dẫn xuất

Hiệu quả chi tiêu: `eff_L = L̄_Post / S` và `eff_gain = (L̄_Post − L̄_Before) / S`, `S` = tổng trợ cấp (đơn vị L trên mỗi token1); `eff_gain ≤ 0` nghĩa là trợ cấp không mua thêm được thanh khoản nào. Tỷ lệ rò rỉ = lợi nhuận kẻ tấn công / `S` (bản bài gốc, bản tăng thêm và bản đầy đủ), họ hàng chỉ số "cải thiện trên mỗi đô-la khuyến khích" của StableSims.

## 5.4 Kiểm định hai lớp

Theo Tarantelli 2026, mục tiêu là tái lập **dấu hiệu**, không tái lập quỹ đạo.

- **Lớp cơ học** (test engine của vai A): bảo toàn token, phí ≥ 0, cross-tick khớp bể tham chiếu độc lập (sai < 1e-8), victim toàn tri đạt `L_V*/L_A = 1` tại `L_A = fQ/(4c_V)` (test của vai C).
- **Lớp dấu hiệu** (`validate_rq1`): kiểm theo **phân phối qua các vụ**. Mỗi tiêu chí là tỷ lệ vụ mô phỏng thỏa một phát biểu của bài gốc, đặt cạnh tỷ lệ tương ứng của bài gốc (x/29); đạt khi tỷ lệ mô phỏng ≥ 50% (mọi phát biểu của bài gốc đều đúng với đa số vụ), riêng "có vụ Attack > 5×" chỉ cần ít nhất một vụ. Mười một phát biểu chính: sập ≥ 10%; Δbuild ≥ 1 ngày; Δextract < 24 giờ; lift Attack ≥ 1×; có vụ lift Attack > 5×; lift Post < 1×; RV Prep < RV Attack; RV Post cao nhất; |độ dời giá quanh `t_m`| < 10%; độ dời giá sau rút < −10%; tường cạn ≥ 80%. Không đặt ngưỡng cho lift Prep; phân phối của nó được so trực tiếp với Bảng 4 bài gốc. Kèm theo là ba bảng chia nhóm như Bảng 4 (volume lift), Bảng 6 (độ dời giá), Bảng 7 (độ tụt tại `t_b`) của bài gốc.

## 5.5 Thiết kế thí nghiệm và khoảng tin cậy

**Bộ tổ hợp RQ1:** 30 cấu hình — mảng trực giao L27 trên sáu yếu tố ba mức (`L_A`, `k = c_V·L_A/(fV)`, `σ`, `Q`, `bg_band`, kho kẻ tấn công) cộng 3 cấu hình trợ cấp log — mỗi cấu hình **10 seed**, tổng 300 lượt. GĐ2: cùng 30 cấu hình × 10 seed cho mỗi biện pháp và loại nạn nhân; phản thực = cùng cấu hình, cùng seed, không biện pháp.

**Vì sao 10 seed và bootstrap phân cụm.** Trên 150 lượt đầu, phần phương sai do seed chỉ 5–36% (lift Prep 6%, lift Post 27%, độ sập 36%); phần lớn là khác biệt giữa cấu hình. Thêm seed vì thế giúp ít hơn thêm cấu hình, nhưng 13/30 cấu hình có lift Post lẫn lộn hai phía 1× giữa 5 seed, nên 5 seed chưa đủ ổn định cho từng cấu hình. Các lượt cùng cấu hình không độc lập, nên mọi tỷ lệ và trung vị trong bảng kiểm định kèm **khoảng tin cậy 95% bằng bootstrap phân cụm** (`metrics.validate.bootstrap_ci`): mỗi lần lấy lại 30 cấu hình có hoàn lại, trong mỗi cấu hình lấy lại seed có hoàn lại, B = 2.000, khoảng bách phân vị, seed bootstrap cố định để tái lập. Với 30 cụm, sai số của một tỷ lệ "x% vụ thỏa" tới **±~18 điểm %** (1,96·√(0,25/30)) khi mỗi cấu hình thỏa trọn hoặc không; vì vậy tỷ lệ mô phỏng chỉ được đặt cạnh x/29 của bài gốc kèm khoảng tin cậy.

**Dòng ngẫu nhiên độc lập giữa cấu hình.** Mỗi lượt sinh số ngẫu nhiên từ `SeedSequence([seed, crc32(mã cấu hình)])`, tách riêng nguồn giao dịch nền và giá ngoài, nên cùng số seed ở hai cấu hình là hai bản nhiễu độc lập và giả định "lượt lồng trong cấu hình" của bootstrap là đúng. Kiểm tra trên 300 lượt: tỷ lệ lift Post < 1× theo seed có độ lệch chuẩn 7,7 điểm %, bằng mức nhiễu nhị thức 7,4 điểm %; seed 0–4 và 5–9 không khác nhau (hoán vị trong cấu hình, p = 0,66). Bootstrap chéo cấu hình × seed (`bootstrap_ci(..., cheo="seed")`, vẫn ghi ở cột `ci_*_cheo` của `kiemdinh.csv` để đối chiếu) cho khoảng gần trùng. (Bản trước dùng chung dòng ngẫu nhiên theo số seed cho mọi cấu hình, tạo yếu tố seed chéo: seed 5 chỉ có 30% cấu hình đạt Post < 1×.)

**GĐ2 — bootstrap cặp** (`bootstrap_cap`): với mỗi biện pháp, tính hiệu `chỉ số(bp) − chỉ số(không biện pháp)` trên từng cặp cùng cấu hình, cùng seed, cùng loại nạn nhân (và cùng phần farm của kẻ tấn công khi có), rồi bootstrap phân cụm theo cấu hình trên các hiệu đó. Ghép cặp cùng seed khử phần nhiễu chung (kể cả yếu tố seed chéo nói trên) nên khoảng tin cậy của hiệu hẹp hơn nhiều so với so hai nhóm độc lập.

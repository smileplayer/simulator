# 5. Phương pháp đo lường (bản sửa cho khớp code, 14/10/2026)

> Bản nháp của B, viết thay mục 5 trong tài liệu chung. **Không commit lên git** (`ket_qua/ban_nhap/` nằm trong `.gitignore`). Code tương ứng: `metrics/` (`phases.py`, `indicators.py`, `pnl.py`, `report.py`, `validate.py`). Mục 5.5 để trống chờ quyết số seed.

Mọi chỉ số tính **chỉ từ log sự kiện** của simulator (mint, burn, collect, swap, subsidy, step; INTERFACE mục 4), không gọi vào engine. Cách đo theo §5–§6 bài gốc, kể cả khi bài gốc có lựa chọn khác hợp lý hơn; chỗ nào chúng tôi thêm biến thể, biến thể được ghi là chỉ số phụ. Đơn vị: tiền tính bằng token định giá (token1, USDT), thời gian tính bằng bước 1 giờ.

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
| Lợi nhuận kẻ tấn công | Chính (bài gốc): token1 thu từ swap chiều sập trong `[t_0, t_end]`. Đầy đủ: dòng token1 ròng trong `[t_m, t_end]` (mint, burn, swap, phí collect, trợ cấp nếu có) + thay đổi kho alpha × giá vốn `c_A` | Đo từ dòng tiền, không suy từ thiệt hại nạn nhân. Bản đầy đủ phụ thuộc mạnh vào `c_A` |
| Chi phí trợ cấp | tổng `amount1` của các dòng `subsidy` | Bài gốc không đo; dạng tuyến tính `σ·min{v, Q}` và dạng log |
| Thanh khoản bể | `L_active` theo giờ; trung bình Before so với Post; độ tụt tick tường tại `t_b`: `drop = (L_max − L(t_b)) / L_max` (§6.2.4) | `L(t)` cộng mọi địa chỉ trên tick tường, nên phần nạn nhân còn kẹt làm `drop` < 100% |

Các chỉ số thị trường theo pha (§6.2): **volume lift** `Lift_s = μ_s / max(μ_Before, ε)`, `μ` = khối lượng token1 trung bình mỗi giờ. Chỉ số chính tính trên **mọi swap** (gồm arbitrageur, như bài gốc đếm mọi dòng non-alpha on-chain); chỉ số phụ bỏ arbitrageur. **Biến động** `RV = √Σ r_i²`, `r_i = ln(1,0001)·(tick_i − tick_{i−1})` qua các swap liên tiếp trong pha. **Độ dời giá** theo VWAP giờ: `before = (P(t_m) − P(t_m − 1)) / P(t_m)`, `attack = (P̄(t_b) − P(t_0)) / P(t_0)`. Biến thể phụ của `attack` lấy mốc là giá bể ngay trước burn tường đầu tiên, vì VWAP giờ `t_0` đã gồm cú xả nên ước thấp độ sập.

## 5.3 Hai chỉ số dẫn xuất

Hiệu quả chi tiêu: `eff_L = L̄_Post / S` và `eff_gain = (L̄_Post − L̄_Before) / S`, `S` = tổng trợ cấp (đơn vị L trên mỗi token1); `eff_gain ≤ 0` nghĩa là trợ cấp không mua thêm được thanh khoản nào. Tỷ lệ rò rỉ = lợi nhuận kẻ tấn công / `S` (bản bài gốc và bản đầy đủ), họ hàng chỉ số "cải thiện trên mỗi đô-la khuyến khích" của StableSims.

## 5.4 Kiểm định hai lớp

Theo Tarantelli 2026, mục tiêu là tái lập **dấu hiệu**, không tái lập quỹ đạo.

- **Lớp cơ học** (test engine của vai A): bảo toàn token, phí ≥ 0, cross-tick khớp bể tham chiếu độc lập (sai < 1e-8), victim toàn tri đạt `L_V*/L_A = 1` tại `L_A = fQ/(4c_V)` (test của vai C).
- **Lớp dấu hiệu** (`validate_rq1`): kiểm theo **phân phối qua các vụ**. Mỗi tiêu chí là tỷ lệ vụ mô phỏng thỏa một phát biểu của bài gốc, đặt cạnh tỷ lệ tương ứng của bài gốc (x/29); đạt khi tỷ lệ mô phỏng ≥ 50% (mọi phát biểu của bài gốc đều đúng với đa số vụ), riêng "có vụ Attack > 5×" chỉ cần ít nhất một vụ. Mười một phát biểu chính: sập ≥ 10%; Δbuild ≥ 1 ngày; Δextract < 24 giờ; lift Attack ≥ 1×; có vụ lift Attack > 5×; lift Post < 1×; RV Prep < RV Attack; RV Post cao nhất; |độ dời giá quanh `t_m`| < 10%; độ dời giá sau rút < −10%; tường cạn ≥ 80%. Không đặt ngưỡng cho lift Prep; phân phối của nó được so trực tiếp với Bảng 4 bài gốc. Kèm theo là ba bảng chia nhóm như Bảng 4 (volume lift), Bảng 6 (độ dời giá), Bảng 7 (độ tụt tại `t_b`) của bài gốc.

## 5.5 Thiết kế thí nghiệm

*(Chờ quyết: số seed mỗi cấu hình — hiện 5, kế hoạch ban đầu ≥ 10 — và có thêm khoảng tin cậy bootstrap hay không.)* Bộ tổ hợp RQ1: 30 cấu hình (mảng trực giao L27 trên `L_A`, `k = c_V·L_A/(fV)`, `σ`, `Q`, `bg_band`, kho kẻ tấn công, cộng 3 cấu hình trợ cấp log). GĐ2: quét lưới `(σ, Q)`; phản thực = cùng seed có / không có biện pháp.

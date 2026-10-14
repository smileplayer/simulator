# Kế hoạch simulator

Tài liệu thiết kế cho `04_Simulator/`. Các quyết định đánh dấu **[CHỐT]** đã thống nhất với Đức; muốn đổi thì bàn lại trước.

## 1. Lộ trình bốn giai đoạn

| GĐ | Nội dung | Sản phẩm | Trả lời |
|---|---|---|---|
| 1 | Engine cross-tick; 3 tác nhân; 4 chỉ số. Mọi vị thế rộng 1 tick; victim tối ưu `L_V` | Tái lập cuộc tấn công, đạt bộ tiêu chuẩn kiểm định | RQ1 |
| 2 | Quét `(σ, Q)`; chạy cặp phản thực bật/tắt hạ trần, trả trễ, cảnh báo (tăng `c_V`), trần động | Bản đồ ba vùng thiết kế; `Q*` thực nghiệm; đánh giá 3–4 biện pháp của bài gốc | RQ2 |
| 3 | Mở `w` thành biến; victim tối ưu `(C_V, w)`; phân bổ phí theo `φ(w)` | Ngưỡng `φ` để một tick thôi tối ưu; cái giá hiệu quả vốn | RQ3 |
| 4 | (Tùy thời gian) bộ phát hiện dựng tường theo luật, chạy trực tuyến trong simulator; hoặc quét `c_V` | Kết quả bổ sung | — |

Nguyên tắc: GĐ1 + GĐ2 đã là một project hoàn chỉnh (lấp được khoảng trống bài gốc tự nêu). GĐ3 là phần cộng thêm có rủi ro cao nhất, để sau cùng.

## 2. Kiến trúc ba lớp

```
04_Simulator/
  engine/        lớp cơ chế: Pool, Position, tick map, swap, mint/burn, tích phí
  agents/        lớp tác nhân: Farmer, VictimLP (toàn tri / thích nghi), Attacker
  metrics/       lớp đo lường: chuỗi thời gian + 4 chỉ số + chỉ số dẫn xuất
  defenses/      điểm móc can thiệp: cap, vesting, risk warning, dynamic cap, range-aware
  scenarios/     cấu hình thí nghiệm, bộ chạy phản thực (cùng seed, bật/tắt)
  tests/         unit test engine + test kiểm định với lý thuyết
```
Đây là bố cục gợi ý, chưa có mã.

## 3. Lớp cơ chế

**[CHỐT]** Cross-tick ngay từ GĐ1, vì cú xả đi xuyên nhiều tick (giá giảm > 10% là hơn nghìn tick).
**[CHỐT]** `Position(tick_lower, tick_upper, L, owner)` tổng quát; tác nhân GĐ1 luôn truyền `tick_upper = tick_lower + 1`. Không tạo kiểu `OneTickPosition`.

```
z = √P, P(i) = 1.0001^i
Trong một tick (L không đổi):  Δz = Δy / L,   Δ(1/z) = Δx / L
Chạm biên tick → cross: L += liquidityNet[tick] (theo chiều)
Thành phần vị thế khi z_L < z < z_U:  y = L(z − z_L),  x = L(1/z − 1/z_U)
Tích phí:  feeGrowth += f·Δin / L_active
```
Có thể đơn giản hóa vùng dưới tick bị tấn công thành thanh khoản nền hằng số.

Trợ cấp (thử cả hai — **[CHỐT]**):
- tuyến tính có trần: `reward = σ·min{v, Q}` (bài gốc)
- log (Binance Alpha, nguồn thứ cấp): điểm ≈ log₂ khối lượng *mua*, cộng dồn 15 ngày

## 4. Lớp tác nhân

**Farmer** — tối ưu `U_T(v) = σ·min{v,Q} − f·v − MC(v)`.
**[CHỐT]** `MC(v)` tính bằng cách mô phỏng swap trên trạng thái bể hiện tại (trượt giá thật), không đặt hàm cứng.

**Victim LP** — **[CHỐT]** phải tối ưu hóa, hai loại:
- *Toàn tri:* biết `Q`, chơi đúng `L_V* = max{0, √(fQL_A/c_V) − L_A}` → kiểm định engine.
- *Thích nghi:* chỉ thấy lợi suất quá khứ, ước lượng rồi tối ưu → thực tế hơn, phản ánh "không phân biệt được nguồn khối lượng".
- **[CHỐT]** `c_V` tính **theo vốn** khi sang GĐ3.

**Attacker** — chọn `L_A`, thời gian giữ tường, thời điểm rút `t_0`; xả tới `z₂ = max{z_floor, z_Ā, z̄}` (hết thanh khoản / hết kho / chạm giá vốn `c_A`). Rút toàn bộ `L_A` trước khi xả.

## 5. Bốn chỉ số

| Chỉ số | Cách tính |
|---|---|
| Thiệt hại nạn nhân | `max{0, V_hold − V_thực}`; `V_hold` = giá trị nếu chỉ ôm tài sản, định giá tại `t_b`; `V_thực` = token rút ra + token còn kẹt; alpha còn lại định giá bằng VWAP `[t_b, t_b+1h]`. Bản bài gốc chỉ đếm phần non-alpha |
| Lợi nhuận kẻ tấn công | phí thu + dòng token1 ròng trong `[t_0, t_b]` − giá vốn − ma sát; đo độc lập |
| Chi phí trợ cấp | `Σ σ·min{v_i, Q}` qua mọi farmer, mọi cửa sổ (bài gốc **không** đo) |
| Thanh khoản bể | `L_active(t)`; so trung bình `[t_m−24h, t_m)` với `(t_b, t_b+24h]` |

Dẫn xuất: **hiệu quả chi tiêu** = thanh khoản thật còn lại sau tấn công / tổng trợ cấp; **tỷ lệ rò rỉ** = lợi nhuận kẻ tấn công / tổng trợ cấp.

## 6. Tiêu chuẩn kiểm định (từ kết quả thực nghiệm bài gốc)

| Dấu hiệu | Phải đạt |
|---|---|
| Thời gian | chuẩn bị theo ngày, thu hoạch theo giờ |
| Khối lượng Prep | trên nền nhưng vừa phải (~1–1,5×) |
| Khối lượng Attack | phân tán, một số kịch bản > 5× |
| **Khối lượng Post** | **dưới nền** — quan trọng nhất, chứng tỏ dòng lệnh phụ thuộc vào tường |
| Biến động | thấp lúc Prep, bật vọt lúc Attack, cao nhất Post |
| Giá | gần 0 quanh lúc dựng tường; âm lớn sau khi rút |
| Lý thuyết | victim toàn tri cho đúng `L_V*`; tại `L_A = fQ/(4c_V)` thấy `L_V*/L_A ≈ 1` |

Có thể lấy cách kiểm định của Tarantelli 2026 (so volatility, kurtosis, hình dạng thanh khoản theo tick với dữ liệu thật) làm chuẩn bổ sung. Mốc hiệu chỉnh khác: pha loãng LP trong JIT (xác minh con số trong PDF của Xiong et al.).

## 7. GĐ3 — phân bổ phí theo độ rộng

**[CHỐT]** Chia lại phí có trọng số, tổng phí không đổi:
```
Share_i = L_i·φ(w_i) / Σ_j L_j·φ(w_j)          w = tick_upper − tick_lower
```
**[CHỐT]** Ở một tick, `φ(1)` triệt tiêu → không tác dụng. Bản "đốt phần bị phạt" tương đương hạ `f` → không dùng.

Với vốn `C`, độ rộng `w`: `L(w) ≈ C/(κw)` → trọng số `∝ φ(w)/w`.

| `φ(w)` | `φ/w` | Lựa chọn của LP |
|---|---|---|
| 1 | giảm | luôn một tick |
| `w/w₀` | hằng | bàng quan |
| `(w/w₀)²` | tăng | ưu tiên dải rộng |

→ Giả thuyết cần kiểm chứng: `φ` phải **siêu tuyến tính** ở vùng `w` nhỏ.

Giải bài toán victim hai biến: với mỗi `w` trên lưới (1, 2, 5, 10, 50, 200…), có nghiệm đóng
```
g(w) = φ(w)/(κw),   W_A = L_A·φ(w_A)
C_V*(w) = [√(f·Q·W_A·g(w)/c) − W_A] / g(w)
```
rồi chọn `w` cho `Π_V` lớn nhất. Thí nghiệm chính: họ `φ(w) = min(1, (w/w₀)^α)`, tìm `α` nhỏ nhất làm `argmax w` rời khỏi 1; đo thiệt hại nạn nhân (thiệt hại từng phần khi dải rộng) và cái giá hiệu quả vốn với LP lành mạnh.

Cơ chế tác động phải nói đúng: **không** ngăn được việc dựng tường (kẻ tấn công không cần phí); làm nạn nhân trải rộng nên chỉ một phần vốn nằm trên đường sập.

## 8. Checklist GĐ1

- [ ] Engine: swap trong một tick khớp công thức tay (`Δz = Δy/L`)
- [ ] Engine: cross-tick cập nhật `L` đúng; bảo toàn token vào = ra + phí
- [ ] Engine: thành phần vị thế `x, y` đúng ở ba trạng thái (dưới / trong / trên dải)
- [ ] Farmer: không giao dịch quá `Q`; `V` tăng khi `L_A` tăng
- [ ] Victim toàn tri khớp Lemma 4; mốc `L_V*/L_A ≈ 1`
- [ ] Attacker: rút trước khi xả; dừng đúng ba sàn
- [ ] 4 chỉ số + chuỗi thời gian
- [ ] Đạt bộ tiêu chuẩn kiểm định ở mục 6

## 9. Câu hỏi mô hình còn mở

- Thời gian rời rạc theo khối hay theo giờ? Bài gốc đo theo giờ/ngày.
- Farmer giao dịch hai chiều thế nào để khối lượng gộp lớn mà giá vẫn trong tick? (Giả định 2 của bài gốc chặt hơn thực tế.)
- Victim thích nghi dùng cửa sổ lợi suất quá khứ dài bao nhiêu?
- Phân phối dòng lệnh tự nhiên (không trợ cấp) để làm mức nền.

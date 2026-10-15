# 4. Mô hình mô phỏng — bản nháp

> Bản nháp của vai C, 15/10/2026. Số liệu lấy từ code và cấu hình: `engine/`, `agents/`, `scenarios/` (`run.py`, `batch.py`, `quet_gd2.py`, `quet_gd3.py`, `hieu_chinh.py`), `defenses/`, `scenarios/configs/co_so.json`, `scenarios/configs/rq1_tohop.json`. Hợp đồng giữa các mô-đun: `INTERFACE.md`. Cách đo chỉ số và khoảng tin cậy để ở Mục 5; mục này chỉ mô tả thế giới được mô phỏng và cách sinh dữ liệu.

Simulator là mô hình dựa trên tác nhân (agent-based) chạy trên một bể CLMM kiểu Uniswap v3. Mục tiêu không phải tái tạo quỹ đạo của từng vụ có thật. Mục tiêu là kiểm tra xem các tác nhân hành xử tối ưu theo mô hình cân bằng của Lu et al. (Theorem 1, Lemma 4, Lemma 5), khi đặt chung trong một bể có cơ chế đầy đủ, có sinh ra đúng các **dấu hiệu thực nghiệm** của 29 vụ hay không (RQ1). Sau đó dùng chính bể đó làm phòng thí nghiệm phản thực cho các biện pháp (RQ2, RQ3). Có ba nguyên tắc. (i) Tác nhân tối ưu theo lý thuyết của bài gốc, không có luật hành vi tùy ý. (ii) Mọi chi phí thực hiện, ví dụ trượt giá, được đo trên bể thật chứ không đặt bằng hàm cứng. (iii) Mọi ngẫu nhiên nằm ở môi trường (giao dịch nền, giá ngoài), còn tác nhân là tất định.

## 4.1 Tổng quan kiến trúc

**Ba lớp.** Mã nguồn tách thành lớp cơ chế (`engine/`), lớp tác nhân và kịch bản (`agents/`, `scenarios/`, `defenses/`) và lớp đo lường (`metrics/`). Lớp đo lường **chỉ đọc log sự kiện**, không gọi vào engine. Nhờ vậy cách đo độc lập với cách sinh dữ liệu, và có thể chạy cùng một bộ đo trên log giả, log mô phỏng, và về nguyên tắc cả log on-chain.

**Engine CLMM xuyên tick.** Bể giữ trạng thái theo tick như v3 (`liquidity_net/gross`, `feeGrowthOutside`, checkpoint phí theo vị thế). Vì vậy vị thế có độ rộng bất kỳ, và "một tick" chỉ là trường hợp `w = tick_upper − tick_lower = 1` (quyết định chốt 1–2). Quy ước: token0 `x` là token alpha bị xả, token1 `y` là token định giá (USDT), mọi giá trị tiền tính bằng token1, và

```
P(i) = 1,0001^i,   z = √P
Trong một tick (L không đổi):  Δz = (1−f)·Δy_in / L,   Δ(1/z) = (1−f)·Δx_in / L
Thành phần vị thế khi z_L < z < z_U:  x = L(1/z − 1/z_U),   y = L(z − z_L)
Phí: f·Δin thu trên token đi vào, feeGrowth += f·Δin / L_active
```

Một lệnh swap đi lần lượt qua các tick. Khi chạm biên, lệnh cộng `liquidity_net` theo chiều đi rồi tiếp tục, cho tới khi hết lượng vào, chạm giới hạn giá, hoặc hết thanh khoản. Cơ chế này cần ngay từ GĐ1, vì cú xả làm giá giảm hơn 10%, tức đi qua hơn một nghìn tick. Số dùng `float` thường, không mô phỏng Q64.96. Engine có `quote_swap` để hỏi giá mà không đổi trạng thái (farmer dùng để tính trượt giá). Từ GĐ3, engine có thêm tham số `fee_weight = φ(w)`: phí được chia theo thanh khoản có trọng số `L·φ(w)`, còn giá vẫn đi theo `L` thật (4.4). Engine được kiểm bằng 7 tệp test: bảo toàn token, phí không âm, khớp với một bể tham chiếu độc lập (sai lệch < 10⁻⁸), phát lại log. Tốc độ khoảng 7 µs mỗi lệnh. Toàn repo có 283 test.

**Log sự kiện.** Mọi thao tác đổi trạng thái (`mint`, `burn`, `collect`, `swap`) ghi một dòng. Bộ chạy ghi thêm dòng `subsidy` (nền tảng trả thưởng) và dòng `step` (ảnh chụp giá, `L_active`, giá ngoài `P_e` ở cuối mỗi bước). Mỗi dòng có `t`, `seq` (thứ tự trong bước), `owner` dạng `vai:số` (`attacker:0`, `victim:0`, `farmer:k`, `bg:k`, `arb:0`, `lp:k`, `platform`), lượng token theo quy ước nhìn từ phía bể (dương = đi vào bể), phí và trạng thái bể sau sự kiện. Meta của lượt chạy lưu tham số và các mốc thật (`t_rut`, `wall_tick`, …), để kiểm chứng chứ không để đo.

**Thời gian và thứ tự trong bước.** Một bước bằng một giờ, vì dữ liệu của bài gốc theo giờ (giá Alpha, cửa sổ `t_b` hai giờ, VWAP một giờ). Thứ tự trong giờ được ghi bằng `seq`. Trong mỗi bước `t`, bộ chạy bảo đảm thứ tự sau:

1. (trần động, nếu có) đặt trần hiện hành;
2. giao dịch nền `bg:0`;
3. farmer, gồm cả phần farm của `attacker:0` khi có;
4. nạn nhân `victim:*`;
5. LP lành mạnh `lp:*` (GĐ3);
6. kẻ tấn công: dựng tường, rút tường, xả;
7. arbitrageur `arb:0` kéo giá bể về `P_e(t)`, nghỉ khi kẻ tấn công đang xả;
8. nếu `(t+1)` chia hết cho `subsidy_window` thì nền tảng chốt thưởng của cửa sổ;
9. thu hồi (clawback, nếu có), rồi trả các khoản thưởng tới hạn;
10. (trần động) nền tảng đọc `L` của tick chứa giá;
11. ghi dòng `step`.

Ở bước cuối, mọi vị thế LP được `collect` để phí hiện trong log.

## 4.2 Thị trường và trợ cấp

**Giá ngoài.** `P_e(t)` là bước ngẫu nhiên log-chuẩn, `P_e(t) = P_e(t−1)·exp(vol·ε_t)` với `ε_t ~ N(0,1)`. Mỗi bước rút đúng một cú sốc, từ một dòng ngẫu nhiên riêng (4.5). Độ biến động đổi theo pha:

- trước khi dựng tường, `vol_pre = 0,002` mỗi giờ;
- khi tường đứng, `P_e` được **neo** vào giữa tick tường với `vol_prep = 0`. Đây là giả định "giá ghim" của bài gốc: thị trường ngoài định giá alpha quanh mức của tường. **Giá bị ghim là điều kiện cần của tấn công:** bể là nơi hình thành giá (token Alpha giao dịch chủ yếu trên chính bể này, không có giá ngoài để arb neo). Nếu có giá ngoài trôi tự do cộng arb, tường một tick không giữ được giá (xem 4.7, mục 11 và 6.6);
- trong các bước xả, `P_e` neo theo giá bể. Ta giả định bể là nơi định giá chính của alpha, nên không có thanh khoản ngoài để kéo giá lại;
- sau đó giá tiếp tục ngẫu nhiên với `vol_post = 0,01`.

Bể khởi đầu ở giữa tick 0 (`P₀ = 1,0001^{0,5} ≈ 1,00005`).

**Giao dịch nền.** Mỗi bước, số lệnh nền `~ Poisson(bg_rate = 4)`. Cỡ lệnh bằng `bg_size·LogNormal(0; 0,5)` token1 (`bg_size = 500`), chiều mua/bán 50/50. Mọi số của một bước được rút **trước** khi khớp. Nếu bể cạn ở giá hiện tại, lệnh bị bỏ nhưng số đã rút vẫn tính, để dòng ngẫu nhiên không phụ thuộc trạng thái bể.

**Thanh khoản nền hữu hạn và đuôi.** LP thụ động gồm `bg_n = 5` vị thế lồng nhau quanh `P₀`. Vị thế thứ `k` phủ `[P₀(1 − bg_band·k/5), P₀(1 + bg_band·k/5)]` với thanh khoản `L_bg/5`, nên mật độ dày nhất ở giữa và bằng 0 ngoài `±bg_band`. Thêm một vị thế "đuôi" phủ toàn dải `[MIN_TICK, MAX_TICK]` với `L = bg_tail·L_bg`. Ở `co_so`, `L_bg = 2·10⁵` và `bg_tail = 7,5%`. Như vậy tường `L_A = 4·10⁸` dày gấp khoảng 2.000 lần nền tại giá. Lý do chọn dạng này ở 4.6.

**Trợ cấp.** Nền tảng trả trợ cấp cho **người giao dịch** theo khối lượng mua `v` (token1) cộng dồn trong một cửa sổ `subsidy_window = 24` bước (một ngày, khớp chu kỳ ngày của Binance Alpha). Có hai dạng (quyết định chốt 8):

```
tuyến tính có trần (bài gốc):  R(v) = σ·min{v, Q}
log (kiểu Binance Alpha):      R(v) = σ·Q·log₂(1 + v/Q)
```

Dạng log bằng dạng tuyến tính tại `v = Q` nhưng không có trần cứng, và lợi biên giảm dần. Thưởng được chốt cuối mỗi cửa sổ và ghi một dòng `subsidy`. Biện pháp trả trễ chỉ dời thời điểm ghi dòng này (4.4). Trợ cấp là ngoại sinh với bể: nền tảng chi, không lấy từ phí.

## 4.3 Các tác nhân

### Farmer (người săn trợ cấp) — Theorem 1

Có `n_farmers = 3` farmer, **chỉ mua** token0 bằng token1. Token0 mua được định giá theo `P_e(t)`. Mỗi bước, farmer chọn `v` để tối đa hóa phần thưởng tăng thêm trừ chi phí thực hiện:

```
U(v) = [R(v_win + v) − R(v_win)] − [v − P_e·x(v)]
U'(v) = R'(v_win + v) − 1 + P_e·(1−f)/z_sau(v)²
```

Trong đó `x(v)` là lượng token0 nhận về, lấy từ `quote_swap` trên **trạng thái bể hiện tại** (quyết định chốt 4), và `v_win` là khối lượng đã làm trong cửa sổ. Phần `v − P_e·x(v) = f·v + MC(v)` gồm phí và trượt giá so với giá ngoài. Vì vậy tường dày (`L` lớn) làm `MC` nhỏ và farmer mua nhiều hơn. `U` lõm, nên nghiệm được tìm bằng chia đôi trên dấu của `U'`, với giá biên lấy từ `sqrt_price_after` (đúng cả khi lệnh đi xuyên tick). Với bể có `L` hằng trong một tick, nghiệm trùng Theorem 1:

```
V*(σ; L) = (L/(1−f))·(√(P_e(1−f)/(1−σ)) − z₀),     σ₀ = 1 − (1−f)·P_e/P₀,
σ_cap(Q; L) = 1 − P_e(1−f) / (z₀ + (1−f)Q/L)²
```

`V = 0` khi `σ ≤ σ₀`, tăng đơn điệu khi `σ₀ < σ < σ_cap`, và bằng `Q` khi `σ ≥ σ_cap`. Có hai lựa chọn mô hình. (a) Farmer **rải đều** trần qua cửa sổ: mỗi bước mua tối đa `Q/W`. Lượng này là cận trên của vùng tìm kiếm, cả ở dạng log. (b) Farmer **không khứ hồi** trong bể, vì khứ hồi gần như thuận nghịch nên chi phí không phụ thuộc `L` và tường mất tác dụng. Giá được kéo lại tick tường nhờ arbitrageur bán token0 ngược lại cuối bước. Lựa chọn này khớp số đo của bài gốc: chỉ 0,0038% swap của farmer là khứ hồi.

### Arbitrageur `arb:0`

Hành động cuối mỗi bước: swap tới đúng `√P_e(t)` bằng `sqrt_price_limit`, và dừng nếu hết thanh khoản. Khối lượng của arb được ghi như mọi swap, nên lớp đo có thể lọc theo vai. Arb nghỉ trong các bước kẻ tấn công xả.

### Nạn nhân toàn tri — Lemma 4, Giả định 1–2

LP nạn nhân tối đa hóa lợi nhuận một cửa sổ:

```
Π_V(L_V) = f·V·L_V/(L_A + L_V) − c_V·L_V
L_V* = max{0, √(f·V·L_A/c_V) − L_A},      tham gia ⟺ V > c_V·L_A/f
```

`c_V` là chi phí hiệu dụng (token1 trên mỗi đơn vị `L` mỗi cửa sổ), đã gồm vốn, tổn thất tạm thời và rủi ro sập. Nạn nhân toàn tri biết luật trợ cấp và dùng `V = (n_farmers + m)·Q_eff`, gồm cả `m` tài khoản farm của kẻ tấn công: phí từ khối lượng đó là phí thật, đúng vai *pressure trader* của bài gốc. Mỗi bước, khi giá còn trong dải của mình, nạn nhân đọc `L_A` là thanh khoản của các LP khác trong tick chứa giá, rồi mint hoặc burn để về `L_V*` nếu lệch quá 1%. Nạn nhân vào ở `t_m + victim_delay = t_m + 30`.

Lemma 4 chỉ đúng khi hai giả định của bài gốc cùng thỏa:

- **Giả định 1 (cap-binding):** `σ ≥ σ_cap`, mọi farmer chạm trần, nên `V = số tài khoản × Q_eff`.
- **Giả định 2 (tick feasibility):** `Q ≤ L_A(z_U − z₀)/(1−f)`, mọi khối lượng được trợ cấp nằm trong một tick.

Khi trần không ràng buộc (σ thấp) hoặc `Q` lớn so với `L_A`, khối lượng thật nhỏ hơn `V` giả định và nạn nhân toàn tri vào quá tay. Các ô đó thuộc vùng "ngoài giả định": hành vi được giữ nguyên để kiểm lý thuyết, và không dùng các ô này để kiểm Lemma 4 hay Theorem 6.

Để điều khiển cỡ nạn nhân, ta tham số hóa chi phí qua tỷ số không thứ nguyên

```
k = c_V·L_A/(f·V)   ⟺   c_V = k·f·V/L_A,       L_V*/L_A = 1/√k − 1.
```

`k = 1/4` là mốc `L_A = fV/(4c_V)`, nơi `L_V*` lớn nhất và `L_V* = L_A`. Mốc này chỉ dùng trong test để kiểm engine. Từ Lemma 4 còn suy ra ngưỡng hạ trần: nạn nhân rút khỏi bể khi `Q_eff ≤ k·Q`. Đây là dạng `Q*/Q = k` được kiểm ở Mục 7.

### Nạn nhân thích nghi

Nạn nhân thích nghi không biết `V` hay `Q`. Nó ước khối lượng từ **phí của cả bể** trong `H = 24` bước gần nhất, tức dữ liệu on-chain công khai:

```
V̂(t) = (Σ phí quy token1 trong [t−H, t)) / f × W/H
```

rồi tối ưu như Lemma 4 với `V̂` thay cho `V`, ngưỡng chỉnh vị thế 10% (vì `V̂` nhiễu từng bước). Loại này phản ánh điều bài gốc nêu: LP không phân biệt được khối lượng do trợ cấp với khối lượng tự nhiên. `V̂` gồm cả khối lượng nền và arb, và phản ứng chậm `H` bước.

### Kẻ tấn công — Lemma 5

Kẻ tấn công đi qua bốn bước.

1. **Dựng** tường thanh khoản `L_A` trong tick chứa giá theo lịch `wall_schedule`. Ở `co_so`: 60% ở `t_m = 48`, 40% ở `t = 72`, tức xây hai ngày.
2. **Chờ** nạn nhân vào.
3. **Rút** toàn bộ tường (burn + collect) ở `t_0 = 168`. Kẻ tấn công phải rút **trước** khi xả, nếu không thì một phần `L_A/(L_A + L_V)` lượng bán đi vào chính vị thế của mình.
4. **Xả** kho `X̄` token0, chia đều qua `dump_steps = 2` bước. Mỗi lần bán dừng ở

```
z₂ = max{z_floor, z_X̄, z̄},     z̄ = √(c_A/(1−f))
```

Ba sàn lần lượt là: hết thanh khoản (engine tự dừng), hết kho, và giá bán biên sau phí bằng giá vốn `c_A`. Ở `co_so`, `c_A = 0,5`, tức sàn giá khoảng 0,501.

Lịch dựng, `L_A`, `t_0` và kho là **tham số ngoại sinh** của vụ, không được tối ưu bên trong mô hình. Dựng hai ngày, xả hai giờ khớp mẫu "xây chậm, rút nhanh" của bài gốc.

*Mở rộng (b) cho GĐ2:* với `attacker_farm_share = s > 0`, kẻ tấn công có thêm `m = s/(1−s)·n_farmers` tài khoản farm ảo, gộp thành một tác nhân với thưởng `m·R(v/m)`. Khi mọi tài khoản chạm trần, phần khối lượng farm của kẻ tấn công bằng `s`. Token0 mua được không cộng vào kho xả.

*Mở rộng cho GĐ3:* kẻ tấn công được **nới tường** thành `w_A` tick, đặt từ tick giá ghim đi lên (cả dải nằm trên đường mua của farmer), với **vốn cố định** bằng vốn của tường một tick: `L_A(w_A) = L_A·ℓ(w_A)/ℓ(1)`. Đây là phản ứng tối ưu tự nhiên trước luật phạt dải hẹp.

### LP lành mạnh (GĐ3)

Hai LP thụ động không bị nhắm tới, mỗi LP vốn 1.000 token1, giữ vị thế trong pha bình thường `[0, t_m − 1)`. `lp:0` tự chọn `w` theo cùng luật với nạn nhân, `lp:1` dùng dải cố định 10 tick. Mỗi bước, các LP này ghi: giá có trong dải không, `L` hoạt động, và trượt giá của một lệnh mua mẫu 1.000 token1. Đây là thước đo **cái giá hiệu quả vốn** của range-aware đối với LP không liên quan tới tấn công.

### Nạn nhân chọn (vốn, độ rộng) khi phí chia theo độ rộng (GĐ3)

Ở GĐ3, chi phí của nạn nhân tính **theo vốn** (quyết định chốt 5): `c` là token1 trên mỗi token1 vốn mỗi cửa sổ. Gọi `ℓ(w)` là `L` trên mỗi token1 vốn của dải `w` tick quanh giá, tính đúng hình học CLMM. Xấp xỉ của nó là `ℓ(w) ≈ 1/(κw)` với `κ = z·ln(1,0001)/2`, sai lệch < 0,3% khi `w ≤ 200`; ở `P₀`, `ℓ(1) ≈ 20.000`. Với `W = Σ L_j·φ(w_j)` của các LP khác trong tick chứa giá, trọng số trên mỗi đơn vị vốn là

```
g(w) = φ(w)·ℓ(w)
Π_V(C, w) = f·V·C·g/(W + C·g) − c·C
C_V*(w) = [√(f·V·W·g/c) − W] / g,        Π_V*(w) = (√(f·V) − √(c·W/g))²
w* = argmax_w g(w)
```

`w*` không phụ thuộc `V`, `W`, `c`, miễn là nạn nhân vào. Nạn nhân (cả hai loại) chọn `w*` trên lưới {1, 2, 5, 10, 20, 50, 100, 200}, đặt dải **căn giữa** tick tường, và giữ `L = X/φ(w)` với `X = max{0, √(f·V·W·g/c) − W}`. Khi `φ ≡ 1`, `w = 1`, `c = c_V·ℓ(1)`, công thức trùng Lemma 4. Vì `ℓ(w) ∝ 1/w`, `w*` rời khỏi 1 chỉ khi `φ(w)/w` tăng ở vùng `w` nhỏ. Với họ `φ = min(1, (w/w₀)^α)`, điều đó cần `α ≳ 1`.

**Công thức tỷ lệ vốn.** Gọi `C_PR` là vốn nạn nhân khi chia pro-rata và `C_RA` là vốn khi range-aware, cùng `k` như RQ1. Đặt

```
u = [ℓ(1)/g(w_v)] · [W_RA/L_A]          (pro-rata, w = 1:  u = 1 + B/L_A)
C_RA / C_PR = (√(u/k) − u) / (1/√k − 1)     (cắt ở 0)
```

`B` là phần LP dải rộng (φ = 1) trong tick giá. Tỷ lệ lớn nhất ở `u* = 1/(4k)` và bằng `1/[4k(1/√k − 1)]`. Do đó, khi `k > 1/4`, mọi `u ∈ ((1/√k − 1)², 1)` cho `C_RA > C_PR`: tường một tick bị phạt và nhường phần phí cho nạn nhân, nên range-aware **kéo nạn nhân vào nhiều vốn hơn**. Kẻ tấn công nới tường làm `u` thay đổi theo `w_A`, `u(w_A) = [ℓ(1)/g(w_v)]·[g(w_A)/ℓ(1) + B/L_A]`, nên có thể chọn `w_A` đưa `u` về gần `u*`. Đây là cơ sở giải tích của thí nghiệm nới tường (Mục 8.3).

## 4.4 Các biện pháp

Biện pháp được cài như "điểm móc" trên luật trợ cấp hoặc trên tham số của nạn nhân. Không biện pháp nào đụng vào engine, trừ range-aware: biện pháp này là tham số của engine theo đúng quyết định chốt 6.

| Biện pháp (bài gốc) | Config | Cơ chế trong mô hình | Mức thử |
|---|---|---|---|
| Hạ trần `Q` (§7.1) | `{"name": "cap", "ty_le": r}` | `Q_eff = r·Q` cho luật thưởng, farmer và `V` của nạn nhân toàn tri | r ∈ {0,90; 0,75; 0,60; 0,50; 0,25; 0,15; 0,10; 0,05} |
| Trả trễ (§7.2) | `{"name": "delay", "D", "don_vi": "token0", "chiet_khau": δ}` | thưởng chốt cuối cửa sổ, trả sau `D` bước, quy đổi ra token0 theo giá lúc chốt (giá sập thì nhận ít đi); farmer quy về hiện tại bằng `δ^D` | D ∈ {24, 72, 168}, δ = 0,995/bước (δ^D ≈ 0,89 / 0,70 / 0,43) |
| Thu hồi (biến thể của §7.2) | `delay` + `"clawback": 0,10` | hủy khoản treo nếu giá ≤ 0,9 × giá đầu cửa sổ tích lũy của khoản đó, **chỉ** với địa chỉ từng có vị thế LP trong `(t_chot − D, t]` (theo lịch sử địa chỉ, nên rút tường trước khi chốt không né được); farmer thuần không bị đụng | D ∈ {24, 72, 168} |
| Cảnh báo rủi ro (§7.3) | `{"name": "warn", "he_so": h}` | công bố rủi ro khi mint dải hẹp → `c_V → h·c_V` cho mọi nạn nhân; farmer và kẻ tấn công không đổi | h ∈ {1,5; 2; 4} |
| Trần động (§7.4) | `{"name": "dyncap", "ty_le": 0,25, "m": 3, "N": 24, "H": 24}` | cuối bước, nếu `L` của tick chứa giá > `m` × trung vị `L` của `N` bước không báo động gần nhất thì báo động; trong `H` bước sau lần báo cuối, trần = `0,25·Q`. Đường nền đóng băng khi báo động, nên báo động kéo dài tới `H` bước sau khi tường biến mất | một cấu hình |
| Range-aware (GĐ3) | `"phi": {"alpha": α, "w0": w₀}` | engine chia phí theo `L_i·φ(w_i)/Σ_j L_j·φ(w_j)`, tổng phí giữ nguyên, `φ(w) = min(1, (w/w₀)^α)` | α ∈ {0,5; 1; 1,5; 2; 3} × w₀ ∈ {10, 50, 200} |

Ba giả định cần nêu khi báo kết quả:

- **Trần động:** luật được công bố. Farmer và nạn nhân toàn tri thấy trần hiện hành ngay, và thưởng mỗi cửa sổ tính theo trần lúc chốt. Tín hiệu bắt chước cách bài gốc dò tường (thanh khoản ròng của tick tăng bất thường, ngưỡng kiểu 3σ), nhưng theo giờ thay vì theo ngày.
- **Trả trễ:** farmer không dự báo giá.
- **Range-aware:** ở một tick, `φ(1)` triệt tiêu trong tỷ số, nên biện pháp vô hiệu ở GĐ1/2 và chỉ đánh giá ở GĐ3 (quyết định chốt 7). Bản "đốt phần bị phạt" tương đương hạ `f`, nên không dùng.

## 4.5 Thiết kế thí nghiệm

**Kịch bản cơ sở.** Mọi vụ kế thừa `co_so.json` rồi ghi đè các yếu tố được quét.

| Nhóm | Tham số | Giá trị `co_so` |
|---|---|---|
| Bể | phí `f`; giá đầu | 0,25%; giữa tick 0 (`P₀ ≈ 1,00005`), `tick_spacing = 1` |
| Thời gian | `steps`; `subsidy_window` | 240 bước (10 ngày); 24 bước |
| Trợ cấp | `σ`; `Q`; dạng; `n_farmers` | 0,01; 24.000 token1/cửa sổ; tuyến tính; 3 |
| Nền | `L_bg`; `bg_band`; `bg_n`; `bg_tail` | 2·10⁵; ±10%; 5; 7,5% |
| Dòng lệnh nền | `bg_rate`; `bg_size` | 4 lệnh/giờ; 500 token1 (LogNormal σ = 0,5) |
| Giá ngoài | `vol_pre`; `vol_prep`; `vol_post` | 0,002; 0 (ghim); 0,01 mỗi giờ |
| Kẻ tấn công | `L_A`; `w_attacker`; lịch dựng; `t_0`; `dump_steps`; kho; `c_A` | 4·10⁸; 1; 60% ở t = 48, 40% ở t = 72; 168; 2; 25.000 token0; 0,5 |
| Nạn nhân | số; loại; `victim_delay`; `w_victim`; `c_V` | 1; toàn tri; 30 bước; 1; 3,375·10⁻⁷ (`k = 0,75` ⇒ `L_V*/L_A ≈ 0,155`, tường ≈ 87%) |

Với `co_so`: `V = 3 × 24.000 = 72.000` token1 mỗi cửa sổ, và tường một tick chứa được khoảng 10.000 token1 mua từ giữa tick lên biên trên. Con số này lớn hơn nhiều so với 3.000 token1 farmer mua mỗi giờ, nên cả hai giả định của Lemma 4 thỏa.

**Bộ tổ hợp RQ1: 30 vụ.** Bài gốc có 29 vụ với tham số khác nhau. Ta dựng 30 vụ phủ không gian tham số một cách cân đối bằng **mảng trực giao L27(3⁶)**: 27 dòng × 6 yếu tố × 3 mức. Các cột được sinh theo `(a, b, c, a+b+c, a+2b, b+2c) mod 3`, nên mọi cặp mức của hai yếu tố bất kỳ xuất hiện đúng 3 lần. Thêm 3 vụ trợ cấp dạng log, lấy mọi yếu tố ở mức giữa, thấp và cao.

| Yếu tố | Mức 0 | Mức 1 | Mức 2 | Vai trò |
|---|---|---|---|---|
| `L_A` | 2·10⁸ | 4·10⁸ | 8·10⁸ | độ dày tường |
| `k = c_V·L_A/(fV)` | 0,64 | 0,80 | 0,95 | cỡ nạn nhân: `L_V*/L_A` = 0,25 / 0,118 / 0,026 (tường ≥ 80%) |
| `σ` | 0,005 | 0,01 | 0,02 | mức trợ cấp |
| `Q` | 12.000 | 24.000 | 48.000 | trần mỗi cửa sổ (token1) |
| `bg_band` | 0,15 | 0,25 | 0,40 | bề rộng thanh khoản nền |
| kho kẻ tấn công | 15.000 | 25.000 | 40.000 | token0 để xả |

**Seed và dòng ngẫu nhiên.** Mỗi vụ chạy **10 seed**, tổng 300 lượt. Gốc ngẫu nhiên của một lượt là `SeedSequence([seed, crc32(mã vụ)])`, tách bằng `spawn` thành hai dòng độc lập: một cho giao dịch nền, một cho cú sốc giá ngoài. Hệ quả:

1. Cùng số seed ở hai vụ khác nhau là hai bản nhiễu độc lập. Phiên bản trước dùng chung `default_rng(seed)` cho mọi vụ, tạo ra yếu tố "seed chéo" làm khoảng tin cậy hẹp giả. Sau khi sửa, hoán vị seed 0–4 với seed 5–9 cho p = 0,66.
2. Mọi số rút ra chỉ phụ thuộc (vụ, seed), không phụ thuộc biện pháp, loại nạn nhân, phần farm hay trạng thái bể.

**Cặp phản thực.** Nhờ điểm 2, một lượt có biện pháp và lượt `không biện pháp` cùng vụ, cùng seed, cùng loại nạn nhân nhận **đúng từng số ngẫu nhiên** giống nhau. Hiệu giữa hai lượt vì thế chỉ do biện pháp gây ra. Mọi so sánh ở GĐ2 và GĐ3 đều là so sánh cặp. GĐ3 ghép mỗi mức φ với pro-rata (α = 0) cùng vụ, seed, loại nạn nhân. Cách tính khoảng tin cậy: Mục 5.5.

**Phản thực phát lại log cho lợi nhuận tăng thêm.** Lợi nhuận "paper" của kẻ tấn công (token1 thu từ cú xả) dương cả khi không có nạn nhân, vì kho được bán vào thanh khoản nền. Câu hỏi đúng theo Theorem 6 là kẻ tấn công **lời thêm bao nhiêu nhờ nạn nhân**. Để trả lời, ta dựng lại bể từ log ngay trước dòng burn tường đầu tiên, bỏ mọi vị thế của `attacker:*` và `victim:*`, rồi phát lại tuần tự các sự kiện tới cú xả cuối:

- mint/burn của các LP khác, và swap nền/arb với đúng chiều và lượng của log;
- cú xả với đúng lượng, vẫn dừng ở `z̄`;
- **lệnh farm được tối ưu lại** trên bể phản thực (cùng luật thưởng, trần theo bước, khối lượng đã làm trong cửa sổ), với `P_e` phản thực bằng `P_e` farmer thấy × (giá bể phát lại / giá bể thật) ở cuối bước trước.

Khối lượng farm trong pha xả là phản ứng nội sinh với giá. Nếu phát lại nguyên lượng thật vào bể phản thực, nơi giá thấp hơn nhiều do không còn nạn nhân đỡ, thì đó là "đỡ giá miễn phí" và làm phản thực phụ thuộc trần (lỗi phát hiện ở v3 và đã sửa ở v4). Chỉ số chính là `excess = paper − bán_thẳng`, bằng 0 đúng khi không có nạn nhân (có test). Lợi nhuận được đo theo **địa chỉ thật** `attacker:0`, nên có cả ở lượt giá không sập.

**Các bộ quét.** Mọi script ghi dần từng dòng CSV và bỏ qua lượt đã có khi chạy lại.

| Bộ | Lệnh | Không gian | Số lượt |
|---|---|---|---|
| RQ1 | `scenarios.batch --seeds 10` | 30 vụ × 10 seed | 300 |
| GĐ2 chính (v4) | `scenarios.quet_gd2` | 30 vụ × 16 biện pháp (không; cap 90…05; delay 24/72/168; warn 15/20/40; dyncap) × 2 loại nạn nhân × 10 seed | 9.600 |
| GĐ2 kẻ tấn công farm (v4) | `quet_gd2 --farm` | 30 vụ × `s` ∈ {0; 0,3; 0,6} × {không, delay24/72/168, claw24/72/168} (bỏ claw khi s = 0; 18 tổ hợp) × 2 × 10 | 10.800 |
| GĐ2 vùng `k` nhỏ (v4) | `quet_gd2 --k_nho` | cùng mảng L27 với `k` ∈ {0,10; 0,25; 0,45} (`L_V*/L_A` ≈ 2,16 / 1,0 / 0,49), `s` = 0,3, 10 biện pháp × 2 × 10 | 6.000 |
| GĐ2 lưới (v4) | `quet_gd2 --luoi` | σ ∈ {0,0025; 0,005; 0,01; 0,02; 0,04} × Q ∈ {6k; 12k; 24k; 48k; 96k} quanh `co_so`, giữ `c_V` của `co_so` (k = 0,75·24.000/Q), {không, cap50} × 2 × 10 | 1.000 |
| GĐ3 | `scenarios.quet_gd3` | 6 vụ (L27_10/16/22 với k = 0,64/0,95/0,80, và bản KN_ cùng vụ với k = 0,10/0,45/0,25) × 16 mức φ × 2 × 10 | 1.920 |
| GĐ3 nới tường | `quet_gd3 --w_A` | 6 vụ × [pro-rata + α ∈ {1,5; 2; 3} × w₀ ∈ {10, 50, 200} × w_A ∈ {1, w₀/4, w₀/2, w₀}] (37 tổ hợp) × 2 × 10 | 4.440 |

Vùng `k` nhỏ được thêm vào vì bộ RQ1 chọn `k ≥ 0,64` để khớp dấu hiệu "tường ≥ 80%". Điều đó làm nạn nhân nhỏ và lợi tăng thêm của kẻ tấn công nhỏ, nên cần vùng nạn nhân lớn để thấy khi nào tấn công thật sự có lãi. Ở GĐ3, mọi lượt (kể cả α = 0) dùng chi phí theo vốn `c_V_von = c_V·ℓ(1)`, nên α = 0 trùng Lemma 4 của RQ1.

## 4.6 Hiệu chỉnh môi trường cho RQ1

Lần chạy đầu trên `co_so` chỉ đạt 8/13 dấu hiệu. Ta sửa bằng ba thay đổi, chỉ chạm **môi trường**: thanh khoản nền, tham số chi phí của nạn nhân, và kho của kẻ tấn công. Không thay đổi nào chạm hành vi tối ưu của tác nhân (Theorem 1, Lemma 4, Lemma 5) hay engine. Mỗi thay đổi sửa một dấu hiệu cụ thể bị hỏng và có lý do kinh tế độc lập với việc "cho qua kiểm định". Bảng trước/sau tái lập được bằng `python -m scenarios.hieu_chinh` (chi tiết: `ket_qua/rq1/NHAT_KY_HIEU_CHINH.md`).

| # | Dấu hiệu hỏng | Thay đổi | Lý do kinh tế | Hệ quả (`co_so`, trung vị 5 seed) |
|---|---|---|---|---|
| 1 | lift Post = 1,15 > 1. Bài gốc: Post **dưới** nền ở 23/29 vụ | Nền phủ đều ±20.000 tick (giá ×/÷ 7,4) → 5 vị thế lồng nhau trong ±`bg_band` | LP thụ động tập trung quanh giá hiện hành. Khi giá rơi khỏi vùng đó, độ sâu cạn và dòng lệnh giảm theo, đúng cơ chế "dòng lệnh phụ thuộc thanh khoản" mà bài gốc dùng để giải thích | Post 0,195 (quá tay); cú xả kẹt ở mép dải (sàn `z_floor`), độ sập ≈ `bg_band` |
| 2 | Tường chỉ chiếm 50% tick. Bài gốc: ≥ 80% ở 25/29 vụ | `c_V` ở mốc `fV/(4c_V)` → `c_V = k·fV/L_A`, `k ∈ [0,64; 1)`, `co_so` k = 0,75 | Mốc `k = 1/4` là điểm làm `L_V*` **lớn nhất**, chỉ hợp để kiểm engine, không phải điểm kẻ tấn công chọn. `k ∈ [0,64; 1) ⟺ L_V*/L_A ∈ (0; 0,25]` ⟺ tường ≥ 80% | Tường 50% → 87%; khối lượng và giá không đổi (farmer chỉ nhìn tổng `L`) |
| 3 | Độ sập luôn ≈ `bg_band` (hoặc luôn −50%) | Thêm đuôi toàn dải `bg_tail` = 7,5%·`L_bg`; kho kẻ tấn công thành yếu tố {15k, 25k, 40k} (trước: cố định 60k); `bg_band` ∈ {0,15; 0,25; 0,40} | Bể thật luôn có ít thanh khoản rải rác ở xa giá (vị thế toàn dải kiểu v2, LP quên chỉnh). Kho lớn làm mọi vụ dừng ở `z̄` (−50%), nên kho phải là ràng buộc chặn trước thì độ sập mới có phân phối | Post 0,78; RV Post cao nhất; trên bộ 30 vụ, độ sập −11 … −50% (trung vị −37%) |

Sau ba thay đổi, bộ 300 lượt đạt 13/13 tiêu chí (Mục 6). Các khác biệt còn lại được ghi trung thực và không hiệu chỉnh tiếp, để tránh ép mô hình khớp số: lift Prep không vụ nào < 1×, tường cạn dồn vào 80–99%, giá sập theo VWAP chỉ đạt ở 52% số vụ (CI 38–67).

## 4.7 Giả định và giới hạn của mô hình

1. **Độ phân giải giờ, thứ tự cố định.** Trong một giờ, thứ tự hành động là cố định (4.1), và không có cạnh tranh thứ tự giao dịch (MEV, sandwich). Kẻ tấn công không cần kiểm soát thứ tự, khớp với mô hình năng lực của bài gốc.
2. **Tác nhân tất định, cận thị.** Farmer tối ưu từng bước, không dự báo giá, và không chịu rủi ro giữ token0 (token0 định giá theo `P_e`). Nạn nhân toàn tri biết luật trợ cấp nhưng không biết ý đồ kẻ tấn công. Mọi nhiễu đến từ giao dịch nền và giá ngoài.
3. **Kẻ tấn công không tối ưu nội sinh** `L_A`, `t_0`, lịch dựng hay kho. Các đại lượng này là yếu tố quét. Chỉ ở GĐ3, phản ứng nới tường `w_A` được quét như một chiến lược. Mỗi vụ có một kẻ tấn công và một nạn nhân, không có kẻ tấn công cạnh tranh.
4. **`c_V` ngoại sinh và hằng.** `c_V` đã gồm rủi ro sập theo định nghĩa của bài gốc, nhưng không được cập nhật theo diễn biến trong vụ. Cảnh báo rủi ro được mô hình hóa đơn giản là nhân `c_V`.
5. **Giả định 1–2 không phải lúc nào cũng thỏa.** Nạn nhân toàn tri tin `V = n·Q_eff` cả khi trần không ràng buộc. Tính tay theo bước giờ: ở 3/27 vụ L27 (L27_02, L27_04, L27_06: `L_A = 2·10⁸`, `Q = 48.000`), farmer mua 6.000 token1 mỗi giờ, vượt sức chứa khoảng 5.000 token1 của tường từ giữa tick lên biên. Trong 24 giờ đầu, khi tường mới đứng 60%, sức chứa còn thấp hơn. Ở các vụ này, khối lượng thật có thể thấp hơn `V` giả định. Điểm này chưa được kiểm trên log. Bản đồ ba vùng ở Mục 7 tách riêng vùng "ngoài giả định".
6. **Thị trường ngoài thụ động khi xả.** `P_e` đi theo giá bể trong lúc xả, tức giả định bể là nơi định giá chính của alpha. Sau sập, giá đi ngẫu nhiên với độ biến động cố định 1%/giờ. Không có LP mới hay người mua bắt đáy phản ứng với cú sập.
7. **Lựa chọn hiệu chỉnh ảnh hưởng tới RQ2.** Chọn `k ≥ 0,64` để khớp "tường ≥ 80%" làm nạn nhân nhỏ, nên lợi tăng thêm của kẻ tấn công trong bộ RQ1 chỉ khoảng 2% lợi nhuận paper. Vì vậy GĐ2 có thêm vùng `k` nhỏ. Lợi của phương án bán thẳng phụ thuộc `Q` (farmer mua đỡ cú bán), trong khi Theorem 6 coi nó không đổi.
8. **GĐ3.** Luật chọn `w` bỏ qua biến động và tổn thất tạm thời khác nhau theo độ rộng: chỉ có trọng số phí và hình học vốn. Nạn nhân toàn tri có thể chỉnh vị thế giữa hai bước xả, nên phần bị lấy bị chặn bởi lượng xả mỗi bước. Trượt giá của LP lành mạnh là của cả bể, đo trước khi dựng tường.
9. **Trợ cấp log** dùng cùng cửa sổ 24 bước và cùng cận mỗi bước `Q/W` như dạng tuyến tính, không dùng cửa sổ trượt 15 ngày của Binance Alpha. Như vậy dạng log trong mô hình chỉ khác ở lợi biên giảm dần.
10. **Số thực `float`**, không phí gas, không làm tròn Q64.96. Sai số số học nằm dưới 10⁻⁸ so với bể tham chiếu, nhỏ hơn rất nhiều so với các hiệu ứng được đo.
11. **Giá bị ghim là điều kiện cần — bể là nơi hình thành giá.** Mô hình giả định token Alpha giao dịch chủ yếu trên chính bể bị tấn công, không có giá ngoài để arb neo, nên `vol_prep = 0`. Nếu có giá ngoài trôi tự do cộng arb, tường một tick không giữ được giá. Ở biến thể độ nhạy `vol_prep = vol_pre` (30 vụ × 10 seed):
    - giá nằm trên tick tường chỉ 1,2% số bước của pha tường;
    - arb vượt một tick tường chỉ cần khoảng `L_A·ln(1,0001)/2` ≈ 20k token1 (10k–40k), giá chỉ nhích 0,01%;
    - 75% lượt nạn nhân vào sai tick (trung vị cách tường 105 tick), nơi không có tường để chia phí, nên `L_V/L_A` trung vị chỉ 0,026 (bản gốc ≈ 0,15);
    - kết quả là thiệt hại nạn nhân và lợi tăng thêm của kẻ tấn công về 0 (trung vị), dù lợi nhuận paper gần như không đổi.

    Vì vậy dấu hiệu "RV Prep thấp" là hệ quả của giả định này, không phải kết quả độc lập. Xem Mục 6.6.

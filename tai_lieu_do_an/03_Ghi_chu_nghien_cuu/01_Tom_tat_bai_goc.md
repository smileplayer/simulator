# Tóm tắt bài gốc — Lu et al., USENIX Security 2026

*Liquidity Mining as an Attack Surface: Incentive-Induced Liquidity Attacks in Concentrated Liquidity Market Makers.* Tác giả: Nora Sinong Lu, Chon Kit Lao (ĐH Macau), Yunlong Mao (ĐH Nam Kinh), Xiaobo Zhou (ĐH Macau), Ruizhe Jia (Stanford), Kanye Ye Wang (ĐH Macau). Trang 1767–1786.

## 1. Ý chính trong một đoạn

Chương trình thưởng theo khối lượng giao dịch (Binance Alpha Points, Blast, Aerodrome, PancakeSwap) trả trợ cấp cho **người giao dịch**. Kẻ tấn công dựng một **bức tường thanh khoản trong đúng một tick** quanh giá hiện tại, làm trượt giá gần bằng 0, hút người săn điểm đến giao dịch. Khối lượng do trợ cấp tạo ra sinh phí, đẩy lợi suất hiển thị lên cao, dụ LP khác nạp vốn vào cùng tick. Khi đủ vốn nạn nhân, kẻ tấn công **rút tường rồi xả token phụ** qua thanh khoản của nạn nhân; giá sụp, nạn nhân giữ toàn token mất giá. Không có lỗi mã nào — lỗ hổng nằm ở tham số khuyến khích.

## 2. Nền CLMM cần nhớ

```
z = √P                      P = token1 trên mỗi token0 (token0 = alpha/token phụ)
P(i) = 1.0001^i             mỗi tick = 0,01%
L = √(x·y)                  L đo mật độ / sức đề kháng của giá, không phải tiền
Δy = L·Δz    Δx = L·Δ(1/z)  tuyến tính trong không gian z → có nghiệm dạng đóng
y = L(z − z_L)              phần dưới giá hiện tại giữ token1
x = L(1/z − 1/z_U)          phần trên giá hiện tại giữ token0
phí / đơn vị L ∝ V / L_active   → LP vào sau làm loãng phí của mọi người
```

Ví dụ vốn ↔ `L`: cùng 1.000 USDT đặt ngay dưới giá `P₀ = 1`:
dải `[0,90 ; 1,00]` → `L ≈ 19.487`; dải một tick `[0,9999 ; 1,00]` → `L = 20.000.000` (gấp hơn 1.000 lần).

## 3. Mô hình (§4.1–4.2)

**Trợ cấp:** `σ ∈ [0,1]` trả cho trader trên khối lượng gộp, trần `Q`. Ngoại sinh với bể (nền tảng chi, không lấy từ phí).

**Trader săn điểm:**
```
U_T(v) = σ·min{v, Q} − f·v − MC(v)        MC = chi phí thực hiện, chủ yếu trượt giá
FOC nội:  σ − f − MC′(V) = 0
v > Q:    dU_T/dv = −f − MC′(v) < 0       → không bao giờ giao dịch quá Q
```

**Kẻ tấn công** (lợi nhuận tính bằng token1):
```
Π_A = f·V·L_A/(L_A + L_V)  +  U_dump  −  c_A·X_sold  −  κ
       thu phí (mồi)          bóc từ cú sập   giá vốn kho   ma sát
```

**LP nạn nhân:**
```
Π_V(L_V) = f·Q·L_V/(L_A + L_V) − c_V·L_V
```
`c_V` = chi phí hiệu dụng mỗi đơn vị thanh khoản, **đã gồm** chi phí vốn, IL kỳ vọng và rủi ro sụp giá.

**Năng lực kẻ tấn công:** nạp/rút thanh khoản tùy ý; giao dịch trong bể; tham gia chương trình theo luật công khai; ảnh hưởng gián tiếp tới `V` qua độ sâu `L_A`. Không cần lỗi mã, quyền quản trị, flash loan hay kiểm soát thứ tự giao dịch.

**Bốn giai đoạn:** dựng tường → tạo khối lượng → nạn nhân vào → rút và bóc tách. Phải rút `L_A` trước khi xả, nếu không tỷ lệ `L_A/(L_A+L_V)` của lượng bán đi vào chính vị thế của kẻ tấn công.

## 4. Phân tích cân bằng (§4.3)

**Giả định 1 (cap-binding):** `σ ≥ σ_cap(Q; L_A)` → `V* = Q` với mọi `L_V`.
**Giả định 2 (tick feasibility):** `Q ≤ V_max^tick(L_A) ≈ L_A(z_U − z₀)/(1 − f)` → mọi giao dịch được trợ cấp nằm trong một tick. Hai giả định cắt vòng lặp điểm bất động giữa `V` và `L`.

**Theorem 1 + Lemma 2 — trợ cấp chế tạo khối lượng:**
```
σ ≤ σ₀          → V = 0
σ₀ < σ < σ_cap  → V tăng đơn điệu theo σ
σ ≥ σ_cap       → V = Q
V*(σ; L₀) = (L₀/(1−f))·(√(P_e(1−f)/(1−σ)) − z₀)      P_e = giá ngoài
σ₀ = 1 − (1−f)·P_e/P₀
σ_cap(Q; L) = 1 − P_e(1−f) / (z₀ + (1−f)Q/L)²
```

**Theorem 3 + Lemma 4 — khối lượng nạp thanh khoản nạn nhân:**
```
L_V* = max{0, √(f·Q·L_A/c_V) − L_A}
tham gia ⟺ Q > c_V·L_A/f
d²Π_V/dL_V² = −2fQL_A/(L_A+L_V)³ < 0  → cực đại toàn cục
```
*Nghịch lý nạn nhân duy lý:* `c_V` đã gồm rủi ro sụp giá mà `L_V*` vẫn dương khi `Q` đủ lớn. Nếu nạn nhân đánh giá thấp rủi ro thì vào nhiều hơn nữa.

*Suy ra thêm (không có trong bài):* `L_A = f·Q/(4c_V)` tối đa hóa `L_V*`, và tại đó `L_V* = L_A`. Dùng làm mốc kiểm tra engine.

**Lemma 5 — xả tới sàn:** `z₂ = max{z_floor, z_Ā, z̄}` — hết thanh khoản, hết kho hàng, hoặc chạm giá vốn `c_A` (điều chỉnh theo phí).

**Theorem 6 — ngưỡng khả thi:** tấn công có lợi hơn bán thẳng ⟺ `Q ≥ Q*`.

**Ba vùng thiết kế:** bootstrap an toàn (`σ < σ_Q` hoặc `Q < Q*`); tăng trưởng rủi ro (`σ ≥ σ_Q` và `Q ≥ Q*`); tối ưu có ràng buộc. Bài toán nền tảng: `σ_opt = min{σ : V*(σ) ≥ V̄}` với ràng buộc ở vùng an toàn.

## 5. Phương pháp đo (§5)

- Dữ liệu: mọi bể kiểu Uniswap v3 trên BSC (quét `PoolCreated`), log Mint/Burn/Swap qua Allium, 01/01–01/10/2025; giá Alpha theo giờ từ API Binance.
- Ứng viên: chỉ vị thế một tick; chuỗi thanh khoản ròng theo ngày cho từng (bể, tick); ngưỡng 3σ; gộp ngày bất thường thành nhóm build-wall / remove-wall; ghép cặp.
- Xác minh hai tầng: giá giảm ≥ 10% trong 2 giờ sau khi rút; swap trong chính bể đó đẩy tick đúng chiều.
- Mốc thời gian: `t_m` (mint đầu) → `t_50` → `t_peak` → `t_0` (bắt đầu rút) → `t_oot` (swap ra khỏi tick) → `t_b` (giá −10%).
- Vai trò: *victim* còn thanh khoản một tick tại `t_end`; *wall provider* vừa mint vừa burn; *pressure trader* swap theo chiều sập, bán alpha; *attacker* = cả hai vai sau; *main attacker* = thị phần tường lớn nhất trước khi rút.
- Thiệt hại nạn nhân: `Loss_u = max{0, E_u}`, `E_u` = giá trị non-alpha theo kịch bản "ôm" trừ phần thực thu hồi, trừ giá trị alpha còn lại (định giá bằng VWAP `[t_b, t_b+1h]`).
- Lợi nhuận kẻ tấn công: dòng tiền non-alpha ròng trong `[t_0, t_b]`, đo độc lập.

## 6. Kết quả (§6)

| Chỉ số | Giá trị |
|---|---|
| Sự kiện | 29 vụ / 18 bể |
| Thiệt hại nạn nhân | 2.874.406 USD; 99 địa chỉ; 13 vụ có thiệt hại |
| Lợi nhuận kẻ tấn công | 23.884.128 USD; 149 địa chỉ, 131 có lãi; trung vị 21.328 USD/địa chỉ, 99.541 USD/vụ |
| Tập trung | vụ lớn nhất 45,80%; 5 vụ lớn nhất 86,64%; 5 địa chỉ lớn nhất 43,76% |
| Thời gian | xây tường > 3 ngày: 12/29; thu hoạch < 24h: 18/29; tháo tường < 1h: 19/29 |
| Khối lượng | Prep ≥ nền 20/29 (11 vụ ở 1–1,5×); Attack > nền 17/29 (4 vụ > 5×); **Post < nền 23/29** |
| Biến động (trung vị) | Prep 0,0119 → Attack 0,1593 → Post 0,8843 (theo Plan_Notion của nhóm) |
| Kiểm tra round-trip | 504 cặp / 26.514.897 swap của farmer = 0,0038% |
| Nhóm đối chứng | 5 bể PancakeSwap ngoài chương trình: 0 vụ |
| Kiểm tra tay | không có tường chẻ qua nhiều tick; không trùng địa chỉ deployer |
| Độ vững | hai quy ước thời điểm kết thúc: lệch 9 nạn nhân, 2,25% thiệt hại |

**Lợi nhuận ≠ thiệt hại** vì: kẻ tấn công còn bóc qua tick lân cận và các bên ngoài tập nạn nhân; có tiền ngoại sinh từ trợ cấp; thiệt hại chỉ đo 99 địa chỉ còn giữ thanh khoản một tick (ước lượng cận dưới).

## 7. Biện pháp đề xuất (§7) — chưa được đánh giá

| # | Biện pháp | Cắt mắt xích | Cơ sở |
|---|---|---|---|
| 7.1 | Hiệu chỉnh trần `Q` và phí `f` | Đưa bể ra khỏi vùng tấn công có lãi | Theorem 6 |
| 7.2 | Trả thưởng trễ (vesting, cooldown, tích lũy theo thời gian) | Lợi thế "xây chậm, rút nhanh" | Số liệu thời gian |
| 7.3 | Công bố rủi ro khi LP mint dải hẹp | Tăng `c_V` → giảm `L_V*` | Lemma 4 |
| 7.4 | Trần động kích hoạt bởi tín hiệu dựng tường | Siết `Q` trước khi xả | Theorem 1; prep dài hơn extract |

## 8. Giới hạn tự nhận (§8)

1. Chỉ bắt tường một tick → bỏ sót biến thể nhiều tick.
2. Phụ thuộc tham số phát hiện (3σ, 10%, 2 giờ).
3. Nhóm đối chứng theo bối cảnh, không thiết lập nhân quả.
4. Vai trò suy từ hành vi, không thấy ý định hay quan hệ ngoài chuỗi.
5. Không đo các bên bị ảnh hưởng khác → ước lượng một phần.
6. Biện pháp là đề xuất thiết kế, chưa đánh giá. Hướng tiếp: đánh giá qua mô phỏng, phản thực lịch sử, hoặc triển khai.

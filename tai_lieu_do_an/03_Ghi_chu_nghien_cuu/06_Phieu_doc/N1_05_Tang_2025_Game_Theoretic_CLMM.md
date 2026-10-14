# Phiếu đọc — Tang, El-Azouzi, Lee, Chan, Fanti 2025, *Game Theoretic Liquidity Provisioning in Concentrated Liquidity Market Makers*

- **Nguồn:** Proc. ACM Meas. Anal. Comput. Syst. (POMACS / SIGMETRICS) 9(1), Art. 7, 03/2025; arXiv:2411.10399 (v2 06/2026). CMU + Avignon + Allium. 46 trang.
- **PDF:** `01_Tai_lieu_tham_khao/02_Chien_luoc_LP_va_ly_thuyet_tro_choi/2024_Tang_Game_Theoretic_Liquidity_Provisioning_in_Concentrated_Liquidity_Market_Makers.pdf` (tên file ghi 2024 theo bản arXiv; khi trích ghi **2025**, POMACS).
- **Mức độ đọc:** toàn văn mục 1–6; phụ lục B (toán CLMM) đọc; phụ lục C–E (chứng minh, chi tiết thực nghiệm) lướt (10/10/2026).
- **Bài gốc trích bài này** (Ref 45). Tang và Fanti cũng là tác giả bài JIT (phiếu N1_04).
- **Vai trò trong đồ án:** mô hình **trò chơi nhiều LP có ngân sách, tự chọn khoảng giá** trong CLMM — gần nhất với "độ rộng nội sinh" (khoảng trống B) nhưng **không có trợ cấp, không có kẻ tấn công**. Có một kết quả cấu trúc quan trọng cho lý lẽ range-aware.

## 1. Câu hỏi
Khi nhiều LP có ngân sách khác nhau cạnh tranh chia phí trong CLMM, cân bằng Nash có tồn tại / duy nhất không, trông thế nào, và LP thật có chơi gần cân bằng không?

## 2. Mô hình (mục 2–3)
- Trò chơi một lượt, hai pha: (1) mỗi LP n chọn véc-tơ thanh khoản `L_{n,(a,b)}` trên **mọi** khoảng `(a,b)` giữa các tick, chịu ràng buộc ngân sách `Σ L·ε_{a,b}(q) ≤ B_n`; (2) trader giao dịch, giá theo quá trình dừng ergodic, LP không đổi vị thế.
- Tiện ích `U_n = F_n − C_n`:
  - Phí trên mỗi "khoảng nguyên tử" m (giữa hai tick liền kề) có tổng cố định `f_m`, chia theo **`K_{n,m}^α / Σ_i K_{i,m}^α`**, với `K_{n,m}` = tổng thanh khoản của LP n phủ khoảng m (pt 3.3).
    - **α là tham số cơ chế chia phí**: Uniswap v3 dùng α = 1. α > 1 khuyến khích dồn; α → ∞ người lớn nhất ăn hết; α → 0 chia đều cho mọi ai có mặt.
  - Tổn thất tạm thời (IL) **tuyến tính theo L**: `C_n = Σ L_{n,(a,b)} · τ̄_{a,b}` (pt 3.4).
- Giả định đơn giản hóa: `f_m` là hằng số, **không phụ thuộc** vào thanh khoản (khối lượng không phản ứng với độ sâu); arbitrageur giữ giá bể = giá ngoài.

## 3. Kết quả chính
- **Mệnh đề 3.3:** trò chơi gốc luôn có cân bằng Nash, nhưng có thể nhiều cân bằng.
- **Định lý 3.7 ("twin games") — kết quả cấu trúc then chốt:** trò chơi gốc (chọn khoảng tùy ý) **tương đương** trò chơi nguyên tử (mỗi LP chỉ chọn thanh khoản trên từng khoảng một tick). Mọi cân bằng của trò chơi gốc cho cùng một histogram thanh khoản theo tick, cùng ngân sách đã dùng, cùng tiện ích.
  - Hệ quả cho nhóm: **với quy tắc chia phí chuẩn (pro-rata theo L ở từng tick) và IL tuyến tính theo L, độ rộng vị thế tự nó không mang thông tin** — một vị thế rộng w tick tương đương w vị thế một tick. Muốn độ rộng ảnh hưởng tới phần chia phí thì cơ chế phải nhìn vào **vị thế** (độ rộng w của nó), không chỉ thanh khoản theo tick → đó chính là `φ(w)` của range-aware. Đây là lý lẽ hình thức tốt cho quyết định số 6–7 của nhóm (và vì sao `φ = 1` không phân biệt được tường một tick).
- **Định lý 3.4:** với `0 < α ≤ 1`, trò chơi nguyên tử có **cân bằng duy nhất** (tính chất lõm chéo nghiêm ngặt kiểu Rosen); tính được bằng relaxation / mirror descent / no-regret; LP học lặp sẽ hội tụ.
- **Mệnh đề 3.8 (waterfilling):** LP nghèo dùng hết ngân sách, LP giàu dùng như nhau một mức `h`; **Mệnh đề 3.9:** LP giàu hơn đặt không ít hơn ở mọi khoảng. **Mệnh đề 3.10:** α < 1 → mọi LP có mặt ở mọi khoảng. **Mệnh đề 3.11:** khi mọi LP dùng ngân sách bằng nhau, tiện ích mỗi LP = `((1−α)N + α)/N² · Σ f_m` → tiện ích tăng khi α giảm.
- Liên hệ cơ chế Kelly trong phân bổ tài nguyên mạng (mục 5).

## 4. Thực nghiệm (mục 4)
- 5 bể Uniswap v3 trên Ethereum (WBTC/USDC 0,3%; USDC/WETH 1%, 0,3%, 0,05%; USDC/USDT 0,05%), swap 01–06/2024, dữ liệu Allium; mỗi ngày một trò chơi (182 trò chơi); người chơi = top ≤ 30 LP giữ NFT cả ngày.
- **Phát hiện 1:** bể ổn định (USDC/USDT) — LP thật gần cân bằng (overlap trung vị 40,4%). Bể rủi ro — overlap thấp (phân vị 75% < 9%): LP thật **chọn rất ít vị thế (> 65% chỉ một vị thế) và khoảng rất rộng**, khác hẳn cân bằng nhiều khoảng hẹp.
- **Phát hiện 2:** "lặp lại hôm qua" khớp > 99,5% với hành vi thật → LP cập nhật chậm.
- **Phát hiện 3–4:** chiến lược cân bằng tính từ 7 ngày lịch sử (I_NE) khớp hành vi tốt hơn; dùng nó tăng lợi nhuận ngày trung vị \$116 (ROI ngày +0,009%); khoảng cách tới cân bằng thật tới +0,855% ROI ngày.
- Bể USDC/WETH 1% có nhiều JIT nên mô hình phủ kém (390/833 khoảng không có người chơi).

## 5. Giới hạn và hướng tiếp theo
- Tự nêu (mục 6): **đưa LP ở thang thời gian khác (như JIT) vào mô hình**; thiết kế chiến lược tốt hơn từ dữ liệu lịch sử.
- Giả định `f_m` cố định (khối lượng không phụ thuộc độ sâu) — bỏ qua đúng kênh mà trợ cấp khai thác trong bài gốc (trợ cấp → khối lượng ↑ → phí ↑).
- Nhận xét của nhóm: không có trợ cấp, không có kẻ tấn công rút thanh khoản; trò chơi một lượt nên không có chuỗi Prep → Attack → Post.

## 6. Liên hệ với đồ án
- **Khoảng trống B:** độ rộng nội sinh có trong mô hình nhưng không có trợ cấp; LP thật ở bể rủi ro chọn khoảng rộng, lệch cân bằng.
- **Khoảng trống A:** hướng tiếp theo "LP ở thang thời gian khác" ↔ nhóm đặt LP thụ động, farmer trợ cấp và kẻ tấn công cùng một bể.
- **Range-aware (GĐ3):** (i) Định lý 3.7 giải thích vì sao cơ chế chuẩn trung lập với độ rộng; (ii) tham số α là **tiền lệ "tổng quát hóa quy tắc chia phí bằng một tham số"**, nhưng α tác động lên *lượng* thanh khoản, còn `φ(w)` của nhóm tác động lên *độ rộng*. Nên đặt hai cái cạnh nhau trong Related Work để phân biệt.
- **Victim thích nghi:** phát hiện "LP cập nhật chậm, lặp lại hôm qua" ủng hộ mô hình victim thích nghi dựa trên lợi suất quá khứ (quyết định kỹ thuật số 3).
- **Phần B:** chỉ số "overlap" (khoảng cách biến phân toàn phần giữa hai phân bố vốn theo khoảng) có thể dùng để so sánh phân bố thanh khoản mô phỏng với kịch bản tham chiếu.

## 7. Câu có thể dùng trong Related Work (diễn đạt lại)
> Tang et al. [2025] mô hình hóa việc cung cấp thanh khoản trong CLMM như một trò chơi giữa các LP có ngân sách, tự chọn khoảng giá, và chứng minh trò chơi tương đương một trò chơi "nguyên tử" trên từng tick có cân bằng Nash duy nhất dạng waterfilling. Hệ quả là dưới quy tắc chia phí pro-rata, độ rộng vị thế tự nó không ảnh hưởng tới phần phí — chỉ histogram thanh khoản theo tick là quan trọng. Mô hình giả định tổng phí mỗi tick cố định và không có trợ cấp hay kẻ tấn công; các tác giả để ngỏ việc đưa LP ở thang thời gian khác vào mô hình.

## 8. Câu hỏi người chấm có thể hỏi
- "Tham số α của Tang có phải là range-aware không?" → không: α biến đổi *lượng* thanh khoản trong tỷ lệ chia; với một tick, α > 1 còn khuyến khích dồn hơn. `φ(w)` gắn với độ rộng của từng vị thế và chỉ có tác dụng khi LP tự chọn độ rộng (GĐ3).

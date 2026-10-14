# Phiếu đọc — Fan, Marmolejo-Cossío, Moroz, Neuder, Rao, Parkes 2021, *Strategic Liquidity Provision in Uniswap v3*

- **Nguồn:** arXiv:2106.12033 (bản v5, 08/2024), Harvard. 28 trang. (Bản đầu 06/2021, là một trong những bài sớm nhất về chiến lược LP trên v3.)
- **PDF:** `01_Tai_lieu_tham_khao/02_Chien_luoc_LP_va_ly_thuyet_tro_choi/2021_Fan_Strategic_Liquidity_Provision_in_Uniswap_v3.pdf`
- **Mức độ đọc:** toàn văn mục 1–7; phụ lục (biến thể log-utility) lướt (10/10/2026).
- ⚠ **Sửa thông tin cũ:** bài gốc (Lu et al.) **không** trích bài này (đã kiểm `du_lieu_tho/lu_refs.txt` — Ref 23 là Sizheng Fan, bài khác).
- **Vai trò trong đồ án:** nền cho **LP chiến lược đơn lẻ** (tối ưu độ rộng và thời điểm tái cân bằng dưới rủi ro); nêu rõ giả định "LP nhỏ" mà kịch bản tấn công phá vỡ; hướng tiếp theo là khung trò chơi cho LP lớn.

## 1. Câu hỏi
Một LP trên Uniswap v3 nên phân bổ vốn vào các khoảng giá thế nào, và khi nào nên tái phân bổ (tốn gas, trượt giá), để tối đa tiện ích kỳ vọng có tính đến mức ngại rủi ro?

## 2. Mô hình
- Giá chia thành "bucket" `B_i = [a_i, b_i]`; vị thế nhiều bucket ≡ nhiều vị thế một bucket (cùng nhận xét với Tang et al.).
- **Một LP duy nhất, đủ nhỏ**: phân phối đường giá (cặp giá hợp đồng – giá thị trường) **không phụ thuộc** thanh khoản của LP. ⇒ **Định lý 4 (từ Fan et al. 2022):** phí LP kiếm được **tuyến tính** theo phân bổ của chính mình và **độc lập** với LP khác; **Định lý 7:** toàn bộ thu nhập tuyến tính theo phân bổ và vốn.
- Giá: giá thị trường theo GBM (ước MLE trên dữ liệu phút ETH/BTC — biến động thấp, ETH/USDT — biến động cao, 03/2022–02/2023); mỗi vòng có `k_r = 10` lệnh "phi arbitrage" đẩy giá hợp đồng ×(1+λ_r) hoặc ÷(1+λ_r); arbitrage kéo giá hợp đồng về khoảng không-arbitrage `[(1−γ)P_m, (1−γ)⁻¹ P_m]`. Lệnh **theo giá chứ không theo khối lượng** để giữ tính độc lập với thanh khoản.
- Chiến lược **τ-reset:** phân bổ quanh bucket tham chiếu, tái phân bổ khi giá rời quá τ bucket; chi phí tái phân bổ tỷ lệ `(1−η)`.
- Tiện ích CARA `u_a(x) = (1−e^{−ax})/a` (a > 0 ngại rủi ro).
- So sánh 5 chiến lược: tĩnh tối ưu (OSA), đều theo thanh khoản (ULRA), đều theo vốn (UPRA), tối ưu không ngữ cảnh (OIRA), tối ưu có ngữ cảnh bằng mạng nơ-ron hồi quy (ODRA). Mã: github.com/Evensgn/uniswap-active-lp.

## 3. Kết quả
- Chiến lược động có ngữ cảnh (ODRA) tốt nhất; mọi chiến lược τ-reset tối ưu đều hơn tĩnh và hơn phân bổ đều kiểu v2.
- **Ngại rủi ro hơn → rải thanh khoản rộng hơn** (Hình 10, 14).
- **Biến động cao hơn → vị thế hẹp hơn** (vì tái phân bổ thường xuyên hơn với cùng τ).
- **Khối lượng phi arbitrage lớn hơn → rải rộng hơn** (LP kiếm phí từ lệnh phi arbitrage).
- **Chi phí tái phân bổ cao → τ tối ưu lớn hơn** (ít reset hơn).

## 4. Giới hạn và hướng tiếp theo (mục 7)
- Tự nêu: đưa LVR vào mục tiêu (LP phòng hộ delta); **"incorporating a game-theoretic framework to liquidity provision which is more apt for large LPs"**; cạnh tranh giữa các bể (v2 vs v3).
- Giả định chính: LP nhỏ, giá ngoại sinh, lệnh theo giá.
- Nhận xét của nhóm: không có trợ cấp; không có LP khác chiến lược; trong kịch bản tấn công, kẻ tấn công **không** nhỏ — tường `L_A` thay đổi cả phần chia phí lẫn đường giá, nên Định lý 4 (phí độc lập với LP khác) **không còn đúng** — đây chính là lý do victim phải tính phần chia `L_V/(L_V + L_A)` như Lemma 4 của bài gốc.

## 5. Liên hệ với đồ án
- **Khoảng trống A:** hướng tiếp theo "khung trò chơi cho LP lớn" → trích được.
- **Victim agent (người làm C, nhưng phần B cần hiểu để giải thích kết quả):** các xu hướng định tính (ngại rủi ro → rộng; biến động → hẹp; phí tái phân bổ → ít reset) là kỳ vọng để **kiểm tra hợp lý** hành vi victim thích nghi khi sang GĐ3 (độ rộng nội sinh).
- **Giả định LP nhỏ** là điểm phân biệt rõ với nhóm: nhóm cố ý mô hình hóa tác động của LP lớn (tường) lên phần chia phí và giá.

## 6. Câu có thể dùng trong Related Work (diễn đạt lại)
> Fan et al. [2021] tối ưu chiến lược phân bổ và tái phân bổ thanh khoản động cho một LP trên Uniswap v3 dưới các mức ngại rủi ro, cho thấy LP ngại rủi ro rải vốn rộng hơn và chi phí tái phân bổ cao làm giảm tần suất điều chỉnh. Phân tích dựa trên giả định LP đủ nhỏ để không ảnh hưởng tới giá và phần chia phí của người khác — giả định mà tường thanh khoản của kẻ tấn công phá vỡ; chính các tác giả đề xuất khung lý thuyết trò chơi cho LP lớn là hướng tiếp theo.

## 7. Câu hỏi người chấm có thể hỏi
- "Victim của nhóm khác victim của Fan ở đâu?" → Fan: một LP nhỏ, phí độc lập với người khác. Nhóm: victim cạnh tranh phần phí với tường `L_A` và với farmer-trợ cấp; lựa chọn tối ưu phụ thuộc `L_A` (Lemma 4 bài gốc: `L_V* ≈ L_A` tại `L_A = fQ/(4c_V)`).

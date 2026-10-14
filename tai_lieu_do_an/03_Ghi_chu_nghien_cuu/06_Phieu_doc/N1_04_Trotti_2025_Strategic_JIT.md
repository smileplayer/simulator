# Phiếu đọc — Trotti, Tang, El-Azouzi, Fanti, Menasché 2025, *Strategic Analysis of Just-In-Time Liquidity Provision in Concentrated Liquidity Market Makers*

- **Nguồn:** arXiv:2509.16157 (v2 ngày 11/06/2026), UFRJ + CMU + Avignon. Danh mục ghi venue AFT 2025 — bản PDF không ghi hội nghị, cần kiểm trên DBLP trước khi trích venue. 38 trang (25 trang chính + phụ lục chứng minh). Lý thuyết tối ưu + đối chiếu dữ liệu.
- **PDF:** `01_Tai_lieu_tham_khao/04_JIT_va_vi_the_sieu_hep/2025_Trotti_Strategic_Analysis_of_Just_In_Time_Liquidity_Provision_in.pdf`
- **Mức độ đọc:** toàn văn mục 1–9; phụ lục B–C đọc chứng minh định lý 3.1 và bổ đề 3.1; phần còn lại lướt (10/10/2026).
- **Tác giả chung:** Weizhao Tang và Giulia Fanti cũng là tác giả bài lý thuyết trò chơi CLMM (Tang et al. 2025, Ref 45 của bài gốc) → đọc liền với phiếu N1_06.
- **Vai trò trong đồ án:** mô hình hình thức **ở mức từng giao dịch** về cách chia phí và tác động giá giữa LP siêu hẹp và LP thụ động trong CLMM; cho định nghĩa "price impact" dùng được trong phần đo lường; hướng tiếp theo là **giao thức bảo đảm công bằng cho LP thụ động**.

## 1. Câu hỏi
Một LP JIT nhìn thấy swap sắp chạy nên chọn vị thế `(L, a, b)` thế nào để tối đa lợi nhuận? Hành vi thực tế có tối ưu không? Tác động lên LP thụ động và trader?

## 2. Mô hình
- CLMM theo tick (`t_i = 1.0001^{τ(i−ι)}`); vị thế `(L, a, b)`; dự trữ theo công thức v3 chuẩn (pt 3).
- **Phí chia pro-rata theo tick** (mục 2.2.1): `F_n = Σ_m δ_m · P_{n,m} / P_m`, với `δ_m` là phí sinh ra ở tick m, `P_{n,m}` thanh khoản của LP n ở tick m. ⇒ Đây chính là quy tắc `φ = 1` mà range-aware của nhóm sẽ thay đổi.
- **Price impact (Định nghĩa 2.1):** `C_n = V_mint − V_withdraw` (giá trị vị thế lúc vào trừ lúc rút, theo giá thị trường). Họ dùng thuật ngữ này thay cho "impermanent loss" vì nó có thể âm (tức có lãi). `PI = C_n / V_mint`.
- Bài toán JIT (mục 4): `U(s; θ) = F(s; θ) − C(s; θ)` (trừ thêm chi phí đấu giá `v` hằng số nếu có), ràng buộc ngân sách `L·V(a,b) ≤ ρ`; chỉ xét khoảng mà giá thực sự đi qua `R(q, q*)`. Giả định giá thị trường không đổi trong một giao dịch; chỉ một vị thế (dữ liệu 2024–2025 cho thấy JIT thực tế chỉ dùng một vị thế).

## 3. Kết quả lý thuyết
- **Định lý 3.1 + Hệ quả 3.1:** với giá thị trường cố định, LP **lãi** khi swap đẩy giá bể **ra xa** giá thị trường, **lỗ** khi swap kéo giá bể **về gần** giá thị trường (vì người giao dịch mua được giá tốt). Điều kiện chính xác: `C ≤ 0 ⟺ (1/q̂)(p_x/p_y)² ≥ q̂'` (khi giá giảm) — tương đương `p_x/p_y ≤ √(q̂ q̂')` (khi giá tăng).
- **Bổ đề 3.1–3.2:** thanh khoản là "giảm chấn" — `L → ∞` thì giá sau swap → giá trước swap; **bất kỳ** LP nào bơm đủ nhiều thanh khoản cũng ép được điều này (Nhận xét 3.2).
- **Bổ đề 4.1:** phí của một LP liên tục theo L và bị chặn trên bởi `α·Δx` (toàn bộ phí của swap).
- **Định lý 4.1:** luôn tồn tại chiến lược tối ưu (tập khoảng giá hữu hạn, U liên tục, miền L compact).
- Ba "nguyên mẫu" swap: *overpriced* (đẩy giá ra xa — JIT lãi nhất), *arbitrage* (kéo về — JIT thường lỗ; Mệnh đề 5.1 cho điều kiện đủ để phí không bù được), *overshoot* (vượt qua giá thị trường — chỉ đặt thanh khoản ở đoạn đã vượt qua).
- Thuật toán 1: duyệt mọi `(a,b) ∈ R(q,q*)`, giải tối ưu một chiều theo L (PSO hoặc tìm nhị phân); thực tế 95% swap chỉ đi qua ≤ 2 tick nên duyệt được. Mã: github.com/brunoCCOS/JITUniswapOptimization.

## 4. Kết quả thực nghiệm (mục 6)
- Dữ liệu: bể USDC/WETH (`0x88e6…5640`) trên Ethereum, 01–06/2024, 1.013.147 giao dịch, từ Allium; nhận diện JIT theo tiêu chí của Capponi et al.; **6.829 swap JIT** (mục 6.1.1 ghi 6.884 — bài không nhất quán).
- JIT thực tế kém tối ưu: dùng Thuật toán 1 có thể **lãi thêm tới 69%** (abstract, mục 6.1.1). (Phần đóng góp ở mục 1 lại ghi "giảm lợi nhuận tới 41%" — hai con số đo khác chiều; khi trích dùng 69% như abstract.)
- Lợi nhuận JIT **chủ yếu đến từ price impact, không phải phí**: tỷ lệ `|C|/(|C|+|F|)` trung vị 0,826, trung bình 0,752 (Hình 4). (Mục 1 ghi 93,7% — không khớp hình; ưu tiên số của Hình 4.)
- JIT hiện chiếm < 2% tổng phí của bể. Nhưng nếu JIT tối ưu và có ngân sách lớn, **phí của LP thụ động giảm tới 44% mỗi giao dịch** (abstract, Hình 5a; mục 1 ghi 40%), trong khi trượt giá của trader giảm (Hình 5b).
- Mục 7.1: phân tích lợi nhuận của arbitrageur thực ra lấy từ trader "nhiễu" chứ không luôn từ LP; JIT giảm biên độ lệch giá → giảm lợi nhuận arbitrage và phần phí của LP thụ động. Nối với LVR (Milionis et al.).

## 5. Giới hạn và hướng tiếp theo
- Tự nêu: không mô hình hóa đấu giá giữa các JIT (thiếu dữ liệu bên thua), coi chi phí đấu giá là hằng số; một bể, sáu tháng; giả định giá thị trường không đổi trong giao dịch.
- **Hướng tiếp theo (mục 9):** *"Future research should explore extensions of AMM models that account for JIT strategies and protocols that safeguard fairness for passive LPs."* → mở rộng mô hình AMM có JIT, và **giao thức bảo vệ công bằng cho LP thụ động**.
- Nhận xét của nhóm: mô hình một giao dịch, LP thụ động cố định (không phản ứng); không có trợ cấp; không xét kẻ tấn công rút thanh khoản để gây biến động.

## 6. Liên hệ với đồ án
- **Khoảng trống C:** câu hướng tiếp theo ở mục 9 — trích được.
- **Phần B (đo lường):** định nghĩa `C_n = V_mint − V_withdraw` và điều kiện dấu (Định lý 3.1) giúp **tách thiệt hại nạn nhân thành phần phí và phần price impact** — hữu ích khi giải thích vì sao nạn nhân lỗ khi kẻ tấn công xả giá (giá bị đẩy ra xa rồi arbitrage kéo về). Có thể dùng để kiểm định: nạn nhân phải lỗ ở pha Post khi giá hồi về.
- **Engine (A):** công thức phí theo tick `F_n = Σ δ_m P_{n,m}/P_m` là test đơn vị tốt cho "hai LP cùng tick chia phí theo L".
- **Bổ đề 3.2 / Nhận xét 3.2** ("bất kỳ LP nào bơm đủ thanh khoản cũng neo được giá") là nền lý thuyết cho việc tường `L_A` của kẻ tấn công giữ giá ổn định ở pha Prep → giải thích vì sao biến động pha Prep thấp.

## 7. Câu có thể dùng trong Related Work (diễn đạt lại)
> Trotti et al. [2025] xây dựng mô hình tối ưu ở mức từng giao dịch cho LP JIT trong CLMM và chứng minh luôn tồn tại chiến lược tối ưu; trên dữ liệu bể USDC/WETH nửa đầu 2024, họ cho thấy lợi nhuận JIT đến chủ yếu từ tác động giá chứ không từ phí, và JIT tối ưu với ngân sách lớn có thể làm phí của LP thụ động giảm tới 44% mỗi giao dịch. Các tác giả nêu thiết kế giao thức bảo đảm công bằng cho LP thụ động là hướng mở; mô hình của họ coi phân bố thanh khoản thụ động là cố định và không có trợ cấp.

## 8. Câu hỏi người chấm có thể hỏi
- "Price impact khác impermanent loss / LVR thế nào?" → price impact = chênh giá trị vị thế trước/sau, có thể âm; với một giao dịch đơn, price impact và LVR trùng nhau (Trotti dẫn Alexander & Fritz).

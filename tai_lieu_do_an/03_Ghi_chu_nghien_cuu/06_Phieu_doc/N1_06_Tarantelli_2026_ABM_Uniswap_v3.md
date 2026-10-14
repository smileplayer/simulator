# Phiếu đọc — Tarantelli 2026, *Constructing and Validating an Agent-Based Simulator for Uniswap v3 Concentrated Liquidity*

- **Nguồn:** Zenodo record 21647967 (2026), **một tác giả, không ghi đơn vị cụ thể, không qua phản biện**. 21 trang. Dữ liệu tới 21/07/2026 → bài rất mới.
- **PDF:** `01_Tai_lieu_tham_khao/07_Simulator_va_phuong_phap_danh_gia/2026_Tarantelli_Agent_Based_Simulator_Uniswap_v3.pdf`
- **Mức độ đọc:** toàn văn kể cả phụ lục A–B (10/10/2026).
- ⚠ **Độ tin cậy:** bản Zenodo tự đăng; nên trích như "một simulator gần đây" chứ không làm chỗ dựa chính. Có thể bổ sung trích Urusov et al. 2024 (backtesting CLMM) hoặc Fritsch 2021 bên cạnh.
- **Vai trò trong đồ án:** simulator CLMM gần nhất với nhóm; **mẫu phương pháp kiểm định hai lớp** (cơ học + thống kê) cho bảng kiểm định RQ1 của phần B; tự nêu **thiếu LP chiến lược** → khoảng trống A.

## 1. Câu hỏi
Xây một simulator Uniswap v3 trung thành với phương trình giao thức ở mức vị thế, và kiểm định nó tái lập được các "dấu hiệu thống kê" (stylised facts) của bể thật, không nhằm dự báo giá.

## 2. Cách xây (mục 3–4)
- Trạng thái `S_t = {P_t, tick_t, tập vị thế (tick_l, tick_u, L), phí tích lũy}`; dự trữ của vị thế tái dựng từ `(L, p_a, p_b, P)` sau mỗi sự kiện.
- **Quá trình sự kiện:** rời rạc, mỗi khe là mint / swap / burn với xác suất ước từ dữ liệu (giai đoạn khởi động 1,89 / 95,93 / 2,18%; vận hành 2,75 / 94,23 / 3,02%). 8 khe nén = 1 ngày.
- **Mint:** gói nhiều LP (trung bình 12 chân, Poisson); 50% là "bậc thang lồng nhau" quanh giá, 50% "vai" lệch nhẹ; độ rộng lấy từ phân phối thực (trung vị 36 tick, phân vị 90% = 580); "lõi" được dịch về giá hiện tại mỗi 8 khe; cắt vị thế xa > 1200 tick, tối đa 350 vị thế.
- **Swap:** chỉ thanh khoản đang hoạt động tham gia; cập nhật `√P` chuẩn v3. **Giá được sinh ngoại sinh** (GARCH(1,1) + Student-t + nhảy Bernoulli), rồi **nghịch đảo ra lượng swap** cần thiết → luồng lệnh không do tác nhân quyết định. Phí `f·|Δx|·P` chia pro-rata cho vị thế đang hoạt động.
- **Burn / refresh:** chọn vị thế đóng theo trọng số tuổi × (không hoạt động ×8) × kích thước; vị thế không hoạt động được "làm mới" quanh giá.

## 3. Kiểm định (mục 5–6) — phần quan trọng cho phần B
- Dữ liệu: bể WETH/USDC 5 bps Ethereum, **181 ngày** 22/01–21/07/2026, ~\$24,79 tỷ khối lượng; 1.083.191 swap, 27.132 mint, 33.871 burn.
- **Chia theo thời gian, không rò rỉ:** 120 ngày hiệu chỉnh, 61 ngày giữ lại; 6 đường Monte Carlo.
- **Lớp cơ học:** sai số tương đối của bất biến v3 ~10⁻¹⁶; tỷ lệ thanh khoản hoạt động; trượt giá phụ thuộc trạng thái.
- **Lớp thống kê (ngoài mẫu):** độ lệch chuẩn log-return ngày 0,0301 vs 0,0292 thật; biên cao–thấp 0,0291 vs 0,0411 (thiếu); kurtosis dư 3,70 vs 3,49; KS = 0,10 (p = 0,93), Wasserstein = 0,0058; tương quan hình dạng `L(tick)` tại một ngày cố định 0,8568.
- **Khoảng trống tự khai:** thanh khoản **không hoạt động** mô phỏng 0,0185 vs thật 0,3864 ở tập giữ lại — rất lệch; tác giả ghi rõ là dấu vết của việc bỏ qua hành vi LP chiến lược.

## 4. Giới hạn và hướng tiếp theo (mục 7–8, nguyên ý)
- Burn và refresh là dạng rút gọn: **không** mô hình rút thanh khoản theo gas, phòng hộ tồn kho, arbitrage liên sàn.
- *"Cross-venue arbitrage latency, liquidation cascades and **strategic LP withdrawals** remain outside the current state transition."*
- Hướng tiếp: arbitrage liên sàn, dòng thanh lý, rút theo gas, **"richer strategic LP rebalancing"**; "further strategic LP heterogeneity remains open".
- Nhận xét của nhóm: **không có trợ cấp, không có kẻ tấn công, LP không tối ưu hóa**; giá ngoại sinh nên không thể có kịch bản "kẻ tấn công xả làm giá sập" nội sinh.

## 5. Liên hệ với đồ án
- **Khoảng trống A:** đây là bằng chứng mạnh — simulator CLMM mới nhất vẫn chỉ có LP dạng rút gọn và tự nhận thiếu rút thanh khoản chiến lược.
- **Khác biệt kiến trúc cần nói rõ:** Tarantelli sinh giá trước rồi suy ra swap; simulator của nhóm phải để **swap do tác nhân (farmer, kẻ tấn công, nền) quyết định** và giá là kết quả — vì cú xả của kẻ tấn công *gây ra* biến động.
- **Phần B (kiểm định RQ1):** mượn khung hai lớp:
  - Lớp cơ học → test của engine (A): bất biến, bảo toàn token.
  - Lớp "dấu hiệu" → bảng kiểm định RQ1: so **phân phối / dấu hiệu định tính** của bài gốc (thời gian các pha, tỷ lệ khối lượng Prep/Attack/Post so với nền, biến động tăng qua ba pha) thay vì khớp từng đường giá. Ghi rõ "mục tiêu là tái lập dấu hiệu, không tái lập quỹ đạo" (cùng triết lý Fagiolo et al. 2007 mà Tarantelli dẫn).
  - Chạy nhiều seed và báo khoảng tin cậy bootstrap (họ dùng 6 đường; nhóm đặt ≥ 10 seed).
  - Báo trung thực chỉ số không đạt (như họ khai khoảng trống thanh khoản không hoạt động) — đúng tinh thần quy ước "không tái lập được Post dưới nền thì ghi trung thực".
- **Kỹ thuật vẽ `L(tick)`:** dựng histogram thanh khoản bằng mảng hiệu tại hai đầu tick của mỗi mint/burn — dùng được trong `plots/` cho hình timeline.

## 6. Câu có thể dùng trong Related Work (diễn đạt lại)
> Tarantelli [2026] xây simulator tác nhân cho bể Uniswap v3 WETH/USDC, giữ đúng phương trình thanh khoản tập trung ở mức vị thế và kiểm định ngoài mẫu trên 181 ngày dữ liệu mainnet theo hai lớp: bất biến giao thức và các dấu hiệu thống kê của lợi suất. Tuy nhiên giá được sinh ngoại sinh rồi suy ra luồng lệnh, hành vi LP ở dạng rút gọn, và tác giả nêu rõ việc rút thanh khoản chiến lược nằm ngoài mô hình — không có trợ cấp hay kẻ tấn công.

## 7. Câu hỏi người chấm có thể hỏi
- "Sao không dùng lại simulator của Tarantelli?" → giá ngoại sinh (không cho phép cú xả nội sinh), LP không chiến lược, không có lớp trợ cấp; ngoài ra là bản tự đăng, mã chưa rõ.
- "Kiểm định simulator của nhóm thế nào?" → hai lớp như Tarantelli; lớp dấu hiệu so với số liệu thực nghiệm của bài gốc (bảng RQ1).

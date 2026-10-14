# Phiếu đọc — Kirillov & Chung 2022, *StableSims: Optimizing MakerDAO Liquidations 2.0 Incentives via Agent-Based Modeling*

- **Nguồn:** arXiv:2201.03519 (01/2022), Blockchain at Berkeley (nhóm sinh viên). 7 trang, không qua phản biện. Mã: github.com/BerkeleyBlockchain/stablesims.
- **PDF:** `01_Tai_lieu_tham_khao/07_Simulator_va_phuong_phap_danh_gia/2022_Kirillov_StableSims_Optimizing_MakerDAO_Liquidations_2_0_Incentives_via_Agent.pdf`
- **Mức độ đọc:** toàn văn (10/10/2026).
- **Vai trò trong đồ án:** **tiền lệ phương pháp** — dùng mô phỏng tác nhân (ABM) để **chọn tham số khuyến khích** của một giao thức DeFi thật, đo đánh đổi "chi phí khuyến khích vs hiệu quả". Biện hộ cho cách RQ2 đánh giá biện pháp bằng mô phỏng. Bài ngắn, cấp độ sinh viên — trích như tiền lệ, không như chuẩn mực.

## 1. Câu hỏi
Trong Liquidations 2.0 của MakerDAO (đấu giá Hà Lan), người "keeper" kích hoạt thanh lý được thưởng `chip · nợ_vault + tip` (chip tỷ lệ theo nợ, tip cố định). Chọn `chip`, `tip` thế nào để **trả ít khuyến khích nhất** mà vault không an toàn vẫn **bị thanh lý nhanh**?

## 2. Mô hình
- Viết lại bằng Python các mô-đun hợp đồng Maker (Core, Collateral, Dai, Liquidation 2.0, một phần Vow) thay vì chạy testchain — lý do: phức tạp, tốc độ, dễ ghép mô-đun. Gas lấy mẫu từ phân phối chuẩn quanh 300.000.
- **Chạy trên dữ liệu lịch sử** (giá ETH, giá gas, thanh khoản Uniswap v2 làm ước lượng bảo thủ) thay vì sinh quá trình giá — chọn 6 ngày nhiều thanh lý (05/09/2020 … 21/06/2021).
- Bước thời gian 10 phút; trong mỗi bước các keeper sinh hành động theo **thứ tự ngẫu nhiên** (mô phỏng độ trễ mạng).
- 5 loại tác nhân: 50 NaiveVaultKeeper (mở vault, tỷ lệ thế chấp ~175%), 1 SpotterKeeper (cập nhật giá), 5 BarkKeeper (thanh lý nếu thưởng > gas), 5 RedoKeeper (khởi động lại đấu giá cũ nếu có lãi), 5 NaiveClipperKeeper (mua lô nếu giá ≤ mức chiết khấu mong muốn ~85% và có lãi sau trượt giá Uniswap).
- Quét lưới `chip ∈ {0,001; 0,01; 0,1}` × `tip ∈ {100; 500; 1000}`, **10 lần chạy** mỗi cấu hình × mỗi ngày.

## 3. Thước đo
- Số thanh lý / bước; số vault không an toàn / bước; tiền khuyến khích đã trả / bước; **thời gian phản hồi trung bình** (số bước từ lúc vault không an toàn tới lúc bị thanh lý).
- **Chỉ số hiệu quả chi phí:** % giảm thời gian phản hồi **trên mỗi đô-la khuyến khích tăng thêm** so với cấu hình tối thiểu.

## 4. Kết quả
- Ngày 19/05/2021 (xấu nhất): cấu hình tối thiểu (0,001; 100) trả 4.705 DAI nhưng phản hồi 7,126 bước. (0,01; 100): 1,053 bước, 25.202 DAI. (0,001; 500): 1,063 bước, 18.437 DAI. (0,001; 1000): 1 bước, 38.725 DAI.
- Hiệu quả: tăng tip lên 500 hiệu quả hơn tăng chip lên 0,01 khoảng **1,5 lần** (0,0062% vs 0,00416% giảm thời gian / đô-la); tăng tip lên 1000 chỉ hiệu quả 0,4 lần so với tip 500 → **lợi ích cận biên giảm dần**.
- Khuyến nghị: tăng **tip cố định** hiệu quả hơn tăng **chip tỷ lệ**. Tham số thật sau đó được đặt (0,001; 300) — nhất quán độc lập với kết quả.

## 5. Giới hạn và hướng tiếp theo
- Tự nêu: tách vai trò keeper cho đơn giản; bỏ qua nghẽn mempool; giá trong 10 phút là hằng; không khẳng định cấu hình chính xác, chỉ khẳng định xu hướng.
- **Hướng tiếp theo đáng chú ý:** *"it would be important to ensure that incentives are balanced to protect against the incentive farming attack laid out in the Liquidations 2.0 documentation"* — tức **chính họ cảnh báo khuyến khích có thể bị "farm"** (tấn công khai thác khuyến khích) nhưng không mô hình hóa.
- Nhận xét của nhóm: keeper có luật ngưỡng cứng, không tối ưu chiến lược; không có kẻ tấn công.

## 6. Liên hệ với đồ án
- **Khoảng trống A/C (phương pháp):** tiền lệ dùng ABM để đánh giá tham số khuyến khích trước khi triển khai; RQ2 làm điều tương tự cho trần thưởng / trả thưởng trễ / cảnh báo.
- **Phần B (chỉ số):** "% cải thiện trên mỗi đô-la khuyến khích" là họ hàng trực tiếp của hai chỉ số dẫn xuất của nhóm — **hiệu quả chi tiêu** (thanh khoản còn lại / tổng trợ cấp) và **tỷ lệ rò rỉ** (lợi nhuận kẻ tấn công / tổng trợ cấp). Trích được để biện hộ cách định nghĩa.
- **Thiết kế thí nghiệm:** quét lưới tham số × nhiều seed × nhiều kịch bản thị trường — đúng khuôn của bản đồ nhiệt `(σ, Q)` ở GĐ2. Họ dùng 10 lần chạy mỗi ô — khớp mức "≥ 10 seed" của nhóm.
- **Khác biệt:** họ không có đối thủ chiến lược khai thác khuyến khích (chỉ cảnh báo "incentive farming"); nhóm mô hình đúng loại tấn công đó trong CLMM.

## 7. Câu có thể dùng trong Related Work (diễn đạt lại)
> Mô phỏng tác nhân đã được dùng để hiệu chỉnh tham số khuyến khích của giao thức DeFi trước khi triển khai: StableSims [Kirillov & Chung 2022] tái hiện cơ chế thanh lý của MakerDAO bằng Python, quét lưới hai tham số thưởng cho keeper trên dữ liệu lịch sử và đo thời gian phản hồi trên mỗi đô-la khuyến khích. Các tác giả lưu ý khuyến khích phải được cân bằng để chống "incentive farming" nhưng không mô hình hóa đối thủ khai thác khuyến khích — điều mà chúng tôi làm cho liquidity mining trong CLMM.

## 8. Câu hỏi người chấm có thể hỏi
- "Dựa vào đâu mà tin mô phỏng đánh giá được biện pháp?" → có tiền lệ (StableSims; Gauntlet làm cho MakerDAO / Aave); và bảng kiểm định RQ1 chứng minh simulator tái lập dấu hiệu thật trước khi dùng cho RQ2.

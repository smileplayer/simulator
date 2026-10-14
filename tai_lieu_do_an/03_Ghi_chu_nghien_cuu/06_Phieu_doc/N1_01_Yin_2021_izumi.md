# Phiếu đọc — Yin & Ren 2021, *On Liquidity Mining for Uniswap v3* (izumi Finance)

- **Nguồn:** arXiv:2108.05800 (08/2021), 6 trang, không qua phản biện. Tác giả thuộc izumi Finance (dự án thương mại, có lợi ích với chính cơ chế đề xuất).
- **PDF:** `01_Tai_lieu_tham_khao/03_Liquidity_mining_va_incentive/2021_Yin_On_Liquidity_Mining_for_Uniswap_v3.pdf`
- **Mức độ đọc:** toàn văn (đã đọc hết, 10/10/2026).
- **Vai trò trong đồ án:** **tiền lệ học thuật của thưởng theo khoảng giá**. Bắt buộc trích để không bị coi là nhận phát minh.

## 1. Câu hỏi
Uniswap v3 biến LP token thành NFT (không thay thế được), nên liquidity mining kiểu cũ (chia thưởng theo số LP token) không áp dụng được. Làm sao thiết kế liquidity mining cho v3 để bên phát thưởng **điều khiển được phân bố thanh khoản** theo giá?

## 2. Mô hình / cơ chế
- Chia trục giá thành tick `p_i = p0·d^i`; **bin** `b_i = [p_i, p_{i+1}]` (tương đương "một tick" trong bài gốc).
- Cơ chế (Định nghĩa 3.1): bên phát thưởng chọn tập bin `B`, tổng thưởng mỗi khe thời gian `R`, chia `R_i` cho từng bin (`Σ R_i = R`). Trong mỗi bin, LP thứ k nhận `R_i · L_ik / L_i` — **pro-rata theo L trong bin**.
- Mục tiêu thiết kế: linh hoạt, công bằng (lợi nhuận khớp vốn), ổn định (LP không phải chỉnh vị thế liên tục).
- Giả định mạnh: LP chỉ tối đa hóa thưởng; **bỏ qua phí giao dịch, bỏ qua dự báo giá, bỏ qua rủi ro giá / IL**.

## 3. Kết quả chính
- **Định lý 4.1 (cân bằng Nash, khi giá nằm đúng biên một bin):** mỗi LP rải token X lên các bin bên phải và Y lên các bin bên trái **tỷ lệ với `R_i`**. Trò chơi giữa các LP là tổng-không (zero-sum) với tổng thưởng cố định.
- Cân bằng không phải chiến lược trội (Ví dụ 1: nếu bin trống, đặt một lượng ε là ăn hết thưởng bin đó) và có thể không duy nhất. Tác giả cho rằng bên phát thưởng tự làm LP đầu tiên để "dẫn" cân bằng.
- Trường hợp tổng quát (giá nằm trong bin) không có lời giải dạng đóng — bài để ngỏ.
- Ba thiết kế phân bố thưởng: (a) giảm trượt giá — thưởng giảm dần theo khoảng cách tới giá hiện tại; (b) ổn định giá — dồn thưởng về hai biên `[p_a, p_b]`; (c) mô phỏng phân bố v2.

## 4. Câu quan trọng nhất cho đồ án (tr. 2, mục 3)
Tác giả **đã nhận ra** rằng nếu chỉ thưởng cho bin đang hoạt động (bin chứa giá hiện tại) thì *"the optimal provision strategy is to put all their liquidity on that bin"* — chiến lược tối ưu là dồn toàn bộ thanh khoản vào bin đó, và vị thế không ổn định. Đây chính là động cơ hình học của tấn công trong bài gốc (vị thế một tick), được nêu từ 2021 dưới góc độ thiết kế, **chưa** dưới góc độ an ninh.

## 5. Giới hạn (tự nêu + nhóm nhận xét)
- Tự nêu (mục 5): chưa xét dự báo giá / thu nhập phí ở bin hay hoạt động; chi phí gas O(|B|) quá đắt trên Ethereum.
- Nhận xét của nhóm:
  - Không có kẻ tấn công, không có LP nạn nhân, không có trợ cấp gắn với **khối lượng giao dịch** (thưởng ở đây gắn với thanh khoản, khác cơ chế Binance Alpha / bài gốc nơi trợ cấp đi theo khối lượng mua).
  - Điều khiển **vị trí** của thưởng (bin nào), không điều khiển **độ rộng** vị thế. Một LP vẫn có thể dồn hết vào bin có thưởng lớn nhất → không chống được vị thế siêu hẹp.
  - Không có thực nghiệm / mô phỏng.

## 6. Liên hệ với đồ án
- **Khoảng trống B:** izumi để ngỏ câu hỏi "chính sách thưởng + dự báo giá định hình phân bố thanh khoản ra sao" — đúng là chỗ GĐ3 (độ rộng nội sinh) chạm vào.
- **Bảng định vị (`02_Khoang_trong...md`, mục 3):** dòng izumi = "điều khiển vị trí thưởng, không phải độ rộng; dồn thưởng một bin → LP dồn vào bin đó". Đọc toàn văn xác nhận dòng này **đúng**.
- **Khác biệt với hướng `φ` của nhóm:** izumi chia `R_i·L_ik/L_i` (≡ `φ = 1` trong từng bin). Nhóm chia lại *phí* theo `L_i·φ(w_i)` với `φ` siêu tuyến tính theo độ rộng `w` → thưởng độ rộng chứ không thưởng vị trí.

## 7. Câu có thể dùng trong Related Work (diễn đạt lại, đã kiểm)
> Yin và Ren [izumi 2021] là những người đầu tiên đề xuất liquidity mining theo khoảng giá cho Uniswap v3: phần thưởng được phân bổ theo bin và chia pro-rata theo thanh khoản trong từng bin; ở cân bằng, LP rải vốn tỷ lệ với phân bố thưởng. Chính các tác giả nhận xét rằng nếu chỉ thưởng cho bin chứa giá hiện tại, chiến lược tối ưu của LP là dồn toàn bộ thanh khoản vào bin đó. Cơ chế này điều khiển *vị trí* của thanh khoản nhưng không ràng buộc *độ rộng* vị thế, và không xét kẻ tấn công hay LP nạn nhân.

## 8. Câu hỏi người chấm có thể hỏi
- "Thưởng theo khoảng giá đã có từ izumi 2021, nhóm mới ở đâu?" → izumi điều khiển vị trí, giả định LP chỉ săn thưởng, không đối thủ; nhóm xét độ rộng nội sinh dưới áp lực tấn công và đo cái giá với LP lành mạnh.

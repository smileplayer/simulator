# Phiếu đọc — Xiong, Wang, Knottenbelt, Huth 2023, *Demystifying Just-in-Time (JIT) Liquidity Attacks on Uniswap V3*

- **Nguồn:** Imperial College London; BRAINS 2023 / Cryptology ePrint Archive 2023/973 (bản trong thư mục, 10 trang). Đo lường thực nghiệm trên Ethereum.
- **PDF:** `01_Tai_lieu_tham_khao/04_JIT_va_vi_the_sieu_hep/2023_Xiong_Demystifying_JIT_Liquidity_Attacks_on_Uniswap_V3.pdf`
- **Mức độ đọc:** toàn văn kể cả phụ lục A (10/10/2026).
- **Vai trò trong đồ án:** bằng chứng thực nghiệm rằng **vị thế một tick làm hại LP hiện hữu** (cùng "nguyên thủy" với tường của kẻ tấn công trong bài gốc), và **lời kêu gọi thước đo phúc lợi** mà bộ 4 chỉ số của phần B đáp lại. Bài gốc không trích bài này.

## 1. Câu hỏi
Hình thức hóa và đo lường "tấn công thanh khoản JIT" trên Uniswap v3: ai làm, lãi bao nhiêu, ai bị hại, chiến lược có tối ưu không.

## 2. Mô hình (mục IV)
- Tác nhân: trader T, kẻ tấn công A (có nút do thám mempool, đủ vốn, đấu giá ưu tiên qua gas hoặc Flashbots / chuyển trực tiếp cho miner), các LP hiện hữu L, miner/validator M.
- Cơ chế: thấy swap lớn đang chờ → mint vị thế `[p_l, p_u]` ngay trước → swap chạy → burn ngay sau, **cùng block**.
- Doanh thu `= Fee + ΔValue`:
  - `Fee(L_A) = Δx_in · ϕ · L_A / L_T` (phí chia theo tỷ lệ thanh khoản trong khoảng; ϕ = mức phí).
  - `ΔValue` = thay đổi giá trị danh mục do tác động giá của chính swap (công thức 13, bốn trường hợp theo vị trí giá sau swap so với khoảng).
- Chi phí `= gas(mint) + gas(burn) + chuyển trực tiếp cho miner`. Giả định chi phí không phụ thuộc tham số → tối đa lợi nhuận ≡ tối đa doanh thu theo `(L_A, p_l, p_u)`.

## 3. Dữ liệu và phương pháp (mục V)
- Ethereum, block 12.545.219 → 16.530.247 (01/06/2021 – 31/01/2023, 20 tháng).
- **Heuristic 1:** mint và burn cùng block, swap mục tiêu cùng bể, người phát khác nhau, chỉ số giao dịch liên tiếp.
- Tác động lên trader: mô phỏng lại swap "như thể không có tấn công" (phản thực theo từng giao dịch).
- Chiến lược: Thuật toán 1 thử lệch tick dưới ±4 tickSpacing cho bot lớn nhất và chạy lại mô phỏng.

## 4. Kết quả chính (số liệu đã đối chiếu với PDF)
| Chỉ số | Giá trị | Vị trí |
|---|---|---|
| Số vụ | 36.671 | Abstract, V-B |
| Tổng lợi nhuận | 7.498 ETH (TB 0,204 ETH/vụ) | Insight 4 |
| Tổng doanh thu | 10.125 ETH = 7.111 ETH thay đổi danh mục + 3.014 ETH phí | V-C-1 |
| Thanh khoản JIT / khối lượng swap | trung bình **269×** | Insight 1, Hình 4 |
| ROI trung bình | 0,007% | Insight 4 |
| Vụ có lãi | 54,7% | Insight 4 |
| Bot lớn nhất `0xa57…6CF` | 76% số vụ, 92% lợi nhuận; dùng 308 EOA, 18 bot tổng cộng | Insight 5 |
| **Pha loãng LP hiện hữu** | **trung bình 85%** (bảng III: "Liq. Share" 85,42%) | Abstract, Insight 2 |
| Cải thiện giá cho trader | +0,139% trung bình (bể 1%: +0,699%) | Insight 6, Bảng II |
| Phần doanh thu đem hối lộ miner | 43,7% ± 25,5% | Insight 3 |
| Độ rộng vị thế JIT | **> 99,99% chỉ phủ đúng một tickSpacing** | VI-A-2 |
| Swap đi ≤ 1 tickSpacing | 97,84% | Bảng I |
| So với sandwich | 208.149 vụ (5,7×), vốn chỉ 6× khối lượng, ROI 1,629%, trader bị thiệt −5,93% | Insight 7 |
| Bot lớn nhất chọn tham số kém tối ưu | 27% số vụ; bỏ lỡ ≥ 7.766 ETH | Insight 8 |

**Ý nghĩa chính xác của "85%":** đó là **tỷ lệ thanh khoản trong khoảng mà kẻ JIT chiếm** lúc swap chạy, kéo theo kẻ JIT lấy trung bình 85% phí của swap đó (tr. 5: *"an average of 85% swap fees are exploited by adversaries"*). Khi trích nên viết "phần thanh khoản (và phí) của LP hiện hữu bị pha loãng trung bình 85%", không viết "LP mất 85% lợi nhuận".

⚠ Lỗi nhỏ trong bài: tổng chi phí ghi 2.027 ETH nhưng 539 + 2.088 = 2.627 ETH (và 10.125 − 7.498 = 2.627). Khi trích chi phí dùng 2.627 hoặc tránh trích.

## 5. Hướng tiếp theo / giới hạn (mục VII) — nguyên ý
1. Tìm lời giải giải tích cho bài toán tối ưu của kẻ tấn công.
2. Giao thức nên tìm cách **bảo vệ LP hiện hữu**; ví dụ cấm mint và burn cùng block — nhưng sẽ hại người cần tái cân bằng.
3. *"it's crucial for academic researchers to devise robust metrics that evaluate the net impact of JIT liquidity attacks on market efficiency, market fairness, and blockchain security … taking the welfare economics of various market participants into account"* → **cần thước đo vững cho tác động ròng, có tính phúc lợi của từng nhóm tham gia.**

Nhận xét của nhóm:
- Chỉ đo, không đánh giá biện pháp nào.
- JIT tồn tại một block, không cần trợ cấp; tường trong bài gốc tồn tại nhiều ngày và sống nhờ trợ cấp. Cùng hình học (một tick), khác thang thời gian và động cơ.
- Đo "pha loãng" theo phần chia phí trong một swap, không theo lãi/lỗ ròng của LP qua cả giai đoạn — khác cách bài gốc đo thiệt hại nạn nhân (gồm cả lỗ do giá bị xả).

## 6. Liên hệ với đồ án
- **Khoảng trống C:** câu kêu gọi thước đo phúc lợi ở mục VII là chỗ dựa trực tiếp cho bộ 4 chỉ số (thiệt hại nạn nhân, lợi nhuận kẻ tấn công, chi phí trợ cấp, thanh khoản bể) + 2 chỉ số dẫn xuất của phần B.
- **Lý do chọn hình học một tick ở GĐ1:** thực tế > 99,99% JIT dùng đúng một tickSpacing → vị thế siêu hẹp là chiến lược trội khi muốn chiếm phần phí.
- **Phương pháp cho phần B:** cách họ đo tác động lên trader bằng cách "chạy lại swap như thể không có tấn công" chính là ý tưởng phản thực mà simulator của nhóm làm ở quy mô cả vụ. Định nghĩa lợi nhuận `= Fee + ΔValue − Cost` tính từ dòng tiền của kẻ tấn công khớp yêu cầu "lợi nhuận kẻ tấn công đo độc lập, không suy từ thiệt hại nạn nhân".
- **Heuristic 1** là mẫu cho cách viết luật nhận diện sự kiện trong log (mint/burn/swap theo thứ tự).

## 7. Câu có thể dùng trong Related Work (diễn đạt lại, đã kiểm số)
> Xiong et al. [2023] đo 36.671 vụ thanh khoản JIT trên Uniswap v3 trong 20 tháng, với tổng lợi nhuận 7.498 ETH. Hơn 99,99% vị thế JIT chỉ phủ đúng một tickSpacing, và trong mỗi vụ kẻ JIT chiếm trung bình 85% thanh khoản trong khoảng, tức pha loãng phần phí của LP hiện hữu tương ứng. Các tác giả kêu gọi xây dựng thước đo vững cho tác động ròng của loại hành vi này lên hiệu quả và công bằng thị trường, có tính đến phúc lợi của từng nhóm tham gia — điều mà bộ chỉ số của chúng tôi hướng tới cho tấn công do khuyến khích.

## 8. Câu hỏi người chấm có thể hỏi
- "JIT và tấn công trong bài gốc khác gì?" → JIT: một block, không trợ cấp, lợi trader. Tấn công do khuyến khích: tường nhiều ngày nhờ trợ cấp, hút LP nạn nhân rồi rút tường và xả giá → hại cả LP lẫn thị trường.
- "Sao không cấm mint/burn cùng block?" → chặn JIT nhưng không chặn được tường nhiều ngày; và chính Xiong et al. nói nó hại người tái cân bằng.

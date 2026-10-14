# Phiếu đọc — Capponi, Jia, Zhu 2023, *The Paradox of Just-in-Time Liquidity in Decentralized Exchanges: More Providers Can Sometimes Mean Less Liquidity*

- **Nguồn:** arXiv:2311.18164v2 (02/2024), Columbia IEOR. 64 trang (26 trang chính + phụ lục chứng minh). Bài kinh tế học / lý thuyết trò chơi, không có dữ liệu thực nghiệm.
- **PDF:** `01_Tai_lieu_tham_khao/04_JIT_va_vi_the_sieu_hep/2023_Capponi_The_Paradox_of_Just_in_Time_Liquidity_in_Decentralized.pdf`
- **Mức độ đọc:** toàn văn phần chính (mục 1–6) + phụ lục A.1–A.12 (đọc lướt chứng minh, đọc kỹ dạng tiện ích và phúc lợi). 10/10/2026.
- **Lưu ý tác giả:** **Ruizhe Jia** là đồng tác giả bài gốc (Lu et al. 2026), nhưng bài gốc **không** trích bài này.
- **Vai trò trong đồ án:** **tiền lệ cơ chế gần nhất** với "chia lại phí giữa các loại LP" (range-aware). Phải trích và phải phân biệt rõ.

## 1. Câu hỏi
LP JIT (gửi thanh khoản ngay trước một lệnh lớn đang chờ trong mempool, rút ngay sau, cùng một block) có làm bể **sâu hơn** không? Trực giác: thêm người cung cấp → thêm thanh khoản. Bài chứng minh điều ngược lại có thể xảy ra.

## 2. Mô hình (mục 2)
- Bể CLMM một khoảng giá `[a, b]` **cho trước, ngoại sinh** — tác giả nói rõ: *"we assume that LPs are constrained to deposit within a predefined range [a,b], rather than allowing them to select this range endogenously"* (tr. 7).
- Trò chơi tuần tự 5 kỳ:
  1. N LP thụ động quyết định gửi toàn bộ vốn hay không (`d_P ∈ {0, e_P/N}`).
  2. Đến một trader **có thông tin** (xác suất α, biết giá tương lai thay đổi theo hệ số ζ) hoặc **không thông tin** (1−α, giao dịch vì định giá riêng ζ_U).
  3. LP JIT đến với xác suất π, **nhìn thấy lệnh trong mempool và biết loại trader**, chọn lượng gửi `d_J`.
  4. Thực thi: JIT gửi → swap → phí chia pro-rata `d_P/(d_P+d_J)` cho LP thụ động → JIT rút.
  5. Có cú sốc giá (nếu trader có thông tin) hoặc arbitrageur kéo giá về (nếu không).
- Giả định: phí gas / priority = 0; mọi tác nhân trung tính rủi ro; tham số là hiểu biết chung.

## 3. Kết quả chính
- **Mệnh đề 3.1–3.2:** cân bằng không tầm thường tồn tại và duy nhất khi `ζ_U > ζ(f, π) = 2(1+f)³ / (2 + πf(3+f))`. JIT **chỉ** gửi khi gặp trader không thông tin (né lựa chọn bất lợi); lượng JIT gửi là một bội số cố định `ν(π)` của thanh khoản thụ động (không vô hạn vì gửi quá nhiều làm giảm tác động giá mà JIT ăn được).
- Tiện ích LP thụ động trên một đơn vị vốn: `U(π) = α·C + (1−α)·R(π)`, với `C < 0` là chi phí bị trader có thông tin "bắn tỉa", `R(π)` là doanh thu phí từ trader không thông tin. LP thụ động gửi hết nếu `U ≥ 0`, không gửi gì nếu `U < 0` → **đóng băng thanh khoản** (liquidity freeze).
- **Định lý 3.3 (nghịch lý):** tồn tại ngưỡng `ζ*(f, π)`:
  - `ζ_U ≥ ζ*`: khối lượng trader không thông tin đàn hồi mạnh theo độ sâu → JIT **bổ sung** cho LP thụ động.
  - `ζ_U < ζ*`: khối lượng kém đàn hồi → JIT **chèn ép** (crowd out) LP thụ động; có thể gây đóng băng.
  - Với π = 1: `ζ*(f,1) = (√f + √(1+f))²`; ví dụ f = 0,03 → ζ* ≈ 1,4116 (Hình 2).
- Cơ chế kinh tế: `R(π) ∝ E[ phần thanh khoản thụ động × (khối lượng không thông tin + khối lượng đảo chiều) ]` — mất phần chia phí vs được thêm khối lượng.

## 4. Biện pháp: phí hai tầng (mục 4) — phần quan trọng nhất cho đồ án
- Tham số chuyển `λ ∈ [0,1]`: JIT giữ `λ` phần phí pro-rata của mình, `(1−λ)` chuyển sang LP thụ động.
  - Phần hiệu dụng của LP thụ động = `(Passive + (1−λ)·JIT) / (Passive + JIT)`; của JIT = `λ·JIT / (Passive + JIT)`.
  - **Trader vẫn trả đủ phí** — tổng phí không đổi, chỉ chia lại. (Cùng tinh thần quyết định kỹ thuật số 6 của nhóm: không đốt phí.)
- **Mệnh đề 4.2:** giảm λ (chuyển nhiều hơn) → JIT gửi ít hơn (so với thanh khoản thụ động) **và** trader không thông tin giao dịch ít hơn → có lực đối nghịch.
- **Định lý 4.3:** nếu `f < π` và `ζ_U ≥ ζ̂(f, π)` thì tiện ích LP thụ động giảm theo λ trên cả [0,1] → chuyển phí luôn có lợi cho LP thụ động, và có khoảng α mà λ đủ nhỏ ngăn được đóng băng.
- **Định lý 4.4 (phúc lợi):** phúc lợi = tổng tiện ích mọi tác nhân, chỉ dương nhờ "lợi ích từ giao dịch" của trader không thông tin. λ tối ưu phúc lợi = **λ lớn nhất mà LP thụ động còn tham gia**: `λ* = max{λ : U(π, λ) ≥ 0}`. Ví dụ số (Hình 3: π=1, f=0,003, ζ=1,05, ζ_U=1,02, α=0,1): `λ* ≈ 0,815`. λ tối ưu cho riêng LP thụ động là 0 (lấy hết phí của JIT).
  → **Đánh đổi giữa bảo vệ LP thụ động và phúc lợi chung** — đúng loại câu hỏi RQ2/RQ3 của nhóm ("giảm thiệt hại bao nhiêu, đổi lại mất bao nhiêu khối lượng / thanh khoản").
- **Triển khai (tr. 20–21):** LP khai báo mức cam kết thời gian `φ ∈ {0,1}` (1 = giữ ít nhất một block = LP dài hạn); hợp đồng theo dõi **hai biến feeGrowth toàn cục** riêng; mỗi swap chuyển `(1−λ)` phí của nhóm ngắn hạn sang nhóm dài hạn.
  - ⚠ **Trùng ký hiệu:** `φ` của Capponi là cờ cam kết thời gian, **khác** `φ(w)` (hàm trọng số độ rộng) của nhóm. Khi viết báo cáo nên ghi rõ hoặc đổi ký hiệu khi trích.
- **Mục 5 (Cournot):** hai JIT cạnh tranh lượng → mỗi JIT muốn chiếm > 50% bể → gửi hết vốn → ngưỡng chèn ép thấp hơn; cạnh tranh có lợi. Nhưng thực tế JIT nộp qua bundle / đấu giá gas nên không có cạnh tranh kiểu này.

## 5. Giới hạn (tự nêu + nhóm nhận xét)
- Tự nêu: khoảng giá ngoại sinh; gas = 0; JIT biết hoàn hảo loại trader.
- Nhận xét của nhóm:
  - Mô hình **một kỳ, một lệnh**; không có trợ cấp, không có kẻ tấn công dựng tường nhiều ngày.
  - Phân loại LP theo **thời gian nắm giữ** (một block). Kẻ tấn công trong bài gốc giữ vị thế một tick **nhiều ngày** → sẽ được xếp vào nhóm "dài hạn" và **hưởng** phần phí chuyển sang. ⇒ Phí hai tầng theo thời gian **không** chặn được tấn công do khuyến khích. Đây là lý lẽ mạnh để nhóm chuyển trục phân loại từ **thời gian** sang **độ rộng** (range-aware).
  - Không có mô phỏng / thực nghiệm; chỉ ví dụ số.

## 6. Liên hệ với đồ án
- **Khoảng trống B:** LP bị gò vào khoảng cho trước → độ rộng không nội sinh (trích được nguyên văn, tr. 7).
- **Khoảng trống C:** có đề xuất bảo vệ LP thụ động nhưng chỉ lý thuyết, không đánh giá thực nghiệm.
- **Bảng định vị:** dòng "Capponi et al. 2023 — phí hai tầng — chia lại phí theo loại LP — cùng họ cơ chế; lý thuyết, bối cảnh JIT": **đúng**, bổ sung thêm "phân loại theo thời gian nắm giữ".
- **Cho phần B (đo lường):** cách định nghĩa phúc lợi (tổng tiện ích các tác nhân; chuyển giao giữa tác nhân không tạo phúc lợi) giúp lập luận vì sao bộ 4 chỉ số tách riêng từng bên thay vì một con số tổng.
- **Cho RQ3:** khung "λ* = mức chuyển lớn nhất còn giữ LP tham gia" là mẫu tốt để phát biểu "φ cần điều kiện gì" và "LP lành mạnh mất bao nhiêu".

## 7. Câu có thể dùng trong Related Work (diễn đạt lại, đã kiểm)
> Capponi, Jia và Zhu [2023] chỉ ra rằng LP JIT — gửi và rút thanh khoản quanh một lệnh trong cùng một block — có thể chèn ép LP thụ động và làm *giảm* tổng thanh khoản khi khối lượng của trader không thông tin kém đàn hồi theo độ sâu bể. Họ đề xuất cấu trúc phí hai tầng chuyển một phần phí của LP ngắn hạn sang LP dài hạn mà không đổi tổng phí trader trả, và chứng minh mức chuyển tối ưu phúc lợi là mức lớn nhất mà LP thụ động còn tham gia. Phân tích của họ giả định khoảng giá ngoại sinh và phân loại LP theo thời gian nắm giữ; kẻ tấn công do khuyến khích giữ vị thế nhiều ngày nên không bị cơ chế này phân biệt.

## 8. Câu hỏi người chấm có thể hỏi
- "Sao không dùng luôn phí hai tầng của Capponi?" → phân loại theo thời gian; tường của kẻ tấn công tồn tại nhiều ngày nên được tính là LP dài hạn. Trục phân biệt đúng là **độ rộng** (tường luôn một tick).
- "Chia lại phí khác hạ phí ở đâu?" → tổng phí trader trả không đổi; chỉ thay ai nhận. Hạ phí làm giảm thu nhập mọi LP và thay đổi hành vi trader.

# Trình bày nhóm và chuẩn bị hỏi đáp

Bản đầy đủ có lời nói từng slide: `02_Bao_cao_va_trinh_bay/Kich_ban_trinh_bay_nhom.docx`. Đây là bản rút gọn để tra nhanh.

## Cấu trúc 8 slide — một người nói, ~7 phút 20 giây (1.100 âm tiết @150/phút)

| # | Slide | Giây | Nguồn |
|---|---|---|---|
| 1 | Vấn đề và bài báo — "không có lỗi mã, lỗ hổng nằm trong chính sách khuyến mãi" | 32 | Chung |
| 2 | Nền CLMM — cùng 1.000 USDT: dải 10% → L ≈ 19.487; một tick → L = 20 triệu | 52 | A |
| 3 | Hai tầng khuyến khích — σ cho trader theo khối lượng → phí chia theo `L_i/L_tổng` → APY → nạn nhân | 49 | A + Notion |
| 4 | Diễn biến tấn công 4 bước; vì sao phải rút tường trước khi xả | 76 | Notion, Hình 1 |
| 5 | Bằng chứng — biến động 0,0119 → 0,1593 → 0,8843; 29 vụ, 99 nạn nhân, 2,87 triệu USD | 61 | Notion, Hình 2–4 |
| 6 | Nghịch lý LP lý trí — `L_V*`, điều kiện `Q > c_V·L_A/f`, `c_V` đã gồm rủi ro | 65 | Notion + C |
| 7 | Khoảng trống và hướng nhóm — simulator 3 lớp, 4 chỉ số, range-aware | 83 | C |
| 8 | Lộ trình | 21 | Chung |

**Rút xuống 5 phút:** gộp slide 3 vào 2 (~35s), gộp bước 2–3 ở slide 4 (~25s), bỏ đoạn đuôi dày ở slide 5 (~20s). **Không cắt slide 6 và 7.**

**Cần cập nhật slide 7** theo đợt tra cứu: thêm câu *"cơ chế đã có triển khai thực tế (Merkl); đóng góp của nhóm là đánh giá và điều kiện `φ`, không phải phát minh"*.

Còn thiếu: hình timeline (Hình 1 bài gốc) cho slide 4, biểu đồ hộp (Hình 2) cho slide 5 — ghi nguồn.

## Hỏi đáp — câu trả lời ngắn

**Thưởng trả cho ai?** Hai tầng. Trợ cấp ngoại sinh trả cho người giao dịch theo khối lượng; phí của bể chia cho LP theo tỷ trọng thanh khoản. Tầng trên tạo khối lượng, tầng dưới biến khối lượng thành lợi suất hiển thị.

**Vì sao kẻ tấn công chọn một tick?** Cùng vốn, dải hẹp nhất cho `L` lớn nhất → trượt giá thấp nhất → hút người săn điểm. Đồng thời tỷ trọng `L` cao làm tăng phần phí được chia.

**Merkl làm rồi, mới ở đâu?** Công cụ không mới. Cái mới: chỉ ra nó tác động vào đâu trong chuỗi tấn công, điều kiện để có tác dụng (`φ` siêu tuyến tính — phạt tuyến tính có tác dụng bằng không lên lựa chọn độ rộng), và đo được hiệu quả. Bài gốc cũng không trích Merkl.

**Vì sao mô phỏng mà không dùng dữ liệu thật?** Cần phản thực: cùng kịch bản chạy có và không có biện pháp. Lịch sử chỉ có một nhánh; bài gốc tự nhận nhóm đối chứng không thiết lập được nhân quả.

**Làm sao biết simulator đúng?** Bộ tiêu chuẩn từ số liệu bài gốc: chuẩn bị theo ngày / thu hoạch theo giờ; biến động thấp rồi bùng nổ; quan trọng nhất là khối lượng tụt dưới nền sau cú sập. Thêm mốc lý thuyết: victim toàn tri khớp Lemma 4.

**Vì sao victim phải tối ưu hóa?** Nếu hardcode "thấy APY cao thì nạp", hạ `Q` thì nó nạp ít hơn chỉ vì mình viết thế — không chứng minh gì. Có tối ưu hóa thì kết luận là *nạn nhân duy lý tự nguyện không vào*.

**Phần phí bị phạt đi đâu?** Chia lại cho các LP khác theo trọng số; tổng phí không đổi.

**Range-aware có ngăn được tấn công không?** Không ngăn việc dựng tường. Nó làm nạn nhân trải rộng nên chỉ một phần vốn nằm trên đường sập; giảm bao nhiêu là thứ cần đo.

**`φ` chọn thế nào?** Không cố định một hàm; quét họ `min(1, (w/w₀)^α)` và báo cáo đánh đổi giữa giảm thiệt hại và giảm hiệu quả vốn.

**Đạo đức?** Toàn bộ trên mô phỏng và dữ liệu lịch sử công khai, không triển khai, không tương tác hệ thống đang chạy — như phần cân nhắc đạo đức của bài gốc.

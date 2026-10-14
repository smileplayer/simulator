# Khoảng trống nghiên cứu và định hướng

Tổng hợp từ đợt quét phần tóm tắt, giới hạn và hướng tiếp theo của các bài trong `01_Tai_lieu_tham_khao/` (04/10/2026). Kết quả quét thô ở `du_lieu_tho/scan_*.txt`. Các ý dưới đây đã diễn giải lại, không chép nguyên văn.

## 1. Năm khoảng trống

### A. Chưa có mô phỏng nào có đủ trợ cấp + kẻ tấn công + LP chiến lược — *tín hiệu mạnh nhất*

| Bài | Tự nhận thiếu gì |
|---|---|
| Tarantelli 2026 (simulator v3, kiểm định 181 ngày mainnet) | Rút thanh khoản dạng rút gọn; LP chiến lược, đa dạng còn mở; không có incentive hay tấn công |
| Tang et al. 2025 (lý thuyết trò chơi CLMM) [Ref 45] | Chưa đưa LP ở thang thời gian khác (JIT) vào mô hình |
| Chionas et al. 2026 (RL) | Hướng tiếp: cạnh tranh nhiều tác nhân giữa LP khác nhau |
| Urusov et al. 2025 | Hướng tiếp: lý thuyết trò chơi qua mean-field hoặc mô phỏng tác nhân |
| Fan et al. 2021 | Hướng tiếp: khung trò chơi cho LP lớn |
| Fritsch 2021; Fritsch & Canidio 2024 | Giả định vị thế mô phỏng quá nhỏ để ảnh hưởng người khác |
| Lu et al. 2026 | Biện pháp chưa đánh giá; đề nghị đánh giá bằng mô phỏng |

### B. Độ rộng khoảng giá hầu như chưa là biến nội sinh trong bối cảnh tấn công / khuyến khích

| Bài | Giới hạn |
|---|---|
| Lu et al. 2026 | Cố định một tick; bỏ sót biến thể nhiều tick |
| Capponi, Jia, Zhu 2023 (Paradox of JIT) | LP bị gò vào khoảng cho trước, không tự chọn |
| Zhang et al. 2023 (DRL) | Không xét vị thế ở khoảng tick tùy ý |
| izumi 2021 | Để ngỏ: chính sách thưởng cộng dự báo giá định hình phân bố thanh khoản ra sao |
| Tang et al. 2025 | Có độ rộng nội sinh nhưng không có trợ cấp; LP thật ở bể rủi ro chọn một dải rộng, lệch cân bằng |

### C. Bảo vệ LP thụ động: đề xuất nhiều, đánh giá ít, thiếu thước đo phúc lợi

- **Xiong et al. 2023 (JIT):** kêu gọi xây thước đo vững cho tác động ròng lên hiệu quả và công bằng thị trường, tính đến phúc lợi từng nhóm; giao thức nên tìm cách bảo vệ LP hiện hữu. → Bộ 4 chỉ số của đề tài đáp đúng lời kêu gọi này.
- **Trotti et al. 2025:** hướng tiếp là giao thức bảo đảm công bằng cho LP thụ động.
- **Capponi, Jia, Zhu 2023:** đề xuất **phí hai tầng** chuyển một phần phí của JIT sang LP thụ động — chỉ lý thuyết. Tiền lệ cơ chế gần nhất với hướng range-aware (cùng họ "chia lại phí giữa các loại LP"). Bài gốc không nối hai ý dù Jia là đồng tác giả cả hai.
- **TierDrop 2024:** giả định farmer bán tháo không hại người khác; Lu et al. cho thấy hoạt động của farmer chính là kênh gây hại cho LP.
- **Lu et al. 2026:** bốn biện pháp chỉ là đề xuất.

### D. Phát hiện sớm việc dựng tường: chưa có

- Bộ phát hiện của Lu et al. là hậu kiểm, ngưỡng theo ngày, chỉ mẫu một tick.
- SILS 2025: phát hiện LP ảnh hưởng hệ thống bằng phản thực; không có bối cảnh khuyến khích; chi phí tính toán cao.
- Phát hiện rug pull theo TVL (TON 2025, Solana 2026): AUC ~0,89 sau 5 phút nhưng cho token mới ra mắt. LROO 2026 cảnh báo **rò rỉ dữ liệu tương lai** phổ biến.
- Chỉ 29 vụ có nhãn → quá ít để học máy.

### E. Mô hình trợ cấp lý thuyết khác luật thật

- Lu et al.: `σ·min{v,Q}` tuyến tính, trần cứng.
- Binance Alpha (nguồn thứ cấp): điểm theo log₂ khối lượng mua, cửa sổ 15 ngày → trần mềm.
- Gogol et al. 2024: ở chuỗi lâu đời TVL tăng không kéo khối lượng tăng → củng cố rằng khối lượng tăng trong vụ tấn công là do trợ cấp.
- Dùng làm **kiểm tra độ vững**, không làm hướng chính.

## 2. Định hướng đề xuất

**Tên:** Đánh giá phản thực các biện pháp phòng thủ trước tấn công thanh khoản do khuyến khích trong CLMM bằng mô phỏng đa tác nhân, và điều kiện để phân bổ phí theo độ rộng khoảng giá có hiệu lực.

| | Câu hỏi | Khoảng trống | GĐ |
|---|---|---|---|
| RQ1 | Simulator có trợ cấp + kẻ tấn công + LP chiến lược có tái lập dấu hiệu thực nghiệm của bài gốc không? | A | 1 |
| RQ2 | Hạ trần, trả thưởng trễ, cảnh báo rủi ro giảm thiệt hại / lợi nhuận kẻ tấn công bao nhiêu, đổi lại mất bao nhiêu khối lượng và thanh khoản? `Q*` thực nghiệm ở đâu? | C | 2 |
| RQ3 | Khi LP tự chọn độ rộng, phân bổ phí theo độ rộng có giảm phơi nhiễm nạn nhân không, `φ` cần điều kiện gì, LP lành mạnh mất bao nhiêu hiệu quả vốn? | B + C | 3 |

**Đóng góp phát biểu trung thực:**
1. Simulator đầu tiên đặt trợ cấp, kẻ tấn công và LP chiến lược vào cùng một bể CLMM.
2. Đánh giá định lượng đầu tiên cho các biện pháp bài gốc chỉ đề xuất, bằng bộ thước đo phúc lợi.
3. Điều kiện `φ` siêu tuyến tính cho phân bổ phí theo độ rộng khi độ rộng nội sinh dưới áp lực tấn công.

## 3. Định vị so với prior art (để trả lời "Merkl làm rồi, mới ở đâu?")

| Cơ chế | Tương đương trong khung `φ` | Hệ quả với lựa chọn độ rộng |
|---|---|---|
| Paradigm 2021 — chia theo active liquidity | `φ = 1` | Đẩy LP **vào** một tick |
| Merkl — trọng số theo phí kiếm được | ≈ `φ = 1` | Đẩy vào một tick |
| Merkl — trọng số theo token nắm giữ | ≈ chia theo vốn ≈ `φ ∝ w` | Bàng quan, không đẩy ra |
| Merkl — loại trừ vị thế siêu hẹp | Ngưỡng cứng | Đẩy ra, nhưng bật/tắt |
| izumi 2021 — thưởng theo bin | Điều khiển *vị trí* thưởng, không phải độ rộng | Dồn thưởng một bin → LP dồn vào bin đó |
| Capponi et al. 2023 — phí hai tầng | Chia lại phí theo loại LP | Cùng họ cơ chế; lý thuyết, bối cảnh JIT |
| **Đề tài** — `φ` siêu tuyến tính, liên tục | `φ/w` tăng theo `w` | Đẩy ra khỏi một tick một cách liên tục; đo được cái giá |

Dòng Merkl đã kiểm lại 14/10/2026 trên docs.merkl.xyz (Concentrated Liquidity Campaigns): ba trọng số hiện là *đóng góp thanh khoản theo thời gian* + token0 + token1 (không còn là "phí kiếm được"); mặc định chỉ thưởng vị thế trong khoảng; chế độ APR cố định trả như nhau mỗi đô-la trong dải ("no tightness bonus"); blacklist người tạo vị thế hẹp rồi tự giao dịch. Không có ngưỡng độ rộng tối thiểu.

Câu trả lời mẫu: *"Công cụ không mới. Cái mới là chỉ ra nó tác động vào đâu trong chuỗi tấn công, điều kiện để nó có tác dụng, và đo được hiệu quả — đúng cách bài gốc tự biện hộ cho bốn biện pháp của họ."*

## 4. Không nên làm hướng chính

- **Bộ phát hiện bất thường:** lĩnh vực đông, 29 vụ có nhãn quá ít. Nếu làm thì theo luật, đánh giá ngay trong simulator, ở GĐ4.
- **Đo lại trên dữ liệu BSC:** bài gốc đã làm; dữ liệu Allium tốn phí; không trả lời được câu hỏi phản thực.

## 5. Rủi ro cần giữ trong đầu

- Không nhận cơ chế range-aware là phát minh.
- LP nạn nhân phải tối ưu hóa thật — khoảng trống A chỉ có giá trị khi tác nhân là chiến lược.
- Thử cả trợ cấp tuyến tính có trần và dạng log.
- GĐ4 (nếu làm): tách thời gian huấn luyện / kiểm tra nghiêm ngặt.

## 6. Ghi chú tra cứu

- Bài gốc không trích dẫn: nhóm JIT (Xiong 2023, Trotti 2025, Capponi–Jia–Zhu 2023), Merkl, izumi, Paradigm. Nên đưa cả vào Related Work.
- Weizhao Tang là tác giả cả bài lý thuyết trò chơi [Ref 45] lẫn bài phân tích chiến lược JIT — đọc liền.
- Chưa có công trình trích dẫn bài gốc (đăng 08/2026). Tra lại "Cited by" trên Google Scholar sau vài tháng.

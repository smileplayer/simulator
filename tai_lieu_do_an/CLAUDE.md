# Đồ án Blockchain — bối cảnh cho phiên làm việc tiếp theo

File này để Claude Code tự nạp khi mở phiên mới ở thư mục này. Chi tiết nằm trong `03_Ghi_chu_nghien_cuu/`; ở đây chỉ giữ những gì cần biết ngay.

## Người dùng

- **Đức**, phụ trách phần **B** (từ 10/10/2026; trước đó là "C") trong nhóm 3 người (môn NT547). Nền blockchain ban đầu ở mức cơ bản; đã học kỹ bài gốc qua 9 bài giảng ở phiên trước (CLMM, mô hình toán, threat model, các định lý, pipeline đo lường, kết quả, biện pháp).
- Trao đổi **bằng tiếng Việt**. **Cuối mỗi lần làm xong việc, luôn nói luôn bước tiếp theo nên làm là gì** (Đức yêu cầu 14/10/2026). Thích giải thích chi tiết, có ví dụ số cụ thể; muốn tự hiểu để bảo vệ được trước người chấm, không chỉ nhận kết quả.
- Phân công nhóm 7 tuần (12/10 – 29/11/2026), chi tiết ở `03_Ghi_chu_nghien_cuu/05_Phan_cong.md`:
  - **A** (chưa xác nhận người) = engine CLMM (`engine/`, `tests/`) + báo cáo nền tảng CLMM.
  - **B = Đức** (nhận ngày 10/10/2026) = đo lường, kiểm định, Related Work (`metrics/`, `plots/`): 4 chỉ số, mốc thời gian/pha, bảng kiểm định RQ1, biểu đồ, báo cáo kết quả tái lập. Slide 4, 5.
  - **C** (chưa chốt, có thể Hưng) = tác nhân, thí nghiệm GĐ2–GĐ3, biện pháp (`agents/`, `scenarios/`, `defenses/`). Người làm C cũng chốt interface trước 18/10.
  - Trước 10/10 phân công cũ là B = Hưng, C = Đức; các ghi chú cũ có thể còn theo cách gọi đó. Người trình bày chưa chốt lại.
- Buổi trình bày nhóm: **một người nói, 5–7 phút**.

## Đề bài (nguyên văn)

> Dựng simulator Uniswap-v3-style concentrated liquidity hoặc thu dữ liệu pool công khai quy mô vừa. Tái lập cơ chế incentive làm attacker tập trung liquidity, hút victim LP rồi gây biến động giá. Đo victim loss, attacker profit, subsidy cost và pool liquidity. Cải tiến: incentive cap/range-aware reward/risk warning hoặc anomaly detector.

## Bài gốc

Lu, Lao, Mao, Zhou, Jia, Wang — *Liquidity Mining as an Attack Surface: Incentive-Induced Liquidity Attacks in Concentrated Liquidity Market Makers*, USENIX Security 2026. PDF ở `00_Bai_goc/`. Tóm tắt đủ công thức: `03_Ghi_chu_nghien_cuu/01_Tom_tat_bai_goc.md`.

## Định hướng đã chốt

**Tên:** Đánh giá phản thực các biện pháp phòng thủ trước tấn công thanh khoản do khuyến khích trong CLMM bằng mô phỏng đa tác nhân, và điều kiện để phân bổ phí theo độ rộng khoảng giá có hiệu lực.

- **RQ1 (GĐ1):** Simulator có trợ cấp + kẻ tấn công + LP nạn nhân chiến lược có tái lập được các dấu hiệu thực nghiệm của bài gốc không?
- **RQ2 (GĐ2):** Hạ trần thưởng, trả thưởng trễ, cảnh báo rủi ro giảm thiệt hại / lợi nhuận kẻ tấn công bao nhiêu, đổi lại mất bao nhiêu khối lượng và thanh khoản? `Q*` thực nghiệm nằm đâu so với lý thuyết?
- **RQ3 (GĐ3):** Khi LP tự chọn độ rộng, phân bổ phí theo độ rộng có giảm phơi nhiễm nạn nhân không, `φ` cần điều kiện gì, LP lành mạnh mất bao nhiêu hiệu quả vốn?

**Định vị đóng góp — bắt buộc giữ:** KHÔNG nhận cơ chế thưởng theo khoảng giá là phát minh (Merkl đã chạy thực tế, izumi 2021 có tiền lệ học thuật, Capponi–Jia–Zhu có phí hai tầng). Cái mới là: simulator có đủ ba bên, đánh giá định lượng các biện pháp bài gốc chỉ đề xuất, và **điều kiện `φ` siêu tuyến tính** với độ rộng nội sinh. Lý lẽ và bằng chứng: `03_Ghi_chu_nghien_cuu/02_Khoang_trong_va_dinh_huong.md`.

## Quyết định kỹ thuật đã chốt (không đi ngược nếu chưa bàn lại với Đức)

1. **Engine phải cross-tick ngay từ GĐ1** — cú xả đi xuyên nhiều tick. "Một tick" ở GĐ1 là hình học vị thế, không phải phạm vi giá.
2. **Độ rộng `w` là tham số của tác nhân**, chỉ đặt bằng 1 ở GĐ1. Không hardcode một tick vào cấu trúc dữ liệu của engine.
3. **LP nạn nhân phải tối ưu hóa** theo Lemma 4, không phản ứng cứng theo ngưỡng APY. Làm hai loại: *toàn tri* (biết `Q`, kiểm định engine) và *thích nghi* (chỉ thấy lợi suất quá khứ).
4. **`MC(v)` của farmer tính từ trạng thái bể thật**, không đặt cứng — nếu không tường `L_A` mất tác dụng.
5. **`c_V` tính theo vốn, không theo `L`** khi sang GĐ3 (ở một tick hai cách trùng nhau).
6. **Range-aware = chia lại phí có trọng số** `L_i·φ(w_i) / Σ L_j·φ(w_j)`, tổng phí giữ nguyên. Không dùng bản "đốt phần bị phạt" — nó tương đương hạ `f`, tức biện pháp hạ phí đã có.
7. **Range-aware vô hiệu ở một tick** (`φ(1)` triệt tiêu trong tỷ lệ) → chỉ đánh giá được ở GĐ3.
8. Trợ cấp: thử **cả** `σ·min{v,Q}` (bài gốc) **và** dạng log (luật Binance Alpha theo nguồn thứ cấp) để kết quả không phụ thuộc giả định.

Thiết kế chi tiết, công thức, tiêu chuẩn kiểm định: `03_Ghi_chu_nghien_cuu/03_Ke_hoach_simulator.md`.

## Trạng thái (cập nhật 10/10/2026, sau đợt đọc tài liệu)

**Đã xong:** đọc hiểu bài gốc; báo cáo lần 2 của Đức; kịch bản trình bày nhóm 8 slide; tra cứu và tải 58 bài liên quan (bao phủ 57/57 tài liệu tham khảo của bài gốc); quét giới hạn và hướng tiếp theo của các bài để tìm khoảng trống; chốt định hướng.

Ngày 08/10 đã lập file phân công 7 tuần ([artifact](https://claude.ai/code/artifact/095d682e-2d52-430b-a7bc-0ca34ecdd67a)); bản chép + cập nhật ở `05_Phan_cong.md`.

**Phiếu đọc (10/10/2026):** `03_Ghi_chu_nghien_cuu/06_Phieu_doc/` — **đọc `00_MUC_LUC.md` trước**. 8 bài đọc toàn văn có phiếu riêng (`N1_*`: izumi, Capponi–Jia–Zhu, Xiong, Trotti, Tang, Tarantelli, StableSims, Fan), 11 bài đọc chọn lọc (`N2_…`), 39 bài chỉ tóm tắt + hướng mở (`N3_…`). Mỗi phiếu có số liệu đã kiểm với PDF, liên hệ khoảng trống A–E và câu trích gợi ý. Khi viết Related Work, dùng các phiếu này thay vì mở lại PDF.

**Bản nháp bài báo (14/10/2026):** khung bài + mục 3 Công trình liên quan viết đầy đủ, ở Claude Docs: https://claude.ai/code/artifact/e448d20d-e034-4eef-86f0-f2711eca0a2e (đọc bằng công cụ docs, không web-fetch). Nguồn web đã lấy 14/10: blog Paradigm (Robinson 2021), docs Merkl (CL campaigns), Binance Alpha Points chỉ có nguồn thứ cấp (DA Labs 2025) — FAQ chính thức không truy cập được.

**Việc tiếp theo của Đức (phần B):**
1. Related Work 2–3 trang dựa trên `02_Khoang_trong_va_dinh_huong.md` + `06_Phieu_doc/` (dàn ý 7 mục ở cuối `00_MUC_LUC.md`) — hạn 25/10. Còn phải đối chiếu luật Binance Alpha (FAQ chính thức) và lấy tài liệu Merkl, blog Paradigm 2021.
2. `04_Simulator/metrics/`: chuỗi thời gian, mốc `t_m → t_b`, ba pha, 4 chỉ số + 2 chỉ số dẫn xuất; chạy trên log giả trước (theo định dạng log trong interface), log thật trước 01/11.
3. Bộ kiểm định RQ1 tự động (mục 6 kế hoạch simulator) — hạn 08/11.
4. Biểu đồ timeline, hộp theo pha, bản đồ nhiệt `(σ, Q)`; báo cáo kết quả tái lập — hạn 22/11.

**Từ 14/10/2026 Đức tự chạy cả 3 vai A, B, C** bằng 3 phiên Claude Code trong `04_Simulator/` (git repo riêng; luật ở `04_Simulator/CLAUDE.md`, hợp đồng `INTERFACE.md`, tiến độ `SYNC.md`; lệnh `/vai A|B|C` khi bắt đầu, `/chot` trước khi dừng). Phiên mở ở thư mục gốc đồ án (không phải `04_Simulator/`) thì không sửa code simulator, trừ khi Đức yêu cầu.

## Bản đồ thư mục

```
00_Bai_goc/                      bài gốc USENIX Security 2026
01_Tai_lieu_tham_khao/           00_DANH_MUC_TAI_LIEU.docx + 9 nhóm, 58 PDF
02_Bao_cao_va_trinh_bay/         báo cáo của Đức, kịch bản nhóm, báo cáo các thành viên
03_Ghi_chu_nghien_cuu/           ghi chú markdown (01–05, 05 = phân công), 06_Phieu_doc/ (phiếu đọc tài liệu), du_lieu_tho/
04_Simulator/                    git repo simulator; 3 vai A/B/C, xem 04_Simulator/CLAUDE.md
99_Cong_cu/                      script tạo danh mục, tải tài liệu, dựng docx
```

## Lưu ý môi trường

- Windows, đường dẫn có dấu tiếng Việt. `curl` trong Git Bash **không ghi được** vào đường dẫn này → dùng Python (`urllib`, `shutil`). Với Node, ghi ra thư mục tạm rồi chép bằng Python.
- Tạo `.docx` bằng thư viện npm `docx` (cài trong `99_Cong_cu/docx` bằng `npm install`). Máy **không có** LibreOffice/pandoc nên không render được để xem; chỉ kiểm cấu trúc và nhờ Đức mở bằng Word.
- arXiv giới hạn tần suất: cách nhau ≥ 3 giây; API `export.arxiv.org` từng trả 429.
- Chỉ tải bản mở (arXiv, IACR ePrint, Zenodo, whitepaper chính thức). Nhà xuất bản chặn tải tự động thì để link, không vượt rào.

## Dữ kiện cần đối chiếu trước khi trích

- Số liệu JIT (Xiong et al.): 36.671 vụ, 7.498 ETH, pha loãng 85% — **đã xác minh với PDF ngày 10/10** (85% = phần thanh khoản / phí mà kẻ JIT chiếm trong mỗi vụ). Xem `06_Phieu_doc/N1_03_…`.
- Fan et al. 2021 (Strategic LP in Uniswap v3) **không** có trong danh mục tham khảo của bài gốc.
- Luật Binance Alpha Points (log₂ khối lượng mua, cửa sổ 15 ngày) lấy từ nguồn thứ cấp — đối chiếu FAQ chính thức.
- Bài gốc **không** trích dẫn nhóm JIT, Merkl, izumi, Paradigm. Ruizhe Jia (đồng tác giả bài gốc) cũng đồng tác giả bài *Paradox of JIT Liquidity*. Tính đến 04/10/2026 chưa thấy công trình nào trích dẫn bài gốc.

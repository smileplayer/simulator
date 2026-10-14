# Phân công 7 tuần (12/10 – 29/11/2026)

Bản gốc có lịch vẽ: [Phân công đồ án Blockchain — 7 tuần](https://claude.ai/code/artifact/095d682e-2d52-430b-a7bc-0ca34ecdd67a) (tạo 08/10/2026). File này là bản chép cho context, **đã cập nhật ngày 10/10/2026: Đức nhận phần B** (bản gốc ghi B = Hưng, C = Đức). **Từ 14/10/2026 Đức chạy cả 3 vai bằng 3 phiên Claude Code** trong `04_Simulator/` (xem `04_Simulator/CLAUDE.md`).

**Mức tối thiểu:** GĐ1 (RQ1) + GĐ2 (RQ2). GĐ3 (RQ3) chỉ làm nếu còn thời gian. Hạn nộp chính xác chưa biết; lịch giả định nộp trong tuần 23–29/11.

**Nguyên tắc:** mỗi người một lớp simulator, tự viết phần báo cáo của lớp mình. Các lớp nói chuyện qua interface (chữ ký hàm `Pool` + định dạng log sự kiện) chốt trước 18/10.

## Bảng phân công

| Phần | Người | Lớp | Thư mục code | Phần báo cáo | Slide |
|---|---|---|---|---|---|
| A | (chưa xác nhận) | Engine CLMM | `engine/`, `tests/` | Nền tảng CLMM; thiết kế engine | 2, 3 |
| **B** | **Đức** | Đo lường, kiểm định, Related Work | `metrics/`, `plots/` | Related Work; kết quả tái lập (RQ1) | 4, 5 |
| C | (chưa chốt — có thể Hưng) | Tác nhân, thí nghiệm, biện pháp | `agents/`, `scenarios/`, `defenses/` | Mô hình; phương pháp; đánh giá biện pháp (RQ2, RQ3) | 1, 6, 7, 8 |

Người trình bày: bản gốc đề xuất là người làm C; cần chốt lại vì Đức đã chuyển sang B.

## B — Đo lường, kiểm định và Related Work (Đức)

Biến log sự kiện của simulator thành 4 chỉ số và biểu đồ, kiểm tra simulator có tái lập đúng dấu hiệu thực nghiệm của bài gốc không. Đọc log nên không phải chờ engine: tuần 1–2 làm trên log giả theo định dạng đã chốt.

**Việc cần làm**
1. **Related Work** (tuần 1–2) dựa trên `02_Khoang_trong_va_dinh_huong.md`: 5 khoảng trống A–E và bảng định vị so với Merkl / izumi / Paradigm / Capponi–Jia–Zhu.
2. Đọc log, dựng chuỗi thời gian: `L_active`, giá, khối lượng, biến động theo bước thời gian.
3. Xác định các mốc `t_m`, `t_50`, `t_peak`, `t_0`, `t_oot`, `t_b` và ba pha Prep / Attack / Post như bài gốc.
4. Tính 4 chỉ số: thiệt hại nạn nhân, lợi nhuận kẻ tấn công (đo độc lập), chi phí trợ cấp, thanh khoản bể. Thêm hiệu quả chi tiêu (thanh khoản còn lại / tổng trợ cấp) và tỷ lệ rò rỉ (lợi nhuận kẻ tấn công / tổng trợ cấp).
5. Bộ kiểm định tự động theo mục 6 của `03_Ke_hoach_simulator.md`, xuất bảng Đạt / Không đạt.
6. Biểu đồ: timeline một vụ (như Hình 1 bài gốc), hộp theo pha (như Hình 2), bản đồ nhiệt `(σ, Q)` cho GĐ2.

**Yêu cầu cần đạt**
- [ ] Related Work 2–3 trang, trích đúng nguồn; nói rõ cơ chế thưởng theo khoảng giá **không** phải phát minh của nhóm
- [ ] Đối chiếu số liệu chưa chắc (pha loãng LP 85% của Xiong et al.; luật Binance Alpha) với PDF / nguồn chính thức trước khi trích
- [ ] Thiệt hại nạn nhân tính được cả bản đầy đủ và bản chỉ đếm non-alpha như bài gốc
- [ ] Lợi nhuận kẻ tấn công tính từ dòng tiền, không suy ra từ thiệt hại nạn nhân
- [ ] Metrics chạy trên log giả cuối tuần 2, trên log thật cuối tuần 3
- [ ] Bảng kiểm định RQ1 đủ dòng: thời gian (chuẩn bị theo ngày, thu hoạch theo giờ), khối lượng Prep ~1–1,5× nền, Attack có kịch bản > 5×, **Post dưới nền**, biến động tăng dần qua ba pha
- [ ] Mọi biểu đồ sinh lại được bằng một lệnh từ kết quả chạy, có nhãn trục và đơn vị
- [ ] Phần báo cáo kết quả tái lập 2–3 trang

**Hạn:** Related Work 25/10; metrics trên log thật 01/11; bảng kiểm định RQ1 08/11; biểu đồ GĐ2 + báo cáo RQ1 22/11.

## A — Engine (tóm tắt)

Pool, `Position(tick_lower, tick_upper, L, owner)` tổng quát, mint/burn, swap cross-tick hai chiều (theo lượng vào và tới giá giới hạn), feeGrowth + checkpoint, `position_amounts`, `fees_owed`, `quote_swap` (cho `MC(v)` của farmer), ghi log; GĐ3: móc chia phí `L_i·φ(w_i)/Σ`.
Yêu cầu chính: swap một tick khớp công thức tay (< 1e-9); xuyên ≥ 1.000 tick đúng; bảo toàn token; `(x, y)` đúng ba trạng thái (1.000 USDT một tick dưới `P₀=1` → `L = 20.000.000`); hai LP cùng tick chia phí theo `L`; không hardcode một tick; `pytest`.
Hạn: test cơ bản 25/10; đủ test 01/11; báo cáo 15/11; móc φ 22/11 (tùy chọn).

## C — Tác nhân, thí nghiệm, biện pháp (tóm tắt)

Chốt interface + bể giả + bộ sinh log giả (18/10); Farmer tối ưu `U_T` với `MC` từ `quote_swap`, hai dạng trợ cấp; Victim toàn tri (Lemma 4) và thích nghi; Attacker rút tường rồi xả tới `z₂`; bộ chạy phản thực nhiều seed; GĐ2 quét `(σ, Q)` + 4 biện pháp + `Q*` thực nghiệm; GĐ3 quét `φ(w)=min(1,(w/w₀)^α)`.
Yêu cầu chính: farmer không vượt `Q`; victim khớp Lemma 4 (< 1%), `L_V*/L_A ≈ 1` tại `L_A = fQ/(4c_V)`; kịch bản cơ sở chạy trên engine thật trước 01/11; mỗi biện pháp có bảng đánh đổi, ≥ 10 seed; kết luận giữ với cả trợ cấp tuyến tính và log.
Hạn: tác nhân 01/11; GĐ2 15/11; GĐ3 22/11 (tùy chọn).

## Lịch

| Tuần | A | B (Đức) | C | Mốc |
|---|---|---|---|---|
| T1 12–18/10 | Engine lõi | Related Work | Interface + bể giả | 18/10 chốt interface |
| T2 19–25/10 | Engine lõi, test cơ bản | Related Work; metrics trên log giả | Ba tác nhân | 25/10 Related Work |
| T3 26/10–1/11 | Đủ test, hỗ trợ ghép | Metrics trên log thật | Ba tác nhân | **01/11 GĐ1 chạy trọn vẹn** |
| T4 2–8/11 | Báo cáo nền + engine | Kiểm định RQ1 | GĐ2 | 08/11 bảng kiểm định RQ1 |
| T5 9–15/11 | Báo cáo | Biểu đồ GĐ2, báo cáo RQ1 | GĐ2 | 15/11 xong GĐ2 |
| T6 16–22/11 | Móc φ (tùy chọn) | Biểu đồ GĐ2, báo cáo RQ1 | GĐ3 (tùy chọn) | Cả nhóm ghép, đọc chéo báo cáo |
| T7 23–29/11 | — | — | — | Slide, tập trình bày, nộp |

## Quy ước chung

- Python 3.11+, `numpy`, `pandas`, `matplotlib`, `pytest`; repo GitHub chung, nhánh riêng, PR có ít nhất một người xem.
- Sau 18/10 đổi interface phải báo cả nhóm trước.
- Họp 30 phút/tuần (xong gì, làm gì, vướng gì); kẹt quá 2 ngày thì nhắn ngay.
- Xong = code vào `main`, test qua, có docstring, có bản nháp báo cáo tương ứng.
- Rủi ro: engine trễ (đường găng) → người làm C ngồi cùng A, dùng bể giả; không tái lập được "Post dưới nền" → kiểm lại dòng lệnh nền và farmer sau khi rút tường, ghi trung thực; thiếu thời gian → bỏ GĐ3 trước.

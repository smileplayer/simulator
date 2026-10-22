# Dàn ý slide — trình bày 5–7 phút (một người nói)

> **Đã thay (17/10/2026)** bằng kịch bản 10 phút ở `../../../02_Bao_cao_va_trinh_bay/Kich_ban_slide_10_phut.md`. Giữ file này làm lịch sử.

> Chỉ huy soạn 15/10/2026. Mỗi slide ~45–60 giây. Số liệu lấy từ `TONG_KET_DU_AN.md` và `ket_qua/*/bang/` — soát lại khi chốt bản thảo.
> Tên đề tài: *Đánh giá phản thực các biện pháp phòng thủ trước tấn công thanh khoản do khuyến khích trong CLMM bằng mô phỏng đa tác nhân, và điều kiện để phân bổ phí theo độ rộng khoảng giá có hiệu lực.*

---

## Slide 1 — Vấn đề (45 s)
- Trợ cấp theo khối lượng (Binance Alpha, Blast…) + thanh khoản tập trung → **tường một tick**: kẻ tấn công dựng tường, farmer kéo khối lượng, LP nạn nhân vào ăn phí, kẻ tấn công rút tường rồi xả → giá sập, nạn nhân lỗ.
- Lu et al. (USENIX Security 2026) đo 29 vụ thật, **đề xuất 4 biện pháp (§7) nhưng chưa đánh giá**.
- Hình: sơ đồ 4 pha (dựng → tạo khối lượng → nạn nhân vào → rút + xả).

## Slide 2 — Đóng góp & cách làm (45 s)
- Simulator đa tác nhân đủ ba bên (farmer tối ưu Theorem 1, victim tối ưu Lemma 4 — toàn tri/thích nghi, attacker Lemma 5) trên engine CLMM xuyên tick.
- Ba câu hỏi: **RQ1** tái lập được dấu hiệu thực nghiệm? **RQ2** biện pháp §7 hiệu quả, đánh đổi gì? **RQ3** phân bổ phí theo độ rộng cần điều kiện gì?
- Phương pháp: 30 vụ (mảng trực giao L27) × 10 seed; **cặp phản thực** cùng chuỗi ngẫu nhiên; lợi nhuận tăng thêm đo bằng **phản thực phát lại log**; CI bootstrap.

## Slide 3 — RQ1: tái lập (60 s)
- **13/13 tiêu chí đạt** trên 300 log: sập ≥ 10% 98%; Post < 1× 80% (bài gốc 79%); RV Post cao nhất 96%; tường cạn ≥ 80% 100%.
- Hình: timeline co_so (`ket_qua/rq1/hinh/timeline_co_so.png`).
- Trung thực: giá sập theo VWAP chỉ 52% (CI 38–67, bài gốc 69%); Prep không vụ nào < 1×.
- Phát hiện phụ: **lợi nhuận "thật" của tấn công chỉ ~2%** con số thô — phần lớn là bán kho vào thanh khoản nền.

## Slide 4 — RQ2: hạ trần và Q* (60 s)
- **Q\*/Q = k** khớp Lemma 4/Theorem 6 (28/30 vụ) khi victim định giá theo trần → hạ dưới ngưỡng xóa hết lợi tấn công, mất 20–26% khối lượng.
- Bản đồ ba vùng (σ, Q) khớp lý thuyết 25/25 ô — hình `ket_qua/gd2/hinh/ba_vung.png`.
- Nhưng victim **thích nghi** (nhìn phí lịch sử): hạ trần chỉ cắt 31–65%, mất tới nửa khối lượng.

## Slide 5 — RQ2: so sánh biện pháp (60 s)
- Hình Pareto (`ket_qua/gd2/hinh/pareto.png`): x = % mất khối lượng, y = % giảm lợi kẻ tấn công.
- **Cảnh báo rủi ro (tăng c_V) tốt nhất**: cắt 94–100% lợi, mất < 2,3% khối lượng.
- Trả trễ: ≈ 0; thu hồi thưởng: chỉ cắt phần farm của kẻ tấn công; trần động ≈ hạ trần.
- **Không biện pháp nào chặn được cú sập giá.**

## Slide 6 — RQ3: phân bổ phí theo độ rộng (60 s)
- Điều kiện: φ phải tăng **nhanh hơn tuyến tính** (α > 1) thì victim mới trải rộng — xác nhận giả thuyết.
- Nhưng: (1) cú sập sâu 600–5.000 tick ≫ dải → vẫn mất ~50% vốn; (2) **kẻ tấn công nới tường** né phạt → vùng victim lớn: vốn victim quay về 0,7–1,0×; vùng RQ1: victim bị hút vào **1,5–10×** (khớp giải tích 46/54 ô); (3) LP dải hẹp mất 50–100% phí.
- Hình: `ket_qua/gd3/hinh/so_sanh_wA.png`.
- → φ dạng lũy thừa **không phải** biện pháp phòng thủ đáng tin cậy.

## Slide 7 — Kết luận & khuyến nghị (45 s)
1. Hạ trần hiệu quả **chỉ khi** LP định giá theo trần; chọn Q < k·Q.
2. **Ưu tiên cảnh báo rủi ro** cho LP dải hẹp — giữ khối lượng tốt nhất; hạ trần tiết kiệm trợ cấp (sửa 20/10).
3. Range-aware cần xét kẻ tấn công thích nghi; dạng lũy thừa có thể phản tác dụng.
4. Giới hạn: một bể, giá ngoài giả lập, luật chọn độ rộng bỏ qua biến động. Hướng mở: dữ liệu bể thật, φ phạt theo hành vi (thời gian giữ) thay vì độ rộng.

## Slide dự phòng (hỏi đáp)
- Bảng 13 tiêu chí RQ1 + CI; công thức Lemma 4, Theorem 6, tỷ lệ vốn RQ3; bảng 19 lỗi đã sửa và cách kiểm (test, phát lại log, bảo toàn token).

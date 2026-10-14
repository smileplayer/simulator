# Phiếu đọc tài liệu cho Related Work — mục lục

Lập ngày 10/10/2026 (phần B — Đức). Mục đích: để viết Related Work (hạn 25/10) và để các phiên làm việc sau hiểu nhanh từng bài mà không phải đọc lại PDF.

## Cách phân nhóm
- **Nhóm 1 — đọc toàn văn, mỗi bài một phiếu** (8 bài, xương sống của Related Work).
- **Nhóm 2 — đọc chọn lọc** (11 bài, một file tổng hợp): tóm tắt, định nghĩa / kết quả chính, kết luận.
- **Nhóm 3 — chỉ tóm tắt + hướng tiếp theo** (39 bài, một file tổng hợp): một dòng mỗi bài, kèm đoạn trích gộp gợi ý.

Mỗi phiếu nhóm 1 có cùng khung: nguồn & độ tin cậy → câu hỏi → mô hình → kết quả (số đã kiểm với PDF) → giới hạn & hướng tiếp theo → liên hệ đồ án (khoảng trống A–E, RQ, phần B) → câu trích gợi ý (đã diễn đạt lại) → câu hỏi người chấm có thể hỏi.

## Nhóm 1
| File | Bài | Ý chính cho đồ án |
|---|---|---|
| `N1_01_Yin_2021_izumi.md` | Yin & Ren 2021 (izumi) — liquidity mining theo bin cho v3 | Tiền lệ thưởng theo khoảng giá; chính tác giả nói thưởng một bin → LP dồn hết vào bin đó; điều khiển **vị trí**, không phải **độ rộng** |
| `N1_02_Capponi_Jia_Zhu_2023_Paradox_JIT.md` | Capponi, Jia, Zhu 2023 — nghịch lý JIT, phí hai tầng | Tiền lệ "chia lại phí giữa các loại LP, tổng phí không đổi"; phân loại theo **thời gian** nên không bắt được tường nhiều ngày → lý do chọn trục **độ rộng**; λ* = mức chuyển lớn nhất còn giữ LP |
| `N1_03_Xiong_2023_JIT_attacks.md` | Xiong et al. 2023 — đo 36.671 vụ JIT | > 99,99% JIT dùng đúng một tickSpacing; pha loãng 85% (đã kiểm); **kêu gọi thước đo phúc lợi** → biện hộ bộ 4 chỉ số |
| `N1_04_Trotti_2025_Strategic_JIT.md` | Trotti et al. 2025 — tối ưu JIT ở mức giao dịch | Định nghĩa price impact `C = V_mint − V_withdraw`; JIT tối ưu cắt phí LP thụ động tới 44%; hướng mở: giao thức công bằng cho LP thụ động |
| `N1_05_Tang_2025_Game_Theoretic_CLMM.md` | Tang et al. 2025 (POMACS, Ref 45) — trò chơi LP có ngân sách | "Twin games": với chia phí pro-rata, **độ rộng tự nó không quan trọng** → muốn phân biệt tường một tick phải dùng `φ(w)` theo vị thế; tham số α là tiền lệ tổng quát hóa quy tắc chia phí |
| `N1_06_Tarantelli_2026_ABM_Uniswap_v3.md` | Tarantelli 2026 (Zenodo, tự đăng) — simulator v3 | Simulator gần nhất, tự nhận thiếu rút thanh khoản chiến lược (khoảng trống A); **khung kiểm định hai lớp** cho bảng RQ1 |
| `N1_07_Kirillov_2022_StableSims.md` | Kirillov & Chung 2022 — ABM chỉnh tham số khuyến khích MakerDAO | Tiền lệ "đánh giá khuyến khích bằng mô phỏng"; chỉ số "% cải thiện / đô-la khuyến khích" ≈ hiệu quả chi tiêu; tự cảnh báo "incentive farming" |
| `N1_08_Fan_2021_Strategic_LP_Uniswap_v3.md` | Fan et al. 2021 — chiến lược LP động | Giả định **LP nhỏ** (phí độc lập với người khác) mà tường phá vỡ; ngại rủi ro → rộng; hướng mở: trò chơi cho LP lớn. **Bài gốc không trích bài này.** |

## Nhóm 2 và 3
- `N2_Tong_hop_doc_chon_loc.md`: Milionis (LVR), Heimbach (IL v3), Fritsch & Canidio (LVR > phí), Zhou SoK DeFi Attacks, Ma & Crapis (pro-rata gây thừa thanh khoản, PoA = O(N)), Messias (airdrop farmer), TierDrop, Gogol (TVL không kéo khối lượng), Urusov 2024 (backtester), Chaudhary & Pinna (ABM cho vay), SILS (cá voi phản thực). Cuối file có bảng "đoạn Related Work ↔ bài".
- `N3_Tong_hop_abstract_future_work.md`: 39 bài còn lại theo 8 cụm + danh sách tài liệu web chưa có PDF (Paradigm, Merkl, Gauntlet, Binance FAQ…) + hai đoạn trích gộp gợi ý.

## Những điều đã kiểm / sửa trong đợt đọc này
- **Pha loãng 85% (Xiong et al.)**: đúng; nghĩa chính xác là kẻ JIT chiếm trung bình 85% thanh khoản trong khoảng (và ~85% phí của swap). Bài có lỗi cộng chi phí (2.027 vs 2.627 ETH).
- **Fan et al. 2021 không được bài gốc trích** (trước đó ghi nhầm là có).
- **Tang et al.**: trích là 2025 (POMACS), không phải 2024.
- **Trotti et al.**: abstract và mục 1 lệch số (69% vs 41%; 44% vs 40%; 93,7% vs Hình 4 trung bình 75%) → trích theo abstract / hình.
- **Tarantelli 2026**: bản tự đăng, một tác giả → không dùng làm chỗ dựa duy nhất; trích kèm Urusov 2024.
- **Milionis**: PDF là bản v6 (2026) đã viết lại khung beta/alpha → ghi rõ phiên bản khi trích.
- **Ký hiệu trùng**: `φ` của Capponi (cờ cam kết thời gian) ≠ `φ(w)` của nhóm.
- **Còn phải làm**: luật Binance Alpha Points (FAQ chính thức), tài liệu Merkl, blog Paradigm 2021 — chưa có bản gốc trong thư mục.

## Gợi ý cấu trúc Related Work (2–3 trang)
1. **CLMM và rủi ro của LP thụ động** — Adams 2021; Loesch; Heimbach; Milionis; Fritsch & Canidio.
2. **Vị thế siêu hẹp và chia phí giữa các loại LP** — Xiong; Capponi–Jia–Zhu; Trotti; Ma & Crapis.
3. **Chiến lược LP và lý thuyết trò chơi** — Fan; Tang; Cartea; nhóm RL (gộp).
4. **Liquidity mining và thiết kế khuyến khích** — izumi; Paradigm; Merkl; Messias; TierDrop; Gogol. → **Định vị**: thưởng theo khoảng giá không phải phát minh của nhóm.
5. **Mô phỏng tác nhân cho DeFi** — Tarantelli; Urusov 2024; StableSims; Chaudhary; Chitra.
6. **Tấn công và thao túng, phát hiện** — Zhou SoK; MEV (gộp); P&D, wash trading, rug pull (gộp); SILS.
7. **Khoảng trống và đóng góp** — bảng 5 khoảng trống A–E (`../02_Khoang_trong_va_dinh_huong.md`).

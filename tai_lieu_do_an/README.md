# Đồ án Blockchain — Tấn công thanh khoản do khuyến khích trong CLMM

Thư mục làm việc của Đức (phụ trách phần B: đo lường, kiểm định, Related Work). Dựa trên bài **Lu et al., USENIX Security 2026**.

## Bắt đầu từ đâu

| Muốn | Mở |
|---|---|
| Nắm lại bài gốc | `03_Ghi_chu_nghien_cuu/01_Tom_tat_bai_goc.md` |
| Biết đề tài đi hướng nào, vì sao | `03_Ghi_chu_nghien_cuu/02_Khoang_trong_va_dinh_huong.md` |
| Bắt tay code simulator | `03_Ghi_chu_nghien_cuu/03_Ke_hoach_simulator.md` |
| Ôn trình bày, hỏi đáp | `03_Ghi_chu_nghien_cuu/04_Trinh_bay_va_hoi_dap.md` |
| Xem ai làm gì, hạn khi nào | `03_Ghi_chu_nghien_cuu/05_Phan_cong.md` |
| Tìm tài liệu tham khảo | `01_Tai_lieu_tham_khao/00_DANH_MUC_TAI_LIEU.docx` |

`CLAUDE.md` là bối cảnh cho Claude Code — tự nạp khi mở phiên mới ở thư mục này.

## Cấu trúc

```
CLAUDE.md                          bối cảnh cho phiên Claude Code sau
README.md                          file này
00_Bai_goc/                        usenixsecurity26-lu-sinong.pdf
01_Tai_lieu_tham_khao/
  00_DANH_MUC_TAI_LIEU.docx        100 mục, 58 PDF, lộ trình đọc, bản đồ khoảng trống
  01_Nen_tang_AMM_CLMM/
  02_Chien_luoc_LP_va_ly_thuyet_tro_choi/
  03_Liquidity_mining_va_incentive/
  04_JIT_va_vi_the_sieu_hep/
  05_Tan_cong_DeFi_va_MEV/
  06_Thao_tung_thi_truong/
  07_Simulator_va_phuong_phap_danh_gia/
  08_Phat_hien_bat_thuong/
  09_Tham_khao_nen_khac/
02_Bao_cao_va_trinh_bay/
  Bao_cao_lan_2_Duc.docx           báo cáo tiến độ của C
  Kich_ban_trinh_bay_nhom.docx     kịch bản 8 slide, một người nói
  Bao_cao_nhom/                    báo cáo của các thành viên
    trich_xuat_van_ban/            bản trích văn bản khi chưa có file gốc
  ban_cu/                          kịch bản 5 phút cá nhân (đã thay bằng bản nhóm)
03_Ghi_chu_nghien_cuu/
  01_Tom_tat_bai_goc.md
  02_Khoang_trong_va_dinh_huong.md
  03_Ke_hoach_simulator.md
  04_Trinh_bay_va_hoi_dap.md
  05_Phan_cong.md                  phân công 7 tuần; Đức = phần B
  du_lieu_tho/                     kết quả quét giới hạn/hướng tiếp + 57 tài liệu tham khảo bài gốc
04_Simulator/                      mã nguồn (chưa bắt đầu)
99_Cong_cu/                        script dựng danh mục, tải tài liệu, tạo docx
```

## Trạng thái

- [x] Đọc hiểu bài gốc
- [x] Báo cáo lần 2, kịch bản trình bày nhóm
- [x] Tra cứu, tải và phân loại tài liệu
- [x] Tìm khoảng trống, chốt định hướng (RQ1–RQ3)
- [ ] GĐ1 — engine + 3 tác nhân + 4 chỉ số
- [ ] GĐ2 — đánh giá các biện pháp của bài gốc
- [ ] GĐ3 — phân bổ phí theo độ rộng
- [ ] Thêm mục Related Work vào báo cáo; cập nhật slide 7

## Việc cần Đức tự làm

- Đóng file `00_DANH_MUC_TAI_LIEU.docx` cũ đang mở trong Word, rồi xóa bản cũ ở thư mục gốc. Bản mới nằm trong `01_Tai_lieu_tham_khao/`; link của bản cũ đã hỏng vì thư mục đã chuyển.
- Chép bản gốc của `Bao_cao_lan_1.2.docx`, `Phan_tich_diem_chung_diem_rieng_3_bao_cao_CLMM.docx`, `Plan_Notion.pdf` và báo cáo của Hưng vào `02_Bao_cao_va_trinh_bay/Bao_cao_nhom/`. Lúc sắp xếp không tìm thấy các file này trên máy.

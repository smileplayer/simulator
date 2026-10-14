# Công cụ

## `tai_lieu/` — danh mục và tài liệu tham khảo (Python)

| File | Việc |
|---|---|
| `catalog.py` | Nguồn của danh mục: 9 nhóm, 100 mục, mức ưu tiên, lý do liên quan. Sửa ở đây rồi chạy `python catalog.py` để sinh `catalog.json` |
| `verify.py` | Kiểm mã arXiv: `python verify.py "2110.01368,2411.10399" out.json` (cách nhau 3 giây) |
| `download.py` | Tải PDF mở: `python download.py "D:/Đức/Đồ án Blockchain/01_Tai_lieu_tham_khao"` → ghi `download_log.json` |
| `scan.py` | Trích abstract + giới hạn + hướng tiếp: `python scan.py "04_JIT_va_vi_the_sieu_hep"` (văn bản tạm vào `txt/`) |

Chạy các script từ trong thư mục `tai_lieu/`. Trên Windows nên đặt `PYTHONIOENCODING=utf-8`. Cần `pdftotext` cho `scan.py`.

## `docx/` — tạo file Word (Node)

Cài một lần: `npm install` (đọc `package.json`, cài thư viện `docx`).

| File | Sinh ra |
|---|---|
| `build_index.js` | Danh mục: `node build_index.js <thư mục chứa catalog.json + download_log.json> <file .docx ra>` |
| `build_report.js` | Báo cáo lần 2 |
| `build_group_script.js` | Kịch bản trình bày nhóm |
| `build_script.js` | Kịch bản 5 phút cá nhân (bản cũ) |
| `dump.py` | Trích văn bản (cả bảng) từ một file .docx |

Lưu ý: Node trong Git Bash có thể truyền sai đường dẫn có dấu. Cách chắc ăn là ghi ra thư mục không dấu rồi chép bằng Python. Danh mục phải đặt cùng cấp với 9 thư mục nhóm thì link "PDF" mới mở được.

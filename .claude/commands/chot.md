---
description: Chốt phiên — chạy test, commit phần của vai mình, cập nhật SYNC.md
---
Chốt lại công việc của vai đang đóng trong phiên này (nếu chưa rõ vai thì hỏi Đức):
1. Chạy test của vai mình (`python -m pytest tests/<engine|metrics|agents> -q`), rồi `python -m pytest -q` cho cả repo. Ghi lại số test qua/hỏng.
2. Đọc lại `SYNC.md`, rồi **chỉ sửa mục của vai mình**: Trạng thái, Đang làm (việc dở, dở tới đâu, file nào), Cần từ vai khác; thêm một dòng nhật ký ở đầu bảng nhật ký: `ngày giờ | vai | việc đã làm | kết quả test`.
3. `git add` thư mục của vai mình + `SYNC.md` (+ `INTERFACE.md` nếu là C và có đổi), rồi `git commit -m "[<vai>] <tóm tắt>"`. Nếu test hỏng vẫn commit nhưng ghi "(test hỏng: …)" trong thông điệp và trong SYNC.md.
4. Báo Đức: đã commit gì, test ra sao, bước tiếp theo của vai này là gì.

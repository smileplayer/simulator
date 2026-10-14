---
description: Nhận vai A, B hoặc C và nạp đúng bối cảnh để làm tiếp
argument-hint: A | B | C
---
Phiên này đóng **vai $ARGUMENTS** (A = Engine, B = Đo lường/kiểm định, C = Tác nhân/thí nghiệm). Nếu `$ARGUMENTS` không phải A, B hoặc C thì hỏi lại Đức và dừng.

Làm theo thứ tự, đọc vừa đủ:
1. Đọc `CLAUDE.md` của thư mục này (luật quyền sửa, git) nếu chưa có trong ngữ cảnh.
2. Đọc `SYNC.md`: mục của vai mình, mục "Cần từ vai khác" của **hai vai còn lại** (xem có ai cần mình không), và 10 dòng nhật ký mới nhất.
3. Đọc `INTERFACE.md`.
4. Đọc mục của vai mình trong `tai_lieu_do_an/03_Ghi_chu_nghien_cuu/05_Phan_cong.md` (việc, yêu cầu cần đạt, hạn).
5. Chạy `git log --oneline -15` và `git status --short`.
6. Báo Đức ngắn gọn (≤ 8 dòng): vai, việc đã xong, việc dở, ai đang cần gì từ mình, và **việc nhỏ tiếp theo** định làm (một việc làm xong được trong một lượt). Hỏi Đức có làm việc đó không, trừ khi Đức đã dặn "cứ làm tiếp".

Chỉ sửa thư mục của vai mình (bảng trong `CLAUDE.md`).

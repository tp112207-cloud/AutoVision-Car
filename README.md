# 🏎️ AutoVision Ultimate: Hệ Thống Định Giá & Nhận Diện Lỗi Xe Cũ Bằng AI

## 📖 Giới thiệu (Introduction)
AutoVision là một ứng dụng Web App thông minh giúp minh bạch hóa thị trường mua bán xe ô tô cũ. Thay vì chỉ định giá dựa trên các thông số cơ bản (Năm SX, Odo...), hệ thống tích hợp Trí tuệ nhân tạo (Computer Vision) để tự động phát hiện các lỗi ngoại thất (Móp, Trầy, Nứt vỡ...) và trừ thẳng chi phí khấu hao vào giá bán cuối cùng.

## ✨ Tính năng nổi bật (Features)
- **🔐 Hệ thống Tài khoản:** Đăng ký / Đăng nhập phân quyền (Khách hàng & Admin).
- **💰 Định giá cốt lõi (Machine Learning):** Sử dụng thuật toán Random Forest Regressor dự đoán giá nền của xe dựa trên tập dữ liệu thực tế.
- **👁️ Nhận diện lỗi (Computer Vision):** Tích hợp YOLOv8 để soi các vết nứt, trầy xước, móp méo... trên ảnh chụp xe.
- **💎 Định giá biển số & Màu sắc:** Tự động nhận diện màu xe và cộng/trừ tiền theo độ "hot" của màu và độ đẹp của biển số.
- **🖨️ Xuất báo cáo PDF:** Tự động tạo và tải xuống báo cáo giám định xe chi tiết kèm hình ảnh minh họa.
- **📊 Admin Panel:** Quản lý lịch sử định giá của người dùng và xem biểu đồ thống kê.

## 🛠️ Công nghệ sử dụng (Tech Stack)
- **Ngôn ngữ:** Python
- **Giao diện (Frontend/Backend):** Streamlit
- **Machine Learning:** Scikit-Learn (Random Forest)
- **Computer Vision:** Ultralytics (YOLOv8), OpenCV
- **Database:** SQLite (Embedded)
- **Tiện ích:** FPDF (Xuất báo cáo PDF), Pandas, NumPy
  ### LINK model_columns.pkl: https://drive.google.com/drive/folders/1PWORDBUVwevrJs9JYlhpedKBEoupsIfrtHZtVJhagNv8t5fQ7sJQdD1f_kmpHeImSake1Kbq?usp=drive_link

import streamlit as st
import pandas as pd
import joblib
import numpy as np
from PIL import Image
from ultralytics import YOLO
import cv2
from sklearn.cluster import KMeans
from fpdf import FPDF
import base64
import unicodedata
import os
import time
import sqlite3
import hashlib
from datetime import datetime

import warnings
import logging
warnings.filterwarnings("ignore")
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)
warnings.simplefilter(action='ignore', category=DeprecationWarning)
os.environ["STREAMLIT_SILENCE_WATCHDOG_WARNING"] = "1"
logging.getLogger("ultralytics").setLevel(logging.ERROR)

# ==========================================
# 1. CẤU HÌNH & CSS (GIỮ NGUYÊN)
# ==========================================
st.set_page_config(page_title="AutoVision Ultimate", page_icon="🏎️", layout="wide")

st.markdown("""
    <style>
    .main {background-color: #0e1117;}
    .metric-card {background-color: #262730; border: 1px solid #41444e; border-radius: 10px; padding: 15px; margin-bottom: 10px;}
    .stButton>button {background: linear-gradient(90deg, #FF4B2B 0%, #FF416C 100%); color: white; border-radius: 8px; font-weight: bold; height: 50px; font-size: 18px;}
    .big-price {font-size: 50px; font-weight: bold; color: #4ade80;}
    .error-text {color: #ff4b4b; font-weight: bold;}
    .login-header {text-align: center; color: #FF4B2B; font-size: 30px; font-weight: bold; margin-bottom: 20px;}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. XỬ LÝ DATABASE & AUTH (ĐÃ SỬA EXCEPT CHUẨN LINTER)
# ==========================================
def init_db():
    conn = sqlite3.connect('autovision.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, car_name TEXT, final_price REAL, timestamp TEXT)')
    try:
        c.execute("INSERT INTO users VALUES (?, ?, ?)", ('admin', hashlib.sha256(str.encode('123')).hexdigest(), 'admin'))
        conn.commit()
    except Exception: 
        pass
    conn.close()

init_db()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text: return True
    return False

def add_user(username, password):
    conn = sqlite3.connect('autovision.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, make_hashes(password), 'user'))
        conn.commit(); conn.close()
        return True
    except Exception:
        conn.close(); return False

def login_user(username, password):
    conn = sqlite3.connect('autovision.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    data = c.fetchall()
    conn.close()
    if data and check_hashes(password, data[0][1]):
        return data[0][2]
    return False

def save_history_db(username, car_name, price):
    conn = sqlite3.connect('autovision.db')
    c = conn.cursor()
    time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO history (username, car_name, final_price, timestamp) VALUES (?, ?, ?, ?)", (username, car_name, price, time_now))
    conn.commit(); conn.close()

# ==========================================
# 3. QUẢN LÝ SESSION
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_role' not in st.session_state: st.session_state.user_role = ""
if 'username' not in st.session_state: st.session_state.username = ""

if 'damage_cost' not in st.session_state: st.session_state.damage_cost = 0
if 'damage_list' not in st.session_state: st.session_state.damage_list = []
if 'ai_color' not in st.session_state: st.session_state.ai_color = "Chưa quét"
if 'final_price' not in st.session_state: st.session_state.final_price = 0
if 'pdf_image_path' not in st.session_state: st.session_state.pdf_image_path = None
if 'box_status_val' not in st.session_state: st.session_state.box_status_val = "Không lỗi (Hoàn hảo)"
if 'box_color_val' not in st.session_state: st.session_state.box_color_val = "Trắng"
if 'file_uploader_key' not in st.session_state: st.session_state.file_uploader_key = 0

# ==========================================
# 4. ĐĂNG NHẬP (ĐÃ DỌN DẸP LINTER)
# ==========================================
if not st.session_state.logged_in:
    st.markdown('<p class="login-header">🔐 HỆ THỐNG AUTOVISION - ĐĂNG NHẬP</p>', unsafe_allow_html=True)
    # SỬA LỖI LINTER (Bỏ khai báo col1, col3 nếu không xài)
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        tab_log, tab_sign = st.tabs(["Đăng Nhập", "Đăng Ký"])
        with tab_log:
            username = st.text_input("Tên đăng nhập")
            password = st.text_input("Mật khẩu", type='password')
            if st.button("Đăng Nhập Ngay"):
                role = login_user(username, password)
                if role:
                    st.session_state.logged_in = True
                    st.session_state.user_role = role
                    st.session_state.username = username
                    st.success("Thành công! Đang vào hệ thống...")
                    st.rerun()
                else: st.error("Sai tên đăng nhập hoặc mật khẩu!")
        with tab_sign:
            new_u = st.text_input("Tạo tên User")
            new_p = st.text_input("Tạo Password", type='password')
            if st.button("Đăng Ký Tài Khoản"):
                if add_user(new_u, new_p): st.success("Tạo thành công! Vui lòng đăng nhập.")
                else: st.error("Tên đăng nhập đã tồn tại.")
    st.stop()

# ==========================================
# 5. ADMIN PANEL & SIDEBAR (ĐÃ THÊM CLEAR PDF_IMAGE)
# ==========================================
with st.sidebar:
    st.write(f"Xin chào, **{st.session_state.username}**!")
    
    if st.button("🔄 Làm mới dữ liệu"):
        st.session_state.damage_cost = 0
        st.session_state.damage_list = []
        st.session_state.ai_color = "Chưa quét"
        st.session_state.final_price = 0
        st.session_state.box_status_val = "Không lỗi (Hoàn hảo)"
        st.session_state.box_color_val = "Trắng"
        # ĐẶC BIỆT THÊM DÒNG NÀY ĐỂ RESET ẢNH TRONG PDF LUN
        st.session_state.pdf_image_path = None
        if 'ai_image' in st.session_state: del st.session_state['ai_image']
        st.session_state.file_uploader_key += 1
        st.rerun()

    if st.button("🚪 Đăng Xuất"):
        st.session_state.logged_in = False
        st.session_state.user_role = ""
        st.rerun()

if st.session_state.user_role == 'admin':
    st.title("🔑 TRANG QUẢN TRỊ ADMIN")
    st.info("Chỉ Admin mới thấy trang này.")
    conn = sqlite3.connect('autovision.db')
    tab_h, tab_u = st.tabs(["📜 Lịch Sử Định Giá", "👥 Quản Lý Người Dùng"])
    with tab_h:
        try:
            df_hist = pd.read_sql("SELECT * FROM history ORDER BY id DESC", conn)
            st.dataframe(df_hist, use_container_width=True)
            if not df_hist.empty:
                st.write("Biểu đồ giá trị các xe đã định giá:")
                st.bar_chart(df_hist['final_price'])
        except Exception: 
            st.write("Chưa có dữ liệu.")
    with tab_u:
        try:
            df_users = pd.read_sql("SELECT username, role FROM users", conn)
            st.dataframe(df_users, use_container_width=True)
        except Exception: 
            pass
    conn.close()
    st.stop()

# ==========================================
# 6. APP ĐỊNH GIÁ (GIỮ NGUYÊN LOGIC, CHỈ FIX ẢNH PDF MÁY CŨ)
# ==========================================
def remove_accents(input_str):
    if not isinstance(input_str, str): return str(input_str)
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def create_pdf(car_info, final_price, damages, image_path=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="BAO CAO DINH GIA XE (AUTOVISION)", ln=1, align='C')
    pdf.ln(5)
    
    if image_path and os.path.exists(image_path):
        try:
            abs_path = os.path.abspath(image_path)
            pdf.image(abs_path, x=55, w=100) 
            pdf.ln(5)
        except Exception as e:
            pdf.cell(200, 10, txt=f"(Loi anh: {str(e)})", ln=1, align='C')
    else:
        pdf.cell(200, 10, txt="(Khong co hinh anh xe)", ln=1, align='C')

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="1. THONG TIN XE:", ln=1)
    pdf.set_font("Arial", size=12)
    for key, value in car_info.items():
        safe_key = remove_accents(str(key))
        safe_val = remove_accents(str(value))
        pdf.cell(200, 10, txt=f"{safe_key}: {safe_val}", ln=1)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="2. CHI TIET HU HONG:", ln=1)
    pdf.set_font("Arial", size=12)
    if not damages:
        pdf.cell(200, 10, txt="Xe dep - Khong phat hien loi", ln=1)
    else:
        for d in damages:
            pdf.cell(200, 10, txt=f"- {remove_accents(d)}", ln=1)
            
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt=f"TONG DINH GIA: {final_price:,.0f} VND", ln=1, align='C')
    return pdf.output(dest='S').encode('latin-1', 'ignore')

def get_brand_logo(car_name):
    if not isinstance(car_name, str): return ""
    brand = car_name.split(' ')[0].lower()
    logos = {
        "maruti": "https://upload.wikimedia.org/wikipedia/en/d/d0/Maruti_Old_Logo.JPG",
        "hyundai": "https://upload.wikimedia.org/wikipedia/commons/4/44/Hyundai_Motor_Company_logo.svg",
        "honda": "https://upload.wikimedia.org/wikipedia/commons/7/7b/Honda_Logo.svg",
        "toyota": "https://upload.wikimedia.org/wikipedia/commons/9/9d/Toyota_carlogo.svg",
        "ford": "https://upload.wikimedia.org/wikipedia/commons/3/3e/Ford_logo_flat.svg",
        "chevrolet": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Chevrolet-logo.png/330px-Chevrolet-logo.png",
        "audi": "https://upload.wikimedia.org/wikipedia/commons/9/92/Audi-Logo_2016.svg",
        "bmw": "https://upload.wikimedia.org/wikipedia/commons/4/44/BMW.svg",
        "kia": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b6/KIA_logo3.svg/250px-KIA_logo3.svg.png",
        "mahindra": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/Mahindra_logo.svg/500px-Mahindra_logo.svg.png",
        "tata": "https://upload.wikimedia.org/wikipedia/commons/8/8e/Tata_logo.svg"
    }
    return logos.get(brand, "https://cdn-icons-png.flaticon.com/512/741/741407.png")

def detect_color(image):
    try:
        img = np.array(image); img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        h, w, _ = img.shape
        center_img = img[int(h*0.3):int(h*0.7), int(w*0.3):int(w*0.7)]
        if center_img.size == 0: return "Màu Khác"
        clt = KMeans(n_clusters=1); clt.fit(center_img.reshape((-1, 3)))
        b, g, r = clt.cluster_centers_[0]
        if r>200 and g>200 and b>200: return "Trắng"
        if r<50 and g<50 and b<50: return "Đen"
        if abs(r-g)<20 and r>100: return "Bạc/Xám"
        if r>150 and g<100: return "Đỏ"
        return "Màu Khác"
    except Exception: return "Màu Khác"

@st.cache_data
def load_data():
    try: return pd.read_csv('cardekho.csv')
    except Exception: return pd.DataFrame() 
df = load_data()
car_options = sorted(df['name'].unique().tolist()) if not df.empty else []

@st.cache_resource
def load_ai():
    p_model = None; y_model = None; cols = []
    try: 
        p_model = joblib.load('model_forest.pkl')
        cols = joblib.load('model_columns.pkl')
    except Exception: pass
    try: y_model = YOLO('best.pt')
    except Exception: pass
    return p_model, cols, y_model

price_model, model_cols, damage_model = load_ai()

st.title("🏎️ AUTOVISION ULTIMATE")

tab1, tab2, tab3 = st.tabs(["🔍 ĐỊNH GIÁ & SOI XE", "📊 BÁO CÁO & TRẢ GÓP", "🏆 TOP 10 XE NGON"])

with tab1:
    colL, colR = st.columns([1, 1.3], gap="large")
    with colL:
        st.markdown('<div class="metric-card"><h4>1. Thông Tin Xe</h4>', unsafe_allow_html=True)
        name = st.selectbox("Dòng xe:", car_options)
        st.image(get_brand_logo(name), width=80)
        c1, c2 = st.columns(2)
        with c1:
            year = st.number_input("Năm SX:", 2000, 2026, 2018)
            km = st.number_input("Odo (Km):", 0, 999999, 50000, step=1000)
            fuel = st.selectbox("Nhiên liệu:", ['Diesel', 'Petrol', 'Electric', 'LPG'])
            owner = st.selectbox("Đời chủ:", ['First Owner', 'Second Owner', 'Third Owner', 'Fourth & Above Owner'])
        with c2:
            trans = st.selectbox("Hộp số:", ['Manual', 'Automatic'])
            seller = st.selectbox("Người bán:", ['Individual', 'Dealer'])
            seats = st.selectbox("Số ghế:", [4, 5, 7, 8], index=1)
            max_power = st.number_input("Mã lực (bhp):", 20.0, 500.0, 80.0)
        st.markdown("---")
        plate = st.text_input("💎 Biển số (VD: 51G-999.99):")
        st.markdown('</div>', unsafe_allow_html=True)

    with colR:
        st.markdown('<div class="metric-card"><h4>2. Kiểm Tra Ngoại Thất</h4>', unsafe_allow_html=True)
        img_file = st.file_uploader("Upload ảnh xe:", type=['jpg','png','jpeg'], key=str(st.session_state.file_uploader_key))
        
        if img_file:
            try:
                img = Image.open(img_file)
                
                if st.session_state.pdf_image_path and os.path.exists(st.session_state.pdf_image_path):
                    try: os.remove(st.session_state.pdf_image_path)
                    except Exception: pass
                
                new_base_name = f"temp_car_{int(time.time())}.jpg"
                abs_fixed_path = os.path.abspath(new_base_name)
                
                # SỬA LỖI 1: ÉP FORMAT LÀ JPEG ĐỂ FPDF ĐỌC ĐƯỢC MỌI ẢNH CŨ
                img.convert("RGB").save(abs_fixed_path, format="JPEG")
                st.session_state.pdf_image_path = abs_fixed_path
            except Exception:
                st.error("Lỗi file ảnh")
                img = None

            if img:
                if st.button("🔍 QUÉT AI (Màu & Lỗi)", type="primary"):
                    try:
                        st.session_state.ai_color = detect_color(img)
                        c_opts = ["Trắng", "Đen", "Bạc/Xám", "Đỏ", "Xanh", "Màu Khác"]
                        if st.session_state.ai_color in c_opts:
                            st.session_state.box_color_val = st.session_state.ai_color
                        else: st.session_state.box_color_val = "Màu Khác"
                        
                        if damage_model:
                            results = damage_model(img)
                            res_plotted = results[0].plot()
                            st.session_state.ai_image = res_plotted
                            
                            if st.session_state.pdf_image_path and os.path.exists(st.session_state.pdf_image_path):
                                try: os.remove(st.session_state.pdf_image_path)
                                except Exception: pass
                                
                            new_ai_name = f"temp_car_ai_{int(time.time())}.jpg"
                            abs_ai_path = os.path.abspath(new_ai_name)
                            # SỬA LỖI 1: ÉP FORMAT LÀ JPEG
                            Image.fromarray(res_plotted[..., ::-1]).convert('RGB').save(abs_ai_path, format="JPEG")
                            st.session_state.pdf_image_path = abs_ai_path 
                            
                            costs = {'crack': 5000000, 'scratch': 1500000, 'dent': 4000000, 'glass shatter': 8000000, 'lamp broken': 3000000}
                            vn_names = {'crack': 'Nứt vỡ', 'scratch': 'Trầy xước', 'dent': 'Móp méo', 'glass shatter': 'Bể Kính', 'lamp broken': 'Vỡ đèn'}
                            
                            total = 0; d_list = []
                            for box in results[0].boxes:
                                cls = damage_model.names[int(box.cls[0])]
                                c = costs.get(cls, 1000000)
                                total += c
                                d_list.append(f"{vn_names.get(cls, cls)} (-{c:,.0f}đ)")
                            
                            st.session_state.damage_cost = total
                            st.session_state.damage_list = d_list

                            if total == 0: st.session_state.box_status_val = "Không lỗi (Hoàn hảo)"
                            elif total <= 3000000: st.session_state.box_status_val = "Trầy xước nhẹ"
                            elif total <= 7000000: st.session_state.box_status_val = "Móp méo"
                            elif total <= 10000000: st.session_state.box_status_val = "Bể kính / Vỡ đèn"
                            else: st.session_state.box_status_val = "Tai nạn nặng"
                        else: st.warning("Chưa có Model AI.")
                    except Exception: pass

                c1, c2 = st.columns(2)
                with c1: st.image(img, caption=f"Màu AI: {st.session_state.ai_color}", use_container_width=True)
                with c2: 
                    if 'ai_image' in st.session_state:
                        st.image(st.session_state.ai_image, caption="AI phát hiện lỗi", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        with st.expander("🛠️ CHỈNH SỬA KẾT QUẢ THỰC TẾ", expanded=True):
            mc1, mc2 = st.columns(2)
            with mc1:
                color_opts = ["Trắng", "Đen", "Bạc/Xám", "Đỏ", "Xanh", "Màu Khác"]
                manual_color = st.selectbox("Màu sắc thực tế:", color_opts, key='box_color_val')
            with mc2:
                dmg_opts = ["Không lỗi (Hoàn hảo)", "Trầy xước nhẹ", "Móp méo", "Bể kính / Vỡ đèn", "Tai nạn nặng"]
                manual_status = st.selectbox("Tình trạng hư hỏng:", dmg_opts, key='box_status_val')

    st.markdown("---")
    if st.button("💰 ĐỊNH GIÁ XE", use_container_width=True):
        if price_model:
            damage_prices = {"Không lỗi (Hoàn hảo)": 0, "Trầy xước nhẹ": 2000000, "Móp méo": 5000000, "Bể kính / Vỡ đèn": 8000000, "Tai nạn nặng": 20000000}
            final_dmg_cost = damage_prices.get(manual_status, 0)
            if final_dmg_cost > 0: st.session_state.damage_list = [f"{manual_status} (-{final_dmg_cost:,.0f}đ)"]
            else: st.session_state.damage_list = []
            
            input_df = pd.DataFrame([{
                'year': year, 'km_driven': km, 'fuel': fuel, 'seller_type': seller,
                'transmission': trans, 'owner': owner, 'mileage(km/ltr/kg)': 20.0,
                'engine': 1248, 'max_power': max_power, 'seats': seats,
                'no_year': 2026 - year
            }])
            input_df = pd.get_dummies(input_df).reindex(columns=model_cols, fill_value=0)
            base_price = price_model.predict(input_df)[0] * 300
            
            plate_bonus = 0
            if plate:
                p = plate.upper().replace(".", "").replace("-", "")
                if "999" in p or "888" in p: plate_bonus = 15000000
                elif "68" in p or "86" in p: plate_bonus = 5000000
            
            color_bonus = 5000000 if manual_color in ["Trắng", "Đen", "Bạc/Xám"] else -3000000
            
            final_price = base_price - final_dmg_cost + plate_bonus + color_bonus
            st.session_state.final_price = final_price 
            
            save_history_db(st.session_state.username, name, final_price)
            
            st.markdown(f"""
            <div style="background-color:#1f2937; padding:20px; border-radius:15px; text-align:center; border:2px solid #4ade80;">
                <h3 style='color:#9ca3af; margin:0;'>GIÁ THỊ TRƯỜNG: {base_price:,.0f} VNĐ</h3>
                <h1 class="big-price">{final_price:,.0f} VNĐ</h1>
            </div>
            """, unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            col1.info(f"🎨 Màu {manual_color}: {color_bonus:+,.0f}")
            col2.success(f"💎 Biển số: +{plate_bonus:,.0f}")
            if final_dmg_cost > 0: col3.error(f"📉 {manual_status}: -{final_dmg_cost:,.0f}")
            else: col3.success("✅ Xe đẹp, không trừ tiền")
        else: st.error("Lỗi Model!")

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        st.header("🖨️ Xuất Báo Cáo PDF")
        if st.session_state.final_price > 0:
            st.success("Đã có kết quả định giá!")
            try:
                car_info = {"Xe": name, "Bien So": plate, "Mau": manual_color, "Nam SX": year}
                pdf_bytes = create_pdf(car_info, st.session_state.final_price, st.session_state.damage_list, st.session_state.pdf_image_path)
                b64 = base64.b64encode(pdf_bytes).decode()
                href = f'<a href="data:application/octet-stream;base64,{b64}" download="BaoCao_DinhGia.pdf"><button style="background-color: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer;">📥 TẢI FILE PDF (CÓ ẢNH)</button></a>'
                st.markdown(href, unsafe_allow_html=True)
            except Exception as e: st.error(f"Lỗi tạo PDF: {e}")
        else: st.warning("Vui lòng định giá xe ở Tab 1 trước.")
    with c2:
        st.header("🏦 Tính Trả Góp")
        loan = st.number_input("Số tiền vay:", 100000000, 5000000000, 300000000, step=10000000)
        rate = st.number_input("Lãi suất (%/năm):", 5.0, 15.0, 9.0)
        year_loan = st.slider("Vay trong (năm):", 1, 10, 5)
        pay = (loan * rate/100/12) + (loan / (year_loan*12))
        st.info(f"👉 Trả mỗi tháng: {pay:,.0f} VNĐ")

with tab3:
    st.header("🏆 Top 10 Xe Đáng Mua")
    budget = st.number_input("Ngân sách (VNĐ):", 0, 5000000000, 400000000, step=50000000)
    if st.button("Tìm Xe Ngon"):
        if not df.empty:
            df['price_vnd'] = df['selling_price'] * 300
            res = df[df['price_vnd'] <= budget].sort_values(['year', 'price_vnd'], ascending=[False, True]).head(10)
            st.dataframe(res[['name', 'year', 'price_vnd']].style.format({'price_vnd': '{:,.0f}'}), use_container_width=True)
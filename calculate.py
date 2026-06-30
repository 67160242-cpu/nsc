import streamlit as st
import pandas as pd
import numpy as np
import joblib
import sqlite3
import hashlib
import warnings

# ปิดการแจ้งเตือนเรื่องเวอร์ชันของโมเดลไม่ตรงกัน (InconsistentVersionWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ตั้งค่าหน้าเว็บให้ดูทันสมัยและกว้างเต็มตา
st.set_page_config(
    page_title="ระบบพยากรณ์ผลผลิตพืช 5 ชนิดด้วย AI", 
    page_icon="🌾", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 💾 ฟังก์ชันจัดการฐานข้อมูล SQLite สำหรับระบบ Login
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users 
        (username TEXT PRIMARY KEY, password TEXT)
    """)
    conn.commit()
    conn.close()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return True
    return False

init_db()

# 🔐 ระบบ Session State
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# 🎨 Custom CSS ตกแต่งแนว AgriTech ทันสมัย
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght=300;400;600&display=swap');
    html, body, [class*="css"]  { font-family: 'Sarabun', sans-serif; }
    div[data-testid="stNumberInput"], div[data-testid="stSelectbox"] {
        background-color: #1e222b; padding: 10px; border-radius: 12px;
        border: 1px solid #3e4451; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .result-card { padding: 25px; border-radius: 15px; margin-top: 15px; box-shadow: 0 8px 16px rgba(0,0,0,0.2); color: white; }
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white; border: none; padding: 10px 24px; border-radius: 8px; font-weight: 600; width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🛑 ส่วนที่ 1: ระบบ LOGIN และ REGISTER
# ==========================================
if not st.session_state.logged_in:
    _, center_col, _ = st.columns([3, 4, 3])
    
    with center_col:
        menu = ["เข้าสู่ระบบ (Login)", "สมัครสมาชิก (Sign Up)"]
        choice = st.radio("เลือกทำรายการ", menu, horizontal=True)
        st.divider()

        if choice == "เข้าสู่ระบบ (Login)":
            st.markdown("<h2 style='text-align: center; color: #38ef7d;'>🔐 เข้าสู่ระบบ</h2>", unsafe_allow_html=True)
            username = st.text_input("Username", placeholder="กรอกชื่อผู้ใช้")
            password = st.text_input("Password", type="password", placeholder="กรอกรหัสผ่าน")
            
            if st.button("Sign In"):
                conn = sqlite3.connect("users.db")
                c = conn.cursor()
                c.execute("SELECT password FROM users WHERE username = ?", (username,))
                user_data = c.fetchone()
                conn.close()
                
                if user_data and check_hashes(password, user_data[0]):
                    st.session_state.logged_in = True
                    st.success(f"ยินดีต้อนรับคุณ {username}!")
                    st.rerun()
                else:
                    st.error("❌ ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

        elif choice == "สมัครสมาชิก (Sign Up)":
            st.markdown("<h2 style='text-align: center; color: #11998e;'>📝 สมัครสมาชิกใหม่</h2>", unsafe_allow_html=True)
            new_user = st.text_input("กำหนด Username", placeholder="เช่น myusername123")
            new_password = st.text_input("กำหนด Password", type="password", placeholder="รหัสผ่านเข้าใช้งาน")
            confirm_password = st.text_input("ยืนยัน Password อีกครั้ง", type="password", placeholder="กรอกรหัสผ่านให้ตรงกัน")
            
            if st.button("ลงทะเบียน (Register)"):
                if new_user == "" or new_password == "":
                    st.warning("⚠️ กรุณากรอกข้อมูลให้ครบถ้วน")
                elif new_password != confirm_password:
                    st.error("❌ รหัสผ่านทั้งสองช่องไม่ตรงกัน")
                else:
                    hashed_password = make_hashes(new_password)
                    try:
                        conn = sqlite3.connect("users.db")
                        c = conn.cursor()
                        c.execute("INSERT INTO users(username, password) VALUES (?,?)", (new_user, hashed_password))
                        conn.commit()
                        conn.close()
                        st.success("🎉 สมัครสมาชิกสำเร็จแล้ว! สลับไปหน้า Login เพื่อใช้งานได้ทันที")
                    except sqlite3.IntegrityError:
                        st.error("❌ Username นี้มีคนใช้ไปแล้ว กรุณาตั้งชื่อใหม่")

# ==========================================
# 🌾 ส่วนที่ 2: หน้า DASHBOARD พยากรณ์พืช 5 ชนิด
# ==========================================
else:
    @st.cache_resource
    def load_multi_crop_models():
        try:
            model = joblib.load('multi_crop_xgb_model.pkl')
            scaler = joblib.load('multi_crop_scaler.pkl')
            return model, scaler
        except Exception as e:
            st.error(f"⚠️ ไม่พบไฟล์โมเดลพืช 5 ชนิด กรุณาตรวจสอบไฟล์ในโฟลเดอร์เดียวกัน: {e}")
            return None, None

    model, scaler = load_multi_crop_models()

    header_col1, header_col2 = st.columns([8, 2])
    with header_col1:
        st.markdown("<h1 style='color: #38ef7d; font-weight: 600; margin:0;'>🌾 Multi-Crop Yield & Quality Predictor</h1>", unsafe_allow_html=True)
        st.write("ระบบวิเคราะห์และพยากรณ์คุณภาพผลผลิตและปริมาณน้ำหนักต่อไร่ของพืช 5 ชนิดด้วย AI (XGBoost)")
    with header_col2:
        if st.button("🚪 ออกจากระบบ"):
            st.session_state.logged_in = False
            st.rerun()

    st.divider()

    main_col1, main_col2 = st.columns([5, 5], gap="large")

    with main_col1:
        st.markdown("<h3 style='color: #11998e; margin-bottom: 15px;'>📥 ระบุปัจจัยในการเพาะปลูก</h3>", unsafe_allow_html=True)
        
        crop_opt = {"Sugarcane (อ้อย)": 0, "Rice (ข้าว)": 1, "Cassava (มันสำปะหลัง)": 2, "Maize (ข้าวโพด)": 3, "Durian (ทุเรียน)": 4}
        soil_opt = {"Loam (ดินร่วน)": 0, "Clay (ดินเหนียว)": 1, "Loamy Sand (ดินร่วนปนทราย)": 2}
        
        c_choice = st.selectbox("🌱 เลือกชนิดพืช", list(crop_opt.keys()))
        s_choice = st.selectbox("🧱 ชนิดของดิน", list(soil_opt.keys()))
        
        water = st.number_input("💧 ปริมาณน้ำรวมที่ได้รับ (ลิตร/ไร่)", min_value=100.0, max_value=5000.0, value=1200.0, step=50.0)
        fertilizer = st.number_input("🧪 ปริมาณปุ๋ยเคมี/อินทรีย์ที่ใส่ (กก./ไร่)", min_value=0.0, max_value=500.0, value=75.0, step=5.0)
        age = st.number_input("📅 ระยะเวลาการเพาะปลูกจนเก็บเกี่ยว (เดือน)", min_value=1.0, max_value=36.0, value=10.0, step=0.5)

    with main_col2:
        st.markdown("<h3 style='color: #11998e; margin-bottom: 15px;'>📋 ผลการวิเคราะห์จาก AI</h3>", unsafe_allow_html=True)
        
        if model is not None and scaler is not None:
            # ดึงรายชื่อคอลัมน์ดั้งเดิมให้ตรงสเกลพืช 5 ชนิด
            feature_names = ['Crop_Type', 'Soil_Type', 'Water_Liters_per_Rai', 'Fertilizer_KG_per_Rai', 'Cultivation_Duration_Months']
            
            input_data = pd.DataFrame([{
                'Crop_Type': crop_opt[c_choice],
                'Soil_Type': soil_opt[s_choice],
                'Water_Liters_per_Rai': water,
                'Fertilizer_KG_per_Rai': fertilizer,
                'Cultivation_Duration_Months': age
            }], columns=feature_names)
            
            input_scaled = scaler.transform(input_data)
            prediction = model.predict(input_scaled)
            
            # [แก้ไขสมบูรณ์] ดึงค่าแถวแรก [0] แล้วเจาะจงคอลัมน์ [0] และ [1] เพื่อแยกค่าพยากรณ์ทั้งสองตัว
            pred_quality = prediction[0][0].item()
            pred_yield = prediction[0][1].item()
            
            crop_id = crop_opt[c_choice]
            quality_unit = "หน่วย CCS" if crop_id == 0 else "% ปริมาณแป้ง" if crop_id == 2 else "คะแนนเกรดคุณภาพ"
            
            st.markdown(f"""
                <div class='result-card' style='background: linear-gradient(135deg, #11998e, #1f4037);'>
                    <h4 style='margin: 0;'>📈 ดัชนีคุณภาพผลผลิตที่คาดว่าจะได้</h4>
                    <p style='font-size: 38px; font-weight: bold; margin: 10px 0; color: #38ef7d;'>{pred_quality:.2f} <span style='font-size: 18px;'>{quality_unit}</span></p>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
                <div class='result-card' style='background: linear-gradient(135deg, #f39c12, #d35400);'>
                    <h4 style='margin: 0;'>🚜 น้ำหนักผลผลิตคาดการณ์ (Yield)</h4>
                    <p style='font-size: 38px; font-weight: bold; margin: 10px 0; color: #f1c40f;'>{pred_yield:.2f} <span style='font-size: 18px;'>ตัน / ไร่</span></p>
                </div>
            """, unsafe_allow_html=True)
            
            st.write("")
            meta_col1, meta_col2 = st.columns(2)
            meta_col1.metric(label="ประมาณการคุณภาพ", value=f"{pred_quality:.2f}")
            meta_col2.metric(label="ประมาณการน้ำหนักต่อไร่", value=f"{pred_yield:.2f} ตัน")
        else:
            st.info("💡 ระบบกำลังโหลดไฟล์โมเดล กรุณารอเปิดไฟล์สำเร็จสักครู่...")

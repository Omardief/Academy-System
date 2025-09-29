import streamlit as st
from supabase import create_client, Client
import pandas as pd
import datetime
import plotly.express as px
import base64
import math

# إعدادات Streamlit
st.set_page_config(page_title="Pioneer Academy", layout="wide")

# ---------------------------
# إعداد الاتصال مع Supabase
# ---------------------------
SUPABASE_URL = "https://ueynpexiegxqhvgskana.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVleW5wZXhpZWd4cWh2Z3NrYW5hIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTg0ODYyODMsImV4cCI6MjA3NDA2MjI4M30.6iLkcEDJ38tDVe3RYFl7I_F8-GCon2Ixb602EtNqOUg"

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()
# ---------------------------
# دوال للتعامل مع الجامعات
# ---------------------------
def check_duplicate_university(name):
    """التحقق من عدم وجود جامعة بنفس الاسم"""
    try:
        response = supabase.table("universities").select("name").eq("name", name).execute()
        return len(response.data) > 0 if response.data else False
    except Exception as e:
        st.error(f"Error checking duplicate: {e}")
        return False

def add_university(name, location):
    """إضافة جامعة جديدة للجدول"""
    try:
        # 🔥 التحقق من التكرار أولاً
        if check_duplicate_university(name):
            return None, "University with this name already exists"
            
        response = supabase.table("universities").insert({
            "name": name, 
            "location": location
        }).execute()
        
        if hasattr(response, 'data') and response.data:
            # 🔥 مسح الكاش بعد الإضافة الناجحة
            st.cache_data.clear()
            return response.data, None
        else:
            error_msg = getattr(response, 'error', None)
            return None, str(error_msg) if error_msg else "Unknown error occurred"
                
    except Exception as e:
        return None, str(e)
    
def get_universities():
    """جلب كل الجامعات من الجدول"""
    try:
        response = supabase.table("universities").select("id, name, location").execute()
        
        # 🔥 التصحيح: التحقق من البيانات بشكل صحيح
        if hasattr(response, 'data') and response.data:
            return pd.DataFrame(response.data)
        else:
            return pd.DataFrame(columns=["id", "name", "location"])
            
    except Exception as e:
        st.error(f"Error fetching universities: {e}")
        return pd.DataFrame(columns=["id", "name", "location"])

# ---------------------------
# دوال للتعامل مع الكورسات
# ---------------------------
def add_course(university_id, name, price, before_mid, after_mid, session_price, instructor_name, course_day, course_time):
    try:
        # تحويل البيانات
        university_id = int(university_id)
        price = float(price)
        before_mid = float(before_mid)
        after_mid = float(after_mid)
        session_price = float(session_price)

        if course_time:
            course_time = course_time.strftime("%H:%M:%S")

        response = supabase.table("courses").insert({
            "university_id": university_id,
            "name": name,
            "price": price,
            "before_mid": before_mid,
            "after_mid": after_mid,
            "session_price": session_price,
            "instructor_name": instructor_name,
            "course_day": course_day,
            "course_time": course_time
        }).execute()

        # 🔥 التصحيح: نفس المنطق
        if hasattr(response, 'data') and response.data:
            return response.data, None
        else:
            error_msg = getattr(response, 'error', None)
            if error_msg:
                return None, str(error_msg)
            else:
                return None, "Unknown error occurred"
                
    except Exception as e:
        return None, str(e)

def get_courses():
    try:
        response = supabase.table("courses").select("* , universities(name)").execute()
        
        if hasattr(response, 'data') and response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame(columns=["id","name","price","before_mid","after_mid","session_price","instructor_name","course_day","course_time","university_id"])
    except Exception as e:
        st.error(f"Error fetching courses: {e}")
        return pd.DataFrame(columns=["id","name","price","before_mid","after_mid","session_price","instructor_name","course_day","course_time","university_id"])

# ---------------------------
# دوال للتعامل مع الطلاب
# ---------------------------
def add_student(name, phone, gmail, university_id, department, commission=None):
    """إضافة طالب جديد مع إمكانية إضافة commission"""
    try:
        # 🔥 بناء بيانات الطالب
        student_data = {
            "name": name,
            "phone": phone,
            "gmail": gmail,
            "university_id": int(university_id) if university_id else None,
            "department": department
        }
        
        # 🔥 إضافة commission إذا تم تمريره
        if commission is not None and commission != "":
            student_data["commission"] = commission

        response = supabase.table("students").insert(student_data).execute()
        
        if hasattr(response, 'data') and response.data:
            # مسح الكاش بعد الإضافة الناجحة
            st.cache_data.clear()
            return response.data, None
        else:
            error_msg = getattr(response, 'error', None)
            if error_msg:
                # 🔥 معالجة unique constraint error بشكل أدق
                error_str = str(error_msg)
                if "duplicate key" in error_str or "23505" in error_str or "students_phone_unique" in error_str:
                    # جلب بيانات الطالب الموجود لنفس الرقم
                    existing_student = supabase.table("students")\
                        .select("name, university_id")\
                        .eq("phone", phone)\
                        .execute()
                    
                    if existing_student.data:
                        existing_name = existing_student.data[0]["name"]
                        existing_uni_id = existing_student.data[0]["university_id"]
                        
                        # جلب اسم الجامعة
                        uni_response = supabase.table("universities")\
                            .select("name")\
                            .eq("id", existing_uni_id)\
                            .execute()
                        
                        uni_name = uni_response.data[0]["name"] if uni_response.data else "غير معروفة"
                        
                        return None, f"❌ رقم الهاتف {phone} مسجل بالفعل للطالب: {existing_name} في جامعة {uni_name}. استخدم رقم مختلف."
                    else:
                        return None, f"❌ رقم الهاتف {phone} مسجل بالفعل لطالب آخر. استخدم رقم مختلف."
                else:
                    return None, f"❌ خطأ في الإضافة: {error_str}"
            else:
                return None, "❌ حدث خطأ غير معروف أثناء إضافة الطالب"
                
    except Exception as e:
        error_str = str(e)
        if "duplicate key" in error_str or "23505" in error_str or "students_phone_unique" in error_str:
            # نفس المعالجة في حالة ال exception
            existing_student = supabase.table("students")\
                .select("name, university_id")\
                .eq("phone", phone)\
                .execute()
            
            if existing_student.data:
                existing_name = existing_student.data[0]["name"]
                existing_uni_id = existing_student.data[0]["university_id"]
                
                uni_response = supabase.table("universities")\
                    .select("name")\
                    .eq("id", existing_uni_id)\
                    .execute()
                
                uni_name = uni_response.data[0]["name"] if uni_response.data else "غير معروفة"
                
                return None, f"❌ رقم الهاتف {phone} مسجل بالفعل للطالب: {existing_name} في جامعة {uni_name}. استخدم رقم مختلف."
            else:
                return None, f"❌ رقم الهاتف {phone} مسجل بالفعل لطالب آخر. استخدم رقم مختلف."
        else:
            return None, f"❌ خطأ غير متوقع: {error_str}"


def get_students():
    try:
        # 🔥 إضافة commission للـ select
        response = supabase.table("students").select("id, name, phone, gmail, department, commission, universities(name)").execute()
        
        if not response.data:
            return pd.DataFrame(columns=["id", "name", "phone", "gmail", "department", "commission", "university"])

        df = pd.DataFrame(response.data)

        if "universities" in df.columns:
            df["university"] = df["universities"].apply(lambda x: x.get("name") if isinstance(x, dict) else (x if isinstance(x, str) else None))
            df = df.drop(columns=["universities"])

        # 🔥 إضافة commission للقائمة
        cols = ["id", "name", "phone", "gmail", "department", "commission", "university"]
        for c in cols:
            if c not in df.columns:
                df[c] = None
        return df[cols]
        
    except Exception as e:
        st.error(f"Error fetching students: {e}")
        return pd.DataFrame(columns=["id", "name", "phone", "gmail", "department", "commission", "university"])
# ---------------------------
# دوال مساعدة للتسجيل
# ---------------------------
def get_students_by_university(university_id):
    try:
        # 🔥 إضافة commission هنا كمان
        resp = supabase.table("students").select("id, name, phone, gmail, department, commission").eq("university_id", int(university_id)).execute()
        if resp.data:
            return pd.DataFrame(resp.data)
        return pd.DataFrame(columns=["id","name","phone","gmail","department","commission"])
    except Exception as e:
        st.error(f"Error fetching students by university: {e}")
        return pd.DataFrame(columns=["id","name","phone","gmail","department","commission"])

def get_courses_by_university(university_id):
    try:
        resp = supabase.table("courses").select("id, name, price, before_mid, after_mid, session_price, instructor_name").eq("university_id", int(university_id)).execute()
        if resp.data:
            return pd.DataFrame(resp.data)
        return pd.DataFrame(columns=["id","name","price","before_mid","after_mid","session_price","instructor_name"])
    except Exception as e:
        st.error(f"Error fetching courses by university: {e}")
        return pd.DataFrame(columns=["id","name","price","before_mid","after_mid","session_price","instructor_name"])

# 🔥 دالة مساعدة موحدة للتعامل مع الـ responses
def _handle_response(resp):
    """دالة مساعدة للتعامل مع responses من Supabase"""
    try:
        if hasattr(resp, 'data'):
            data = resp.data
            error = getattr(resp, 'error', None)
            return data, str(error) if error else None
        else:
            return None, "Invalid response format"
    except Exception as e:
        return None, str(e)
    try:
        return getattr(resp, "data", None), getattr(resp, "error", None)
    except Exception as e:
        return None, str(e)

def register_student_courses_simple(
    student_id,
    course_details,  # list of dicts مع كل التفاصيل المحسوبة مسبقاً
    payment_option,
    payment_method="cash"
):
    """
    دالة مبسطة لتسجيل الطالب في الكورسات - تقوم بالإدخال فقط
    course_details: list of dictionaries تحتوي على:
        - course_id
        - course_name
        - total_fee
        - enrolled_fee
        - discount
        - payment_for_course
    """
    try:
        results = []
        
        for course in course_details:
            cid = course["course_id"]
            total_fee = course["total_fee"]
            enrolled_fee = course["enrolled_fee"]
            discount = course["discount"]
            payment_for_course = course["payment_for_course"]
            
            # إدخال تسجيل الطالب في الكورس
            insert_row = {
                "student_id": int(student_id),
                "course_id": int(cid),
                "enrollment_date": datetime.date.today().isoformat(),
                "total_fee": total_fee,
                "enrolled_fee": enrolled_fee,
                "payment_option": payment_option,
                "discount": discount,
                "amount_paid": 0.0,  # سيتم تحديثها بعد إدخال الدفعة
                "remaining_amount": enrolled_fee,
                "created_at": datetime.datetime.utcnow().isoformat() + "Z",
                "updated_at": datetime.datetime.utcnow().isoformat() + "Z"
            }
            
            ins_resp = supabase.table("student_courses").insert(insert_row).execute()
            ins_data, ins_err = _handle_response(ins_resp)
            if ins_err or not ins_data:
                return None, f"Failed to create registration for course {cid}: {ins_err}"
            
            sc_id = int(ins_data[0]["id"])
            
            # إذا كان هناك دفعة أولية، نسجلها
            if payment_for_course > 0:
                pay_resp = supabase.table("payments").insert({
                    "student_course_id": sc_id,
                    "amount": payment_for_course,
                    "payment_method": payment_method,
                    "paid_at": datetime.datetime.utcnow().isoformat() + "Z"
                }).execute()
                _, perr = _handle_response(pay_resp)
                if perr:
                    return None, f"Error inserting payment for course {cid}: {perr}"

                new_paid = payment_for_course
                new_remaining = max(enrolled_fee - new_paid, 0.0)
                
                # تحديث المبالغ بعد الدفع
                upd2 = supabase.table("student_courses").update({
                    "amount_paid": new_paid,
                    "remaining_amount": new_remaining,
                    "updated_at": datetime.datetime.utcnow().isoformat() + "Z"
                }).eq("id", sc_id).execute()
                _, uerr2 = _handle_response(upd2)
                if uerr2:
                    return None, f"Error updating after payment for course {cid}: {uerr2}"

                results.append({
                    "course_id": cid,
                    "course_name": course["course_name"],
                    "action": "created_and_paid_partial",
                    "total_fee": total_fee,
                    "enrolled_fee": enrolled_fee,
                    "discount": discount,
                    "paid_now": payment_for_course,
                    "amount_paid": new_paid,
                    "remaining": new_remaining
                })
            else:
                results.append({
                    "course_id": cid,
                    "course_name": course["course_name"],
                    "action": "created_no_payment",
                    "total_fee": total_fee,
                    "enrolled_fee": enrolled_fee,
                    "discount": discount,
                    "paid_now": 0.0,
                    "amount_paid": 0.0,
                    "remaining": enrolled_fee
                })

        return results, None

    except Exception as e:
        return None, str(e)

def allocate_payment_sequential_exact(courses, payment):
    """
    توزيع الدفعة تدريجيًا على الكورسات بناءً على المتبقي، مع الجمع مع المبالغ السابقة.
    courses: list of dicts each with keys: id, remaining_amount, amount_paid (float)
    payment: float (the total cash user wants to pay)
    Returns:
      allocations: list of dicts [{"course_id": id, "alloc": x}, ...]
      leftover: any leftover amount not allocated
    """
    allocations = []
    remaining_payment = float(payment)
    courses_with_remaining = [c for c in courses if float(c.get("remaining_amount", 0) or 0) > 0]
    
    if not courses_with_remaining:
        return allocations, remaining_payment
    
    for course in courses_with_remaining:
        course_id = course["id"]
        current_remaining = float(course.get("remaining_amount", 0) or 0)
        current_paid = float(course.get("amount_paid", 0) or 0)
        
        if remaining_payment <= 0 or current_remaining <= 0:
            allocations.append({"course_id": course_id, "alloc": 0.0})
            continue
        
        # المبلغ الممكن دفعه لهذا الكورس (أقل من المتبقي أو الدفعة المتبقية)
        alloc_amount = min(remaining_payment, current_remaining)
        
        allocations.append({
            "course_id": course_id,
            "alloc": alloc_amount
        })
        
        remaining_payment -= alloc_amount
    
    # إرجاع الباقي إذا كان فيه
    leftover = round(remaining_payment, 2)
    return allocations, leftover


def metric_card(title, value, color="#2A2AC2"):
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, {color}, #6A0DAD);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            color: white;
            box-shadow: 0 8px 16px rgba(0,0,0,0.2);
            border: 1px solid rgba(255,255,255,0.2);
            margin: 10px;
            ">
            <h4 style="margin:0; font-size:16px; font-weight:300;">{title}</h4>
            <h2 style="margin:0; font-size:32px; font-weight:700;">{value}</h2>
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------------------------
# إعدادات التصميم المتطور
# ---------------------------
def set_premium_style():
    st.markdown("""
    <style>
    /* تخصيص عام */
    .main-header {
        font-size: 2.8rem;
        background: linear-gradient(135deg, #8A2BE2, #6A0DAD);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 800;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    .section-header {
        font-size: 1.8rem;
        color: #8A2BE2;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        border-bottom: 3px solid #8A2BE2;
        padding-bottom: 0.5rem;
        font-weight: 600;
    }
    
    /* تخصيص الخلفية */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* تخصيص الأزرار */
    .stButton>button {
        background: linear-gradient(135deg, #8A2BE2, #6A0DAD);
        color: white;
        border-radius: 12px;
        border: none;
        padding: 0.7rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 8px rgba(138, 43, 226, 0.3);
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, #6A0DAD, #8A2BE2);
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(138, 43, 226, 0.4);
    }
    
    /* تخصيص الأختيارات */
    .stSelectbox>div>div>div {
        color: #8A2BE2;
        font-weight: 600;
    }
    
    /* تخصيص الجداول */
    .dataframe {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 6px 12px rgba(0,0,0,0.1);
        border: 1px solid rgba(138, 43, 226, 0.1);
    }
    
    /* تخصيص التبويبات */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 60px;
        white-space: pre-wrap;
        background: linear-gradient(135deg, #f8f9fa, #e9ecef);
        border-radius: 12px 12px 0 0;
        gap: 8px;
        padding: 15px 20px;
        font-weight: 600;
        border: 1px solid rgba(138, 43, 226, 0.1);
        margin: 2px;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #8A2BE2, #6A0DAD);
        color: white;
        box-shadow: 0 4px 8px rgba(138, 43, 226, 0.3);
    }
    
    /* تخصيص الأرقام */
    .stNumberInput>div>div>input {
        border: 2px solid #8A2BE2;
        border-radius: 10px;
        background: rgba(138, 43, 226, 0.05);
    }
    
    /* تخصيص النصوص */
    .stTextInput>div>div>input {
        border: 2px solid #8A2BE2;
        border-radius: 10px;
        background: rgba(138, 43, 226, 0.05);
    }
    
    /* تخصيص الشريط الجانبي */
    .css-1d391kg {
        background: linear-gradient(180deg, #8A2BE2 0%, #6A0DAD 100%);
        box-shadow: 4px 0 12px rgba(0,0,0,0.1);
    }
    
    .css-1d391kg h1 {
        color: white;
        text-align: center;
        font-weight: 700;
    }
    
    .stRadio>div {
        background: rgba(255,255,255,0.9);
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    /* تخصيص الرسوم البيانية */
    .js-plotly-plot .plotly {
        border-radius: 12px;
        box-shadow: 0 6px 12px rgba(0,0,0,0.1);
        background: white;
    }
    
    /* تخصيص البطاقات */
    .card {
        background: linear-gradient(135deg, #ffffff, #f8f9fa);
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 6px 12px rgba(0,0,0,0.1);
        border: 1px solid rgba(138, 43, 226, 0.1);
    }
    
    /* تخصيص التنبيهات */
    .stAlert {
        border-radius: 12px;
        border-left: 5px solid #8A2BE2;
    }
    
    /* تخصيص النجاح */
    .stSuccess {
        background: linear-gradient(135deg, #d4edda, #c3e6cb);
        border-left: 5px solid #28a745;
    }
    
    /* تخصيص التحذيرات */
    .stWarning {
        background: linear-gradient(135deg, #fff3cd, #ffeaa7);
        border-left: 5px solid #ffc107;
    }
    
    /* تخصيص الأخطاء */
    .stError {
        background: linear-gradient(135deg, #f8d7da, #f5c6cb);
        border-left: 5px solid #dc3545;
    }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------
# شعار Pioneer Academy (بديل نصي متطور)
# ---------------------------

def get_base64_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

# مثال لاستخدام اللوجو (استبدل 'logo.png' بمسار الصورة الحقيقي)
logo_path = "logo.png"  # غيّر المسار ده للموقع الصحيح للوجو
base64_logo = get_base64_image(logo_path)

def display_premium_logo():
    # استبدال العمود بتاع اللوجو في الكود
    st.markdown(
        f"""
        <div style="text-align: center; margin-bottom: 2rem; padding: 2rem; background: linear-gradient(135deg, #8A2BE2, #6A0DAD); border-radius: 20px; box-shadow: 0 8px 16px rgba(0,0,0,0.2);">
            <div style="display: flex; align-items: center; justify-content: center; gap: 20px;">
                <div style="background: white; border-radius: 50%; width: 80px; height: 80px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 8px rgba(0,0,0,0.2); overflow: hidden;">
                    <img src="data:image/png;base64,{base64_logo}" alt="Logo" style="width: 100%; height: 100%; object-fit: cover;">
                </div>
                <div>
                    <h1 style="color: white; font-size: 3.5rem; margin: 0; font-weight: 800; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">Pioneer Academy</h1>
                    <p style="color: rgba(255,255,255,0.9); font-size: 1.3rem; margin: 0; font-weight: 300;"> Expert Coding, Pioneered   </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


set_premium_style()

# إدارة حالة تسجيل الدخول
if "logged_in" not in st.session_state:
    st.session_state.logged_in = True
    st.session_state.role = "full_admin"
    st.session_state.username = "admin"
    st.session_state.selected_page = "welcome"

# صفحة تسجيل الدخول
if not st.session_state.logged_in:
    display_premium_logo()
    st.markdown("<h1 style='text-align: center;'>🔐 تسجيل الدخول</h1>", unsafe_allow_html=True)
    
    # توسيط حقول الإدخال والزر
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])  # عمودين فارغين على الجانبين، عمود في النص
    with col2:
        st.markdown('<div class="login-input">', unsafe_allow_html=True)
        username = st.text_input("اسم المستخدم", key="login_username")
        password = st.text_input("كلمة المرور", type="password", key="login_password")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-button">', unsafe_allow_html=True)
        if st.button("تسجيل الدخول", key="login_button"):
            if not username or not password:
                st.error("❌ يرجى إدخال اسم المستخدم وكلمة المرور")
            else:
                try:
                    # التحقق من وجود username
                    users = supabase.table("users").select("*").eq("username", username).execute().data
                    st.write(f"Debug: Response from Supabase for username '{username}': {users}")  # تصحيح مؤقت
                    if users:
                        user = users[0]
                        if user["password"] == password:
                            st.session_state.logged_in = True
                            st.session_state.role = user["role"]
                            st.session_state.username = user["username"]
                            st.session_state.selected_page = "Welcome"
                            st.success(f"✅ تم تسجيل الدخول بنجاح! الدور: {user['role']}")
                            st.rerun()
                        else:
                            st.error("❌ كلمة المرور غير صحيحة")
                    else:
                        st.error("❌ اسم المستخدم غير موجود")
                except Exception as e:
                    st.error(f"❌ خطأ في الاتصال بقاعدة البيانات: {str(e)}")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.stop()  # إيقاف الكود لحين تسجيل الدخول

# تعريف الصفحات مع تجميعها تحت أقسام
page_options = {
    "🏫 Pioneer": [
        "Welcome",
        "Dashboard",
        "الجامعات",
        "الكورسات",
        "إدارة الطلاب",
        "تسجيل دفعة"
    ],
    "📚 Pioneer Private": [
        "Private Dashboard",
        "Registration"
    ],
    "🎓 Tech Trek": [
        "TT Dashboard"
    ],
    "📊 Admin Panel": [
        "Main Dashboard"
    ]
}

# تصفية الصفحات بناءً على الدور
if st.session_state.role == "full_admin":
    filtered_page_options = page_options  # يشوف كل الصفحات
elif st.session_state.role == "pioneer_secretary":
    filtered_page_options = {
        "🏫 Pioneer": [
            "إدارة الطلاب",
            "تسجيل دفعة"
        ],
        "📚 Pioneer Private": [
            "Registration"
    ]
    }  # يشوف بس صفحتين تحت Pioneer
else:
    filtered_page_options = {}

# إنشاء قائمة موحدة للصفحات مع فواصل بصرية
flattened_options = []
for section, pages in filtered_page_options.items():
    flattened_options.append(f"--- {section} ---")
    flattened_options.extend(pages)

# إعداد القائمة الجانبية
with st.sidebar:
    # عرض الشعار المتميز
    st.markdown("""
    <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, #8A2BE2, #6A0DAD); border-radius: 15px; margin-bottom: 2rem;">
        <div style="background: white; border-radius: 50%; width: 60px; height: 60px; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem auto; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
            <span style="font-size: 2rem; color: #8A2BE2; font-weight: bold;">🎓</span>
        </div>
        <h3 style="color: white; margin: 0; font-weight: 700;">Pioneer Academy</h3>
        <p style="color: rgba(255,255,255,0.9); margin: 0; font-size: 0.9rem;">Management System</p>
    </div>
    """, unsafe_allow_html=True)
    st.title("📂 Menu")


    # إضافة st.selectbox للصفحات المتاحة
    if flattened_options:  # التأكد من أن القائمة ليست فاضية
        page = st.selectbox(
            "اختر الصفحة",
            flattened_options,
            index=flattened_options.index(st.session_state.selected_page) if st.session_state.selected_page in flattened_options else 0,
            format_func=lambda x: x if not x.startswith("---") else x.replace("--- ", "").replace(" ---", ""),
            key="main_page_select"
        )
        # تحديث st.session_state عند اختيار صفحة جديدة
        if page != st.session_state.selected_page and not page.startswith("---"):
            st.session_state.selected_page = page
    else:
        st.error("⚠️ لا توجد صفحات متاحة لهذا الدور")
    
        # زر تسجيل الخروج
    if st.button("🚪 تسجيل الخروج", key="logout_button"):
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.username = None
        st.session_state.selected_page = None
        st.rerun()
        
# عرض الشعار الرئيسي
display_premium_logo()

# عرض المحتوى بناءً على الصفحة المختارة
page = st.session_state.selected_page

if page == "Welcome":
    st.markdown('<div class="main-header"> Welcome in Pioneer Academy 🎉</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="card">
        <p style="font-size: 1.2rem; color: #333; text-align: center; line-height: 1.6;">
            مرحبًا بك في نظام إدارة أكاديمية Pioneer! هذا النظام مصمم لتسهيل إدارة الجامعات، الكورسات، الطلاب، والمدفوعات بطريقة متكاملة وسهلة الاستخدام.
            <br><br>
            اختر من القائمة الجانبية للتنقل بين الصفحات المختلفة، سواء لإدارة البيانات أو عرض الإحصائيات.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # --- الجدول الزمني الأسبوعي ---
    st.markdown('<div class="section-header">🗓️ الجدول الزمني الأسبوعي للكورسات</div>', unsafe_allow_html=True)

    # جلب بيانات الجامعات والكورسات
    universities_df = get_universities()
    courses_df = get_courses()

    if universities_df.empty:
        st.warning("⚠️ لا توجد جامعات مضافة بعد.")
    elif courses_df.empty:
        st.info("ℹ️ لا توجد كورسات مسجلة بعد.")
    else:
        # فلتر الجامعة (اختياري)
        uni_name = st.selectbox("🏫 اختر الجامعة (اختياري)", ["الكل"] + universities_df["name"].tolist())
        if uni_name != "الكل":
            uni_id = int(universities_df.loc[universities_df["name"] == uni_name, "id"].values[0])
            courses_df = courses_df[courses_df["university_id"] == uni_id]

        # إعداد الجدول الزمني
        days = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        time_slots = [f"{h:02d}:00" for h in range(12, 22)]  # من 8 صباحًا إلى 10 مساءً

        # إنشاء DataFrame فارغ للجدول
        timetable = pd.DataFrame(index=time_slots, columns=days)
        timetable = timetable.fillna(" ")  # تعبئة الجدول بـ "فارغ" افتراضيًا

        # تحويل course_time إلى صيغة ساعة
        def format_time(t):
            try:
                return pd.to_datetime(t, format="%H:%M:%S").strftime("%H:00")
            except:
                return None

        # ملء الجدول ببيانات الكورسات
        for _, course in courses_df.iterrows():
            day = course["course_day"]
            time = format_time(course["course_time"])
            if day in days and time in time_slots:
                course_info = f"{course['name']} ({course['instructor_name']})"
                timetable.loc[time, day] = course_info

        # تنسيق الجدول باستخدام CSS مخصص
        def style_dataframe(df):
            def highlight_empty(val):
                color = "#e0f7fa" if val == " " else "#ffffff"
                return f"background-color: {color}; text-align: center; padding: 10px; border: 1px solid #ddd;"
            
            styled_df = df.style.applymap(highlight_empty).set_properties(**{
                "border-collapse": "collapse",
                "font-size": "14px",
                "font-weight": "500"
            }).set_table_styles([
                {"selector": "th", "props": [("background-color", "#8A2BE2"), ("color", "white"), ("padding", "10px"), ("text-align", "center")]}
            ])
            return styled_df

        # عرض الجدول
        st.dataframe(style_dataframe(timetable), use_container_width=True)

elif page == "الجامعات":
    st.markdown('<div class="main-header">🏫 إدارة الجامعات</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["➕ إضافة جامعة", "📋 عرض الجامعات"])

    # --- إضافة جامعة ---
    with tab1:
        st.markdown('<div class="section-header">➕ إضافة جامعة جديدة</div>', unsafe_allow_html=True)
        
        # 🔥 استخدام session state لمنع الإرسال المكرر
        if 'university_submitted' not in st.session_state:
            st.session_state.university_submitted = False
            
        with st.form("add_university_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("اسم الجامعة", key="uni_name_input")
            with col2:
                location = st.text_input("المكان", key="uni_location_input")

            submit = st.form_submit_button("إضافة")

            if submit:
                if name.strip() == "":
                    st.error("❌ من فضلك أدخل اسم الجامعة")
                else:
                    # 🔥 التحقق من عدم وجود جامعة بنفس الاسم أولاً
                    existing_unis = get_universities()
                    if not existing_unis.empty and name in existing_unis['name'].values:
                        st.error("❌ جامعة بنفس الاسم موجودة بالفعل!")
                    else:
                        data, error = add_university(name, location)
                        if error:
                            # 🔥 معالجة الخطأ بشكل أفضل
                            if "duplicate key" in str(error) or "23505" in str(error):
                                st.error("❌ جامعة بنفس الاسم موجودة بالفعل!")
                            else:
                                st.error(f"❌ خطأ: {error}")
                        else:
                            st.success("✅ تم إضافة الجامعة بنجاح")
                            # 🔥 استخدام success message بدل rerun
                            st.session_state.university_submitted = True
                            
        # 🔥 عرض رسالة النجاح بدون استخدام rerun
        if st.session_state.get('university_submitted', False):
            st.info("✅ تمت إضافة الجامعة بنجاح. يمكنك إضافة جامعة جديدة أو الانتقال إلى تبويب العرض.")
            if st.button("إضافة جامعة أخرى"):
                st.session_state.university_submitted = False
                st.rerun()

    # --- عرض الجامعات ---
    with tab2:
        st.markdown('<div class="section-header">📋 قائمة الجامعات</div>', unsafe_allow_html=True)
        
        # 🔥 استخدام cache للحفاظ على استقرار الجدول
        def load_universities_data():
            return get_universities()
            
        try:
            df = load_universities_data()
            if not df.empty:
                # 🔥 إضافة search filter للجامعات
                search_term = st.text_input("🔍 بحث باسم الجامعة:", key="uni_search")
                
                if search_term:
                    filtered_df = df[df['name'].str.contains(search_term, case=False, na=False)]
                else:
                    filtered_df = df
                
                # عرض الجدول
                st.dataframe(filtered_df, use_container_width=True)
                
                # 🔥 إحصائيات
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("عدد الجامعات", len(filtered_df))
                with col2:
                    locations_count = filtered_df['location'].nunique()
                    st.metric("عدد المواقع", locations_count)
                with col3:
                    if st.button("🔄 تحديث البيانات", key="refresh_unis"):
                        st.cache_data.clear()
                        st.rerun()
                        
            else:
                st.info("ℹ️ لا يوجد جامعات مسجلة حتى الآن.")
        except Exception as e:
            st.error(f"❌ خطأ في تحميل البيانات: {e}")
# ---------------------------
# صفحة إدارة الكورسات
# ---------------------------
elif page == "الكورسات":
    st.markdown('<div class="main-header"> إدارة الكورسات</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["➕ إضافة كورس", "📋 عرض الكورسات", "تعديل بيانات الكورس "])

    # --- إضافة كورس ---
    with tab1:
        universities_df = get_universities()
        if universities_df.empty:
            st.warning("⚠️ لا توجد جامعات مضافة بعد. قم بإضافة جامعة أولًا.")
        else:
            st.markdown('<div class="section-header">📘 إضافة كورس جديد</div>', unsafe_allow_html=True)
            with st.form("add_course_form"):
                # الصف الأول (اسم الكورس + الجامعة)
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("اسم الكورس")
                with col2:
                    university_name = st.selectbox("اختر الجامعة", universities_df["name"].tolist())
                    uni_id = universities_df.loc[universities_df["name"] == university_name, "id"].values[0]

                # الصف الثاني (السعر الكلي + سعر السيشن)
                col3, col4 = st.columns(2)
                with col3:
                    price = st.number_input("💰 السعر الكلي", min_value=0.0, step=100.0)
                with col4:
                    session_price = st.number_input("💵 سعر السيشن", min_value=0.0, step=50.0)

                # الصف الثالث (قبل الميد + بعد الميد)
                col5, col6 = st.columns(2)
                with col5:
                    before_mid = st.number_input("📑 الجزء قبل الميد", min_value=0.0, step=50.0)
                with col6:
                    after_mid = st.number_input("📑 الجزء بعد الميد", min_value=0.0, step=50.0)

                # الصف الرابع (المحاضر + اليوم + الوقت)
                col7, col8, col9 = st.columns(3)
                with col7:
                    instructor_name = st.text_input("👨‍🏫 اسم المحاضر")
                with col8:
                    course_day = st.selectbox("📅 اليوم", ["Saturday","Sunday","Monday","Tuesday","Wednesday","Thursday","Friday"])
                with col9:
                    course_time = st.time_input("🕒 الساعة")

                # زرار الإضافة
                submit_course = st.form_submit_button("✅ إضافة الكورس")

                if submit_course:
                    if name.strip() == "":
                        st.error("❌ من فضلك أدخل اسم الكورس")
                    else:
                        data, error = add_course(uni_id, name, price, before_mid, after_mid, session_price, instructor_name, course_day, course_time )
                        if error:
                            st.error(f"❌ خطأ: {error}")
                        else:
                            st.success("✅ تم إضافة الكورس بنجاح")

    # --- عرض الكورسات ---
    with tab2:
        st.markdown('<div class="section-header">📋 قائمة الكورسات</div>', unsafe_allow_html=True)
        # تحميل بيانات الكورسات والجامعات
        courses_data = supabase.table("courses").select("*").execute().data
        universities_data = supabase.table("universities").select("*").execute().data

        courses_df = pd.DataFrame(courses_data)
        universities_df = pd.DataFrame(universities_data)

        if not courses_df.empty and not universities_df.empty:
            # ربط الكورسات بالجامعات
            courses_df = courses_df.merge(
                universities_df,
                left_on="university_id",
                right_on="id",
                suffixes=("", "_univ")
            )

            # اختيار الأعمدة اللي عايزها
            display_df = courses_df[[
                "name", "price", "before_mid", "after_mid",
                "session_price", "instructor_name", "course_day",
                "course_time", "name_univ"
            ]].rename(columns={
                "name": "اسم الكورس",
                "price": "السعر الكلي",
                "before_mid": "قبل الميد",
                "after_mid": "بعد الميد",
                "session_price": "سعر السيشن",
                "instructor_name": "المدرس",
                "course_day": "اليوم",
                "course_time": "الساعة",
                "name_univ": "الجامعة"
            })

            # فلتر الجامعات
            universities = display_df["الجامعة"].dropna().unique().tolist()
            selected_uni = st.selectbox("🎓 اختر الجامعة", ["الكل"] + universities)

            if selected_uni != "الكل":
                display_df = display_df[display_df["الجامعة"] == selected_uni]

            # عرض الجدول
            st.dataframe(display_df, use_container_width=True)

        else:
            st.info("ℹ️ لا يوجد كورسات مسجلة حتى الآن.")

    with tab3:
        st.markdown('<div class="section-header">✏️ تعديل بيانات الكورس</div>', unsafe_allow_html=True)
        
        # جلب الكورسات والجامعات
        courses_data = supabase.table("courses").select("*").execute().data
        universities_data = supabase.table("universities").select("*").execute().data
        
        if not courses_data or not universities_data:
            st.info("ℹ️ لا يوجد كورسات مسجلة حتى الآن.")
        else:
            courses_df = pd.DataFrame(courses_data)
            universities_df = pd.DataFrame(universities_data)
            
            # ربط الكورسات بالجامعات للعرض
            courses_display_df = courses_df.merge(
                universities_df,
                left_on="university_id", 
                right_on="id",
                suffixes=("", "_univ")
            )
            
            # اختيار الكورس للتعديل
            course_options = [f"{row['name']} - {row['name_univ']}" for _, row in courses_display_df.iterrows()]
            selected_course = st.selectbox("اختر الكورس للتعديل", course_options)
            
            if selected_course:
                # استخراج ID الكورس المختار
                course_name, university_name = selected_course.split(" - ")
                course_id = courses_display_df[
                    (courses_display_df["name"] == course_name) & 
                    (courses_display_df["name_univ"] == university_name)
                ]["id"].values[0]
                
                # جلب بيانات الكورس الحالية
                current_course = courses_df[courses_df["id"] == course_id].iloc[0]
                
                st.markdown("### 📝 تعديل البيانات")
                with st.form("edit_course_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_name = st.text_input("اسم الكورس", value=current_course.get("name", ""))
                    with col2:
                        # الجامعة لا يمكن تعديلها (للتجنب المشاكل في العلاقات)
                        st.text_input("الجامعة", value=university_name, disabled=True)
                    
                    col3, col4 = st.columns(2)
                    with col3:
                        new_price = st.number_input(
                            "💰 السعر الكلي", 
                            min_value=0.0, 
                            step=100.0,
                            value=float(current_course.get("price", 0))
                        )
                    with col4:
                        new_session_price = st.number_input(
                            "💵 سعر السيشن", 
                            min_value=0.0, 
                            step=50.0,
                            value=float(current_course.get("session_price", 0))
                        )
                    
                    col5, col6 = st.columns(2)
                    with col5:
                        new_before_mid = st.number_input(
                            "📑 الجزء قبل الميد", 
                            min_value=0.0, 
                            step=50.0,
                            value=float(current_course.get("before_mid", 0))
                        )
                    with col6:
                        new_after_mid = st.number_input(
                            "📑 الجزء بعد الميد", 
                            min_value=0.0, 
                            step=50.0,
                            value=float(current_course.get("after_mid", 0))
                        )
                    
                    col7, col8, col9 = st.columns(3)
                    with col7:
                        new_instructor = st.text_input(
                            "👨‍🏫 اسم المحاضر", 
                            value=current_course.get("instructor_name", "")
                        )
                    with col8:
                        days = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
                        current_day = current_course.get("course_day", "Saturday")
                        new_day = st.selectbox(
                            "📅 اليوم", 
                            days,
                            index=days.index(current_day) if current_day in days else 0
                        )
                    with col9:
                        # التعامل مع الوقت
                        current_time = current_course.get("course_time")
                        if current_time:
                            try:
                                # تحويل الوقت من string إلى time object
                                if isinstance(current_time, str):
                                    time_obj = datetime.datetime.strptime(current_time, "%H:%M:%S").time()
                                else:
                                    time_obj = current_time
                            except:
                                time_obj = datetime.time(10, 0)  # وقت افتراضي
                        else:
                            time_obj = datetime.time(10, 0)
                        
                        new_time = st.time_input("🕒 الساعة", value=time_obj)
                    
                    # زرار التحديث
                    update_button = st.form_submit_button("💾 حفظ التعديلات")
                    
                    if update_button:
                        if new_name.strip() == "":
                            st.error("❌ من فضلك أدخل اسم الكورس")
                        else:
                            try:
                                # تحويل الوقت إلى string للتخزين
                                time_str = new_time.strftime("%H:%M:%S")
                                
                                # تحديث البيانات في Supabase
                                response = supabase.table("courses").update({
                                    "name": new_name,
                                    "price": new_price,
                                    "session_price": new_session_price,
                                    "before_mid": new_before_mid,
                                    "after_mid": new_after_mid,
                                    "instructor_name": new_instructor,
                                    "course_day": new_day,
                                    "course_time": time_str
                                    
                                }).eq("id", course_id).execute()
                                
                                if response.data:
                                    st.success("✅ تم تحديث بيانات الكورس بنجاح")
                                    st.rerun()
                                else:
                                    st.error("❌ حدث خطأ أثناء التحديث")
                                    
                            except Exception as e:
                                st.error(f"❌ خطأ: {e}")
                
                # عرض البيانات الحالية للمقارنة
                st.markdown("### 📊 البيانات الحالية")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.info(f"**الاسم:** {current_course.get('name', '')}")
                    st.info(f"**السعر الكلي:** {current_course.get('price', 0):.2f} جنيه")
                    st.info(f"**قبل الميد:** {current_course.get('before_mid', 0):.2f} جنيه")
                    st.info(f"**بعد الميد:** {current_course.get('after_mid', 0):.2f} جنيه")
                
                with col2:
                    st.info(f"**سعر السيشن:** {current_course.get('session_price', 0):.2f} جنيه")
                    st.info(f"**المحاضر:** {current_course.get('instructor_name', '')}")
                    st.info(f"**اليوم:** {current_course.get('course_day', '')}")
                    st.info(f"**الوقت:** {current_course.get('course_time', '')}")

# ---------------------------
# صفحة إدارة الطلاب
# ---------------------------
elif page == "إدارة الطلاب":
    st.markdown('<div class="main-header">🎓 إدارة الطلاب</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["➕ إضافة طالب", "📋 عرض الطلاب","➕ تسجيل كورس جديد"])

    # --- إضافة طالب ---
    with tab1:
        universities_df = get_universities()
        if universities_df.empty:
            st.warning("⚠️ لا توجد جامعات مضافة بعد. قم بإضافة جامعة أولًا.")
        else:
            st.markdown('<div class="section-header">👨‍🎓 إضافة طالب جديد</div>', unsafe_allow_html=True)
            
            # 🔥 استخدام session state لمنع الإرسال المكرر
            if 'student_submitted' not in st.session_state:
                st.session_state.student_submitted = False
                
            with st.form("add_student_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("اسم الطالب", key="student_name")
                with col2:
                    phone = st.text_input("📞 رقم الهاتف", key="student_phone")

                col3, col4 = st.columns(2)
                with col3:
                    gmail = st.text_input("📧 Gmail", key="student_gmail")
                with col4:
                    department = st.text_input("🏷️ القسم", key="student_department")

                col5, col6 = st.columns(2)
                with col5:
                    # اختيار الجامعة
                    university_name = st.selectbox(
                        "🏫 اختر الجامعة", 
                        universities_df["name"].tolist(),
                        key="student_university"
                    )
                    university_id = universities_df.loc[universities_df["name"] == university_name, "id"].values[0]
                
                with col6:
                    # 🔥 اختيار الـ commission
                    commission_options = ["", "Menna", "Mariem", "Malak", "Salma", "Pioneer", "ANU"]
                    commission = st.selectbox(
                        "👥  Sales ", 
                        commission_options,
                        key="student_commission"
                    )

                submit_student = st.form_submit_button("✅ حفظ الطالب")

                if submit_student:
                    if name.strip() == "" or gmail.strip() == "" or department.strip() == "":
                        st.error("❌ من فضلك أدخل كل البيانات المطلوبة (الاسم، الـ Gmail، والقسم)")
                    elif phone.strip() == "":
                        st.error("❌ من فضلك أدخل رقم الهاتف")
                    else:
                        # 🔥 التحقق من صحة رقم الهاتف
                        if not phone.replace(' ', '').replace('-', '').replace('+', '').isdigit():
                            st.error("❌ رقم الهاتف يجب أن يحتوي على أرقام فقط")
                        else:
                            data, error = add_student(name, phone, gmail, university_id, department, commission)
                            if error:
                                if "رقم الهاتف مسجل" in error:
                                    st.error("❌ رقم الهاتف مسجل بالفعل لطالب آخر")
                                else:
                                    st.error(f"❌ خطأ: {error}")
                            else:
                                st.success("✅ تم إضافة الطالب بنجاح")
                                st.session_state.student_submitted = True
                                
            # 🔥 عرض رسالة النجاح بدون استخدام rerun
            if st.session_state.get('student_submitted', False):
                st.info("✅ تمت إضافة الطالب بنجاح. يمكنك إضافة طالب جديد أو الانتقال إلى تبويب العرض.")
                if st.button("إضافة طالب آخر"):
                    st.session_state.student_submitted = False
                    st.rerun()

    with tab2:
        st.markdown('<div class="section-header">📋 قائمة الطلاب</div>', unsafe_allow_html=True)
        
        @st.cache_data(ttl=60)
        def load_students_data():
            return get_students()
            
        try:
            students_df = load_students_data()
            if not students_df.empty:
                # فلتر الجامعات
                universities = students_df["university"].dropna().unique().tolist()
                selected_uni = st.selectbox(
                    "🎓 اختر الجامعة", 
                    ["الكل"] + universities,
                    key="view_students_uni"
                )

                # 🔥 فلتر الـ commission
                commissions = students_df["commission"].dropna().unique().tolist()
                selected_commission = st.selectbox(
                    "👥 فلتر حسب المسوق", 
                    ["الكل"] + commissions,
                    key="view_students_commission"
                )

                # 🔥 بحث بالاسم أو رقم الهاتف
                search_term = st.text_input("🔍 بحث بالاسم أو رقم الهاتف:", key="student_search")

                # تطبيق الفلاتر
                filtered_df = students_df.copy()
                if selected_uni != "الكل":
                    filtered_df = filtered_df[filtered_df["university"] == selected_uni]
                if selected_commission != "الكل":
                    filtered_df = filtered_df[filtered_df["commission"] == selected_commission]
                if search_term:
                    filtered_df = filtered_df[
                        filtered_df["name"].str.contains(search_term, case=False, na=False) |
                        filtered_df["phone"].str.contains(search_term, case=False, na=False)
                    ]

                if filtered_df.empty:
                    st.info("📭 لا توجد نتائج تطابق معايير البحث.")
                else:
                    # إحصائيات
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("عدد الطلاب", len(filtered_df))
                    with col2:
                        unique_commissions = filtered_df["commission"].nunique()
                        st.metric("عدد المسوقين", unique_commissions)
                    with col3:
                        if st.button("🔄 تحديث البيانات", key="refresh_students"):
                            st.cache_data.clear()
                            st.rerun()

                    # عرض البيانات
                    display_df = filtered_df.rename(columns={
                        "name": "👤 الاسم",
                        "phone": "📞 الهاتف", 
                        "gmail": "📧 الإيميل",
                        "department": "🏷️ القسم",
                        "commission": "👥 المسوق",
                        "university": "🏫 الجامعة"
                    })
                    
                    st.dataframe(display_df, use_container_width=True)
            else:
                st.info("ℹ️ لا يوجد طلاب مسجلين حتى الآن.")
        except Exception as e:
            st.error(f"❌ خطأ في تحميل البيانات: {e}")
            
    with tab3:
        st.markdown('<div class="section-header">➕ تسجيل طالب في كورسات جديدة</div>', unsafe_allow_html=True)

        # استخدام Session State للخصم الجديد
        if 'fixed_discount' not in st.session_state:
            st.session_state.fixed_discount = 0

        # اختيار الجامعة (فلتر)
        universities_df = get_universities()
        if universities_df.empty:
            st.warning("⚠️ لا توجد جامعات مضافة بعد. أضف جامعة أولاً.")
            st.stop()

        uni_name = st.selectbox("🏫 اختر الجامعة", universities_df["name"].tolist())
        uni_id = int(universities_df.loc[universities_df["name"] == uni_name, "id"].values[0])

        # جلب طلاب وكورسات هذه الجامعة
        students_df = get_students_by_university(uni_id)
        courses_df = get_courses_by_university(uni_id)

        # عرض اختيارات الطالب و الكورسات
        colA, colB = st.columns(2)
        with colA:
            st.subheader("🔎 ابحث عن طالب أو اختر من القائمة")
            selected_student_id = None
            phone_search = st.text_input("🔍 بحث برقم الموبايل (اختياري)")

            if phone_search.strip() != "":
                matched = students_df[students_df["phone"].astype(str).str.contains(phone_search.strip(), na=False)].reset_index(drop=True)
                if matched.empty:
                    st.info("لم يتم العثور على طالب بهذا الرقم داخل هذه الجامعة.")
                elif len(matched) == 1:
                    s = matched.iloc[0]
                    st.markdown(f"**موجود:** {s['name']} — {s['phone']}")
                    selected_student_id = int(s["id"])
                else:
                    choices = [(int(row["id"]), f"{row['name']} — {row['phone']}") for _, row in matched.iterrows()]
                    labels = [label for _id, label in choices]
                    pick = st.selectbox("اختر من النتائج:", labels)
                    selected_student_id = next(_id for _id, label in choices if label == pick)
            else:
                if students_df.empty:
                    st.info("لا يوجد طلاب في هذه الجامعة بعد.")
                    st.stop()
                else:
                    students_list = students_df.reset_index(drop=True)
                    choices = [(int(row["id"]), f"{row['name']} — {row['phone']}") for _, row in students_list.iterrows()]
                    labels = [label for _id, label in choices]
                    sel = st.selectbox("اختر الطالب من القائمة", labels)
                    selected_student_id = next(_id for _id, label in choices if label == sel)

            st.markdown("---")
            st.subheader("📚 اختر الكورسات")
            if courses_df.empty:
                st.info("لا توجد كورسات في هذه الجامعة بعد.")
                selected_course_ids = []
                course_choices = []
            else:
                course_choices = [(int(row["id"]), f"{row['name']} — {float(row.get('price') or 0):.2f}") for _, row in courses_df.iterrows()]
                course_labels = [label for _id, label in course_choices]
                selected_course_labels = st.multiselect("اختار كورسات", course_labels)
                label_to_id = {label: _id for _id, label in course_choices}
                selected_course_ids = [label_to_id[label] for label in selected_course_labels]

        with colB:
            st.subheader("💳 إعدادات الدفع")
            payment_option = st.selectbox("نوع الدفعة (ينطبق على كل الكورسات المحددة):",
                                        ["full", "before_mid", "after_mid", "one_session"],
                                        format_func=lambda x: {"full":"كورس كامل","before_mid":"جزء قبل الميد","after_mid":"جزء بعد الميد","one_session":"سيشن واحدة"}[x])

            payment_method = st.selectbox("طريقة الدفع:",
                                        ["cash","instapay","vodafone","card","other"],
                                        format_func=lambda x: {"cash":"نقداً","instapay":"InstaPay","vodafone":"Vodafone Cash","card":"بطاقة","other":"أخرى"}[x])
            
            # خيارات الخصم الجديدة (فقط لو full)
            if payment_option == "full" and selected_course_ids:
                st.markdown("### 🎟️ تطبيق خصم")
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("100 جنيه"):
                        st.session_state.fixed_discount = 100
                        st.rerun()
                    if st.button("200 جنيه"):
                        st.session_state.fixed_discount = 200
                        st.rerun()
                with col2:
                    if st.button("300 جنيه"):
                        st.session_state.fixed_discount = 300
                        st.rerun()
                    if st.button("400 جنيه"):
                        st.session_state.fixed_discount = 400
                        st.rerun()
                with col3:
                    if st.button("500 جنيه"):
                        st.session_state.fixed_discount = 500
                        st.rerun()
                    if st.button("No Discount"):
                        st.session_state.fixed_discount = 0
                        st.rerun()
                
                st.info(f"**الخصم الحالي: {st.session_state.fixed_discount} جنيه**")
            else:
                st.session_state.fixed_discount = 0

            # عرض تفاصيل المبلغ
            # عرض تفاصيل المبلغ
            total = 0.0
            course_totals = []  # list لتخزين total_fee لكل كورس
            details = []
            if selected_course_ids:
                for cid in selected_course_ids:
                    row = courses_df[courses_df["id"] == cid].iloc[0]
                    price = float(row.get("price") or 0)
                    before_mid = float(row.get("before_mid") or 0)
                    after_mid = float(row.get("after_mid") or 0)
                    session_price = float(row.get("session_price") or 0)

                    if payment_option == "full":
                        total_fee = price
                    elif payment_option == "before_mid":
                        total_fee = before_mid
                    elif payment_option == "after_mid":
                        total_fee = after_mid
                    elif payment_option == "one_session":
                        total_fee = session_price
                    else:
                        total_fee = price

                    course_totals.append(total_fee)
                    details.append((row["name"], total_fee))
                    total += total_fee
            else:
                st.info("اختر على الأقل كورس واحد لحساب المبلغ.")
                st.stop()

            # حساب الخصم الجديد
            discount_amount = st.session_state.fixed_discount
            final_total = total - discount_amount
            if final_total < 0:
                final_total = 0

            # تقسيم الخصم بالتساوي (لأن الأسعار متساوية)
            num_courses = len(selected_course_ids)
            discount_per_course = discount_amount / num_courses if num_courses > 0 else 0
        st.markdown("---")
        st.subheader(" 💰 تفاصيل المبلغ والكورسات")

        for i, (nm, total_fee) in enumerate(details):
            display_amount = total_fee - discount_per_course  # enrolled_fee للعرض
            if display_amount < 0:
                display_amount = 0  # منع سلبي (نادر)
            
            st.markdown(f"<div style='display:flex; justify-content:space-between; padding:5px 10px; border:1px solid #ddd; border-radius:8px; margin-bottom:5px; background-color:#f9f9f9;'>"
                        f"<strong>{nm}</strong>"
                        f"<span>{display_amount:.2f} جنيه (السعر الأصلي: {total_fee:.2f})</span>"
                        f"</div>", unsafe_allow_html=True)

        # كارت السعر قبل الخصم
        st.markdown(f"<div style='display:flex; justify-content:space-between; padding:10px; border:2px solid #9E9E9E; border-radius:8px; margin-top:10px; background-color:#f5f5f5;'>"
                    f"<strong>الإجمالي قبل الخصم</strong>"
                    f"<span>{total:.2f} جنيه</span>"
                    f"</div>", unsafe_allow_html=True)

        # كارت الخصم (لو موجود)
        if discount_amount > 0:
            st.markdown(f"<div style='display:flex; justify-content:space-between; padding:10px; border:2px solid #4CAF50; border-radius:8px; margin-top:10px; background-color:#e8f5e9;'>"
                        f"<strong>خصم مبلغ ثابت</strong>"
                        f"<span>تم خصم {discount_amount:.2f} جنيه</span>"
                        f"</div>", unsafe_allow_html=True)

        # كارت السعر النهائي
        st.markdown(f"<div style='display:flex; justify-content:space-between; padding:10px; border:2px solid #2196F3; border-radius:8px; margin-top:10px; background-color:#e3f2fd;'>"
                    f"<strong>الإجمالي المطلوب الآن</strong>"
                    f"<span>{final_total:.2f} جنيه</span>"
                    f"</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("💸 دفعة الآن (اختياري)")
        max_possible = final_total
        initial_payment = st.number_input("كم هتدفع الآن (مجموع لكل الكورسات المحددة)", min_value=0.0, value=0.0, step=50.0)
        if initial_payment > max_possible and max_possible > 0:
            st.warning(f"المبلغ المدخل أكبر من الإجمالي ({max_possible:.2f}) — سيتم استخدام الحد الأقصى تلقائيًا.")
            initial_payment = max_possible

        # تقسيم الدفعة الأولية بالتساوي
        base_payment = initial_payment / num_courses if num_courses > 0 else 0

        # عرض توزيع الدفعة الأولية
        if initial_payment > 0 and num_courses > 0:
            st.markdown("### توزيع الدفعة الأولية")
            for i, (nm, _) in enumerate(details):
                st.markdown(f"<div style='display:flex; justify-content:space-between; padding:5px 10px; border:1px solid #ddd; border-radius:8px; margin-bottom:5px;'>"
                            f"<strong>{nm}</strong>"
                            f"<span>{base_payment:.2f} جنيه</span>"
                            f"</div>", unsafe_allow_html=True)
        st.markdown("---")
        st.subheader("✅ تنفيذ التسجيل")

        if st.button("تسجيل ودفع الآن"):
            if selected_student_id is None:
                st.error("❌ اختر طالب أولاً.")
            elif not selected_course_ids:
                st.error("❌ اختر كورس واحد على الأقل.")
            else:
                        # نحسب كل التفاصيل هنا في الواجهة أولاً
                course_details = []
                
                for i, cid in enumerate(selected_course_ids):
                    row = courses_df[courses_df["id"] == cid].iloc[0]
                    
                    # حساب المبالغ لكل كورس
                    price = float(row.get("price") or 0)
                    before_mid = float(row.get("before_mid") or 0)
                    after_mid = float(row.get("after_mid") or 0)
                    session_price = float(row.get("session_price") or 0)

                    if payment_option == "full":
                        total_fee = price
                    elif payment_option == "before_mid":
                        total_fee = before_mid
                    elif payment_option == "after_mid":
                        total_fee = after_mid
                    elif payment_option == "one_session":
                        total_fee = session_price
                    else:
                        total_fee = price
                    
                    # حساب enrolled_fee (نفس الحساب اللي في الواجهة)
                    enrolled_fee = total_fee - discount_per_course
                    if enrolled_fee < 0 :
                        enrolled_fee = 0 
                    
                    # حساب الدفعة لهذا الكورس
                    payment_for_course = base_payment if initial_payment > 0 else 0
                    
                    course_details.append({
                        "course_id": cid,
                        "course_name": row.get("name", ""),
                        "total_fee": total_fee,
                        "enrolled_fee": enrolled_fee,
                        "discount": discount_per_course if payment_option == "full" else 0,
                        "payment_for_course": payment_for_course
                    })

                # ندخل البيانات للداتابيز
                results, err = register_student_courses_simple(
                    selected_student_id,
                    course_details,
                    payment_option,
                    payment_method
                )
                if err:
                    st.error(f"❌ خطأ أثناء التسجيل: {err}")
                else:
                    st.success("✅ تمت العملية بنجاح.")
                    # عرض النتائج
                    res_df = pd.DataFrame(results)
                    if not res_df.empty and "course_id" in res_df.columns:
                        res_df["course_name"] = res_df["course_id"].apply(
                            lambda x: (courses_df[courses_df["id"] == int(x)]["name"].values[0])
                            if (courses_df is not None and not courses_df.empty and int(x) in courses_df["id"].values)
                            else str(x)
                        )
                    col_order = ["course_name"]
                    for k in ["course_id", "action", "total_fee", "enrolled_fee", "discount", "paid_now", "amount_paid", "remaining"]:
                        if k in res_df.columns:
                            col_order.append(k)
                    st.dataframe(res_df[col_order].reset_index(drop=True), use_container_width=True)

                    # تحديث عرض حالة التسجيل من DB
                    try:
                        sc_resp = supabase.table("student_courses")\
                                .select("id, course_id, total_fee, enrolled_fee, amount_paid, remaining_amount, payment_option, discount")\
                                .eq("student_id", int(selected_student_id))\
                                .in_("course_id", selected_course_ids).execute()
                        sc_data = sc_resp.data or []
                        sc_df = pd.DataFrame(sc_data)
                        if not sc_df.empty:
                            sc_df["course_name"] = sc_df["course_id"].apply(
                                lambda x: (courses_df[courses_df["id"]==int(x)]["name"].values[0])
                                if (courses_df is not None and not courses_df.empty and int(x) in courses_df["id"].values)
                                else str(x)
                            )
                            display_cols = ["course_name", "course_id", "id", "total_fee", "enrolled_fee", "discount", "amount_paid", "remaining_amount", "payment_option"]
                            st.markdown("### حالة التسجيلات (محدثة من قاعدة البيانات)")
                            st.dataframe(
                                sc_df[display_cols].rename(columns={
                                    "id":"student_course_id",
                                    "remaining_amount":"remaining"
                                }).reset_index(drop=True),
                                use_container_width=True
                            )
                    except Exception as e:
                        st.warning(f"تم التسجيل لكن حدث خطأ عند جلب حالة التسجيل النهائية: {e}")

elif page == "تسجيل دفعة":
    st.markdown('<div class="main-header">🎓 إدارة الطلاب</div>', unsafe_allow_html=True)
    tab4, tab5 = st.tabs([ "💰 الطلاب اللي عليهم باقي", "💵 تسجيل دفعة جديدة "])
    
    with tab4:
        st.markdown('<div class="section-header">💰 الطلاب اللي عليهم باقي</div>', unsafe_allow_html=True)

        universities_df = get_universities()
        if universities_df.empty:
            st.warning("⚠️ لا توجد جامعات مضافة بعد. أضف جامعة أولاً.")
        else:
            # 🔥 إضافة key فريد
            uni_name = st.selectbox(
                "🏫 اختر الجامعة", 
                universities_df["name"].tolist(), 
                key="debt_uni_select"
            )
            uni_id = int(universities_df.loc[universities_df["name"] == uni_name, "id"].values[0])

            # جلب البيانات
            students_df = get_students_by_university(uni_id)
            courses_df = get_courses_by_university(uni_id)
            
            # جلب بيانات التسجيلات
            try:
                sc_resp = supabase.table("student_courses").select("*").execute()
                sc_data = sc_resp.data if sc_resp.data else []
            except Exception as e:
                st.error(f"❌ خطأ في جلب البيانات: {e}")
                sc_data = []
                
            sc_df = pd.DataFrame(sc_data)

            if sc_df.empty or students_df.empty or courses_df.empty:
                st.info("📭 لا توجد تسجيلات بعد.")
            else:
                # فلترة على الباقي
                sc_df = sc_df[sc_df["remaining_amount"] > 0]
                
                # فلترة بالجامعة
                sc_df = sc_df[sc_df["student_id"].isin(students_df["id"].values)]

                if sc_df.empty:
                    st.success("✅ لا يوجد طلاب عليهم باقي في هذه الجامعة.")
                else:
                    # دمج البيانات
                    merged = sc_df.merge(
                        students_df, 
                        left_on="student_id", 
                        right_on="id", 
                        suffixes=("", "_student")
                    ).merge(
                        courses_df, 
                        left_on="course_id", 
                        right_on="id", 
                        suffixes=("", "_course")
                    )

                    # فلاتر إضافية
                    col3, col4 = st.columns(2)
                    with col3:
                        # فلتر الكورسات
                        course_options = ["الكل"] + merged["name_course"].unique().tolist()
                        selected_course = st.selectbox(
                            "📚 اختر الكورس (اختياري)", 
                            course_options, 
                            key="debt_course_filter"
                        )
                    with col4:
                        # فلتر الطلاب
                        student_options = ["الكل"] + [f"{row['name']} — {row['phone']}" for _, row in merged.drop_duplicates("student_id").iterrows()]
                        selected_student = st.selectbox(
                            "👤 اختر الطالب (اختياري)", 
                            student_options, 
                            key="debt_student_filter"
                        )

                    # تطبيق الفلاتر
                    filtered_df = merged.copy()
                    if selected_course != "الكل":
                        filtered_df = filtered_df[filtered_df["name_course"] == selected_course]
                    if selected_student != "الكل":
                        student_name, student_phone = selected_student.split(" — ")
                        filtered_df = filtered_df[
                            (filtered_df["name"] == student_name) & 
                            (filtered_df["phone"] == student_phone)
                        ]

                    if filtered_df.empty:
                        st.info("📭 لا توجد بيانات بعد تطبيق الفلاتر.")
                    else:
                        # حساب الإحصائيات بعد الفلاتر
                        num_students = filtered_df["student_id"].nunique()
                        total_remaining = filtered_df["remaining_amount"].sum()

                        # عرض الكاردات
                        col1, col2 = st.columns(2)
                        with col1:
                            metric_card("👥 عدد الطلاب اللي باقي عليهم", num_students, "#2196F3")
                        with col2:
                            metric_card("💰 إجمالي المبلغ الباقي", f"{total_remaining:,.2f} جنيه", "#4CAF50")

                        st.markdown("---")

                        # عرض الجدول
                        display_df = filtered_df[[
                            "name", "phone", "name_course", "payment_option",
                            "amount_paid", "remaining_amount", "created_at"
                        ]].rename(columns={
                            "name": "👤 الطالب",
                            "phone": "📞 الموبايل",
                            "name_course": "📚 الكورس",
                            "payment_option": "💳 نوع التسجيل",
                            "amount_paid": "✅ المدفوع",
                            "remaining_amount": "⌛ الباقي",
                            "created_at": "📅 تاريخ التسجيل"
                        })

                        st.markdown("### 📋 تفاصيل الطلاب اللي عليهم باقي")
                        st.dataframe(display_df, use_container_width=True)


    with tab5:
        st.markdown('<div class="section-header">💵 تسجيل دفعة جديدة</div>', unsafe_allow_html=True)
        try:
            # جلب البيانات (كما عندك)
            students_data = supabase.table("students").select("*").execute().data or []
            universities_data = supabase.table("universities").select("*").execute().data or []
            sc_data = supabase.table("student_courses").select("*").execute().data or []
            courses_data = supabase.table("courses").select("*").execute().data or []

            if not students_data or not universities_data or not sc_data or not courses_data:
                st.info("⚠️ لا توجد بيانات كافية (جامعات/طلاب/تسجيلات/كورسات).")
                st.stop()

            students_df = pd.DataFrame(students_data)
            universities_df = pd.DataFrame(universities_data)
            sc_df = pd.DataFrame(sc_data)
            courses_df = pd.DataFrame(courses_data)

            # دمج كما سبق
            students_df = students_df.merge(
                universities_df,
                left_on="university_id",
                right_on="id",
                suffixes=("", "_univ")
            )

            merged_df = sc_df.merge(
                students_df,
                left_on="student_id",
                right_on="id",
                suffixes=("_sc", "_student")
            ).merge(
                courses_df,
                left_on="course_id",
                right_on="id",
                suffixes=("", "_course")
            )

            universities = ["الكل"] + merged_df["name_univ"].dropna().unique().tolist()
            selected_uni = st.selectbox("اختر الجامعة", universities, key="payment_uni_select")

            if selected_uni == "الكل":
                students_with_balance = merged_df[merged_df["remaining_amount"] > 0]
            else:
                students_with_balance = merged_df[
                    (merged_df["name_univ"] == selected_uni) &
                    (merged_df["remaining_amount"] > 0)
                ]

            if students_with_balance.empty:
                st.info("لا يوجد طلاب عليهم مبالغ مستحقة ✅")
                st.stop()

            student_options = {
                f"{row['name']} - {row['phone']}": row["student_id"]
                for _, row in students_with_balance.drop_duplicates("student_id").iterrows()
            }
            selected_student = st.selectbox("اختر الطالب", list(student_options.keys()), key="payment_student_select")
            student_id = student_options[selected_student]

            student_data = students_with_balance[students_with_balance["student_id"] == student_id].iloc[0]
            total_remaining = students_with_balance[students_with_balance["student_id"] == student_id]["remaining_amount"].sum()

            st.markdown("### 👤 بيانات الطالب")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**الاسم:** {student_data['name']}")
                st.markdown(f"**رقم الهاتف:** {student_data['phone']}")
            with col2:
                st.markdown(f"**الجامعة:** {student_data['name_univ']}")
                st.markdown(f"**الإجمالي المتبقي:** {total_remaining:,.2f} جنيه")

            student_courses = students_with_balance[students_with_balance["student_id"] == student_id].copy()
            # نرتب بحسب enrollment_date أو id لضمان ترتيب ثابت
            if "enrollment_date" in student_courses.columns:
                student_courses = student_courses.sort_values(by="enrollment_date")
            else:
                student_courses = student_courses.sort_values(by="id")

            display_df = student_courses[[
                "name_course", "total_fee", "enrolled_fee", "discount", "amount_paid", "remaining_amount"
            ]].rename(columns={
                "name_course": "الكورس",
                "total_fee": "السعر الأصلي",
                "enrolled_fee": "السعر بعد الخصم",
                "discount": "الخصم (جنيه)",
                "amount_paid": "المدفوع",
                "remaining_amount": "المتبقي"
            })
            st.markdown("### 📋 تفاصيل الكورسات")
            st.dataframe(display_df, use_container_width=True)

            # إدخال الدفعة
            st.markdown("### 💸 تسجيل الدفعة")
            col3, col4 = st.columns(2)
            with col3:
                amount_paid = st.number_input(
                    "المبلغ المدفوع",
                    min_value=0.0,
                    step=1.0,  # تغيير من 50 إلى 1 علشان نعرف ندخل أي مبلغ
                    max_value=float(total_remaining),
                    key="payment_amount"
                )
            with col4:
                payment_method = st.selectbox(
                    "طريقة الدفع",
                    ["cash", "instapay", "vodafone", "card", "other"],
                    format_func=lambda x: {
                        "cash": "نقدًا",
                        "instapay": "InstaPay",
                        "vodafone": "Vodafone Cash",
                        "card": "بطاقة",
                        "other": "أخرى"
                    }[x],
                    key="new_payment_method"
                )

            # إعداد قائمة كورسات من DB بترتيب ثابت للمُعالجة
            student_courses_db = supabase.table("student_courses")\
                .select("*")\
                .eq("student_id", student_id)\
                .order("enrollment_date", desc=False).execute().data or []
            # فلتر على المتبقي > 0
            student_courses_db = [c for c in student_courses_db if float(c.get("remaining_amount", 0) or 0) > 0]

            # if no courses with remaining, stop
            if not student_courses_db:
                st.info("لا يوجد مبالغ قابلة للدفع لهذا الطالب.")
                st.stop()

            # عرض التوزيع المقترح في الواجهة قبل التأكيد
            if amount_paid > 0:
                allocations, leftover = allocate_payment_sequential_exact(student_courses_db, amount_paid)
                st.markdown("### 📊 التوزيع المقترح للدفعة")
                total_allocated = 0.0
                for alloc in allocations:
                    if alloc["alloc"] > 0:
                        # get course name
                        course_name = next((c["course_id"] == alloc["course_id"] and c.get("course_name") for c in student_courses_db), None)
                        # safer: find name via merged df:
                        try:
                            course_row = student_courses[student_courses["course_id"] == alloc["course_id"]].iloc[0]
                            course_name = course_row["name_course"]
                        except Exception:
                            course_name = str(alloc["course_id"])
                        st.markdown(
                            f"<div style='display:flex; justify-content:space-between; padding:6px 10px; border:1px solid #ddd; border-radius:8px; margin-bottom:5px;'>"
                            f"<strong>{course_name}</strong>"
                            f"<span>{alloc['alloc']:.2f} جنيه</span>"
                            f"</div>", unsafe_allow_html=True
                        )
                        total_allocated += alloc["alloc"]
                if leftover > 0:
                    st.warning(f"تبقى مبلغ صغير لم يتم توزيعه: {leftover:.2f} جنيه. يمكنك تعديل المبلغ المدفوع أو السماح بتوزيع هذا الباقي يدوياً).")
                st.markdown(f"**الإجمالي المقترح للإيداع:** {total_allocated:.2f} جنيه")

            if st.button("💾 تسجيل الدفعة", key="register_payment_btn"):
                if amount_paid <= 0:
                    st.error("ادخل مبلغًا أكبر من صفر.")
                else:
                    with st.spinner("جاري تسجيل الدفعة..."):
                        try:
                            # إعادة جلب بيانات الكورسات من DB للتحديث (حالة concurrency)
                            student_courses_db = supabase.table("student_courses")\
                                .select("*")\
                                .eq("student_id", student_id)\
                                .order("enrollment_date", desc=False).execute().data or []
                            student_courses_db = [c for c in student_courses_db if float(c.get("remaining_amount", 0) or 0) > 0]
                            if not student_courses_db:
                                st.error("لا يوجد مبالغ متبقية لهذا الطالب.")
                                st.stop()

                            allocations, leftover = allocate_payment_sequential_exact(student_courses_db, amount_paid)
                            total_recorded = 0.0

                            for alloc in allocations:
                                cid = alloc["course_id"]
                                amount_for_this = alloc["alloc"]
                                if amount_for_this <= 0:
                                    continue

                                # find course record
                                course_rec = next((c for c in student_courses_db if c["id"] == cid), None)
                                if course_rec is None:
                                    continue

                                # جمع المبلغ الجديد مع السابق
                                new_paid = float(course_rec.get("amount_paid", 0) or 0) + amount_for_this
                                # التريجر هيحدث remaining_amount بناءً على enrolled_fee
                                new_remaining = max(float(course_rec.get("enrolled_fee", 0) or 0) - new_paid, 0.0)

                                # update student_courses
                                update_resp = supabase.table("student_courses").update({
                                    "amount_paid": new_paid,
                                    "remaining_amount": new_remaining,  # التريجر هيحسبها صح لو فيه تحديث
                                    "updated_at": datetime.datetime.utcnow().isoformat() + "Z"
                                }).eq("id", cid).execute()
                                _, update_err = _handle_response(update_resp)
                                if update_err:
                                    st.error(f"❌ خطأ أثناء تحديث كورس {cid}: {update_err}")
                                    continue

                                # insert payment record
                                payment_resp = supabase.table("payments").insert({
                                    "student_course_id": cid,
                                    "amount": amount_for_this,
                                    "payment_method": payment_method,
                                    "created_at": datetime.datetime.utcnow().isoformat() + "Z"
                                }).execute()
                                _, payment_err = _handle_response(payment_resp)
                                if payment_err:
                                    st.error(f"❌ خطأ أثناء تسجيل دفعة لكورس {cid}: {payment_err}")
                                    continue

                                total_recorded += amount_for_this

                            if total_recorded > 0:
                                st.success(f"✅ تم تسجيل دفعة بقيمة {total_recorded:.2f} جنيه بنجاح")
                                if leftover > 0:
                                    st.warning(f"تبقى مبلغ صغير لم يتم توزيعه: {leftover:.2f} جنيه.")
                                st.rerun()
                            else:
                                st.error("لم يتم تسجيل أي دفعات. تأكد من القيم وحاول مرة أخرى.")

                        except Exception as e:
                            st.error(f"❌ خطأ عام أثناء تسجيل الدفعة: {e}")

        except Exception as e:
            st.error(f"❌ خطأ في تحميل البيانات: {e}")


elif page == "Dashboard":
    st.markdown('<div class="main-header">Courses Dashboard</div>', unsafe_allow_html=True)

    # --- إحصائيات عامة على كل الجامعات ---
    resp_all = supabase.table("student_courses").select("id, student_id, total_fee, amount_paid, remaining_amount, created_at").execute()
    sc_all = pd.DataFrame(resp_all.data) if resp_all.data else pd.DataFrame()

    if not sc_all.empty:
        total_students_all = sc_all["student_id"].nunique()
        total_paid_all = sc_all["amount_paid"].sum()
        total_remaining_all = sc_all["remaining_amount"].sum()

        st.markdown("### 🌍 إحصائيات عامة لكل الجامعات")
        c1, c2, c3 = st.columns(3)
        with c1:
            metric_card("👥 إجمالي الطلاب", total_students_all, "#2196F3")
        with c2:
            metric_card("💰 إجمالي المدفوع", f"{total_paid_all:.2f}", "#4CAF50")
        with c3:
            metric_card("⌛ إجمالي المتبقي", f"{total_remaining_all:.2f}", "#FF9800")

    st.markdown("---")

    # --- فلتر الجامعة ---
    universities_df = get_universities()
    if universities_df.empty:
        st.warning("⚠️ لا توجد جامعات بعد.")
    else:
        uni_name = st.selectbox("🏫 اختر الجامعة", universities_df["name"].tolist())
        uni_id = int(universities_df.loc[universities_df["name"] == uni_name, "id"].values[0])

        # --- جلب بيانات ---
        students_df = get_students_by_university(uni_id)
        courses_df = get_courses_by_university(uni_id)

        resp = supabase.table("student_courses").select("*").execute()
        sc_df = pd.DataFrame(resp.data) if resp.data else pd.DataFrame()

        if sc_df.empty:
            st.info("لا توجد تسجيلات بعد لهذه الجامعة.")
        else:
            sc_df = sc_df[sc_df["student_id"].isin(students_df["id"])]

            # --- جلب بيانات الدفع لإضافة payment_method ---
            pay_resp = supabase.table("payments").select("student_course_id, payment_method, paid_at").execute()
            payments_df = pd.DataFrame(pay_resp.data) if pay_resp.data else pd.DataFrame()

            if not payments_df.empty:
                last_payments = payments_df.sort_values("paid_at").groupby("student_course_id").last().reset_index()
                sc_df = sc_df.merge(last_payments[["student_course_id", "payment_method"]],
                                    left_on="id", right_on="student_course_id", how="left")
            else:
                sc_df["payment_method"] = None

            # --- فلتر الكورسات ---
            course_choices = [(int(row["id"]), row["name"]) for _, row in courses_df.iterrows()]
            course_labels = [label for _id, label in course_choices]
            selected_course_labels = st.multiselect("🎯 فلتر حسب الكورس (اختياري)", course_labels)

            if selected_course_labels:
                label_to_id = {label: _id for _id, label in course_choices}
                selected_course_ids = [label_to_id[label] for label in selected_course_labels]
                sc_df = sc_df[sc_df["course_id"].isin(selected_course_ids)]

            # --- فلتر طريقة الدفع ---
            pay_methods = ["الكل"] + sc_df["payment_method"].dropna().unique().tolist()
            selected_pay_method = st.selectbox("💳 فلتر حسب طريقة الدفع (اختياري)", pay_methods)
            if selected_pay_method != "الكل":
                sc_df = sc_df[sc_df["payment_method"] == selected_pay_method]

            # --- فلتر التاريخ ---
            st.markdown("### 📅 فلترة حسب التاريخ")
            # تحويل العمود created_at إلى datetime باستخدام ISO8601
            sc_df["created_at"] = pd.to_datetime(sc_df["created_at"], format='ISO8601', errors='coerce')
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("من تاريخ", value=sc_df["created_at"].min().date() if not pd.isna(sc_df["created_at"].min()) else datetime.now().date())
            with col2:
                end_date = st.date_input("إلى تاريخ", value=sc_df["created_at"].max().date() if not pd.isna(sc_df["created_at"].max()) else datetime.now().date())

            # فلترة البيانات بناءً على التاريخ
            sc_df = sc_df[(sc_df["created_at"].dt.date >= start_date) & (sc_df["created_at"].dt.date <= end_date)]

            if sc_df.empty:
                st.warning("⚠️ لا توجد بيانات في الفترة المختارة")
            else:
                # --- إحصائيات الجامعة والفلاتر ---
                total_students_uni = sc_df["student_id"].nunique()
                total_paid_uni = sc_df["amount_paid"].sum()
                total_remaining_uni = sc_df["remaining_amount"].sum()

                st.markdown(f"### 🏫 إحصائيات جامعة {uni_name}")
                c1, c2, c3 = st.columns(3)
                with c1:
                    metric_card("👥 الطلاب المسجلين", total_students_uni, "#2196F3")
                with c2:
                    metric_card("💰 المدفوع", f"{total_paid_uni:.2f}", "#4CAF50")
                with c3:
                    metric_card("⌛ المتبقي", f"{total_remaining_uni:.2f}", "#FF9800")

                # 🔸 رسومات بيانية
                col1, col2 = st.columns(2)

                # توزيع طرق الدفع
                with col1:
                    pay_counts = sc_df["payment_method"].fillna("غير محدد").value_counts().reset_index()
                    pay_counts.columns = ["طريقة الدفع", "عدد"]
                    if not pay_counts.empty:
                        fig_payment = px.pie(
                            pay_counts,
                            names="طريقة الدفع",
                            values="عدد",
                            hole=0.4,
                            color_discrete_sequence=px.colors.qualitative.Set2,
                            title="💳 توزيع طرق الدفع"
                        )
                        st.plotly_chart(fig_payment, use_container_width=True)

                # أنواع التسجيل
                with col2:
                    option_counts = sc_df["payment_option"].fillna("غير محدد").value_counts().reset_index()
                    option_counts.columns = ["نوع التسجيل", "عدد"]
                    if not option_counts.empty:
                        fig_option = px.pie(
                            option_counts,
                            names="نوع التسجيل",
                            values="عدد",
                            hole=0.4,
                            color_discrete_sequence=px.colors.qualitative.Pastel,
                            title="📚 أنواع التسجيل"
                        )
                        st.plotly_chart(fig_option, use_container_width=True)

                # 👥 عدد الطلاب في كل كورس
                st.markdown("### 👥 عدد الطلاب في كل كورس")
                course_merge = sc_df.merge(courses_df, left_on="course_id", right_on="id", suffixes=("", "_course"))
                course_counts = course_merge["name"].value_counts().reset_index()
                course_counts.columns = ["الكورس", "عدد الطلاب"]
                if not course_counts.empty:
                    fig_courses = px.bar(
                        course_counts,
                        x="الكورس",
                        y="عدد الطلاب",
                        title="👨‍🎓 الطلاب في الكورسات",
                        text_auto=True,
                        color="عدد الطلاب",
                        color_continuous_scale="Blues"
                    )
                    fig_courses.update_layout(xaxis_title="", yaxis_title="عدد الطلاب")
                    st.plotly_chart(fig_courses, use_container_width=True)

                # 📈 رسم بياني خطي لعدد الطلاب المسجلين حسب التاريخ
                st.markdown("### 📈 عدد الطلاب المسجلين حسب التاريخ")
                time_group = st.selectbox("اختر الفترة الزمنية", ["يومي", "أسبوعي", "شهري"], key="time_group")
                sc_df["registration_date"] = sc_df["created_at"].dt.date
                if time_group == "أسبوعي":
                    sc_df["registration_date"] = sc_df["created_at"].dt.to_period("W").apply(lambda r: r.start_time.date())
                elif time_group == "شهري":
                    sc_df["registration_date"] = sc_df["created_at"].dt.to_period("M").apply(lambda r: r.start_time.date())

                students_per_date = sc_df.groupby("registration_date")["student_id"].nunique().reset_index()
                students_per_date.columns = ["التاريخ", "عدد الطلاب"]

                if not students_per_date.empty:
                    fig_students_over_time = px.line(
                        students_per_date,
                        x="التاريخ",
                        y="عدد الطلاب",
                        title="📈 عدد الطلاب المسجلين حسب التاريخ",
                        markers=True,
                        color_discrete_sequence=["#2196F3"]
                    )
                    fig_students_over_time.update_layout(
                        xaxis_title="التاريخ",
                        yaxis_title="عدد الطلاب",
                        xaxis_tickangle=45,
                        showlegend=False
                    )
                    st.plotly_chart(fig_students_over_time, use_container_width=True)
                else:
                    st.info("ℹ️ لا توجد بيانات تسجيلات متاحة للفترة المحددة.")

                # --- 📋 الجدول النهائي ---
                merged = sc_df.merge(students_df, left_on="student_id", right_on="id", suffixes=("", "_student"))
                merged = merged.merge(courses_df, left_on="course_id", right_on="id", suffixes=("", "_course"))

                display_df = merged[[
                    "name", "phone", "name_course", "payment_option",
                    "amount_paid", "remaining_amount", "payment_method", "created_at"
                ]].rename(columns={
                    "name": "👤 الطالب",
                    "phone": "📞 الموبايل",
                    "name_course": "📚 الكورس",
                    "payment_option": "💳 نوع التسجيل",
                    "amount_paid": "✅ المدفوع",
                    "remaining_amount": "⌛ الباقي",
                    "payment_method": "💳 طريقة الدفع الأخيرة",
                    "created_at": "📅 تاريخ التسجيل"
                })

                st.markdown("### 📋 تفاصيل التسجيلات")
                st.dataframe(display_df, use_container_width=True)

                # --- زر تصدير كـCSV ---
                csv = display_df.to_csv(index=False)
                st.download_button(
                    label="📥 تصدير كـCSV",
                    data=csv,
                    file_name=f"dashboard_data_{uni_name}_{start_date}_to_{end_date}.csv",
                    mime="text/csv"
                )
else:
    st.error("⚠️ الرجاء اختيار صفحة صالحة.")
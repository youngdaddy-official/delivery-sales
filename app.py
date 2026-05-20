import streamlit as st
import pandas as pd
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="매출/지출 통합 관리시스템", layout="wide")

# --- [로그인 체크 함수] ---
def check_password():
    if "password" not in st.secrets:
        st.error("⚠️ Streamlit Cloud의 Secrets 설정에 'password' 항목이 없습니다.")
        return False
    def password_entered():
        if str(st.session_state["password_input"]) == str(st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password_input"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center;'>🔒 시스템 접속 로그인</h2>", unsafe_allow_html=True)
        st.divider()
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.text_input("비밀번호를 입력하고 엔터를 치세요", type="password", on_change=password_entered, key="password_input")
        return False
    elif not st.session_state["password_correct"]:
        st.error("❌ 비밀번호가 일치하지 않습니다.")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.text_input("다시 입력해 주세요", type="password", on_change=password_entered, key="password_input")
        return False
    else:
        return True

# --- [본 프로그램 시작] ---
if check_password():
    
    # [디자인 & 번역 방지]
    st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"] { -webkit-text-size-adjust: none; unicode-bidi: isolate; }
    .notranslate { translate: no !important; }
    [data-testid="stWidgetLabel"] p { color: #31333F !important; font-weight: 600 !important; opacity: 1 !important; }
    button[data-testid="stNumberInputStepDown"], button[data-testid="stNumberInputStepUp"] { display: none !important; }
    input[type=number]::-webkit-inner-spin-button, input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none !important; margin: 0 !important; }
    input[type=number] { -moz-appearance: textfield !important; }
    div[data-testid="stNumberInputContainer"], div[data-testid="stTextInputRootElement"], div[data-testid="stSelectbox"] > div {
        background-color: white !important; border: 1px solid rgba(49, 51, 63, 0.2) !important; border-radius: 0.5rem !important;
    }
    input:disabled { background-color: white !important; color: #31333F !important; -webkit-text-fill-color: #31333F !important; opacity: 1 !important; border: 1px solid rgba(49, 51, 63, 0.1) !important; cursor: default !important; }
</style>
    """, unsafe_allow_html=True)
    st.markdown('<head><meta name="google" content="notranslate"></head>', unsafe_allow_html=True)

    # 로그아웃 버튼은 사이드바에 깔끔하게 보관
    if st.sidebar.button("로그아웃"):
        st.session_state["password_correct"] = False
        st.rerun()

    st.title("📊 매출 및 지출 통합 관리시스템")

    # 2. 구글 시트 연결
    conn = st.connection("gsheets", type=GSheetsConnection)

    # --- [자동 계산용 콜백 함수] ---
    def update_sales_tax():
        st.session_state.s_tax_val = int(st.session_state.s_fare_val * 0.1)

    # --- [데이터 로드 함수] ---
    def load_data(sheet_name):
        try:
            df = conn.read(worksheet=sheet_name, ttl="0")
            if df is None or df.empty:
                return pd.DataFrame()
            df = df.copy()
            date_col = "운송 일자" if sheet_name == "매출" else "지출 일자"
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce').dt.date
                df = df.dropna(subset=[date_col])
            
            num_cols = ['운임료', '수수료', '세액', '합계', '입금액', '미수금'] if sheet_name == "매출" else ['금액']
            for col in num_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            return df
        except:
            return pd.DataFrame()

    df_sales = load_data("매출")
    df_exp = load_data("지출")

    # --- [메인 섹션 1: 대시보드 요약] ---
    st.subheader("📈 통합 현황 요약")
    
    col_date, _ = st.columns([1, 1])
    with col_date:
        date_range = st.date_input("조회 기간", [date.today().replace(day=1), date.today()])
    
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_d, end_d = date_range
    else:
        start_d = end_d = date_range[0] if isinstance(date_range, (list, tuple)) else date_range

    f_sales = df_sales[(df_sales['운송 일자'] >= start_d) & (df_sales['운송 일자'] <= end_d)] if not df_sales.empty else pd.DataFrame

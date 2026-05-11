import streamlit as st
import pandas as pd
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="매출 통합 관리시스템", layout="wide")

# [디자인 끝판왕] 모든 라벨, 입력창, 비활성화 상태의 색상을 강제로 통일하는 CSS
st.markdown("""
    <style>
    /* 1. 모든 라벨(제목) 글자색 통일 - 자동 계산 필드 포함 */
    [data-testid="stWidgetLabel"] p {
        color: #31333F !important;
        font-weight: 500 !important;
        opacity: 1 !important;
    }

    /* 2. 모든 숫자 입력창의 -, + 버튼 및 브라우저 스피너 숨기기 */
    div[data-testid="stNumberInputContainer"] button {
        display: none !important;
    }
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button {
        -webkit-appearance: none !important;
        margin: 0 !important;
    }
    input[type=number] {
        -moz-appearance: textfield !important;
    }

    /* 3. 입력창 테두리 및 배경색 통일 */
    div[data-testid="stNumberInputContainer"], 
    div[data-testid="stTextInputRootElement"] {
        background-color: white !important;
        border: 1px solid rgba(49, 51, 63, 0.2) !important;
        border-radius: 0.5rem !important;
    }

    /* 4. 비활성화된(합계) 칸 디자인 강제 통일 - 배경색, 글자색, 흐림효과 제거 */
    input:disabled {
        background-color: white !important;
        color: #31333F !important; /* 내부 글자색 */
        -webkit-text-fill-color: #31333F !important; /* 사파리/크롬용 글자색 */
        opacity: 1 !important; /* 흐릿해지는 효과 완전히 제거 */
        cursor: default !important;
    }

    /* 사이드바 내부 비활성화 스타일 별도 강제 적용 */
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        color: #31333F !important;
    }
    section[data-testid="stSidebar"] input:disabled {
        background-color: white !important;
        color: #31333F !important;
        -webkit-text-fill-color: #31333F !important;
    }
    
    /* 버튼 위치 정렬 보정 */
    div[data-testid="stNumberInputContainer"] input {
        padding-right: 1rem !important;
        padding-left: 1rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# 메인 제목 변경
st.title("📊 매출 통합 관리시스템")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 데이터 불러오기 및 전처리
try:
    df_raw = conn.read(ttl="0")
    if df_raw.empty:
        df = pd.DataFrame(columns=["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"])
    else:
        df = df_raw.copy()
        if '운송 일자' in df.columns:
            df['운송 일자'] = pd.to_datetime(df['운송 일자'], errors='coerce')
            df = df.dropna(subset=['운송 일자'])
            df['운송 일자'] = df['운송 일자'].dt.date
        
        num_cols = ['공급가액', '세액', '합계', '입금액', '미수금']
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
except Exception as e:
    df = pd.DataFrame(columns=["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"])

# --- [사이드바: 신규 내역 등록] ---
with st.sidebar:
    st.header("➕ 신규 내역 등록")
    new_date = st.date_input("운송 일자", date.today())
    new_client = st.text_input("거래처명")
    
    new_supply = st.number_input("공급가액", min_value=0, value=0)
    new_tax_auto = int(new_supply * 0.1)
    new_tax = st.number_input("세액", min_value=0, value=new_tax_auto)
    new_total = new_supply + new_tax
    
    # [디자인 통합] 합계 금액 칸
    st.number_input("합계 금액 (자동)", value=new_total, disabled=True)
    
    new_status = st.selectbox("수금상태", ["미입금", "일부입금", "완납"])
    if new_status == "완납":
        new_dep = new_total
    elif new_status == "미입금":
        new_dep = 0
    else:
        new_dep = st.number_input("입금액", min_value=0, max_value=new_total)
    
    if st.button("내역 저장하기"):
        if new_client:
            new_entry = pd.DataFrame([{
                "운송 일자": new_date.strftime('%Y-%m-%d'), "거래처": new_client, "공급가액": int(new_supply),
                "세액": int(new_tax), "합계": int(new_total), "수금상태": new_status, "입금액": int(new_dep), "미수금": int(new_total - new_dep)
            }])
            final_data = pd.concat([df_raw, new_entry], ignore_index=True)
            conn.update(data=final_data[["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"]])
            st.success("✅ 저장 완료!")
            st.rerun()

# --- [메인 화면: 대시보드 및 상세 내역] ---
if not df.empty:
    st.subheader("📊 매출 현황 요약")
    col_f1, col_f2 = st.columns([1, 1])
    with col_f1:
        start_d, end_d = st.date_input("조회 기간 설정", [date.today().replace(day=1), date.today()])

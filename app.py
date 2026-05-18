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

    if st.sidebar.button("로그아웃"):
        st.session_state["password_correct"] = False
        st.rerun()

    st.title("📊 매출 및 지출 통합 관리시스템")

    # 2. 구글 시트 연결
    conn = st.connection("gsheets", type=GSheetsConnection)

    # --- [자동 계산용 콜백 함수] ---
    def update_sales_tax():
        # 공급가액이 입력되는 순간 세액을 10%로 강제 계산하여 세션에 보관합니다.
        st.session_state.s_tax_val = int(st.session_state.s_sup_val * 0.1)

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
            return df
        except:
            return pd.DataFrame()

    df_sales = load_data("매출")
    df_exp = load_data("지출")

    # --- [사이드바: 등록 메뉴] ---
    menu = st.sidebar.selectbox("📝 작업 선택", ["매출 등록", "지출 등록"])

    if menu == "매출 등록":
        st.sidebar.header("➕ 신규 매출 등록")
        s_date = st.sidebar.date_input("운송 일자", date.today())
        s_client = st.sidebar.text_input("거래처명")
        s_origin = st.sidebar.text_input("출발지 (시/군/구 단위 등)")
        s_dest = st.sidebar.text_input("도착지 (시/군/구 단위 등)")
        
        # [핵심 보완] 공급가액 입력 시 세액 계산 함수(on_change) 연동
        s_supply = st.sidebar.number_input("공급가액", min_value=0, key="s_sup_val", on_change=update_sales_tax)
        
        # 세액 변수 초기화 및 세션 상태 연결
        if 's_tax_val' not in st.session_state:
            st.session_state.s_tax_val = 0
        s_tax = st.sidebar.number_input("세액 (자동)", min_value=0, key="s_tax_val")
        
        s_total = s_supply + s_tax
        st.sidebar.number_input("합계 금액 (자동)", value=s_total, disabled=True)
        s_status = st.sidebar.selectbox("수금상태", ["미입금", "일부입금", "완납"])
        s_dep = s_total if s_status == "완납" else (0 if s_status == "미입금" else st.sidebar.number_input("입금액", min_value=0, max_value=s_total))

        if st.sidebar.button("매출 저장하기"):
            if s_client and s_origin and s_dest:
                new_s = pd.DataFrame([{
                    "운송 일자": s_date.strftime('%Y-%m-%d'), 
                    "거래처": s_client, 
                    "출발지": s_origin,
                    "도착지": s_dest,
                    "공급가액": int(s_supply), 
                    "세액": int(s_tax), 
                    "합계": int(s_total), 
                    "수금상태": s_status, 
                    "입금액": int(s_dep), 
                    "미수금": int(s_total - s_dep)
                }])
                conn.update(worksheet="매출", data=pd.concat([df_sales, new_s], ignore_index=True))
                st.sidebar.success("✅ 매출 저장 완료!")
                st.rerun()
            elif not s_client:
                st.sidebar.warning("⚠️ 거래처명을 입력해 주세요.")
            elif not s_origin:
                st.sidebar.warning("⚠️ 출발지를 입력해 주세요.")
            elif not s_dest:
                st.sidebar.warning("⚠️ 도착지를 입력해 주세요.")

    else:
        st.sidebar.header("💸 신규 지출 등록")
        e_date = st.sidebar.date_input("지출 일자", date.today())
        e_category = st.sidebar.selectbox("지출 항목", ["연료비", "통행료", "기타"])
        e_vendor = st.sidebar.text_input("지출처")
        e_amount = st.sidebar.number_input("지출 금액", min_value=0, value=0)
        e_memo = st.sidebar.text_input("비고 (선택)")

        if st.sidebar.button("지출 저장하기"):
            if e_amount > 0 and e_vendor:
                new_e = pd.DataFrame([{"지출 일자": e_date.strftime('%Y-%m-%d'), "지출 항목": e_category, "지출처": e_vendor, "금액": e_amount, "비고": e_memo}])
                conn.update(worksheet="지출", data=pd.concat([df_exp, new_e], ignore_index=True))
                st.sidebar.success("✅ 지출 저장 완료!")
                st.rerun()
            elif not e_vendor:
                st.sidebar.warning("⚠️ 지출처를 입력해 주세요.")

    # --- [메인 화면: 대시보드] ---
    st.subheader("📈 통합 현황 요약")
    cf1, cf2 = st.columns(2)
    with cf1:
        start_d, end_d = st.date_input("조회 기간", [date.today().replace(day=1), date.today()])

    f_sales = df_sales[(df_sales['운송 일자'] >= start_d) & (df_sales['운송 일자'] <= end_d)] if not df_sales.empty else pd.DataFrame()
    f_exp = df_exp[(df_exp['지출 일자'] >= start_d) & (df_exp['지출 일자'] <= end_d)] if not df_exp.empty else pd.DataFrame()

    total_s = int(f_sales['합계'].sum()) if not f_sales.empty else 0
    total_e = int(f_exp['금액'].sum()) if not f_exp.empty else 0
    profit = total_s - total_e

    m1, m2, m3 = st.columns(3)
    m1.metric("총 매출액", f"{total_s:,}원")
    m2.metric("총 지출액", f"{total_e:,}원")
    m3.metric("순이익 (매출-지출)", f"{profit:,}원", delta=f"{profit:,}원")

    tab1, tab2 = st.tabs(["🚛 매출 내역", "💰 지출 내역"])
    
    with tab1:
        if not f_sales.empty:
            st.dataframe(f_sales.sort_values("운송 일자", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("기간 내 매출 내역이 없습니다.")

    with tab2:
        if not f_exp.empty:
            st.dataframe(f_exp.sort_values("지출 일자", ascending=False), use_container_width=True, hide_index=True)
            st.write("📊 항목별 지출 요약")
            st.bar_chart(f_exp.groupby("지출 항목")["금액"].sum())
        else:
            st.info("기간 내 지출 내역이 없습니다.")

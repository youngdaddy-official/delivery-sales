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

    f_sales = df_sales[(df_sales['운송 일자'] >= start_d) & (df_sales['운송 일자'] <= end_d)] if not df_sales.empty else pd.DataFrame()
    f_exp = df_exp[(df_exp['지출 일자'] >= start_d) & (df_exp['지출 일자'] <= end_d)] if not df_exp.empty else pd.DataFrame()

    total_s = int(f_sales['합계'].sum()) if not f_sales.empty else 0
    total_e = int(f_exp['금액'].sum()) if not f_exp.empty else 0
    profit = total_s - total_e

    m1, m2, m3 = st.columns(3)
    m1.metric("총 매출액 (운임-수수료+세액)", f"{total_s:,}원")
    m2.metric("총 지출액 (연료비+통행료+기타)", f"{total_e:,}원")
    m3.metric("순수익 (매출 - 지출)", f"{profit:,}원", delta=f"{profit:,}원")

    # --- [메인 섹션 2: 한 페이지 좌우 입력 메뉴] ---
    st.divider()
    
    # 접었다 폈다 할 수 있는 대형 보관함(Expander)으로 감싸 화면을 더 깔끔하게 만듭니다.
    with st.expander("📝 신규 내역 등록 (이곳에서 매출과 지출을 바로 입력하세요)", expanded=True):
        col_sales, col_exp = st.columns(2)
        
        # 왼쪽 칸: 매출 등록
        with col_sales:
            st.markdown("### 🟢 신규 매출 등록")
            s_date = st.date_input("운송 일자", date.today(), key="in_s_date")
            s_client = st.text_input("거래처명", key="in_s_client")
            
            c_route1, c_route2 = st.columns(2)
            with c_route1: s_origin = st.text_input("출발지", key="in_s_ori")
            with c_route2: s_dest = st.text_input("도착지", key="in_s_des")
            
            c_money1, c_money2 = st.columns(2)
            with c_money1: s_fare = st.number_input("운임료", min_value=0, value=0, key="s_fare_val", on_change=update_sales_tax)
            with c_money2: s_fee = st.number_input("수수료", min_value=0, value=0, key="s_fee_val")
            
            if 's_tax_val' not in st.session_state:
                st.session_state.s_tax_val = 0
            
            c_money3, c_money4 = st.columns(2)
            with c_money3: s_tax = st.number_input("세액 (자동)", min_value=0, key="s_tax_val")
            s_total = s_fare - s_fee + s_tax
            with c_money4: st.number_input("매출 합계 (자동)", value=s_total, disabled=True, key="in_s_total")
            
            c_pay1, c_pay2 = st.columns(2)
            with c_pay1: s_pmethod = st.selectbox("결제방식", ["이체", "현금", "전자세금계산서", "카드"], key="in_s_pm")
            with c_pay2: s_status = st.selectbox("수금상태", ["미입금", "일부입금", "완납"], key="in_s_st")
            
            s_dep = s_total if s_status == "완납" else (0 if s_status == "미입금" else st.number_input("입금액", min_value=0, max_value=s_total, key="in_s_dep"))

            if st.button("💾 매출 저장하기", use_container_width=True):
                if s_client and s_origin and s_dest:
                    new_s = pd.DataFrame([{"운송 일자": s_date.strftime('%Y-%m-%d'), "거래처": s_client, "출발지": s_origin, "도착지": s_dest, "운임료": int(s_fare), "수수료": int(s_fee), "세액": int(s_tax), "합계": int(s_total), "결제방식": s_pmethod, "수금상태": s_status, "입금액": int(s_dep), "미수금": int(s_total - s_dep)}])
                    conn.update(worksheet="매출", data=pd.concat([df_sales, new_s], ignore_index=True))
                    st.success("✅ 매출 저장 완료!")
                    st.rerun()
                elif not s_client: st.sidebar.warning("⚠️ 거래처명을 입력해 주세요.")
                elif not s_origin: st.sidebar.warning("⚠️ 출발지를 입력해 주세요.")
                elif not s_dest: st.sidebar.warning("⚠️ 도착지를 입력해 주세요.")

        # 오른쪽 칸: 지출 등록
        with col_exp:
            st.markdown("### 🔴 신규 지출 등록")
            e_date = st.date_input("지출 일자", date.today(), key="in_e_date")
            e_category = st.selectbox("지출 항목", ["연료비", "통행료", "기타"], key="in_e_cat")
            e_vendor = st.text_input("지출처", key="in_e_ven")
            e_amount = st.number_input("지출 금액", min_value=0, value=0, key="in_e_amo")
            e_memo = st.text_input("비고 (선택)", key="in_e_mem")
            
            # 매출 입력창과 높이를 맞추기 위한 여백용 빈 칸
            st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)

            if st.button("💾 지출 저장하기", use_container_width=True):
                if e_amount > 0 and e_vendor:
                    new_e = pd.DataFrame([{"지출 일자": e_date.strftime('%Y-%m-%d'), "지출 항목": e_category, "지출처": e_vendor, "금액": e_amount, "비고": e_memo}])
                    conn.update(worksheet="지출", data=pd.concat([df_exp, new_e], ignore_index=True))
                    st.success("✅ 지출 저장 완료!")
                    st.rerun()
                elif not e_vendor:
                    st.error("⚠️ 지출처를 입력해 주세요.")

    # --- [메인 섹션 3: 통합 입출금 장부] ---
    st.divider()
    st.subheader("📝 통합 입출금 장부")

    t_sales = pd.DataFrame()
    if not f_sales.empty:
        t_sales = pd.DataFrame({
            "날짜": f_sales["운송 일자"],
            "구분": "🟢 매출",
            "거래처/지출처": f_sales["거래처"],
            "상세 내용 (경로/항목)": f_sales["출발지"].astype(str) + " ➡️ " + f_sales["도착지"].astype(str),
            "매출액(+)": f_sales["합계"],
            "지출액(-)": 0,
            "결제/수금 상태": f_sales["결제방식"].astype(str) + " (" + f_sales["수금상태"].astype(str) + ")",
            "비고": ""
        })

    t_exp = pd.DataFrame()
    if not f_exp.empty:
        t_exp = pd.DataFrame({
            "날짜": f_exp["지출 일자"],
            "구분": "🔴 지출",
            "거래처/지출처": f_exp["지출처"],
            "상세 내용 (경로/항목)": f_exp["지출 항목"],
            "매출액(+)": 0,
            "지출액(-)": f_exp["금액"],
            "결제/수금 상태": "-",
            "비고": f_exp["비고"].fillna("").astype(str)
        })

    if not t_sales.empty or not t_exp.empty:
        df_total = pd.concat([t_sales, t_exp], ignore_index=True)
        df_total = df_total.sort_values(by="날짜", ascending=False)
        
        st.dataframe(
            df_total, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "매출액(+)": st.column_config.NumberColumn(format="%d원"),
                "지출액(-)": st.column_config.NumberColumn(format="%d원")
            }
        )
    else:
        st.info("선택하신 기간 내에 입출금 내역이 없습니다.")

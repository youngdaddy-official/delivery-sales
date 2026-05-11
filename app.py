import streamlit as st
import pandas as pd
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정 (가장 먼저 실행되어야 함)
st.set_page_config(page_title="매출 통합 관리시스템", layout="wide")

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
        st.markdown("<h2 style='text-align: center;'>🔒 매출 통합 관리시스템 접속</h2>", unsafe_allow_html=True)
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
    
    # 2. 디자인 및 번역 방지 설정 (여기가 글자로 나오지 않도록 수정된 핵심 부분입니다)
    st.markdown("""
<style>
    /* 구글 번역 팝업 방지 및 디자인 통일 */
    html, body, [data-testid="stAppViewContainer"] {
        -webkit-text-size-adjust: none;
        unicode-bidi: isolate;
    }
    
    /* 모든 라벨(제목) 글자색 진하게 */
    [data-testid="stWidgetLabel"] p {
        color: #31333F !important;
        font-weight: 600 !important;
        opacity: 1 !important;
    }

    /* 숫자 입력창 옆의 -, + 버튼 숨기기 */
    button[data-testid="stNumberInputStepDown"], 
    button[data-testid="stNumberInputStepUp"] {
        display: none !important;
    }

    /* 숫자 입력창 내부 화살표(스피너) 제거 */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button {
        -webkit-appearance: none !important;
        margin: 0 !important;
    }
    input[type=number] {
        -moz-appearance: textfield !important;
    }

    /* 모든 입력창 배경을 흰색으로 고정 */
    div[data-testid="stNumberInputContainer"], 
    div[data-testid="stTextInputRootElement"], 
    div[data-testid="stSelectbox"] > div {
        background-color: white !important;
        border: 1px solid rgba(49, 51, 63, 0.2) !important;
        border-radius: 0.5rem !important;
    }

    /* 비활성화된(합계) 칸을 일반 칸과 똑같이 보이게 함 */
    input:disabled {
        background-color: white !important;
        color: #31333F !important;
        -webkit-text-fill-color: #31333F !important;
        opacity: 1 !important;
        border: 1px solid rgba(49, 51, 63, 0.1) !important;
        cursor: default !important;
    }

    /* 사이드바 글자색 보정 */
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        color: #31333F !important;
    }
</style>
    """, unsafe_allow_html=True)

    # 3. 번역 방지 메타 태그 추가
    st.markdown('<head><meta name="google" content="notranslate"></head>', unsafe_allow_html=True)

    # 로그아웃 버튼
    if st.sidebar.button("로그아웃"):
        st.session_state["password_correct"] = False
        st.rerun()

    st.title("📊 매출 통합 관리시스템")

    # 4. 구글 시트 연결
    conn = st.connection("gsheets", type=GSheetsConnection)

    # 자동 계산용 함수
    def update_new_tax():
        st.session_state.new_tax_val = int(st.session_state.new_supply_val * 0.1)
    def update_edit_tax():
        st.session_state.edit_tax_val = int(st.session_state.edit_supply_val * 0.1)

    # 5. 데이터 불러오기
    try:
        df_raw = conn.read(ttl="0")
        if df_raw is None or df_raw.empty:
            df = pd.DataFrame(columns=["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"])
        else:
            df = df_raw.copy()
            if '운송 일자' in df.columns:
                df['운송 일자'] = pd.to_datetime(df['운송 일자'], errors='coerce')
                df = df.dropna(subset=['운송 일자']).copy()
                df['운송 일자'] = df['운송 일자'].dt.date
            for col in ['공급가액', '세액', '합계', '입금액', '미수금']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    except Exception as e:
        df = pd.DataFrame(columns=["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"])

    # --- [사이드바: 등록] ---
    with st.sidebar:
        st.header("➕ 신규 내역 등록")
        new_date = st.date_input("운송 일자", date.today())
        new_client = st.text_input("거래처명")
        new_supply = st.number_input("공급가액", min_value=0, key="new_supply_val", on_change=update_new_tax)
        if 'new_tax_val' not in st.session_state: st.session_state.new_tax_val = 0
        new_tax = st.number_input("세액", min_value=0, key="new_tax_val")
        new_total = new_supply + new_tax
        st.number_input("합계 금액 (자동)", value=new_total, disabled=True)
        new_status = st.selectbox("수금상태", ["미입금", "일부입금", "완납"])
        new_dep = new_total if new_status == "완납" else (0 if new_status == "미입금" else st.number_input("입금액", min_value=0, max_value=new_total))
        
        if st.button("내역 저장하기"):
            if new_client:
                new_entry = pd.DataFrame([{"운송 일자": new_date.strftime('%Y-%m-%d'), "거래처": new_client, "공급가액": int(new_supply), "세액": int(new_tax), "합계": int(new_total), "수금상태": new_status, "입금액": int(new_dep), "미수금": int(new_total - new_dep)}])
                final_data = pd.concat([df_raw, new_entry], ignore_index=True)
                conn.update(data=final_data[["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"]])
                st.success("✅ 저장 완료!")
                st.rerun()

    # --- [메인 화면] ---
    if not df.empty:
        st.subheader("📊 매출 현황 요약")
        clients = ["전체"] + sorted([str(c) for c in df["거래처"].dropna().unique().tolist()])
        cf1, cf2 = st.columns(2)
        with cf1: start_d, end_d = st.date_input("조회 기간 설정", [date.today().replace(day=1), date.today()])
        with cf2: selected_client = st.selectbox("업체 필터", clients)
        f_df = df[(df['운송 일자'] >= start_d) & (df['운송 일자'] <= end_d)]
        if selected_client != "전체": f_df = f_df[f_df["거래처"] == selected_client]
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("건수", f"{len(f_df)}건")
        m2.metric("매출", f"{int(f_df['합계'].sum()):,}원")
        m3.metric("입금액", f"{int(f_df['입금액'].sum()):,}원")
        m4.metric("미수금", f"{int(f_df['미수금'].sum()):,}원", delta_color="inverse")
        
        st.divider()
        st.subheader("📑 상세 운송 내역")
        display_df = f_df.sort_values(by="운송 일자", ascending=False).copy()
        if not display_df.empty:
            display_df.insert(0, '번호', range(1, len(display_df) + 1))
            st.dataframe(display_df[["번호", "운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"]], use_container_width=True, hide_index=True)

        with st.expander("🛠️ 내역 수정 및 삭제 관리"):
            if not display_df.empty:
                target_no = st.selectbox("수정/삭제할 번호 선택", options=display_df['번호'].tolist())
                row_idx = display_df[display_df['번호'] == target_no].index[0]
                if f"init_{target_no}" not in st.session_state:
                    st.session_state.edit_supply_val = int(df.at[row_idx, '공급가액'])
                    st.session_state.edit_tax_val = int(df.at[row_idx, '세액'])
                    st.session_state[f"init_{target_no}"] = True
                ce1, ce2, ce3 = st.columns(3)
                with ce1:
                    e_date = ce1.date_input("날짜 수정", df.at[row_idx, '운송 일자'])
                    e_client = ce1.text_input("거래처 수정", df.at[row_idx, '거래처'])
                with ce2:
                    e_supply = ce2.number_input("공급가액 수정", min_value=0, key="edit_supply_val", on_change=update_edit_tax)
                    e_tax = ce2.number_input("세액 수정", min_value=0, key="edit_tax_val")
                with ce3:
                    e_status = ce3.selectbox("수금상태 수정", ["미입금", "일부입금", "완납"], index=["미입금", "일부입금", "완납"].index(df.at[row_idx, '수금상태']))
                    e_total = e_supply + e_tax
                    st.number_input("수정 후 합계 (자동)", value=e_total, disabled=True)
                    e_dep = e_total if e_status == "완납" else (0 if e_status == "미입금" else ce3.number_input("입금액 수정", value=int(df.at[row_idx, '입금액'])))
                
                b1, b2, _ = st.columns([1, 1, 3])
                if b1.button("💾 수정 적용"):
                    df.at[row_idx, '운송 일자'], df.at[row_idx, '거래처'] = e_date, e_client
                    df.at[row_idx, '공급가액'], df.at[row_idx, '세액'], df.at[row_idx, '합계'] = e_supply, e_tax, e_total
                    df.at[row_idx, '수금상태'], df.at[row_idx, '입금액'], df.at[row_idx, '미수금'] = e_status, e_dep, e_total - e_dep
                    conn.update(data=df[["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"]])
                    st.success("✅ 수정 완료!")
                    st.rerun()
                if b2.button("🗑️ 삭제", type="primary"):
                    conn.update(data=df.drop(row_idx)[["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"]])
                    st.rerun()
    else:
        st.info("💡 등록된 데이터가 없습니다.")

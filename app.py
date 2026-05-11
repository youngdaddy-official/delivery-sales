import streamlit as st
import pandas as pd
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="매출 통합 관리시스템", layout="wide")

# [디자인] 스피너 제거 및 모든 입력창 디자인 통일 CSS
st.markdown("""
    <style>
    /* 1. 모든 위젯 라벨(제목) 디자인 통일 */
    [data-testid="stWidgetLabel"] p {
        color: #31333F !important;
        font-weight: 600 !important;
        opacity: 1 !important;
    }

    /* 2. 모든 숫자 입력창의 -, + 버튼 및 스피너 완전 제거 */
    button[data-testid="stNumberInputStepDown"],
    button[data-testid="stNumberInputStepUp"],
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

    /* 3. 모든 입력창 디자인 통일 (배경: 흰색, 테두리 적용) */
    div[data-testid="stNumberInputContainer"], 
    div[data-testid="stTextInputRootElement"],
    div[data-testid="stSelectbox"] > div {
        background-color: white !important;
        border: 1px solid rgba(49, 51, 63, 0.2) !important;
        border-radius: 0.5rem !important;
    }

    /* 4. 비활성화된(합계) 칸을 일반 칸처럼 보이게 강제 설정 */
    input:disabled {
        background-color: white !important;
        color: #31333F !important;
        -webkit-text-fill-color: #31333F !important;
        opacity: 1 !important;
        border: none !important;
        cursor: default !important;
    }

    /* 사이드바 전용 스타일 */
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        color: #31333F !important;
    }
    section[data-testid="stSidebar"] input:disabled {
        background-color: white !important;
        color: #31333F !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 매출 통합 관리시스템")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# --- [계산 자동 연동 함수] ---
def update_new_tax():
    # 신규 등록 시 세액 자동 계산 (10%)
    st.session_state.new_tax_val = int(st.session_state.new_supply_val * 0.1)

def update_edit_tax():
    # 수정 시 세액 자동 계산 (10%)
    st.session_state.edit_tax_val = int(st.session_state.edit_supply_val * 0.1)

# 3. 데이터 불러오기
try:
    df_raw = conn.read(ttl="0")
    if df_raw is None or df_raw.empty:
        df = pd.DataFrame(columns=["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"])
    else:
        df = df_raw.copy()
        if '운송 일자' in df.columns:
            df['운송 일자'] = pd.to_datetime(df['운송 일자'], errors='coerce')
            df = df.dropna(subset=['운송 일자'])
            df['운송 일자'] = df['운송 일자'].dt.date
        for col in ['공급가액', '세액', '합계', '입금액', '미수금']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
except Exception as e:
    df = pd.DataFrame(columns=["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"])

# --- [사이드바: 신규 내역 등록] ---
with st.sidebar:
    st.header("➕ 신규 내역 등록")
    new_date = st.date_input("운송 일자", date.today())
    new_client = st.text_input("거래처명")
    
    # [핵심] on_change를 사용하여 공급가액 입력 시 세액을 즉시 업데이트
    new_supply = st.number_input("공급가액", min_value=0, key="new_supply_val", on_change=update_new_tax)
    
    # 세액 칸의 값을 세션 상태와 연결하여 자동 변경되게 함
    if 'new_tax_val' not in st.session_state: st.session_state.new_tax_val = 0
    new_tax = st.number_input("세액", min_value=0, key="new_tax_val")
    
    new_total = new_supply + new_tax
    st.number_input("합계 금액 (자동)", value=new_total, disabled=True)
    
    new_status = st.selectbox("수금상태", ["미입금", "일부입금", "완납"])
    if new_status == "완납": new_dep = new_total
    elif new_status == "미입금": new_dep = 0
    else: new_dep = st.number_input("입금액", min_value=0, max_value=new_total)
    
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

# --- [메인 화면: 대시보드] ---
if not df.empty:
    st.subheader("📊 매출 현황 요약")
    clients = ["전체"] + sorted([str(c) for c in df["거래처"].dropna().unique().tolist()])
    cf1, cf2 = st.columns(2)
    with cf1: start_d, end_d = st.date_input("조회 기간 설정", [date.today().replace(day=1), date.today()])
    with cf2: selected_client = st.selectbox("업체 필터", clients)

    f_df = df[(df['운송 일자'] >= start_d) & (df['운송 일자'] <= end_d)]
    if selected_client != "전체": f_df = f_df[f_df["거래처"] == selected_client]

    m1, m2, m3, m4 = st.columns(4)
    p = f"[{selected_client}] " if selected_client != "전체" else "[전체] "
    m1.metric(f"{p}건수", f"{len(f_df)}건")
    m2.metric(f"{p}매출", f"{int(f_df['합계'].sum()):,}원")
    m3.metric(f"{p}입금액", f"{int(f_df['입금액'].sum()):,}원")
    m4.metric(f"{p}미수금", f"{int(f_df['미수금'].sum()):,}원", delta_color="inverse")
    
    st.divider()

    st.subheader("📑 상세 운송 내역")
    display_df = f_df.sort_values(by="운송 일자", ascending=False).copy()
    if not display_df.empty:
        display_df.insert(0, '번호', range(1, len(display_df) + 1))
        st.dataframe(display_df[["번호", "운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"]], use_container_width=True, hide_index=True)

    # [수정 메뉴 핵심 보완]
    st.divider()
    with st.expander("🛠️ 내역 수정 및 삭제 관리"):
        if not display_df.empty:
            target_no = st.selectbox("수정/삭제할 번호 선택", options=display_df['번호'].tolist())
            row_idx = display_df[display_df['번호'] == target_no].index[0]
            
            # 수정을 위해 선택된 행의 데이터를 세션에 초기화 (처음 한 번만)
            if f"init_{target_no}" not in st.session_state:
                st.session_state.edit_supply_val = int(df.at[row_idx, '공급가액'])
                st.session_state.edit_tax_val = int(df.at[row_idx, '세액'])
                st.session_state[f"init_{target_no}"] = True

            ce1, ce2, ce3 = st.columns(3)
            with ce1:
                e_date = ce1.date_input("날짜 수정", df.at[row_idx, '운송 일자'])
                e_client = ce1.text_input("거래처 수정", df.at[row_idx, '거래처'])
            with ce2:
                # [수정 시에도 연동] 공급가액을 고치면 세액이 즉시 반영됨
                e_supply = ce2.number_input("공급가액 수정", min_value=0, key="edit_supply_val", on_change=update_edit_tax)
                e_tax = ce2.number_input("세액 수정", min_value=0, key="edit_tax_val")
            with ce3:
                e_status = ce3.selectbox("수금상태 수정", ["미입금", "일부입금", "완납"], 
                                         index=["미입금", "일부입금", "완납"].index(df.at[row_idx, '수금상태']))
                e_total = e_supply + e_tax
                st.number_input("수정 후 합계 (자동)", value=e_total, disabled=True)
                
                if e_status == "완납": e_dep = e_total
                elif e_status == "미입금": e_dep = 0
                else: e_dep = ce3.number_input("입금액 수정", value=int(df.at[row_idx, '입금액']))

            b1, b2, _ = st.columns([1, 1, 3])
            if b1.button("💾 이 내용으로 수정 적용"):
                df.at[row_idx, '운송 일자'] = e_date
                df.at[row_idx, '거래처'] = e_client
                df.at[row_idx, '공급가액'], df.at[row_idx, '세액'], df.at[row_idx, '합계'] = e_supply, e_tax, e_total
                df.at[row_idx, '수금상태'], df.at[row_idx, '입금액'], df.at[row_idx, '미수금'] = e_status, e_dep, e_total - e_dep
                conn.update(data=df[["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"]])
                st.success("✅ 수정 완료!")
                st.rerun()

            if b2.button("🗑️ 해당 내역 삭제", type="primary"):
                df_del = df.drop(row_idx)
                conn.update(data=df_del[["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"]])
                st.rerun()
else:
    st.info("💡 등록된 데이터가 없습니다.")

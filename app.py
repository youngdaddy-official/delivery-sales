import streamlit as st
import pandas as pd
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="매출 통합 관리시스템", layout="wide")

# [디자인 완결] 모든 입력칸과 라벨의 색상/디자인을 강제로 일치시키는 초강력 CSS
st.markdown("""
    <style>
    /* 1. 모든 위젯의 제목(라벨) 색상을 진한 검정으로 고정 */
    [data-testid="stWidgetLabel"] p {
        color: #31333F !important;
        font-weight: 600 !important;
        opacity: 1 !important;
    }

    /* 2. 숫자 입력창의 -, + 버튼 및 브라우저 스피너 완전 제거 */
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

    /* 3. 비활성화된(합계) 칸 디자인을 일반 칸과 100% 동일하게 강제 고정 */
    input:disabled {
        background-color: white !important;
        color: #31333F !important;
        -webkit-text-fill-color: #31333F !important;
        opacity: 1 !important;
        border: 1px solid rgba(49, 51, 63, 0.2) !important;
        cursor: default !important;
    }

    /* 4. 입력창 테두리와 배경색 통일 */
    div[data-testid="stNumberInputContainer"], 
    div[data-testid="stTextInputRootElement"],
    div[data-testid="stSelectbox"] {
        background-color: white !important;
        border-radius: 0.5rem !important;
    }
    
    /* 사이드바 글자색 강제 보정 */
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        color: #31333F !important;
    }
    </style>
""", unsafe_allow_html=True)

# 프로그램 명칭 변경
st.title("📊 매출 통합 관리시스템")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 데이터 불러오기 및 안전한 전처리
try:
    df_raw = conn.read(ttl="0")
    if df_raw is None or df_raw.empty:
        df = pd.DataFrame(columns=["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"])
    else:
        df = df_raw.copy()
        # 컬럼 이름 확인 및 날짜 변환
        if '운송 일자' in df.columns:
            df['운송 일자'] = pd.to_datetime(df['운송 일자'], errors='coerce')
            df = df.dropna(subset=['운송 일자'])
            df['운송 일자'] = df['운송 일자'].dt.date
        
        # 숫자형 변환
        for col in ['공급가액', '세액', '합계', '입금액', '미수금']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    df = pd.DataFrame(columns=["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"])

# --- [사이드바: 신규 내역 등록] ---
with st.sidebar:
    st.header("➕ 신규 내역 등록")
    new_date = st.date_input("운송 일자", date.today(), key="sb_date")
    new_client = st.text_input("거래처명", key="sb_client")
    
    new_supply = st.number_input("공급가액", min_value=0, value=0, key="sb_supply")
    new_tax_auto = int(new_supply * 0.1)
    new_tax = st.number_input("세액", min_value=0, value=new_tax_auto, key="sb_tax")
    new_total = new_supply + new_tax
    
    # 합계창 디자인 통일
    st.number_input("합계 금액 (자동)", value=new_total, disabled=True, key="sb_total")
    
    new_status = st.selectbox("수금상태", ["미입금", "일부입금", "완납"], key="sb_status")
    if new_status == "완납":
        new_dep = new_total
    elif new_status == "미입금":
        new_dep = 0
    else:
        new_dep = st.number_input("입금액", min_value=0, max_value=new_total, key="sb_dep")
    
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
    st.subheader("📑 매출 현황 요약")
    
    # [오류 방지용] 업체 필터 명단 만들기 (비어있는 값 제외)
    raw_clients = df["거래처"].dropna().unique().tolist()
    client_list = ["전체"] + sorted([str(c) for c in raw_clients])

    col_f1, col_f2 = st.columns([1, 1])
    with col_f1:
        start_d, end_d = st.date_input("조회 기간 설정", [date.today().replace(day=1), date.today()])
    with col_f2:
        selected_client = st.selectbox("업체 필터", client_list)

    # 필터 적용
    f_df = df[(df['운송 일자'] >= start_d) & (df['운송 일자'] <= end_d)]
    if selected_client != "전체":
        f_df = f_df[f_df["거래처"] == selected_client]

    # 지표 카드
    m1, m2, m3, m4 = st.columns(4)
    p = f"[{selected_client}] " if selected_client != "전체" else "[전체] "
    m1.metric(f"{p}운송 건수", f"{len(f_df)}건")
    m2.metric(f"{p}매출 합계", f"{int(f_df['합계'].sum()):,}원")
    m3.metric(f"{p}입금액", f"{int(f_df['입금액'].sum()):,}원")
    m4.metric(f"{p}미수금 잔액", f"{int(f_df['미수금'].sum()):,}원", delta_color="inverse")
    
    st.divider()

    # 상세 내역 표
    st.subheader("📑 상세 운송 장부")
    display_df = f_df.sort_values(by="운송 일자", ascending=False).copy()
    if not display_df.empty:
        display_df.insert(0, '번호', range(1, len(display_df) + 1))
        st.dataframe(display_df[["번호", "운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"]], 
                     use_container_width=True, hide_index=True)

    # 수정 및 삭제
    with st.expander("🛠️ 내역 수정 및 삭제 관리"):
        if not display_df.empty:
            target_no = st.selectbox("수정/삭제할 번호 선택", options=display_df['번호'].tolist(), key="edit_no")
            row_idx = display_df[display_df['번호'] == target_no].index[0]
            
            ce1, ce2, ce3 = st.columns(3)
            with ce1:
                e_date = ce1.date_input("날짜 수정", df.at[row_idx, '운송 일자'], key="e_date")
                e_client = ce1.text_input("거래처 수정", df.at[row_idx, '거래처'], key="e_client")
            with ce2:
                e_supply = ce2.number_input("공급가액 수정", value=int(df.at[row_idx, '공급가액']), key="e_supply")
                e_tax = ce2.number_input("세액 수정", value=int(e_supply * 0.1), key="e_tax")
            with ce3:
                e_status = ce3.selectbox("수금상태 수정", ["미입금", "일부입금", "완납"], 
                                         index=["미입금", "일부입금", "완납"].index(df.at[row_idx, '수금상태']), key="e_status")
                e_total = e_supply + e_tax
                st.number_input("수정 후 합계 (자동)", value=e_total, disabled=True, key="e_total")
                
                if e_status == "완납": e_dep = e_total
                elif e_status == "미입금": e_dep = 0
                else: e_dep = ce3.number_input("입금액 수정", value=int(df.at[row_idx, '입금액']), key="e_dep")

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
    st.info("💡 등록된 데이터가 없습니다. 왼쪽 사이드바에서 첫 매출을 등록해 보세요!")
    # 데이터가 있는데 안 나오는 경우를 대비해 원본 데이터를 확인하는 창을 숨겨둡니다.
    with st.expander("🔍 데이터 불러오기 문제 해결"):
        st.write("현재 구글 시트에서 가져온 원본 데이터입니다.")
        st.dataframe(df_raw)

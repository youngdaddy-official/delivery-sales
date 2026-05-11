import streamlit as st
import pandas as pd
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="용달 매출 통합 관리 시스템", layout="wide")

# [디자인 끝판왕] 모든 숫자 입력창의 버튼을 없애고, 비활성화된 합계 칸의 디자인을 일반 칸과 완전히 똑같이 만듭니다.
st.markdown("""
    <style>
    /* 1. 숫자 입력창의 -, + 버튼 강제 박멸 */
    div[data-testid="stNumberInputContainer"] button {
        display: none !important;
    }
    
    /* 2. 버튼이 사라진 자리를 꽉 채우기 */
    div[data-testid="stNumberInputContainer"] input {
        padding-right: 1rem !important;
        padding-left: 1rem !important;
    }

    /* 3. 브라우저 기본 화살표 숨기기 */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button {
        -webkit-appearance: none !important;
        margin: 0 !important;
    }
    input[type=number] {
        -moz-appearance: textfield !important;
    }

    /* 4. 비활성화(합계) 칸 디자인 강제 통일 (흰색 배경, 진한 글자색) */
    div[data-testid="stNumberInputContainer"] {
        background-color: white !important;
        border: 1px solid rgba(49, 51, 63, 0.2) !important;
        border-radius: 0.5rem !important;
    }

    input:disabled {
        background-color: white !important;
        -webkit-text-fill-color: #31333F !important; /* 글자색 강제 지정 */
        color: #31333F !important;
        opacity: 1 !important; /* 투명도 제거 */
    }

    /* 사이드바와 메인 화면 모두에 적용되도록 설정 */
    .stSidebar input:disabled {
        background-color: white !important;
        color: #31333F !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🚛 용달 매출 및 업체별 맞춤 통계")

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
    
    # [디자인 통일] 사이드바 합계 칸
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
            st.success("✅ 저장되었습니다!")
            st.rerun()

# --- [메인 화면: 대시보드 및 상세 내역] ---
if not df.empty:
    st.subheader("📊 매출 요약 및 분석")
    col_f1, col_f2 = st.columns([1, 1])
    with col_f1:
        start_d, end_d = st.date_input("조회 기간 설정", [date.today().replace(day=1), date.today()])
    with col_f2:
        client_options = ["전체"] + sorted(df["거래처"].unique().tolist())
        selected_client = st.selectbox("조회할 업체 선택", client_options)

    f_df = df[(df['운송 일자'] >= start_d) & (df['운송 일자'] <= end_d)]
    if selected_client != "전체":
        f_df = f_df[f_df["거래처"] == selected_client]

    m1, m2, m3, m4 = st.columns(4)
    prefix = f"[{selected_client}] " if selected_client != "전체" else "[전체] "
    m1.metric(f"{prefix}운송 건수", f"{len(f_df)}건")
    m2.metric(f"{prefix}매출 합계", f"{int(f_df['합계'].sum()):,}원")
    m3.metric(f"{prefix}입금액", f"{int(f_df['입금액'].sum()):,}원")
    m4.metric(f"{prefix}미수금 잔액", f"{int(f_df['미수금'].sum()):,}원", delta_color="inverse")
    
    st.divider()

    # 상세 내역 표
    st.subheader("📑 상세 운송 내역")
    display_df = f_df.sort_values(by="운송 일자", ascending=False).copy()
    if not display_df.empty:
        display_df.insert(0, '번호', range(1, len(display_df) + 1))
        st.dataframe(display_df[["번호", "운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"]], 
                     use_container_width=True, hide_index=True)

    # [수정 및 삭제 기능]
    st.divider()
    with st.expander("🛠️ 상세 내역 수정 및 삭제"):
        if not display_df.empty:
            target_no = st.selectbox("수정/삭제할 내역의 '번호' 선택", options=display_df['번호'].tolist())
            row_idx = display_df[display_df['번호'] == target_no].index[0]
            
            col_e1, col_e2, col_e3 = st.columns(3)
            with col_e1:
                edit_date = st.date_input("날짜 수정", df.at[row_idx, '운송 일자'])
                edit_client = st.text_input("거래처 수정", df.at[row_idx, '거래처'])
            with col_e2:
                edit_supply = st.number_input("공급가액 수정", value=int(df.at[row_idx, '공급가액']))
                auto_tax_edit = int(edit_supply * 0.1)
                edit_tax = st.number_input("세액 수정", value=auto_tax_edit)
            with col_e3:
                edit_status = st.selectbox("수금상태 수정", ["미입금", "일부입금", "완납"], 
                                           index=["미입금", "일부입금", "완납"].index(df.at[row_idx, '수금상태']))
                
                edit_total = edit_supply + edit_tax
                # [디자인 통일] 수정 메뉴 합계 칸
                st.number_input("수정 후 합계 (자동)", value=edit_total, disabled=True)
                
                if edit_status == "완납":
                    edit_dep = edit_total
                elif edit_status == "미입금":
                    edit_dep = 0
                else:
                    edit_dep = st.number_input("입금액 수정", value=int(df.at[row_idx, '입금액']))

            btn_col1, btn_col2, _ = st.columns([1, 1, 3])
            
            if btn_col1.button("💾 이 내용으로 수정 적용", type="secondary"):
                df.at[row_idx, '운송 일자'] = edit_date
                df.at[row_idx, '거래처'] = edit_client
                df.at[row_idx, '공급가액'] = int(edit_supply)
                df.at[row_idx, '세액'] = int(edit_tax)
                df.at[row_idx, '합계'] = int(edit_total)
                df.at[row_idx, '수금상태'] = edit_status
                df.at[row_idx, '입금액'] = int(edit_dep)
                df.at[row_idx, '미수금'] = int(edit_total - edit_dep)
                
                conn.update(data=df[["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"]])
                st.success("✅ 수정 완료!")
                st.rerun()

            if btn_col2.button("🗑️ 해당 내역 완전히 삭제", type="primary"):
                df_deleted = df.drop(row_idx)
                conn.update(data=df_deleted[["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"]])
                st.warning("⚠️ 삭제되었습니다.")
                st.rerun()
else:
    st.info("💡 등록된 데이터가 없습니다.")

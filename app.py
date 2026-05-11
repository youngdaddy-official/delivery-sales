import streamlit as st
import pandas as pd
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="용달 매출/통계 관리", layout="wide")
st.title("🚛 용달 매출 및 업체별 운송 통계")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 데이터 불러오기 및 전처리
try:
    df = conn.read(ttl="0")
    if '운송 일자' in df.columns:
        df['운송 일자'] = pd.to_datetime(df['운송 일자'], errors='coerce').dt.date
    
    # 숫자형 변환 및 소수점 제거
    num_cols = ['공급가액', '세액', '합계', '입금액', '미수금']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
except Exception as e:
    df = pd.DataFrame(columns=["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"])

# --- [사이드바: 신규 등록] ---
with st.sidebar:
    st.header("➕ 신규 내역 등록")
    input_date = st.date_input("운송 일자", date.today())
    client_name = st.text_input("거래처명")
    supply_val = st.number_input("공급가액", min_value=0, step=1000)
    tax_val = st.number_input("세액", min_value=0, value=int(supply_val * 0.1))
    total_val = st.number_input("합계", min_value=0, value=supply_val + tax_val)
    status = st.selectbox("수금상태", ["미입금", "일부입금", "완납"])
    dep_amt = total_val if status == "완납" else (0 if status == "미입금" else st.number_input("입금액", min_value=0))
    
    if st.button("저장하기"):
        if client_name:
            new_entry = pd.DataFrame([{"운송 일자": input_date.strftime('%Y-%m-%d'), "거래처": client_name, "공급가액": int(supply_val), "세액": int(tax_val), "합계": int(total_val), "수금상태": status, "입금액": int(dep_amt), "미수금": int(total_val - dep_amt)}])
            updated_df = pd.concat([df, new_entry], ignore_index=True)
            conn.update(data=updated_df[["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"]])
            st.success("저장 완료!")
            st.rerun()

# --- [메인 화면: 대시보드] ---
if not df.empty:
    st.subheader("📊 기간별/업체별 요약")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_d, end_d = st.date_input("조회 기간", [date.today().replace(day=1), date.today()])
    
    # 기간 필터링
    f_df = df[(df['운송 일자'] >= start_d) & (df['운송 일자'] <= end_d)]
    
    # 상단 지표
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("총 운송 건수", f"{len(f_df)}건")
    m2.metric("선택 기간 매출", f"{int(f_df['합계'].sum()):,}원")
    m3.metric("총 입금액", f"{int(f_df['입금액'].sum()):,}원")
    m4.metric("미수금 잔액", f"{int(f_df['미수금'].sum()):,}원", delta_color="inverse")
    
    st.divider()

    # 업체별 통계 (건수, 합계)
    st.subheader("🏢 업체별 운송 현황 (조회 기간 기준)")
    if not f_df.empty:
        # 업체별로 그룹화하여 건수와 합계 계산
        client_stats = f_df.groupby('거래처').agg(
            운송건수=('거래처', 'size'),
            매출합계=('합계', 'sum'),
            미수금합계=('미수금', 'sum')
        ).reset_index().sort_values(by='운송건수', ascending=False)
        
        # 소수점 제거 및 콤마 표시
        client_stats['매출합계'] = client_stats['매출합계'].apply(lambda x: f"{int(x):,}원")
        client_stats['미수금합계'] = client_stats['미수금합계'].apply(lambda x: f"{int(x):,}원")
        
        st.dataframe(client_stats, use_container_width=True, hide_index=True)
    
    st.divider()

    # 상세 내역 (연번 추가)
    st.subheader("📑 상세 운송 내역")
    display_df = f_df.sort_values(by="운송 일자", ascending=False).copy()
    
    #

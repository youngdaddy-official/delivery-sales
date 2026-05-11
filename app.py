import streamlit as st
import pandas as pd
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="용달 매출 통합 관리 시스템", layout="wide")
st.title("🚛 용달 매출 및 업체별 운송 통계")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 데이터 불러오기 및 전처리
try:
    df_raw = conn.read(ttl="0")
    
    if df_raw.empty:
        df = pd.DataFrame(columns=["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"])
    else:
        # 데이터가 있을 경우 날짜 및 숫자 전처리
        df = df_raw.copy()
        if '운송 일자' in df.columns:
            df['운송 일자'] = pd.to_datetime(df['운송 일자'], errors='coerce')
            df = df.dropna(subset=['운송 일자']) # 날짜 없는 행 제외
            df['운송 일자'] = df['운송 일자'].dt.date
        
        # 모든 금액 컬럼을 정수(Int)로 변환
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
    
    if st.button("내역 저장하기"):
        if client_name:
            new_entry = pd.DataFrame([{
                "운송 일자": input_date.strftime('%Y-%m-%d'),
                "거래처": client_name,
                "공급가액": int(supply_val),
                "세액": int(tax_val),
                "합계": int(total_val),
                "수금상태": status,
                "입금액": int(dep_amt),
                "미수금": int(total_val - dep_amt)
            }])
            # 구글 시트에 업데이트
            final_data = pd.concat([df_raw, new_entry], ignore_index=True)
            valid_cols = ["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"]
            conn.update(data=final_data[valid_cols])
            st.success("✅ 저장되었습니다!")
            st.rerun()

# --- [메인 화면: 대시보드] ---
if not df.empty:
    # 1. 기간별 통계 섹션
    st.subheader("📅 기간별 매출 요약")
    col1, col2 = st.columns([1, 2])
    with col1:
        # 오늘 날짜 기준 이번 달 1일부터 오늘까지를 기본값으로
        start_d, end_d = st.date_input("조회 기간 설정", [date.today().replace(day=1), date.today()])
    
    f_df = df[(df['운송 일자'] >= start_d) & (df['운송 일자'] <= end_d)]
    
    if not f_df.empty:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("총 운송 건수", f"{len(f_df)}건")
        m2.metric("기간 내 매출액", f"{int(f_df['합계'].sum()):,}원")
        m3.metric("기간 내 입금액", f"{int(f_df['입금액'].sum()):,}원")
        m4.metric("남은 미수금", f"{int(f_df['미수금'].sum()):,}원", delta_color="inverse")
        
        st.divider()

        # 2. 업체별 통계 섹션 (원하셨던 기능!)
        st.subheader("🏢 업체별 운송 현황 (조회 기간 내)")
        # 거래처별로 그룹화하여 건수와 금액 계산
        client_stats = f_df.groupby('거래처').agg(
            운송건수=('거래처', 'size'),
            매출합계=('합계', 'sum'),
            미수금잔액=('미수금', 'sum')
        ).reset_index().sort_values(by='운송건수', ascending=False)
        
        # 보기 편하게 돈 단위 포맷팅
        client_stats['매출합계'] = client_stats['매출합계'].apply(lambda x: f"{int(x):,}원")
        client_stats['미수금잔액'] = client_stats['미수금잔액'].apply(lambda x: f"{int(x):,}원")
        
        # 표 출력 (연번 없이 깔끔하게)
        st.dataframe(client_stats, use_container_width=True, hide_index=True)
    else:
        st.warning

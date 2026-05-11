import streamlit as st
import pandas as pd
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# 페이지 설정
st.set_page_config(page_title="용달 매출 통계 시스템", layout="wide")
st.title("🚛 용달 매출 관리 및 실시간 통계")

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 데이터 불러오기 (실시간 반영을 위해 ttl=0)
try:
    df = conn.read(ttl="0")
    # 날짜 컬럼을 날짜 형식으로 변환
    df['일자'] = pd.to_datetime(df['일자']).dt.date
except Exception as e:
    df = pd.DataFrame(columns=["일자", "거래처", "공급가액", "세액", "합계금액", "수금상태", "입금액", "미수금"])

# --- [사이드바: 내역 입력] ---
with st.sidebar:
    st.header("➕ 신규 내역 등록")
    input_date = st.date_input("운송 일자", date.today())
    client_name = st.text_input("거래처명")
    
    supply_val = st.number_input("공급가액", min_value=0, step=1000)
    tax_val = st.number_input("세액(수정가능)", min_value=0, value=int(supply_val * 0.1))
    total_val = st.number_input("합계(수정가능)", min_value=0, value=supply_val + tax_val)
    
    status = st.selectbox("수금상태", ["미입금", "일부입금", "완납"])
    if status == "완납": deposit_amount = total_val
    elif status == "미입금": deposit_amount = 0
    else: deposit_amount = st.number_input("입금액", min_value=0, max_value=total_val)
    
    if st.button("내역 저장하기"):
        if client_name:
            new_entry = pd.DataFrame([{
                "일자": input_date.strftime('%Y-%m-%d'),
                "거래처": client_name,
                "공급가액": supply_val,
                "세액": tax_val,
                "합계금액": total_val,
                "수금상태": status,
                "입금액": deposit_amount,
                "미수금": total_val - deposit_amount
            }])
            updated_df = pd.concat([df, new_entry], ignore_index=True)
            conn.update(data=updated_df)
            st.success("✅ 저장 완료!")
            st.rerun()
        else:
            st.error("거래처명을 입력하세요.")

# --- [메인 화면: 검색 및 통계] ---
st.subheader("🔍 매출 조회 및 분석")

if not df.empty:
    # 필터 구역
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        # 기간 필터 (기본값: 이번달 1일 ~ 오늘)
        start_d, end_d = st.date_input("조회 기간", [date.today().replace(day=1), date.today()])
    with col_f2:
        # 거래처 필터
        client_list = ["전체"] + sorted(df["거래처"].unique().tolist())
        sel_client = st.selectbox("거래처 선택", client_list)

    # 데이터 필터링 적용
    mask = (df['일자'] >= start_d) & (df['일자'] <= end_d)
    f_df = df.loc[mask]
    if sel_client != "전체":
        f_df = f_df[f_df["거래처"] == sel_client]

    # 상단 요약 지표 (Metric)
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric(f"선택 기간 매출 합계", f"{f_df['합계금액'].sum():,}원")
    m2.metric(f"총 입금액", f"{f_df['입금액'].sum():,}원")
    m3.metric(f"미수금 잔액", f"{f_df['미수금'].sum():,}원", delta=f"-{f_df['미수금'].sum():,}", delta_color="inverse")

    # 월별 매출 그래프 (막대 차트)
    st.subheader("📈 월별 매출 추이")
    f_df['월'] = pd.to_datetime(f_df['일자']).dt.strftime('%Y-%m')
    monthly_sales = f_df.groupby('월')['합계금액'].sum()
    st.bar_chart(monthly_sales)

    # 상세 내역 표
    st.subheader("📑 상세 운송 내역")
    st.dataframe(f_df.sort_values(by="일자", ascending=False), use_container_width=True)
else:
    st.info("데이터가 없습니다. 왼쪽에서 첫 내역을 등록해 보세요!")

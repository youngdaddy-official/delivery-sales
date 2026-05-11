import streamlit as st
import pandas as pd
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# 페이지 기본 설정
st.set_page_config(page_title="용달 매출 관리 시스템", layout="wide")
st.title("🚛 실시간 동기화 용달 매출 관리")

# --- 구글 시트 연결 (Secrets에 설정된 정보를 자동으로 사용함) ---
conn = st.connection("gsheets", type=GSheetsConnection)

# 데이터 불러오기
try:
    # Secrets에 적힌 spreadsheet 주소를 사용해 데이터를 읽어옵니다.
    df = conn.read()
except Exception as e:
    # 데이터가 아예 없거나 에러 발생 시 초기 데이터프레임 생성
    df = pd.DataFrame(columns=["일자", "거래처", "공급가액", "세액", "합계금액", "수금상태", "입금액", "미수금"])

# --- 사이드바: 내역 입력 ---
with st.sidebar:
    st.header("➕ 신규 내역 등록")
    input_date = st.date_input("운송 일자", date.today())
    client = st.text_input("거래처")
    
    st.divider()
    supply_val = st.number_input("공급가액(원)", min_value=0, step=1000)
    
    # 자동 계산되지만 수정 가능
    default_tax = int(supply_val * 0.1)
    tax_val = st.number_input("세액(수정 가능)", min_value=0, value=default_tax)
    total_val = st.number_input("합계금액(수정 가능)", min_value=0, value=supply_val + tax_val)
    
    st.divider()
    status = st.selectbox("수금상태", ["미입금", "일부입금", "완납"])
    
    if status == "완납":
        deposit_amount = total_val
    elif status == "미입금":
        deposit_amount = 0
    else:
        deposit_amount = st.number_input("입금된 금액(원)", min_value=0, max_value=total_val)
    
    unpaid_amount = total_val - deposit_amount

    if st.button("내역 저장하기"):
        if client:
            new_entry = pd.DataFrame([{
                "일자": input_date.strftime('%Y-%m-%d'),
                "거래처": client,
                "공급가액": supply_val,
                "세액": tax_val,
                "합계금액": total_val,
                "수금상태": status,
                "입금액": deposit_amount,
                "미수금": unpaid_amount
            }])
            
            # 기존 데이터에 추가 후 구글 시트 업데이트
            updated_df = pd.concat([df, new_entry], ignore_index=True)
            conn.update(data=updated_df)
            st.success(f"✅ {client} 내역이 구글 시트에 저장되었습니다!")
            st.rerun() # 새로고침하여 목록 갱신
        else:
            st.error("거래처명을 입력하세요.")

# --- 메인 화면: 통계 및 데이터 표시 ---
if not df.empty:
    # 상단 요약 지표
    m1, m2, m3 = st.columns(3)
    m1.metric("총 매출", f"{df['합계금액'].sum():,}원")
    m2.metric("총 입금액", f"{df['입금액'].sum():,}원")
    m3.metric("총 미수금", f"{df['미수금'].sum():,}원", delta=f"-{df['미수금'].sum():,}", delta_color="inverse")

    st.divider()
    
    # 데이터 목록 표시
    st.subheader("📑 상세 운송 장부")
    # 날짜 기준 내림차순 정렬하여 보여주기
    st.dataframe(df.sort_values(by="일자", ascending=False), use_container_width=True)
else:
    st.info("현재 저장된 데이터가 없습니다. 왼쪽 메뉴에서 첫 내역을 등록해 보세요!")

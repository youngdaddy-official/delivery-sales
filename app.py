import streamlit as st
import pandas as pd
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# 1. 시트 주소를 변수에 고정 (에러 방지)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1EF32RmNCpoUkcW0Xy8tqfPRZnh2-GmZiT5b1lqP8bgc/edit?usp=sharing"

st.set_page_config(page_title="용달 매출 관리", layout="wide")
st.title("🚛 실시간 동기화 용달 매출 관리")

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 데이터 불러오기 (ttl=0은 실시간 반영을 위함)
try:
    df = conn.read(spreadsheet=SHEET_URL, ttl="0")
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    df = pd.DataFrame(columns=["일자", "거래처", "공급가액", "세액", "합계금액", "수금상태", "입금액", "미수금"])

# --- 사이드바 입력창 ---
with st.sidebar:
    st.header("➕ 신규 내역 등록")
    input_date = st.date_input("운송 일자", date.today())
    client = st.text_input("거래처")
    supply_val = st.number_input("공급가액", min_value=0, step=1000)
    tax_val = st.number_input("세액", min_value=0, value=int(supply_val * 0.1))
    total_val = st.number_input("합계", min_value=0, value=supply_val + tax_val)
    status = st.selectbox("수금상태", ["미입금", "일부입금", "완납"])
    
    if status == "완납":
        deposit_amount = total_val
    elif status == "미입금":
        deposit_amount = 0
    else:
        deposit_amount = st.number_input("입금액", min_value=0, max_value=total_val)
    
    if st.button("저장하기"):
        if client:
            new_data = pd.DataFrame([{
                "일자": input_date.strftime('%Y-%m-%d'),
                "거래처": client,
                "공급가액": supply_val,
                "세액": tax_val,
                "합계금액": total_val,
                "수금상태": status,
                "입금액": deposit_amount,
                "미수금": total_val - deposit_amount
            }])
            
            # 기존 데이터에 추가
            updated_df = pd.concat([df, new_data], ignore_index=True)
            
            # ★ 핵심: 저장할 때 주소를 한 번 더 확실히 알려줌
            conn.update(spreadsheet=SHEET_URL, data=updated_df)
            st.success("✅ 저장 완료!")
            st.rerun()
        else:
            st.error("거래처명을 입력해주세요.")

# 메인 화면 통계 및 표
if not df.empty:
    st.metric("총 미수금", f"{df['미수금'].sum():,}원")
    st.dataframe(df.sort_values(by="일자", ascending=False), use_container_width=True)

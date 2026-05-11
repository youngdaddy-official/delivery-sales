import streamlit as st
import pandas as pd
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# 1. 구글 시트 주소 설정 (여기에 본인 시트 주소를 꼭 넣으세요)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1EF32RmNCpoUkcW0Xy8tqfPRZnh2-GmZiT5b1lqP8bgc/edit?usp=sharing"

st.set_page_config(page_title="용달 매출 관리", layout="wide")
st.title("🚛 실시간 동기화 용달 매출 관리")

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df = conn.read(spreadsheet=SHEET_URL)
except:
    df = pd.DataFrame(columns=["일자", "거래처", "공급가액", "세액", "합계금액", "수금상태", "입금액", "미수금"])

# 사이드바 입력창
with st.sidebar:
    st.header("➕ 신규 내역 등록")
    input_date = st.date_input("운송 일자", date.today())
    client = st.text_input("거래처")
    supply_val = st.number_input("공급가액", min_value=0, step=1000)
    tax_val = st.number_input("세액", min_value=0, value=int(supply_val * 0.1))
    total_val = st.number_input("합계", min_value=0, value=supply_val + tax_val)
    status = st.selectbox("수금상태", ["미입금", "일부입금", "완납"])
    
    if status == "완납": deposit_amount = total_val
    elif status == "미입금": deposit_amount = 0
    else: deposit_amount = st.number_input("입금액", min_value=0, max_value=total_val)
    
    if st.button("저장하기"):
        new_data = pd.DataFrame([{"일자": input_date.strftime('%Y-%m-%d'), "거래처": client, "공급가액": supply_val, "세액": tax_val, "합계금액": total_val, "수금상태": status, "입금액": deposit_amount, "미수금": total_val - deposit_amount}])
        updated_df = pd.concat([df, new_data], ignore_index=True)
        conn.update(spreadsheet=SHEET_URL, data=updated_df)
        st.success("저장 완료!")
        st.rerun()

# 메인 화면 통계 및 표
if not df.empty:
    st.metric("총 미수금", f"{df['미수금'].sum():,}원")
    st.dataframe(df.sort_values(by="일자", ascending=False), use_container_width=True)
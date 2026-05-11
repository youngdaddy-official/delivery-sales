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
    # 전체 데이터 읽기
    df_raw = conn.read(ttl="0")
    
    # 빈 데이터프레임 방지
    if df_raw.empty:
        df = pd.DataFrame(columns=["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"])
    else:
        df = df_raw.copy()
        # '운송 일자'가 없으면 생성
        if '운송 일자' not in df.columns:
            df['운송 일자'] = None
            
        # 날짜 변환 시도
        df['운송 일자'] = pd.to_datetime(df['운송 일자'], errors='coerce')
        # 날짜가 제대로 들어있는 데이터만 남기되, 없으면 안내만 함
        df_valid = df.dropna(subset=['운송 일자']).copy()
        df_valid['운송 일자'] = df_valid['운송 일자'].dt.date
        
        # 숫자형 데이터 변환
        num_cols = ['공급가액', '세액', '합계', '입금액', '미수금']
        for col in num_cols:
            if col in df_valid.columns:
                df_valid[col] = pd.to_numeric(df_valid[col], errors='coerce').fillna(0).astype(int)
        
        df = df_valid
except Exception as e:
    st.error(f"시트 읽기 오류: {e}")
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
            # 기존 데이터가 비어있을 수 있으므로 처리
            final_to_save = pd.concat([df_raw if not df_raw.empty else pd.DataFrame(), new_entry], ignore_index=True)
            # 필요한 열만 필터링 (오류 방지)
            valid_cols = ["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"]
            conn.update(data=final_to_save[valid_cols])
            st.success("저장 완료!")
            st.rerun()

# --- [메인 화면: 대시보드] ---
# 데이터가 있는지 확인
if not df.empty:
    st.subheader("📊 기간별/업체별 요약")
    
    # 날짜 필터 범위를 데이터의 최소/최대값으로 자동 설정하거나 기본값 사용
    min_date = min(df['운송 일자']) if not df.empty else date.today().replace(day=1)
    max_date = max(df['운송 일자']) if not df.empty else date.today()
    
    start_d, end_d = st.date_input("조회 기간 설정", [min_date, max_date])
    
    f_df = df[(df['운송 일자'] >= start_d) & (df['운송 일자'] <= end_d)]
    
    if not f_df.empty:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("총 운송 건수", f"{len(f_df)}건")
        m2.metric("조회 기간 매출", f"{int(f_df['합계'].sum()):,}원")
        m3.metric("총 입금액", f"{int(f_df['입금액'].sum()):,}원")
        m4.metric("미수금 잔액", f"{int(f_df['미수금'].sum()):,}원", delta_color="inverse")
        
        st.divider()
        
        # 업체별 통계
        st.subheader("🏢 업체별 현황")
        client_stats = f_df.groupby('거래처').agg(
            운송건수=('거래처', 'size'),
            매출합계=('합계', 'sum'),
            미수금잔액=('미수금', 'sum')
        ).reset_index().sort_values(by='운송건수', ascending=False)
        st.dataframe(client_stats, use_container_width=True, hide_index=True)
    else:
        st.warning("선택한 기간 내에 해당하는 데이터가 없습니다. 기간을 조정해 보세요.")

    st.divider()

    # 상세 내역
    st.subheader("📑 상세 운송 내역")
    display_df = df.sort_values(by="운송 일자", ascending=False).copy()
    display_df.insert(0, '번호', range(1, len(display_df) + 1))
    st.dataframe(display_df, use_container_width=True, hide_index=True)

else:
    st.info("💡 현재 표시할 수 있는 데이터가 없습니다.")
    st.write("### 확인해 보세요:")
    st.write("1. 왼쪽 메뉴에서 **신규 내역을 하나 등록**해 보세요.")
    st.write("2. 구글 시트의 **'운송 일자'** 칸에 날짜가 제대로 들어있는지 확인해 보세요.")
    
    # 디버깅용: 실제 시트에서 읽어온 원본 데이터 보여주기
    if not df_raw.empty:
        with st.expander("🔍 현재 구글 시트 원본 데이터 보기"):
            st.write("프로그램이 읽어온 데이터입니다. '운송 일자' 칸이 비어있는지 확인하세요.")
            st.dataframe(df_raw)

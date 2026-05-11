import streamlit as st
import pandas as pd
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="용달 매출 통합 관리 시스템", layout="wide")
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
        
        # 숫자형 변환
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
                "운송 일자": input_date.strftime('%Y-%m-%d'), "거래처": client_name, "공급가액": int(supply_val),
                "세액": int(tax_val), "합계": int(total_val), "수금상태": status, "입금액": int(dep_amt), "미수금": int(total_val - dep_amt)
            }])
            final_data = pd.concat([df_raw, new_entry], ignore_index=True)
            conn.update(data=final_data[["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"]])
            st.success("✅ 저장되었습니다!")
            st.rerun()

# --- [메인 화면: 대시보드] ---
if not df.empty:
    st.subheader("📊 매출 요약 및 분석")
    col_f1, col_f2 = st.columns([1, 1])
    with col_f1:
        start_d, end_d = st.date_input("조회 기간 설정", [date.today().replace(day=1), date.today()])
    with col_f2:
        client_options = ["전체"] + sorted(df["거래처"].unique().tolist())
        selected_client = st.selectbox("조회할 업체 선택", client_options)

    # 데이터 필터링 적용
    f_df = df[(df['운송 일자'] >= start_d) & (df['운송 일자'] <= end_d)]
    if selected_client != "전체":
        f_df = f_df[f_df["거래처"] == selected_client]

    # [상단 지표 카드]
    m1, m2, m3, m4 = st.columns(4)
    label_prefix = f"[{selected_client}] " if selected_client != "전체" else "[전체] "
    m1.metric(f"{label_prefix}운송 건수", f"{len(f_df)}건")
    m2.metric(f"{label_prefix}매출 합계", f"{int(f_df['합계'].sum()):,}원")
    m3.metric(f"{label_prefix}입금액", f"{int(f_df['입금액'].sum()):,}원")
    m4.metric(f"{label_prefix}미수금 잔액", f"{int(f_df['미수금'].sum()):,}원", delta_color="inverse")
    
    st.divider()

    # [업체별 요약 표]
    st.subheader("🏢 업체별 현황 요약 (선택 기간 내)")
    summary_df = f_df.groupby('거래처').agg(
        운송건수=('거래처', 'size'), 매출합계=('합계', 'sum'), 미수금잔액=('미수금', 'sum')
    ).reset_index().sort_values(by='운송건수', ascending=False)
    summary_df['매출합계'] = summary_df['매출합계'].apply(lambda x: f"{int(x):,}원")
    summary_df['미수금잔액'] = summary_df['미수금잔액'].apply(lambda x: f"{int(x):,}원")
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
    
    st.divider()

    # [상세 내역]
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
            # 실제 원본 데이터프레임의 인덱스 찾기
            row_idx = display_df[display_df['번호'] == target_no].index[0]
            
            # 수정 입력 칸들
            col_e1, col_e2, col_e3 = st.columns(3)
            with col_e1:
                edit_date = st.date_input("날짜 수정", df.at[row_idx, '운송 일자'])
                edit_client = st.text_input("거래처 수정", df.at[row_idx, '거래처'])
            with col_e2:
                edit_supply = st.number_input("공급가액 수정", value=int(df.at[row_idx, '공급가액']))
                edit_tax = st.number_input("세액 수정", value=int(df.at[row_idx, '세액']))
            with col_e3:
                edit_status = st.selectbox("수금상태 수정", ["미입금", "일부입금", "완납"], 
                                           index=["미입금", "일부입금", "완납"].index(df.at[row_idx, '수금상태']))
                edit_dep = st.number_input("입금액 수정", value=int(df.at[row_idx, '입금액']))

            # 버튼 구역
            btn_col1, btn_col2, _ = st.columns([1, 1, 3])
            
            if btn_col1.button("💾 이 내용으로 수정 적용", type="secondary"):
                df.at[row_idx, '운송 일자'] = edit_date
                df.at[row_idx, '거래처'] = edit_client
                df.at[row_idx, '공급가액'] = int(edit_supply)
                df.at[row_idx, '세액'] = int(edit_tax)
                df.at[row_idx, '합계'] = int(edit_supply + edit_tax)
                df.at[row_idx, '수금상태'] = edit_status
                df.at[row_idx, '입금액'] = int(edit_dep)
                df.at[row_idx, '미수금'] = int((edit_supply + edit_tax) - edit_dep)
                
                # 구글 시트 업데이트
                conn.update(data=df[["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"]])
                st.success("✅ 수정이 완료되었습니다!")
                st.rerun()

            if btn_col2.button("🗑️ 해당 내역 완전히 삭제", type="primary"):
                df_deleted = df.drop(row_idx)
                conn.update(data=df_deleted[["운송 일자", "거래처", "공급가액", "세액", "합계", "수금상태", "입금액", "미수금"]])
                st.warning("⚠️ 삭제되었습니다.")
                st.rerun()
else:
    st.info("💡 등록된 데이터가 없습니다.")

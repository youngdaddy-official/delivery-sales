import streamlit as st
import pandas as pd
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="매출/지출 통합 관리시스템", layout="wide")

# --- [로그인 체크 함수] ---
def check_password():
    if "password" not in st.secrets:
        st.error("⚠️ Streamlit Cloud의 Secrets 설정에 'password' 항목이 없습니다.")
        return False
    def password_entered():
        if str(st.session_state["password_input"]) == str(st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password_input"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center;'>🔒 시스템 접속 로그인</h2>", unsafe_allow_html=True)
        st.divider()
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.text_input("비밀번호를 입력하고 엔터를 치세요", type="password", on_change=password_entered, key="password_input")
        return False
    elif not st.session_state["password_correct"]:
        st.error("❌ 비밀번호가 일치하지 않습니다.")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.text_input("다시 입력해 주세요", type="password", on_change=password_entered, key="password_input")
        return False
    else:
        return True

# --- [본 프로그램 시작] ---
if check_password():
    
    # [디자인 & 번역 방지]
    st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"] { -webkit-text-size-adjust: none; unicode-bidi: isolate; }
    .notranslate { translate: no !important; }
    [data-testid="stWidgetLabel"] p { color: #31333F !important; font-weight: 600 !important; opacity: 1 !important; }
    button[data-testid="stNumberInputStepDown"], button[data-testid="stNumberInputStepUp"] { display: none !important; }
    input[type=number]::-webkit-inner-spin-button, input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none !important; margin: 0 !important; }
    input[type=number] { -moz-appearance: textfield !important; }
    div[data-testid="stNumberInputContainer"], div[data-testid="stTextInputRootElement"], div[data-testid="stSelectbox"] > div {
        background-color: white !important; border: 1px solid rgba(49, 51, 63, 0.2) !important; border-radius: 0.5rem !important;
    }
    input:disabled { background-color: white !important; color: #31333F !important; -webkit-text-fill-color: #31333F !important; opacity: 1 !important; border: 1px solid rgba(49, 51, 63, 0.1) !important; cursor: default !important; }
</style>
    """, unsafe_allow_html=True)
    st.markdown('<head><meta name="google" content="notranslate"></head>', unsafe_allow_html=True)

    # 2. 구글 시트 연결
    conn = st.connection("gsheets", type=GSheetsConnection)

    # --- [콤마가 포함된 문자열을 숫자로 변환하는 함수] ---
    def parse_money(val_str):
        cleaned = str(val_str).replace(",", "").replace("원", "").strip()
        try:
            return int(cleaned)
        except ValueError:
            return 0

    # --- [입력 데이터 초기 설정 메모리] ---
    if 's_fare_val' not in st.session_state: st.session_state.s_fare_val = 0
    if 'side_s_fee' not in st.session_state: st.session_state.side_s_fee = 0
    if 'side_s_dep' not in st.session_state: st.session_state.side_s_dep = 0
    if 'side_e_amo' not in st.session_state: st.session_state.side_e_amo = 0

    # --- [데이터 로드 함수] ---
    def load_data(sheet_name):
        try:
            df = conn.read(worksheet=sheet_name, ttl="0")
            if df is None or df.empty:
                return pd.DataFrame()
            df = df.copy()
            df['원본인덱스'] = df.index 
            
            date_col = "운송 일자" if sheet_name == "매출" else "지출 일자"
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce').dt.date
                df = df.dropna(subset=[date_col])
            
            num_cols = ['운임료', '수수료', '세액', '합계', '입금액', '미수금'] if sheet_name == "매출" else ['금액']
            for col in num_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            return df
        except:
            return pd.DataFrame()

    df_sales = load_data("매출")
    df_exp = load_data("지출")

    # --- [사이드바: 왼쪽 입력 메뉴] ---
    with st.sidebar:
        st.header("📝 신규 내역 등록")
        
        # [구역 1] 매출 등록 입력창
        st.subheader("🟢 신규 매출 등록")
        s_date = st.date_input("운송 일자", date.today(), key="side_s_date")
        s_client = st.text_input("거래처명", key="side_s_client")
        s_origin = st.text_input("출발지", key="side_s_ori")
        s_dest = st.text_input("도착지", key="side_s_des")
        
        # 💡 천 단위 콤마가 실시간으로 입력창에 적용되는 로직
        s_fare_input = st.text_input("운임료", value=f"{st.session_state.s_fare_val:,}")
        s_fare = parse_money(s_fare_input)
        st.session_state.s_fare_val = s_fare
        
        s_tax = int(s_fare * 0.1)
        st.text_input("세액 (자동)", value=f"{s_tax:,}", disabled=True)
        
        s_subtotal = s_fare + s_tax
        st.text_input("매출 합계 (자동)", value=f"{s_subtotal:,}", disabled=True)
        
        s_fee_input = st.text_input("수수료", value=f"{st.session_state.side_s_fee:,}")
        s_fee = parse_money(s_fee_input)
        st.session_state.side_s_fee = s_fee
        
        s_final = s_subtotal - s_fee
        st.text_input("최종 금액 (자동)", value=f"{s_final:,}", disabled=True)
        
        s_pmethod = st.selectbox("결제방식", ["이체", "현금", "전자세금계산서", "카드"], key="side_s_pm")
        s_status = st.selectbox("수금상태", ["미입금", "일부입금", "완납"], key="side_s_st")
        
        if s_status == "완납":
            s_dep = s_final
            st.text_input("입금액", value=f"{s_dep:,}", disabled=True)
        elif s_status == "미입금":
            s_dep = 0
            st.text_input("입금액", value="0", disabled=True)
        else:
            s_dep_input = st.text_input("입금액", value=f"{st.session_state.side_s_dep:,}")
            s_dep = parse_money(s_dep_input)
            if s_dep > s_final:
                s_dep = s_final
            st.session_state.side_s_dep = s_dep

        if st.button("💾 매출 저장하기", use_container_width=True, key="btn_s_save"):
            if s_client and s_origin and s_dest:
                new_s = pd.DataFrame([{
                    "운송 일자": s_date.strftime('%Y-%m-%d'), 
                    "거래처": s_client, 
                    "출발지": s_origin,
                    "도착지": s_dest,
                    "운임료": int(s_fare),
                    "수수료": int(s_fee),
                    "세액": int(s_tax), 
                    "합계": int(s_final), 
                    "결제방식": s_pmethod,
                    "수금상태": s_status, 
                    "입금액": int(s_dep), 
                    "미수금": int(s_final - s_dep)
                }])
                df_raw_sales = conn.read(worksheet="매출", ttl="0")
                conn.update(worksheet="매출", data=pd.concat([df_raw_sales, new_s], ignore_index=True))
                
                # 저장 완료 후 입력값 다음 입력 위해 0으로 자동 청소
                st.session_state.s_fare_val = 0
                st.session_state.side_s_fee = 0
                st.session_state.side_s_dep = 0
                
                st.success("✅ 매출 저장 완료!")
                st.rerun()
            elif not s_client: st.warning("⚠️ 거래처명을 입력해 주세요.")
            elif not s_origin: st.warning("⚠️ 출발지를 입력해 주세요.")
            elif not s_dest: st.warning("⚠️ 도착지를 입력해 주세요.")

        st.markdown("---") # 매출과 지출 구분선
        
        # [구역 2] 지출 등록 입력창
        st.subheader("🔴 신규 지출 등록")
        e_date = st.date_input("지출 일자", date.today(), key="side_e_date")
        e_category = st.selectbox("지출 항목", ["연료비", "통행료", "기타"], key="side_e_cat")
        e_vendor = st.text_input("지출처", key="side_e_ven")
        
        # 💡 지출 금액 입력창 천 단위 콤마 자동 포맷팅 적용
        e_amount_input = st.text_input("지출 금액", value=f"{st.session_state.side_e_amo:,}")
        e_amount = parse_money(e_amount_input)
        st.session_state.side_e_amo = e_amount
        
        e_memo = st.text_input("비고 (선택)", key="side_e_mem")

        if st.button("💾 지출 저장하기", use_container_width=True, key="btn_e_save"):
            if e_amount > 0 and e_vendor:
                new_e = pd.DataFrame([{"지출 일자": e_date.strftime('%Y-%m-%d'), "지출 항목": e_category, "지출처": e_vendor, "금액": e_amount, "비고": e_memo}])
                df_raw_exp = conn.read(worksheet="지출", ttl="0")
                conn.update(worksheet="지출", data=pd.concat([df_raw_exp, new_e], ignore_index=True))
                
                # 저장 완료 후 지출 입력값 다음 입력 위해 0으로 자동 청소
                st.session_state.side_e_amo = 0
                
                st.success("✅ 지출 저장 완료!")
                st.rerun()
            elif not e_vendor:
                st.error("⚠️ 지출처를 입력해 주세요.")

        st.markdown("---")
        if st.button("🚪 로그아웃", use_container_width=True):
            st.session_state["password_correct"] = False
            st.rerun()

    # --- [메인 화면: 대시보드 및 통합 장부] ---
    st.title("📊 매출 및 지출 통합 관리시스템")
    st.subheader("📈 통합 현황 요약")
    
    col_date, _ = st.columns([1, 1])
    with col_date:
        date_range = st.date_input("조회 기간", [date.today().replace(day=1), date.today()])
    
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_d, end_d = date_range
    else:
        start_d = end_d = date_range[0] if isinstance(date_range, (list, tuple)) else date_range

    # 데이터 필터링
    f_sales = df_sales[(df_sales['운송 일자'] >= start_d) & (df_sales['운송 일자'] <= end_d)] if not df_sales.empty else pd.DataFrame()
    f_exp = df_exp[(df_exp['지출 일자'] >= start_d) & (df_exp['지출 일자'] <= end_d)] if not df_exp.empty else pd.DataFrame()

    # 금액 계산 및 수익 공식 적용
    total_s = int(f_sales['합계'].sum()) if not f_sales.empty else 0
    total_e = int(f_exp['금액'].sum()) if not f_exp.empty else 0
    profit = total_s - total_e

    m1, m2, m3 = st.columns(3)
    m1.metric("총 매출액 (운임-수수료+세액)", f"{total_s:,}원")
    m2.metric("총 지출액 (연료비+통행료+기타)", f"{total_e:,}원")
    m3.metric("순수익 (매출 - 지출)", f"{profit:,}원", delta=f"{profit:,}원")

    st.divider()
    st.subheader("📝 통합 입출금 장부")

    # --- 매출과 지출 데이터 하나로 합치기 로직 ---
    t_sales = pd.DataFrame()
    if not f_sales.empty:
        t_sales = pd.DataFrame({
            "원본인덱스": f_sales["원본인덱스"],
            "날짜": f_sales["운송 일자"],
            "구분": "🟢 매출",
            "거래처/지출처": f_sales["거래처"],
            "상세 내용 (경로/항목)": f_sales["출발지"].astype(str) + " ➡️ " + f_sales["도착지"].astype(str),
            "매출액(+)": f_sales["합계"],
            "지출액(-)": 0,
            "결제/수금 상태": f_sales["결제방식"].astype(str) + " (" + f_sales["수금상태"].astype(str) + ")",
            "비고": ""
        })

    t_exp = pd.DataFrame()
    if not f_exp.empty:
        t_exp = pd.DataFrame({
            "원본인덱스": f_exp["원본인덱스"],
            "날짜": f_exp["지출 일자"],
            "구분": "🔴 지출",
            "거래처/지출처": f_exp["지출처"],
            "상세 내용 (경로/항목)": f_exp["지출 항목"],
            "매출액(+)": 0,
            "지출액(-)": f_exp["금액"],
            "결제/수금 상태": "-",
            "비고": f_exp["비고"].fillna("").astype(str)
        })

    if not t_sales.empty or not t_exp.empty:
        df_total = pd.concat([t_sales, t_exp], ignore_index=True)
        df_total = df_total.sort_values(by="날짜", ascending=False).reset_index(drop=True)
        
        # 표 헤더 생성 (가로 비율 지정)
        grid_widths = [1.2, 0.8, 1.5, 2.0, 1.2, 1.2, 1.8, 1.5, 0.6]
        headers = ["날짜", "구분", "거래처/지출처", "상세 내용 (경로/항목)", "매출액(+)", "지출액(-)", "결제/수금 상태", "비고", "삭제"]
        
        col_header = st.columns(grid_widths)
        for col, title in zip(col_header, headers):
            col.markdown(f"**{title}**")
        st.markdown("<hr style='margin: 0.5rem 0; border-top: 2px solid #ccc;'>", unsafe_allow_html=True)
        
        # 데이터 행 출력 진행
        for idx, row in df_total.iterrows():
            col_row = st.columns(grid_widths)
            
            col_row[0].write(str(row["날짜"]))
            col_row[1].write(row["구분"])
            col_row[2].write(row["거래처/지출처"])
            col_row[3].write(row["상세 내용 (경로/항목)"])
            col_row[4].write(f"{row['매출액(+)']:,}원")
            col_row[5].write(f"{row['지출액(-)']:,}원")
            col_row[6].write(row["결제/수금 상태"])
            col_row[7].write(row["비고"] if row["비고"] != "" else "-")
            
            if col_row[8].button("🗑️", key=f"del_{idx}_{row['원본인덱스']}", type="primary", help="해당 내역 삭제"):
                orig_idx = row['원본인덱스']
                
                if row['구분'] == "🟢 매출":
                    df_raw = conn.read(worksheet="매출", ttl="0")
                    df_clean = df_raw.drop(int(orig_idx)).reset_index(drop=True)
                    conn.update(worksheet="매출", data=df_clean)
                else:
                    df_raw = conn.read(worksheet="지출", ttl="0")
                    df_clean = df_raw.drop(int(orig_idx)).reset_index(drop=True)
                    conn.update(worksheet="지출", data=df_clean)
                
                st.clear_caches()
                st.rerun()
            st.markdown("<hr style='margin: 0.3rem 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)
    else:
        st.info("선택하신 기간 내에 입출금 내역이 없습니다.")

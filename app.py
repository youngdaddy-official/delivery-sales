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
        
        st.subheader("🟢 신규 매출 등록")
        s_date = st.date_input("운송 일자", date.today(), key="side_s_date")
        s_client = st.text_input("거래처명", key="side_s_client")
        s_origin = st.text_input("출발지", key="side_s_ori")
        s_dest = st.text_input("도착지", key="side_s_des")
        
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
                
                st.session_state.s_fare_val = 0
                st.session_state.side_s_fee = 0
                st.session_state.side_s_dep = 0
                st.success("✅ 매출 저장 완료!")
                st.rerun()
            elif not s_client: st.warning("⚠️ 거래처명을 입력해 주세요.")
            elif not s_origin: st.warning("⚠️ 출발지를 입력해 주세요.")
            elif not s_dest: st.warning("⚠️ 도착지를 입력해 주세요.")

        st.markdown("---") 
        
        st.subheader("🔴 신규 지출 등록")
        e_date = st.date_input("지출 일자", date.today(), key="side_e_date")
        e_category = st.selectbox("지출 항목", ["연료비", "통행료", "기타"], key="side_e_cat")
        e_vendor = st.text_input("지출처", key="side_e_ven")
        
        e_amount_input = st.text_input("지출 금액", value=f"{st.session_state.side_e_amo:,}")
        e_amount = parse_money(e_amount_input)
        st.session_state.side_e_amo = e_amount
        
        e_memo = st.text_input("비고 (선택)", key="side_e_mem")

        if st.button("💾 지출 저장하기", use_container_width=True, key="btn_e_save"):
            if e_amount > 0 and e_vendor:
                new_e = pd.DataFrame([{"지출 일자": e_date.strftime('%Y-%m-%d'), "지출 항목": e_category, "지출처": e_vendor, "금액": e_amount, "비고": e_memo}])
                df_raw_exp = conn.read(worksheet="지출", ttl="0")
                conn.update(worksheet="지출", data=pd.concat([df_raw_exp, new_e], ignore_index=True))
                
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
    st.subheader("📈 전체 기간 현황 요약")
    
    col_date, _ = st.columns([1, 1])
    with col_date:
        date_range = st.date_input("조회 기간 선택", [date.today().replace(day=1), date.today()])
    
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_d, end_d = date_range
    else:
        start_d = end_d = date_range[0] if isinstance(date_range, (list, tuple)) else date_range

    f_sales = df_sales[(df_sales['운송 일자'] >= start_d) & (df_sales['운송 일자'] <= end_d)] if not df_sales.empty else pd.DataFrame()
    f_exp = df_exp[(df_exp['지출 일자'] >= start_d) & (df_exp['지출 일자'] <= end_d)] if not df_exp.empty else pd.DataFrame()

    total_s = int(f_sales['합계'].sum()) if not f_sales.empty else 0
    total_e = int(f_exp['금액'].sum()) if not f_exp.empty else 0
    profit = total_s - total_e

    m1, m2, m3 = st.columns(3)
    m1.metric("총 매출액 (운임-수수료+세액)", f"{total_s:,}원")
    m2.metric("총 지출액 (연료비+통행료+기타)", f"{total_e:,}원")
    m3.metric("순수익 (매출 - 지출)", f"{profit:,}원", delta=f"{profit:,}원")

    st.divider()
    st.subheader("📝 통합 입출금 장부")

    t_sales = pd.DataFrame()
    if not f_sales.empty:
        t_sales = pd.DataFrame({
            "삭제(체크)": False,
            "원본인덱스": f_sales["원본인덱스"],
            "날짜": f_sales["운송 일자"],
            "구분": "🟢 매출",
            "거래처/지출처": f_sales["거래처"],
            "출발지": f_sales["출발지"],
            "도착지": f_sales["도착지"],
            "지출항목": "",
            "운임료": f_sales["운임료"],
            "매출 합계": f_sales["운임료"] + f_sales["세액"],
            "수수료": f_sales["수수료"],
            "최종 금액": f_sales["합계"],
            "지출액": 0,
            "결제방식": f_sales["결제방식"],
            "수금상태": f_sales["수금상태"],
            "비고": ""
        })

    t_exp = pd.DataFrame()
    if not f_exp.empty:
        t_exp = pd.DataFrame({
            "삭제(체크)": False,
            "원본인덱스": f_exp["원본인덱스"],
            "날짜": f_exp["지출 일자"],
            "구분": "🔴 지출",
            "거래처/지출처": f_exp["지출처"],
            "출발지": "",
            "도착지": "",
            "지출항목": f_exp["지출 항목"],
            "운임료": 0,
            "매출 합계": 0,
            "수수료": 0,
            "최종 금액": 0,
            "지출액": f_exp["금액"],
            "결제방식": "",
            "수금상태": "",
            "비고": f_exp["비고"].fillna("").astype(str)
        })

    if not t_sales.empty or not t_exp.empty:
        df_total = pd.concat([t_sales, t_exp], ignore_index=True)
        df_total = df_total.sort_values(by="날짜", ascending=False).reset_index(drop=True)

        st.markdown("##### 🔍 엑셀형 다중 선택 필터 (원하는 항목을 클릭하여 자유롭게 검색하세요)")
        f1, f2, f3, f4, f5, f6 = st.columns(6)
        
        with f1:
            opt_type = df_total["구분"].unique().tolist()
            sel_type = st.multiselect("구분", opt_type, placeholder="전체 선택")
        with f2:
            opt_ven = [x for x in df_total["거래처/지출처"].unique().tolist() if x != ""]
            sel_ven = st.multiselect("거래처/지출처", opt_ven, placeholder="전체 선택")
        with f3:
            opt_ori = [x for x in df_total["출발지"].unique().tolist() if x != ""]
            sel_ori = st.multiselect("출발지", opt_ori, placeholder="전체 선택")
        with f4:
            opt_dest = [x for x in df_total["도착지"].unique().tolist() if x != ""]
            sel_dest = st.multiselect("도착지", opt_dest, placeholder="전체 선택")
        with f5:
            opt_pm = [x for x in df_total["결제방식"].unique().tolist() if x != ""]
            sel_pm = st.multiselect("결제방식", opt_pm, placeholder="전체 선택")
        with f6:
            opt_st = [x for x in df_total["수금상태"].unique().tolist() if x != ""]
            sel_st = st.multiselect("수금상태", opt_st, placeholder="전체 선택")

        if sel_type: df_total = df_total[df_total["구분"].isin(sel_type)]
        if sel_ven: df_total = df_total[df_total["거래처/지출처"].isin(sel_ven)]
        if sel_ori: df_total = df_total[df_total["출발지"].isin(sel_ori)]
        if sel_dest: df_total = df_total[df_total["도착지"].isin(sel_dest)]
        if sel_pm: df_total = df_total[df_total["결제방식"].isin(sel_pm)]
        if sel_st: df_total = df_total[df_total["수금상태"].isin(sel_st)]

        df_total = df_total.reset_index(drop=True)
        if not df_total.empty:
            df_total.insert(1, 'No', range(1, len(df_total) + 1))

        f_count = len(df_total)
        f_sales_sum = int(df_total[df_total["구분"] == "🟢 매출"]["최종 금액"].sum()) if not df_total.empty else 0
        f_exp_sum = int(df_total[df_total["구분"] == "🔴 지출"]["지출액"].sum()) if not df_total.empty else 0
        f_profit_sum = f_sales_sum - f_exp_sum

        st.success(f"**📌 검색 결과 요약:** 조회된 내역 총 **{f_count}건** ｜ 매출 합계 **{f_sales_sum:,}원** ｜ 지출 합계 **{f_exp_sum:,}원** ｜ 순수익 **{f_profit_sum:,}원**")
        st.caption("✅ 지우고 싶은 내역 앞의 체크박스(☑️)를 누르면 하단에 전용 삭제 버튼이 뜹니다.")
        
        # 💡 [핵심 기술] 표 데이터가 섞이지 않도록 동적 고유 식별자(Key)를 삽입했습니다.
        editor_key = f"table_editor_{len(df_total)}_{f_sales_sum}_{f_exp_sum}"
        
        edited_df = st.data_editor(
            df_total,
            use_container_width=True,
            hide_index=True,
            key=editor_key,
            column_config={
                "삭제(체크)": st.column_config.CheckboxColumn("삭제(체크)", default=False),
                "No": st.column_config.NumberColumn("No", format="%d"),
                "원본인덱스": None, 
                "운임료": st.column_config.NumberColumn(format="%d원"),
                "매출 합계": st.column_config.NumberColumn(format="%d원"),
                "수수료": st.column_config.NumberColumn(format="%d원"),
                "최종 금액": st.column_config.NumberColumn(format="%d원"),
                "지출액": st.column_config.NumberColumn(format="%d원")
            },
            disabled=["No", "날짜", "구분", "거래처/지출처", "출발지", "도착지", "지출항목", "운임료", "매출 합계", "수수료", "최종 금액", "지출액", "결제방식", "수금상태", "비고"]
        )

        to_delete = edited_df[edited_df["삭제(체크)"] == True]
        if len(to_delete) > 0:
            st.error(f"⚠️ {len(to_delete)}개의 내역을 삭제하도록 선택하셨습니다. (삭제 후에는 복구할 수 없습니다.)")
            if st.button("🗑️ 선택한 내역 완전히 삭제하기", type="primary"):
                df_raw_sales = conn.read(worksheet="매출", ttl="0")
                df_raw_exp = conn.read(worksheet="지출", ttl="0")
                
                sales_to_drop = to_delete[to_delete["구분"] == "🟢 매출"]["원본인덱스"].astype(int).tolist()
                exp_to_drop = to_delete[to_delete["구분"] == "🔴 지출"]["원본인덱스"].astype(int).tolist()
                
                if sales_to_drop:
                    df_raw_sales = df_raw_sales.drop(sales_to_drop).reset_index(drop=True)
                    conn.update(worksheet="매출", data=df_raw_sales)
                
                if exp_to_drop:
                    df_raw_exp = df_raw_exp.drop(exp_to_drop).reset_index(drop=True)
                    conn.update(worksheet="지출", data=df_raw_exp)
                
                st.rerun()
    else:
        st.info("선택하신 기간 내에 입출금 내역이 없습니다.")

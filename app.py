import streamlit as st
import os
from dotenv import load_dotenv
from utils.aws_helper import upload_exam, get_all_exams, delete_exam

# ローカル用設定読み込み
load_dotenv()

st.set_page_config(page_title="過去問掲示サイト", layout="wide", page_icon="📝")

# --- 1. ログインチェック機能 ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    def password_entered():
        correct_username = st.secrets.get("LOGIN_USERNAME") or os.getenv("LOGIN_USERNAME")
        correct_password = st.secrets.get("LOGIN_PASSWORD") or os.getenv("LOGIN_PASSWORD")

        if (st.session_state.get("username") == correct_username and 
            st.session_state.get("password") == correct_password):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.title("🔒 ログイン")
        with st.form("login_form"):
            st.text_input("ユーザー名", key="username")
            st.text_input("パスワード", type="password", key="password")
            st.form_submit_button("ログイン", on_click=password_entered, width='stretch')
        if st.session_state.get("password_correct") == False:
            st.error("😕 ユーザー名またはパスワードが正しくありません")
    return False

if not check_password():
    st.stop()

# --- 2. サイドバー (アップロード) ---
with st.sidebar:
    st.header("👤 ユーザー設定")
    if st.button("ログアウト", width='stretch', type="primary"):
        st.session_state["password_correct"] = False
        st.rerun()
    st.divider()
    
    st.header("📁 新規データ登録")
    with st.form("upload_form", clear_on_submit=True):
        subject = st.text_input("教科名 (例: 数学I)")
        year = st.number_input("年度", min_value=2000, max_value=2100, value=2026)
        uploaded_file = st.file_uploader("試験ファイル (PDF等)", type=["pdf", "png", "jpg", "jpeg"])
        if st.form_submit_button("アップロード", width='stretch'):
            if uploaded_file and subject:
                with st.spinner("アップロード中..."):
                    if upload_exam(uploaded_file, subject, year):
                        st.success("アップロード完了！")
                        st.cache_data.clear()
                        st.rerun()
            else:
                st.warning("教科名とファイルは必須です。")

# --- 3. データ取得と加工 ---
@st.cache_data(ttl=600)
def fetch_all_data():
    exams = get_all_exams()
    demo_pdf_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    demo_exams = [
        {"exam_id": "demo1", "subject": "【デモ】数学I", "year": 2023, "created_at": "2024-01-01T10:00:00", "file_url": demo_pdf_url, "file_key": "demo/1"},
        {"exam_id": "demo2", "subject": "【デモ】英語コミュニケーション", "year": 2022, "created_at": "2024-01-02T15:30:00", "file_url": demo_pdf_url, "file_key": "demo/2"}
    ]
    return demo_exams + exams

# --- 4. メインコンテンツ ---
st.title("📝 過去問掲示サイト")
all_exams = fetch_all_data()

c1, c2 = st.columns([3, 1])
with c1:
    search_query = st.text_input("🔍 教科名で検索", placeholder="教科名を入力...")
with c2:
    years = sorted(list(set(exam['year'] for exam in all_exams)), reverse=True)
    year_filter = st.selectbox("📅 年度で絞り込み", ["すべて"] + years)

filtered_exams = [
    e for e in all_exams 
    if search_query.lower() in e['subject'].lower() and 
    (year_filter == "すべて" or e['year'] == year_filter)
]
filtered_exams.sort(key=lambda x: x.get('created_at', ''), reverse=True)

st.header(f"🔍 登録済み一覧 ({len(filtered_exams)}件)")
if not filtered_exams:
    st.info("データが見つかりませんでした。")
else:
    h_cols = st.columns([2, 1, 2, 1, 1])
    headers = ["教科名", "年度", "登録日時", "表示", "削除"]
    for col, head in zip(h_cols, headers):
        col.write(f"**{head}**")
    st.divider()

    for i, exam in enumerate(filtered_exams):
        cols = st.columns([2, 1, 2, 1, 1])
        cols[0].write(exam['subject'])
        cols[1].write(f"{exam['year']}年度")
        
        raw_date = exam.get('created_at', '不明')
        created_at = raw_date[:16].replace('T', ' ') if 'T' in raw_date else raw_date
        cols[2].write(created_at)
        
        cols[3].link_button("開く", exam['file_url'], width='stretch')
        
        with cols[4]:
            if "demo" in str(exam.get('exam_id', '')):
                st.button("固定", key=f"fixed_{i}", disabled=True, width='stretch')
            else:
                with st.popover("削除", width='stretch'):
                    st.warning("削除しますか？")
                    # .get() を使うことで、項目がなくてもKeyErrorを防ぐ
                    e_id = exam.get('exam_id')
                    f_key = exam.get('file_key')
                    
                    if st.button("確定", key=f"del_{i}", type="primary", width='stretch'):
                        if e_id and f_key:
                            if delete_exam(e_id, f_key):
                                st.cache_data.clear()
                                st.rerun()
                        else:
                            st.error("削除に必要なデータ（ID等）が不足しています。")
        st.divider()

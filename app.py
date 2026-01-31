import streamlit as st
import os
from dotenv import load_dotenv
from utils.aws_helper import upload_exam, get_all_exams

# .envファイルを読み込む
load_dotenv()

# --- UI設定 ---
st.set_page_config(page_title="過去問掲示サイト", layout="wide", page_icon="📝")

# --- 1. ログインチェック機能 ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    def password_entered():
        correct_username = os.getenv("LOGIN_USERNAME") or st.secrets.get("auth", {}).get("username")
        correct_password = os.getenv("LOGIN_PASSWORD") or st.secrets.get("auth", {}).get("password")

        if (st.session_state["username"] == correct_username and 
            st.session_state["password"] == correct_password):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.title("🔒 Login")
        # フォームにすることでEnterキーでの送信を有効化
        with st.form("login_form"):
            st.text_input("ユーザー名", key="username")
            st.text_input("パスワード", type="password", key="password")
            st.form_submit_button("ログイン", on_click=password_entered, use_container_width=True)
        
        if st.session_state.get("password_correct") == False:
            st.error("😕 ユーザー名またはパスワードが正しくありません")
    return False

if not check_password():
    st.stop()

# --- 2. 共通サイドバー ---
with st.sidebar:
    st.header("👤 User")
    st.write(f"ログイン中: `{os.getenv('LOGIN_USERNAME', 'User')}`")
    if st.button("ログアウト", use_container_width=True, type="primary"):
        st.session_state["password_correct"] = False
        st.rerun()
    
    st.divider()
    
    st.header("📁 新規データ登録")
    with st.form("upload_form", clear_on_submit=True):
        subject = st.text_input("教科名 (例: 数学I)")
        year = st.number_input("年度", min_value=2000, max_value=2100, value=2026)
        uploaded_file = st.file_uploader("試験ファイル (PDF/画像)", type=["pdf", "png", "jpg", "jpeg"])
        submit_button = st.form_submit_button("アップロード", use_container_width=True)

        if submit_button:
            if uploaded_file and subject:
                with st.spinner("AWSへ送信中..."):
                    try:
                        if upload_exam(uploaded_file, subject, year):
                            st.success("アップロード完了！")
                            st.cache_data.clear() 
                            st.rerun()
                    except Exception as e:
                        st.error(f"エラーが発生しました: {e}")
            else:
                st.warning("教科名とファイルは必須です。")

# --- 3. データ取得 ---
@st.cache_data(ttl=600)
def fetch_all_data():
    try:
        # 実際の運用では get_all_exams() から取得
        exams = get_all_exams()
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        exams = []
    
    # デモデータの連結（本番環境では削除または条件分岐）
    demo_pdf_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    demo_exams = [
        {"subject": "【デモ】数学I", "year": 2023, "created_at": "2024-01-01T10:00:00", "file_url": demo_pdf_url},
        {"subject": "【デモ】英語コミュニケーション", "year": 2022, "created_at": "2024-01-02T15:30:00", "file_url": demo_pdf_url}
    ]
    return demo_exams + exams

# --- 4. メインコンテンツ ---
st.title("📝 過去問掲示サイト")

all_exams = fetch_all_data()

# フィルタリングUI
with st.container(border=True):
    c1, c2 = st.columns([3, 1])
    with c1:
        search_query = st.text_input("🔍 教科名で検索", placeholder="キーワードを入力...")
    with c2:
        available_years = sorted(list(set(exam['year'] for exam in all_exams)), reverse=True)
        year_filter = st.selectbox("📅 年度", ["すべて"] + available_years)

# データの絞り込み
filtered_exams = [
    e for e in all_exams 
    if search_query.lower() in e['subject'].lower() and 
    (year_filter == "all" or year_filter == "すべて" or e['year'] == year_filter)
]
filtered_exams.sort(key=lambda x: x.get('created_at', ''), reverse=True)

# 表示
st.subheader(f"登録済み一覧 ({len(filtered_exams)}件)")

if not filtered_exams:
    st.info("該当する過去問はまだありません。")
else:
    # テーブルのヘッダー
    h_col1, h_col2, h_col3, h_col4 = st.columns([3, 1, 2, 1])
    h_col1.caption("教科名")
    h_col2.caption("年度")
    h_col3.caption("登録日時")
    h_col4.caption("リンク")
    st.divider()

    for exam in filtered_exams:
        col1, col2, col3, col4 = st.columns([3, 1, 2, 1])
        col1.markdown(f"**{exam['subject']}**")
        col2.write(f"{exam['year']}")
        
        raw_date = exam.get('created_at', '不明')
        created_at = raw_date[:16].replace('T', ' ') if 'T' in raw_date else raw_date
        col3.write(created_at)
        
        col4.link_button("表示", exam['file_url'], use_container_width=True)

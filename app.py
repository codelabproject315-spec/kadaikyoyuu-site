import streamlit as st
import os
from dotenv import load_dotenv
from utils.aws_helper import upload_exam, get_all_exams

# .envファイルを読み込む
load_dotenv()

# --- UI設定 ---
st.set_page_config(page_title="過去問掲示サイト", layout="wide")

# --- 1. ログインチェック機能 ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    def password_entered():
        # 環境変数または st.secrets から取得
        correct_username = os.getenv("LOGIN_USERNAME") or st.secrets.get("auth", {}).get("username")
        correct_password = os.getenv("LOGIN_PASSWORD") or st.secrets.get("auth", {}).get("password")

        if (st.session_state["username"] == correct_username and 
            st.session_state["password"] == correct_password):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # セキュリティのため削除
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if not st.session_state.get("password_correct", False):
        _, col, _ = st.columns([1, 2, 1])
        with col:
            st.title("🔒 Login")
            st.text_input("ユーザー名", key="username")
            # Enterキーでも実行可能に
            st.text_input("パスワード", type="password", key="password", on_change=password_entered) 
            st.button("ログイン", on_click=password_entered, use_container_width=True)
            if st.session_state.get("password_correct") == False:
                st.error("😕 認証に失敗しました")
        return False
    return True

# ログインしていない場合は処理を停止
if not check_password():
    st.stop()

# --- 2. 共通サイドバー (ログアウト・アップロード) ---
with st.sidebar:
    st.header("👤 ユーザー設定")
    if st.button("ログアウト", use_container_width=True):
        st.session_state["password_correct"] = False
        st.rerun()
    
    st.divider()
    
    st.header("📁 新規データ登録")
    with st.form("upload_form", clear_on_submit=True):
        subject = st.text_input("教科名 (例: 数学I)")
        year = st.number_input("年度", min_value=2000, max_value=2100, value=2026)
        uploaded_file = st.file_uploader("試験ファイル (PDF等)", type=["pdf", "png", "jpg", "jpeg"])
        submit_button = st.form_submit_button("アップロード", use_container_width=True)

        if submit_button:
            if uploaded_file and subject:
                with st.spinner("アップロード中..."):
                    try:
                        if upload_exam(uploaded_file, subject, year):
                            st.success("アップロード完了！")
                            st.cache_data.clear() 
                            st.rerun()
                    except Exception as e:
                        st.error(f"エラー: {e}")
            else:
                st.warning("教科名とファイルは必須です。")

# --- 3. データ取得と加工 ---
@st.cache_data(ttl=600)
def fetch_all_data():
    try:
        exams = get_all_exams()
    except Exception as e:
        print(f"AWS Fetch Error: {e}")
        exams = []
    
    # デモデータ
    demo_pdf_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    demo_exams = [
        {"subject": "【デモ】数学I", "year": 2023, "created_at": "2024-01-01T10:00:00", "file_url": demo_pdf_url},
        {"subject": "【デモ】英語コミュニケーション", "year": 2022, "created_at": "2024-01-02T15:30:00", "file_url": demo_pdf_url}
    ]
    return demo_exams + exams

# --- 4. メインコンテンツ ---
st.title("📝 過去問掲示サイト")

all_exams = fetch_all_data()

st.header("🔍 登録済み試験一覧")
c1, c2 = st.columns([3, 1])
with c1:
    search_query = st.text_input("教科名で検索", placeholder="教科名を入力してください...")
with c2:
    years = sorted(list(set(exam['year'] for exam in all_exams)), reverse=True)
    year_filter = st.selectbox("年度で絞り込み", ["すべて"] + years)

# フィルタリング
filtered_exams = [
    e for e in all_exams 
    if search_query.lower() in e['subject'].lower() and 
    (year_filter == "すべて" or e['year'] == year_filter)
]
filtered_exams.sort(key=lambda x: x.get('created_at', ''), reverse=True)

# 一覧表示（改善されたテーブル表示）
if not filtered_exams:
    st.info("条件に一致するデータが見つかりませんでした。")
else:
    # 見出し
    h_col1, h_col2, h_col3, h_col4 = st.columns([3, 1, 2, 1])
    h_col1.write("**教科名**")
    h_col2.write("**年度**")
    h_col3.write("**登録日時**")
    h_col4.write("**操作**")
    st.divider()

    for i, exam in enumerate(filtered_exams):
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 1, 2, 1])
            with col1:
                # 教科名を強調
                st.markdown(f"**{exam['subject']}**")
            with col2:
                st.text(f"{exam['year']}年度")
            with col3:
                raw_date = exam.get('created_at', '不明')
                created_at = raw_date[:16].replace('T', ' ') if raw_date != '不明' else '不明'
                st.caption(f"📅 {created_at}")
            with col4:
                st.link_button("📄 表示", exam['file_url'], use_container_width=True)
            st.divider()

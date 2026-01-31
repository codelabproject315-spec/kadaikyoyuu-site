import streamlit as st
import os
from dotenv import load_dotenv
from utils.aws_helper import upload_exam, get_all_exams

# .envファイルを読み込む（ローカル開発用）
load_dotenv()

# --- UI設定 ---
st.set_page_config(page_title="過去問掲示サイト", layout="wide")

# --- 1. ログインチェック機能 ---
def check_password():
    """ユーザー名とパスワードが一致するか確認する関数"""
    def password_entered():
        # ローカル（.env）または クラウド（Secrets）から設定値を取得
        correct_username = os.getenv("LOGIN_USERNAME") or st.secrets.get("auth", {}).get("username")
        correct_password = os.getenv("LOGIN_PASSWORD") or st.secrets.get("auth", {}).get("password")

        if (
            st.session_state["username"] == correct_username
            and st.session_state["password"] == correct_password
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # セキュリティのため入力を消去
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # 初回アクセス時：中央にログインフォームを表示
        _, col, _ = st.columns([1, 2, 1])
        with col:
            st.title("🔒 ログインが必要です")
            st.text_input("ユーザー名", key="username")
            st.text_input("パスワード", type="password", key="password")
            st.button("ログイン", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        # 失敗時
        _, col, _ = st.columns([1, 2, 1])
        with col:
            st.title("🔒 ログインが必要です")
            st.text_input("ユーザー名", key="username")
            st.text_input("パスワード", type="password", key="password")
            st.button("ログイン", on_click=password_entered)
            st.error("😕 ユーザー名またはパスワードが正しくありません")
        return False
    else:
        # 成功時
        return True

# ログインが通るまでこれ以降のコードを実行させない
if not check_password():
    st.stop()

# --- 2. メインアプリ部分 (ログイン成功後のみ表示) ---
st.title("📝 過去問掲示サイト")

# サイドバー：新規登録
st.sidebar.header("新規データ登録")
with st.sidebar.form("upload_form", clear_on_submit=True):
    subject = st.text_input("教科名 (例: 数学I)")
    year = st.number_input("年度", min_value=2000, max_value=2100, value=2024)
    uploaded_file = st.file_uploader("試験ファイル (PDF等)", type=["pdf", "png", "jpg", "jpeg"])
    
    submit_button = st.form_submit_button("アップロード")

    if submit_button:
        if uploaded_file and subject:
            with st.spinner("アップロード中..."):
                try:
                    if upload_exam(uploaded_file, subject, year):
                        st.success("アップロード完了！")
                        st.rerun()
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")
        else:
            st.sidebar.warning("教科名とファイルは必須です。")

# メインエリア：一覧表示
st.header("登録済み試験一覧")

# AWSからデータを取得
try:
    exams = get_all_exams()
except Exception as e:
    st.error(f"データ取得エラー: {e}")
    exams = []

# --- デモデータ ---
demo_exams = [
    {
        "subject": "【デモ】数学I",
        "year": 2023,
        "created_at": "2024-01-01T10:00:00",
        "file_url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    },
    {
        "subject": "【デモ】英語コミュニケーション",
        "year": 2022,
        "created_at": "2024-01-02T15:30:00",
        "file_url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    }
]

# 実データと合体
all_exams = demo_exams + exams

if not all_exams:
    st.info("登録されているデータはまだありません。")
else:
    for exam in all_exams:
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 1, 3, 1])
            col1.write(f"**{exam['subject']}**")
            col2.write(f"{exam['year']}年度")
            
            created_at = exam.get('created_at', '不明')[:16].replace('T', ' ')
            col3.write(f"作成日: {created_at}")
            
            col4.link_button("ファイルを開く", exam['file_url'])
            st.divider()

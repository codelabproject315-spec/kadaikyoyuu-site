import streamlit as st
import os
import pandas as pd
from dotenv import load_dotenv
from utils.aws_helper import upload_exam, get_all_exams

# .envファイルを読み込む
load_dotenv()

# --- UI設定 ---
st.set_page_config(page_title="過去問掲示サイト Pro", layout="wide")

# --- 1. ログインチェック機能 (UX改善版) ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    def login_action():
        # secrets.toml または .env から取得
        correct_username = st.secrets.get("auth", {}).get("username") or os.getenv("LOGIN_USERNAME")
        correct_password = st.secrets.get("auth", {}).get("password") or os.getenv("LOGIN_PASSWORD")

        if (st.session_state["username"] == correct_username and 
            st.session_state["password"] == correct_password):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        st.title("🔒 ログイン")
        # フォームにすることでEnterキーでの送信に対応
        with st.form("login_form"):
            st.text_input("ユーザー名", key="username")
            st.text_input("パスワード", type="password", key="password")
            submit = st.form_submit_button("ログイン", use_container_width=True)
            if submit:
                login_action()
                if st.session_state.get("password_correct"):
                    st.rerun()
                else:
                    st.error("😕 ユーザー名またはパスワードが正しくありません")
    return False

if not check_password():
    st.stop()

# --- 2. 共通サイドバー (アップロード機能) ---
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
                with st.spinner("AWSへアップロード中..."):
                    try:
                        if upload_exam(uploaded_file, subject, year):
                            st.success("アップロード完了！")
                            st.cache_data.clear() # キャッシュをクリアして最新化
                            st.rerun()
                    except Exception as e:
                        st.error(f"アップロードエラー: {e}")
            else:
                st.warning("教科名とファイルは必須です。")

# --- 3. データ取得と加工 ---
@st.cache_data(ttl=600)
def fetch_all_data():
    try:
        exams = get_all_exams()
    except Exception as e:
        st.error(f"AWS接続エラー: {e}")
        exams = []
    
    # デモデータ
    demo_pdf_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    demo_exams = [
        {"subject": "【デモ】数学I", "year": 2023, "created_at": "2024-01-01T10:00:00", "file_url": demo_pdf_url},
        {"subject": "【デモ】英語コミュニケーション", "year": 2022, "created_at": "2024-01-02T15:30:00", "file_url": demo_pdf_url}
    ]
    return demo_exams + exams

# --- 4. メインコンテンツ (データフレーム版) ---
st.title("📝 過去問掲示サイト")

all_exams = fetch_all_data()
df = pd.DataFrame(all_exams)

# 列名の整理とフォーマット
if not df.empty:
    df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
    
    st.header("🔍 登録済み試験一覧")
    
    # フィルタリングUI
    c1, c2 = st.columns([3, 1])
    with c1:
        search_query = st.text_input("教科名で検索", placeholder="教科名を入力してください...")
    with c2:
        years = sorted(df['year'].unique().tolist(), reverse=True)
        year_filter = st.selectbox("年度で絞り込み", ["すべて"] + [int(y) for y in years])

    # フィルタリング実行
    filtered_df = df.copy()
    if search_query:
        filtered_df = filtered_df[filtered_df['subject'].str.contains(search_query, case=False)]
    if year_filter != "all" and year_filter != "すべて":
        filtered_df = filtered_df[filtered_df['year'] == year_filter]

    # インタラクティブなデータ表示
    st.data_editor(
        filtered_df,
        column_config={
            "subject": "教科名",
            "year": st.column_config.NumberColumn("年度", format="%d"),
            "created_at": "登録日時",
            "file_url": st.column_config.LinkColumn("ファイルリンク", display_text="開く")
        },
        hide_index=True,
        use_container_width=True,
        disabled=True # 閲覧専用
    )
else:
    st.info("データがまだ登録されていません。")

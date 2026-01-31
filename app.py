import streamlit as st
import os
from dotenv import load_dotenv
from utils.aws_helper import upload_exam, get_all_exams

load_dotenv()

# --- UI設定 ---
st.set_page_config(page_title="過去問掲示サイト", layout="wide")

# --- 1. ログインチェック機能 ---
def check_password():
    """ユーザーが認証済みかどうかを確認し、フォームを表示する"""
    if st.session_state.get("password_correct", False):
        return True

    def password_entered():
        # 環境変数またはSecretsから取得
        correct_username = os.getenv("LOGIN_USERNAME") or st.secrets.get("auth", {}).get("username")
        correct_password = os.getenv("LOGIN_PASSWORD") or st.secrets.get("auth", {}).get("password")

        if (st.session_state["username"] == correct_username and 
            st.session_state["password"] == correct_password):
            st.session_state["password_correct"] = True
            # 不要な情報を削除
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        st.title("🔒 Login")
        st.text_input("ユーザー名", key="username")
        st.text_input("パスワード", type="password", key="password")
        st.button("ログイン", on_click=password_entered, use_container_width=True)
        
        if st.session_state.get("password_correct") == False:
            st.error("😕 ユーザー名またはパスワードが正しくありません")
    return False

if not check_password():
    st.stop()

# --- 2. メインアプリ部分 ---
st.title("📝 過去問掲示サイト")

# サイドバー：新規登録
st.sidebar.header("📁 新規データ登録")
with st.sidebar.form("upload_form", clear_on_submit=True):
    subject = st.text_input("教科名 (例: 数学I)")
    year = st.number_input("年度", min_value=2000, max_value=2100, value=2026)
    uploaded_file = st.file_uploader("試験ファイル (PDF等)", type=["pdf", "png", "jpg", "jpeg"])
    submit_button = st.form_submit_button("アップロード", use_container_width=True)

    if submit_button:
        if uploaded_file and subject:
            with st.spinner("AWSへアップロード中..."):
                try:
                    # 成功時にTrueを返す想定
                    if upload_exam(uploaded_file, subject, year):
                        st.sidebar.success(f"『{subject}』を登録しました！")
                        st.rerun() # リストを更新するために再起動
                except Exception as e:
                    st.sidebar.error(f"アップロードエラー: {e}")
        else:
            st.sidebar.warning("教科名とファイルは必須です。")

# --- 3. データ取得 ---
@st.cache_data(ttl=600) # 10分間キャッシュ（頻繁なAPIコールを防ぐ）
def fetch_exams():
    try:
        return get_all_exams()
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        return []

exams = fetch_exams()

# デモデータの合算（本番では削除推奨）
demo_exams = [
    {"subject": "【デモ】数学I", "year": 2025, "created_at": "2026-01-01T10:00:00", "file_url": "#"},
]
all_exams = demo_exams + exams

# --- 4. 検索・フィルタリング ---
st.header("🔍 登録済み試験一覧")

c1, c2 = st.columns([3, 1])
with c1:
    search_query = st.text_input("教科名で検索", placeholder="例: 物理、英語...")
with c2:
    years = sorted(list(set(exam['year'] for exam in all_exams)), reverse=True)
    year_filter = st.selectbox("年度で絞り込み", ["すべて"] + years)

# フィルタリング
filtered = [
    e for e in all_exams 
    if search_query.lower() in e['subject'].lower() and 
    (year_filter == "すべて" or e['year'] == year_filter)
]
filtered.sort(key=lambda x: x.get('created_at', ''), reverse=True)

# --- 5. 表示 ---
if not filtered:
    st.info("条件に一致するデータはありません。")
else:
    # テーブル風のヘッダー
    cols = st.columns([2, 1, 2, 1])
    headers = ["教科名", "年度", "登録日時", "リンク"]
    for col, h in zip(cols, headers):
        col.write(f"**{h}**")
    st.divider()

    for exam in filtered:
        col1, col2, col3, col4 = st.columns([2, 1, 2, 1])
        col1.text(exam['subject'])
        col2.text(f"{exam['year']}年度")
        
        # フォーマット
        raw_date = exam.get('created_at', '不明')
        formatted_date = raw_date[:16].replace('T', ' ') if 'T' in raw_date else raw_date
        col3.text(formatted_date)
        
        if exam['file_url'] == "#":
            col4.button("無効", disabled=True, key=f"btn_{exam['subject']}_{exam['created_at']}")
        else:
            col4.link_button("開く", exam['file_url'], use_container_width=True)

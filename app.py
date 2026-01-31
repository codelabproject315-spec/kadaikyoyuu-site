import streamlit as st
import os
from dotenv import load_dotenv
from utils.aws_helper import upload_exam, get_all_exams, delete_exam

load_dotenv()

# --- UI設定 ---
st.set_page_config(page_title="過去問掲示サイト", layout="wide")

# --- 1. ログインチェック機能 ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    def password_entered():
        # 設定値を取得
        correct_username = os.getenv("LOGIN_USERNAME") or st.secrets.get("auth", {}).get("username")
        correct_password = os.getenv("LOGIN_PASSWORD") or st.secrets.get("auth", {}).get("password")
        admin_username = os.getenv("ADMIN_USERNAME") or st.secrets.get("auth", {}).get("admin_username")

        if (st.session_state["username"] == correct_username and 
            st.session_state["password"] == correct_password):
            
            st.session_state["password_correct"] = True
            
            # 管理者かどうかを判定してセッションに保存
            st.session_state["is_admin"] = (st.session_state["username"] == admin_username)
            
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.title("🔒 ログインが必要です")
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

# 管理者のみアップロードフォームを表示
if st.session_state.get("is_admin", False):
    st.sidebar.header("📁 管理者メニュー: 新規登録")
    with st.sidebar.form("upload_form", clear_on_submit=True):
        subject = st.text_input("教科名 (例: 数学I)")
        year = st.number_input("年度", min_value=2000, max_value=2100, value=2026)
        uploaded_file = st.file_uploader("試験ファイル (PDF等)", type=["pdf", "png", "jpg", "jpeg"])
        submit_button = st.form_submit_button("アップロード", use_container_width=True)

        if submit_button:
            if uploaded_file and subject:
                with st.spinner("アップロード中..."):
                    try:
                        if upload_exam(uploaded_file, subject, year):
                            st.sidebar.success("アップロード完了！")
                            st.cache_data.clear() 
                            st.rerun()
                    except Exception as e:
                        st.sidebar.error(f"エラー: {e}")
            else:
                st.sidebar.warning("教科名とファイルは必須です。")
else:
    st.sidebar.info("一般ユーザーとしてログイン中")

# --- 3. データ取得 ---
@st.cache_data(ttl=600)
def fetch_all_data():
    try:
        exams = get_all_exams()
    except:
        exams = []
    
    demo_pdf_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    demo_exams = [
        {"id": "demo1", "subject": "【デモ】数学I", "year": 2023, "created_at": "2024-01-01T10:00:00", "file_url": demo_pdf_url},
        {"id": "demo2", "subject": "【デモ】英語コミュニケーション", "year": 2022, "created_at": "2024-01-02T15:30:00", "file_url": demo_pdf_url}
    ]
    return demo_exams + exams

all_exams = fetch_all_data()

# --- 4. 検索・フィルタリング ---
st.header("🔍 登録済み試験一覧")
c1, c2 = st.columns([3, 1])
with c1:
    search_query = st.text_input("教科名で検索", placeholder="教科名を入力してください...")
with c2:
    available_years = sorted(list(set(exam['year'] for exam in all_exams)), reverse=True)
    year_filter = st.selectbox("年度で絞り込み", ["すべて"] + available_years)

filtered_exams = [
    e for e in all_exams 
    if search_query.lower() in e['subject'].lower() and 
    (year_filter == "すべて" or e['year'] == year_filter)
]
filtered_exams.sort(key=lambda x: x.get('created_at', ''), reverse=True)

# --- 5. 一覧表示 ---
if not filtered_exams:
    st.info("条件に一致するデータが見つかりませんでした。")
else:
    # 管理者の場合のみ「管理」列を追加
    is_admin = st.session_state.get("is_admin", False)
    if is_admin:
        cols_ratio = [2.5, 1, 2, 1, 1]
    else:
        cols_ratio = [2.5, 1, 2, 1]
    
    cols = st.columns(cols_ratio)
    cols[0].write("**教科名**")
    cols[1].write("**年度**")
    cols[2].write("**登録日時**")
    cols[3].write("**閲覧**")
    if is_admin:
        cols[4].write("**管理**")
    st.divider()

    for i, exam in enumerate(filtered_exams):
        row_cols = st.columns(cols_ratio)
        row_cols[0].write(exam['subject'])
        row_cols[1].write(f"{exam['year']}年度")
        
        created_at = exam.get('created_at', '不明')[:16].replace('T', ' ')
        row_cols[2].write(created_at)
        
        row_cols[3].link_button("開く", exam['file_url'], use_container_width=True)
        
        # 管理者のみ削除ボタンを表示
        if is_admin:
            if "id" in exam and str(exam["id"]).startswith("demo"):
                row_cols[4].button("固定", key=f"del_{i}", disabled=True, use_container_width=True)
            else:
                if row_cols[4].button("🗑️", key=f"del_{i}", use_container_width=True):
                    @st.dialog("削除の確認")
                    def confirm_delete(item):
                        st.warning(f"「{item['subject']}」を削除しますか？")
                        if st.button("実行", type="primary"):
                            if delete_exam(item):
                                st.success("削除しました")
                                st.cache_data.clear()
                                st.rerun()
                    confirm_delete(exam)
        st.divider()

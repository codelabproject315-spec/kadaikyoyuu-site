import streamlit as st
import os
from dotenv import load_dotenv
from utils.aws_helper import upload_exam, get_all_exams, delete_exam

load_dotenv()

st.set_page_config(page_title="過去問掲示サイト", layout="wide", page_icon="📝")

# --- 1. ログインチェック ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    def password_entered():
        correct_user = os.getenv("LOGIN_USERNAME") or st.secrets.get("auth", {}).get("username")
        correct_pw = os.getenv("LOGIN_PASSWORD") or st.secrets.get("auth", {}).get("password")
        if st.session_state["username"] == correct_user and st.session_state["password"] == correct_pw:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.title("🔒 Login")
        with st.form("login"):
            st.text_input("ユーザー名", key="username")
            st.text_input("パスワード", type="password", key="password")
            st.form_submit_button("ログイン", on_click=password_entered, use_container_width=True)
        if st.session_state.get("password_correct") == False:
            st.error("😕 認証に失敗しました")
    return False

if not check_password():
    st.stop()

# --- 2. サイドバー (アップロード) ---
with st.sidebar:
    st.header("👤 ユーザー設定")
    if st.button("ログアウト", use_container_width=True):
        st.session_state["password_correct"] = False
        st.rerun()
    st.divider()
    
    st.header("📁 新規登録")
    with st.form("upload_form", clear_on_submit=True):
        subject = st.text_input("教科名")
        year = st.number_input("年度", 2000, 2100, 2026)
        file = st.file_uploader("ファイル", type=["pdf", "png", "jpg"])
        if st.form_submit_button("アップロード", use_container_width=True):
            if file and subject:
                if upload_exam(file, subject, year):
                    st.success("成功！")
                    st.cache_data.clear()
                    st.rerun()
            else:
                st.warning("入力が足りません")

# --- 3. データ取得 ---
@st.cache_data(ttl=600)
def fetch_data():
    return get_all_exams()

# --- 4. メイン表示 ---
st.title("📝 過去問アーカイブ")
all_exams = fetch_data()

# 検索・フィルタ
c1, c2 = st.columns([3, 1])
with c1:
    q = st.text_input("🔍 教科名検索", placeholder="キーワード...")
with c2:
    years = sorted(list(set(e['year'] for e in all_exams)), reverse=True)
    y_filter = st.selectbox("📅 年度", ["すべて"] + years)

filtered = [
    e for e in all_exams 
    if q.lower() in e['subject'].lower() and (y_filter == "すべて" or e['year'] == y_filter)
]
filtered.sort(key=lambda x: x.get('created_at', ''), reverse=True)

# 一覧表示
st.subheader(f"一覧 ({len(filtered)}件)")
if not filtered:
    st.info("データがありません。")
else:
    # ヘッダー
    h_cols = st.columns([2, 1, 2, 1, 1])
    headers = ["教科名", "年度", "登録日時", "リンク", "操作"]
    for col, text in zip(h_cols, headers):
        col.caption(text)
    st.divider()

    for i, exam in enumerate(filtered):
        cols = st.columns([2, 1, 2, 1, 1])
        cols[0].markdown(f"**{exam['subject']}**")
        cols[1].write(exam['year'])
        cols[2].write(exam.get('created_at', '不明')[:16].replace('T', ' '))
        cols[3].link_button("開く", exam['file_url'], use_container_width=True)
        
        # 削除ボタン (Popoverで確認)
        with cols[4]:
            with st.popover("削除", use_container_width=True):
                st.error("データを削除しますか？")
                if st.button("確定", key=f"del_{i}", type="primary", use_container_width=True):
                    if delete_exam(exam['exam_id'], exam['file_key']):
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("失敗")
        st.divider()

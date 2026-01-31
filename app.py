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
            st.error("😕 認証に失敗しました")
    return False

if not check_password():
    st.stop()

# --- 2. サイドバー (登録) ---
with st.sidebar:
    st.header("👤 設定")
    if st.button("ログアウト", width='stretch', type="primary"):
        st.session_state["password_correct"] = False
        st.rerun()
    st.divider()
    
    st.header("📁 新規登録")
    with st.form("upload_form", clear_on_submit=True):
        subject = st.text_input("教科名")
        year = st.number_input("年度", 2000, 2100, 2026)
        file = st.file_uploader("ファイル", type=["pdf", "png", "jpg", "jpeg"])
        if st.form_submit_button("アップロード", width='stretch'):
            if file and subject:
                with st.spinner("処理中..."):
                    if upload_exam(file, subject, year):
                        st.success("完了！")
                        st.cache_data.clear()
                        st.rerun()
            else:
                st.warning("教科名とファイルは必須です。")

# --- 3. データ取得 ---
@st.cache_data(ttl=600)
def fetch_all_data():
    exams = get_all_exams()
    demo_pdf_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    demo_exams = [
        {"exam_id": "demo1", "subject": "【デモ】数学I", "year": 2023, "created_at": "2024-01-01T10:00:00", "file_url": demo_pdf_url, "file_key": "demo/1"},
        {"exam_id": "demo2", "subject": "【デモ】英語コミュニケーション", "year": 2022, "created_at": "2024-01-02T15:30:00", "file_url": demo_pdf_url, "file_key": "demo/2"}
    ]
    return demo_exams + exams

# --- 4. メイン ---
st.title("📝 過去問アーカイブ")
all_exams = fetch_all_data()

c1, c2 = st.columns([3, 1])
with c1:
    q = st.text_input("🔍 検索", placeholder="教科名...")
with c2:
    years = sorted(list(set(e['year'] for e in all_exams)), reverse=True)
    y_f = st.selectbox("📅 年度", ["すべて"] + years)

filtered = [
    e for e in all_exams 
    if q.lower() in e['subject'].lower() and (y_f == "すべて" or e['year'] == y_f)
]
filtered.sort(key=lambda x: x.get('created_at', ''), reverse=True)

st.header(f"一覧 ({len(filtered)}件)")
if not filtered:
    st.info("データがありません。")
else:
    h_cols = st.columns([2, 1, 2, 1, 1])
    for col, head in zip(h_cols, ["教科名", "年度", "登録日時", "表示", "削除"]):
        col.write(f"**{head}**")
    st.divider()

    for i, exam in enumerate(filtered):
        cols = st.columns([2, 1, 2, 1, 1])
        cols[0].write(exam['subject'])
        cols[1].write(f"{exam['year']}")
        
        # 日時整形
        raw_dt = exam.get('created_at', '不明')
        cols[2].write(raw_dt[:16].replace('T', ' ') if 'T' in raw_dt else raw_dt)
        
        cols[3].link_button("開く", exam['file_url'], width='stretch')
        
        # 削除ボタン
        with cols[4]:
            if "demo" in str(exam.get('exam_id', '')):
                st.button("固定", key=f"fixed_{i}", disabled=True, width='stretch')
            else:
                with st.popover("削除", width='stretch'):
                    st.warning("消去しますか？")
                    eid = exam.get('exam_id')
                    fkey = exam.get('file_key') # 取得できなくてもNoneが入る
                    
                    if st.button("確定", key=f"del_{i}", type="primary", width='stretch'):
                        # IDさえあれば削除を試みる
                        if eid:
                            if delete_exam(eid, fkey):
                                st.cache_data.clear()
                                st.rerun()
                        else:
                            st.error("ID不明のため削除不可")
        st.divider()

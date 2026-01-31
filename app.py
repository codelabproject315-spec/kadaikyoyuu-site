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
        # Secretsまたは環境変数から正解のパスワードを取得
        correct_password = st.secrets.get("LOGIN_PASSWORD") or os.getenv("LOGIN_PASSWORD")

        # パスワードが一致すればログインを許可
        if st.session_state.get("password") == correct_password:
            st.session_state["password_correct"] = True
            # 入力された任意のユーザー名を権限判定用に保存
            st.session_state["login_user"] = st.session_state["username"]
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.title("🔒 過去問アーカイブ")
        # 案内文を削除し、シンプルなフォームに
        with st.form("login_form"):
            st.text_input("ユーザー名", key="username", placeholder="ユーザー名を入力してください")
            st.text_input("パスワード", type="password", key="password", placeholder="パスワードを入力してください")
            st.form_submit_button("ログイン", on_click=password_entered, width='stretch')
        if st.session_state.get("password_correct") == False:
            st.error("😕 パスワードが正しくありません")
    return False

if not check_password():
    st.stop()

# --- 2. 共通サイドバー ---
with st.sidebar:
    current_user = st.session_state.get('login_user', 'guest')
    st.header("👤 ユーザー情報")
    st.write(f"ログイン中: **{current_user}**")
    
    # 権限の状態をサイドバーでさりげなく表示
    if current_user == "admin":
        st.success("管理者モード: 全操作が可能")
    else:
        st.info("一般モード: 閲覧と投稿が可能")

    if st.button("ログアウト", width='stretch', type="primary"):
        st.session_state["password_correct"] = False
        st.rerun()
    
    st.divider()
    
    st.header("📁 新規データ登録")
    with st.form("upload_form", clear_on_submit=True):
        subject = st.text_input("教科名")
        year = st.number_input("年度", min_value=2000, max_value=2100, value=2026)
        uploaded_file = st.file_uploader("ファイルを選択", type=["pdf", "png", "jpg", "jpeg"])
        if st.form_submit_button("アップロード", width='stretch'):
            if uploaded_file and subject:
                with st.spinner("処理中..."):
                    if upload_exam(uploaded_file, subject, year):
                        st.success("アップロード完了！")
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
        {"exam_id": "demo1", "subject": "【デモ】物理学基礎", "year": 2025, "created_at": "2025-10-23T10:00:00", "file_url": demo_pdf_url, "file_key": "demo/1"},
        {"exam_id": "demo2", "subject": "【デモ】プログラミング演習", "year": 2025, "created_at": "2025-12-07T15:30:00", "file_url": demo_pdf_url, "file_key": "demo/2"}
    ]
    return demo_exams + exams

# --- 4. メインコンテンツ ---
st.title("📝 過去問アーカイブ")
all_exams = fetch_all_data()

c1, c2 = st.columns([3, 1])
with c1:
    search_query = st.text_input("🔍 検索", placeholder="教科名を入力...")
with c2:
    years = sorted(list(set(exam['year'] for exam in all_exams)), reverse=True)
    year_filter = st.selectbox("📅 年度", ["すべて"] + years)

filtered_exams = [
    e for e in all_exams 
    if search_query.lower() in e['subject'].lower() and 
    (year_filter == "すべて" or e['year'] == year_filter)
]
filtered_exams.sort(key=lambda x: x.get('created_at', ''), reverse=True)

st.header(f"一覧 ({len(filtered_exams)}件)")
if not filtered_exams:
    st.info("該当するデータがありません。")
else:
    h_cols = st.columns([2, 1, 2, 1, 1])
    for col, head in zip(h_cols, ["教科名", "年度", "登録日時", "表示", "削除"]):
        col.write(f"**{head}**")
    st.divider()

    for i, exam in enumerate(filtered_exams):
        cols = st.columns([2, 1, 2, 1, 1])
        cols[0].write(exam['subject'])
        cols[1].write(f"{exam['year']}")
        
        raw_dt = exam.get('created_at', '不明')
        cols[2].write(raw_dt[:16].replace('T', ' ') if 'T' in raw_dt else raw_dt)
        
        cols[3].link_button("開く", exam['file_url'], width='stretch')
        
        with cols[4]:
            # デモデータ
            if "demo" in str(exam.get('exam_id', '')):
                st.button("固定", key=f"fixed_{i}", disabled=True, width='stretch')
            
            # 管理者 (admin) の場合のみ削除を許可
            elif st.session_state.get("login_user") == "admin":
                with st.popover("削除", width='stretch'):
                    st.warning("消去しますか？")
                    eid = exam.get('exam_id')
                    fkey = exam.get('file_key')
                    if st.button("確定", key=f"del_{i}", type="primary", width='stretch'):
                        if eid and delete_exam(eid, fkey):
                            st.cache_data.clear()
                            st.rerun()
            
            # それ以外のユーザー（削除ボタンを非表示にする、またはロックアイコンを表示）
            else:
                st.write("🔒")

        st.divider()

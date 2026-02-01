import streamlit as st
from utils.aws_helper import upload_exam, get_all_exams, delete_exam, get_demo_data

# ページの基本設定
st.set_page_config(page_title="過去問掲示サイト", layout="wide", page_icon="📝")

# --- 1. ログインチェック機能 ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    def password_entered():
        email_or_user = st.session_state.get("username", "").strip().lower()
        password = st.session_state.get("password", "")
        correct_password = st.secrets.get("LOGIN_PASSWORD")
        
        # ドメイン判定
        is_sit = email_or_user.endswith("@sit.ac.jp")
        is_utokyo = (
            email_or_user.endswith("@g.ecc.u-tokyo.ac.jp") or 
            email_or_user.endswith("@mail.u-tokyo.ac.jp")
        )
        is_admin_user = (email_or_user == "admin")
        
        if (is_sit or is_utokyo or is_admin_user) and password == correct_password:
            st.session_state["password_correct"] = True
            
            # 大学識別子の保存
            if is_sit:
                st.session_state["user_univ"] = "SIT"
            elif is_utokyo:
                st.session_state["user_univ"] = "UTokyo"
            else:
                st.session_state["user_univ"] = "ADMIN"

            st.session_state["login_user"] = email_or_user.split("@")[0]
            
            if "password" in st.session_state: del st.session_state["password"]
            if "username" in st.session_state: del st.session_state["username"]
            st.query_params.clear()
        else:
            st.session_state["password_correct"] = False
            st.session_state["login_error"] = True

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.title("🔒 過去問掲示板 ログイン")
        st.write("大学公式メールアドレス、または管理者アカウントでログインしてください。")
        
        if st.query_params.get("logged_out") == "true":
            st.info("✅ ログアウトしました。")
            st.query_params.clear()

        with st.form("login_form"):
            st.text_input("ユーザー名 / メールアドレス", key="username", placeholder="こちらに入力してください")
            st.text_input("パスワード", type="password", key="password", placeholder="パスワードを入力")
            st.form_submit_button("ログイン", on_click=password_entered, width='stretch')
        
        if st.session_state.get("login_error"):
            st.error("❌ 認証エラー: 許可されたドメインかパスワードを確認してください。")
            
    return False

if not check_password():
    st.stop()

# ユーザー情報の取得
current_user = st.session_state.get('login_user', 'guest')
user_univ = st.session_state.get('user_univ', 'UNKNOWN')
is_admin = (current_user.lower() == "admin")

# --- 2. 共通サイドバー ---
with st.sidebar:
    st.header("👤 ユーザー情報")
    if user_univ == "SIT":
        st.info("🏫 埼玉工業大学")
    elif user_univ == "UTokyo":
        st.success("🏫 東京大学")
    else:
        st.warning("🛠️ 管理者権限")

    st.write(f"ログイン中: **{current_user}**")
    
    if st.button("ログアウト", width='stretch', type="primary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.query_params["logged_out"] = "true"
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
                    if upload_exam(uploaded_file, subject, year, user_univ):
                        st.success("アップロード完了！")
                        st.cache_data.clear()
                        st.rerun()
            else:
                st.warning("教科名とファイルは必須です。")

# --- 3. データ取得 ---
@st.cache_data(ttl=600)
def fetch_filtered_data(univ):
    all_data = get_all_exams()
    
    # 実データのフィルタリング（自分の大学、またはadminなら全部）
    if univ == "ADMIN":
        real_exams = all_data
    else:
        real_exams = [e for e in all_data if e.get('university') == univ or 'university' not in e]
    
    # 共通のデモデータを取得
    demo_exams = get_demo_data()
    return demo_exams + real_exams

# --- 4. メインコンテンツ ---
st.title(f"📝 {user_univ} 過去問掲示板")
display_exams = fetch_filtered_data(user_univ)

c1, c2 = st.columns([3, 1])
with c1:
    search_query = st.text_input("🔍 検索", placeholder="教科名を入力...")
with c2:
    years = sorted(list(set(exam['year'] for exam in display_exams)), reverse=True)
    year_filter = st.selectbox("📅 年度", ["すべて"] + years)

filtered_exams = [
    e for e in display_exams 
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
            if "demo" in str(exam.get('exam_id', '')):
                st.button("固定", key=f"fixed_{i}", disabled=True, width='stretch')
            elif is_admin:
                with st.popover("削除", width='stretch'):
                    st.warning("消去しますか？")
                    if st.button("確定", key=f"del_{i}", type="primary", width='stretch'):
                        if delete_exam(exam.get('exam_id'), exam.get('file_key')):
                            st.cache_data.clear()
                            st.rerun()
            else:
                st.write("🔒")
        st.divider()

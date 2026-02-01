import streamlit as st
from utils.aws_helper import upload_exam, get_all_exams, delete_exam

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
        is_utokyo = email_or_user.endswith("@g.ecc.u-tokyo.ac.jp") or email_or_user.endswith("@mail.u-tokyo.ac.jp")
        is_admin_user = (email_or_user == "admin")
        
        if (is_sit or is_utokyo or is_admin_user) and password == correct_password:
            st.session_state["password_correct"] = True
            
            # 所属大学をセッションに保存
            if is_sit:
                st.session_state["user_univ"] = "SIT"
            elif is_utokyo:
                st.session_state["user_univ"] = "UTokyo"
            else:
                st.session_state["user_univ"] = "ADMIN" # adminは全データにアクセス可能

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
        with st.form("login_form"):
            st.text_input("ユーザー名 / メールアドレス", key="username", placeholder="こちらに入力してください")
            st.text_input("パスワード", type="password", key="password", placeholder="パスワードを入力")
            st.form_submit_button("ログイン", on_click=password_entered, width='stretch')
        if st.session_state.get("login_error"):
            st.error("❌ 認証エラー: 入力内容を確認してください。")
    return False

if not check_password():
    st.stop()

# ユーザー情報の取得
current_user = st.session_state.get('login_user', 'guest')
user_univ = st.session_state.get('user_univ', 'UNKNOWN')
is_admin = (current_user.lower() == "admin")

# --- 2. サイドバー ---
with st.sidebar:
    st.header("👤 ユーザー情報")
    # 大学名のバッジを表示
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
        st.rerun()
    
    st.divider()
    
    st.header("📁 新規データ登録")
    with st.form("upload_form", clear_on_submit=True):
        subject = st.text_input("教科名")
        year = st.number_input("年度", min_value=2000, max_value=2100, value=2026)
        uploaded_file = st.file_uploader("ファイルを選択", type=["pdf", "png", "jpg", "jpeg"])
        if st.form_submit_button("アップロード", width='stretch'):
            if uploaded_file and subject:
                # アップロード時に大学情報を付与（※aws_helper.pyに引数を追加する場合）
                if upload_exam(uploaded_file, subject, year, univ=user_univ):
                    st.success("アップロード完了！")
                    st.cache_data.clear()
                    st.rerun()

# --- 3. データ取得とフィルタリング ---
@st.cache_data(ttl=600)
def fetch_filtered_data(univ):
    all_data = get_all_exams()
    # ログインした大学のデータ、または大学情報がない古いデータのみを表示
    # adminの場合は全件表示
    if univ == "ADMIN":
        return all_data
    return [e for e in all_data if e.get('university') == univ or 'university' not in e]

# --- 4. メインコンテンツ ---
st.title(f"📝 {user_univ} 過去問ページ")
display_exams = fetch_filtered_data(user_univ)

# 検索・表示ロジックは以前と同じ（以下省略可能ですが、一覧表示部分は維持）
c1, c2 = st.columns([3, 1])
with c1:
    search_query = st.text_input("🔍 検索", placeholder="教科名を入力...")
with c2:
    years = sorted(list(set(exam['year'] for exam in display_exams)), reverse=True)
    year_filter = st.selectbox("📅 年度", ["すべて"] + years)

filtered_exams = [
    e for e in display_exams 
    if search_query.lower() in e['subject'].lower() and (year_filter == "すべて" or e['year'] == year_filter)
]

st.header(f"一覧 ({len(filtered_exams)}件)")
# ... (以下、テーブル表示部分は変更なし) ...
for i, exam in enumerate(filtered_exams):
    cols = st.columns([2, 1, 2, 1, 1])
    cols[0].write(exam['subject'])
    cols[1].write(f"{exam['year']}")
    raw_dt = exam.get('created_at', '不明')
    cols[2].write(raw_dt[:16].replace('T', ' ') if 'T' in raw_dt else raw_dt)
    cols[3].link_button("開く", exam['file_url'], width='stretch')
    with cols[4]:
        if is_admin:
            with st.popover("削除"):
                if st.button("確定", key=f"del_{i}", type="primary"):
                    if delete_exam(exam.get('exam_id'), exam.get('file_key')):
                        st.cache_data.clear()
                        st.rerun()
        else:
            st.write("🔒")
    st.divider()

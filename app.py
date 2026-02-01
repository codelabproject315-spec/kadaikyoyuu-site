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
        
        # --- ドメイン判定リスト ---
        # 資料に基づいたドメイン設定
        domain_map = {
            "sit.ac.jp": "SIT",
            "u-tokyo.ac.jp": "UTokyo",
            "g.ecc.u-tokyo.ac.jp": "UTokyo",
            "mail.u-tokyo.ac.jp": "UTokyo",
            "tohoku.ac.jp": "TOHOKU",
            "tsukuba.ac.jp": "TSUKUBA",
            "chiba-u.ac.jp": "CHIBA",
            "ynu.ac.jp": "YNU",
            "kyoto-u.ac.jp": "KYOTO",
            "osaka-u.ac.jp": "OSAKA",
            "kyushu-u.ac.jp": "KYUSHU"
        }

        user_domain = email_or_user.split("@")[-1] if "@" in email_or_user else ""
        
        # 認証ロジック
        if email_or_user == "admin" and password == correct_password:
            st.session_state["password_correct"] = True
            st.session_state["user_univ"] = "ADMIN"
            st.session_state["login_user"] = "admin"
        elif user_domain in domain_map and password == correct_password:
            st.session_state["password_correct"] = True
            st.session_state["user_univ"] = domain_map[user_domain]
            st.session_state["login_user"] = email_or_user.split("@")[0]
        else:
            st.session_state["password_correct"] = False
            st.session_state["login_error"] = True

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.title("🔒 過去問掲示板 ログイン")
        with st.form("login_form"):
            st.text_input("ユーザー名 / メールアドレス", key="username", placeholder="大学のメールアドレスを入力")
            st.text_input("パスワード", type="password", key="password")
            st.form_submit_button("ログイン", on_click=password_entered, width='stretch')
        if st.session_state.get("login_error"):
            st.error("❌ 認証エラー: 許可された大学ドメインかパスワードを確認してください。")
    return False

if not check_password():
    st.stop()

# ユーザー情報の取得
user_univ = st.session_state.get('user_univ', 'UNKNOWN')
current_user = st.session_state.get('login_user', 'guest')
is_admin = (user_univ == "ADMIN")

# --- 2. サイドバー ---
with st.sidebar:
    st.header("👤 ユーザー情報")
    st.info(f"🏫 所属: {user_univ}")
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
                if upload_exam(uploaded_file, subject, year, user_univ):
                    st.success("アップロード完了！")
                    st.cache_data.clear()
                    st.rerun()

# --- 3. データ取得とフィルタリング ---
@st.cache_data(ttl=600)
def fetch_filtered_data(univ):
    all_data = get_all_exams()
    # 実データのフィルタリング
    if univ == "ADMIN":
        real_exams = all_data
    else:
        real_exams = [e for e in all_data if e.get('university') == univ]
    
    # 共通デモデータを合体
    return get_demo_data() + real_exams

# --- 4. メインコンテンツ ---
st.title(f"📝 {user_univ} 過去問掲示板")
display_exams = fetch_filtered_data(user_univ)

# 検索と年度フィルタ
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

# 一覧表示
st.header(f"一覧 ({len(filtered_exams)}件)")
if is_admin:
    cols_width = [2, 1, 1, 2, 1, 1]
    headers = ["教科名", "大学", "年度", "登録日時", "表示", "削除"]
else:
    cols_width = [2, 1, 2, 1, 1]
    headers = ["教科名", "年度", "登録日時", "表示", "削除"]

h_cols = st.columns(cols_width)
for col, head in zip(h_cols, headers):
    col.write(f"**{head}**")
st.divider()

for i, exam in enumerate(filtered_exams):
    cols = st.columns(cols_width)
    cols[0].write(exam['subject'])
    
    idx = 1
    if is_admin:
        cols[idx].write(exam.get('university', '-'))
        idx += 1
    
    cols[idx].write(f"{exam['year']}")
    raw_dt = exam.get('created_at', '不明')
    cols[idx+1].write(raw_dt[:16].replace('T', ' ') if 'T' in raw_dt else raw_dt)
    cols[idx+2].link_button("開く", exam['file_url'], width='stretch')
    
    with cols[idx+3]:
        if "demo" in str(exam.get('exam_id', '')):
            st.button("固定", key=f"fixed_{i}", disabled=True, width='stretch')
        elif is_admin:
            if st.button("削除", key=f"del_{i}", type="primary"):
                if delete_exam(exam.get('exam_id'), exam.get('file_key')):
                    st.cache_data.clear()
                    st.rerun()
        else:
            st.write("🔒")
    st.divider()

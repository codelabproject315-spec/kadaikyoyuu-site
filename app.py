import streamlit as st
from utils.aws_helper import upload_exam, get_all_exams, delete_exam

# ページの基本設定
st.set_page_config(page_title="過去問掲示サイト", layout="wide", page_icon="📝")

# --- 1. ログインチェック機能 ---
def check_password():
    """認証済みならTrue、未認証ならログイン画面を表示してFalseを返す"""
    
    # すでにログイン済みかチェック
    if st.session_state.get("password_correct", False):
        return True

    def password_entered():
        """ログインボタンが押された時の処理"""
        # 入力値の取得
        email = st.session_state.get("username", "").strip()
        password = st.session_state.get("password", "")
        correct_password = st.secrets.get("LOGIN_PASSWORD")
        
        # --- ドメイン認証ロジック ---
        # 埼玉工業大学のドメイン（@sit.jp）で終わっているかチェック
        is_sit_email = email.lower().endswith("@sit.jp")
        
        # ドメインとパスワードの両方が正しい場合のみ許可
        if is_sit_email and password == correct_password:
            st.session_state["password_correct"] = True
            # メールアドレスの@より前をユーザー名として保持
            st.session_state["login_user"] = email.split("@")[0]
            # セッションから機密情報を削除
            if "password" in st.session_state: del st.session_state["password"]
            if "username" in st.session_state: del st.session_state["username"]
            if "login_error" in st.session_state: del st.session_state["login_error"]
            st.query_params.clear()
        else:
            st.session_state["password_correct"] = False
            # エラー原因を特定してメッセージを出し分ける
            if not is_sit_email:
                st.session_state["login_error"] = "DOMAIN_ERROR"
            else:
                st.session_state["login_error"] = "PASSWORD_ERROR"

    # ログイン画面のUI構成
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.title("🔒 SIT 過去問掲示板 ログイン")
        st.write("埼玉工業大学のアカウントでログインしてください。")
        
        # ログアウト直後のメッセージ表示
        if st.query_params.get("logged_out") == "true":
            st.info("✅ ログアウトしました。")
            st.query_params.clear()

        # ログインフォーム
        with st.form("login_form"):
            st.text_input("大学メールアドレス", key="username", placeholder="学籍番号@sit.jp")
            st.text_input("パスワード", type="password", key="password", placeholder="パスワードを入力")
            st.form_submit_button("ログイン", on_click=password_entered, width='stretch')

        # エラーフィードバック
        error_type = st.session_state.get("login_error")
        if error_type == "DOMAIN_ERROR":
            st.error("❌ 認証エラー: 埼玉工業大学（@sit.jp）のメールアドレスのみ使用可能です。")
        elif error_type == "PASSWORD_ERROR":
            st.error("😕 パスワードが正しくありません。")
            
    return False

# 認証が通らなければここで処理を止める
if not check_password():
    st.stop()


# --- 2. 共通サイドバー ---
with st.sidebar:
    current_user = st.session_state.get('login_user', 'guest')
    st.header("👤 ユーザー情報")
    st.write(f"ログイン中: **{current_user}**")
    
    # 特定のユーザー（例: admin または あなたの学籍番号）を管理者に設定
    if current_user == "admin":
        st.success("管理者モード: 全操作が可能")
    else:
        st.info("一般モード: 閲覧と投稿が可能")

    # ログアウトボタン
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
                    if upload_exam(uploaded_file, subject, year):
                        st.success("アップロード完了！")
                        st.cache_data.clear()
                        st.rerun()
            else:
                st.warning("教科名とファイルは必須です。")

# --- 3. データ取得 ---
@st.cache_data(ttl=600)
def fetch_all_data():
    # 実データ取得
    exams = get_all_exams()
    # デモデータ
    demo_pdf_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    demo_exams = [
        {"exam_id": "demo1", "subject": "【デモ】数学", "year": 2025, "created_at": "2025-10-23T10:00:00", "file_url": demo_pdf_url, "file_key": "demo/1"},
        {"exam_id": "demo2", "subject": "【デモ】英語コミュニケーション", "year": 2023, "created_at": "2025-12-07T15:30:00", "file_url": demo_pdf_url, "file_key": "demo/2"}
    ]
    return demo_exams + exams

# --- 4. メインコンテンツ ---
st.title("📝 過去問掲示サイト")
all_exams = fetch_all_data()

# 検索とフィルタ
c1, c2 = st.columns([3, 1])
with c1:
    search_query = st.text_input("🔍 検索", placeholder="教科名を入力...")
with c2:
    years = sorted(list(set(exam['year'] for exam in all_exams)), reverse=True)
    year_filter = st.selectbox("📅 年度", ["すべて"] + years)

# フィルタリング適用
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
    # テーブル表示
    h_cols = st.columns([2, 1, 2, 1, 1])
    titles = ["教科名", "年度", "登録日時", "表示", "削除"]
    for col, head in zip(h_cols, titles):
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
            elif st.session_state.get("login_user") == "admin":
                with st.popover("削除", width='stretch'):
                    st.warning("消去しますか？")
                    if st.button("確定", key=f"del_{i}", type="primary", width='stretch'):
                        if delete_exam(exam.get('exam_id'), exam.get('file_key')):
                            st.cache_data.clear()
                            st.rerun()
            else:
                st.write("🔒")
        st.divider()

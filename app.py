import streamlit as st
from utils.aws_helper import upload_exam, get_all_exams, delete_exam

st.set_page_config(page_title="過去問掲示サイト", layout="wide", page_icon="📝")

# --- 1. ログインチェック機能 ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    def password_entered():
        # ★追加：入力されたらログアウトメッセージを消す
        if "logged_out" in st.query_params:
            del st.query_params["logged_out"]
            
        correct_password = st.secrets.get("LOGIN_PASSWORD")
        if st.session_state.get("password") == correct_password:
            st.session_state["password_correct"] = True
            st.session_state["login_user"] = st.session_state["username"]
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.title("🔒 ログイン")
        
        # ★追加：ログアウト直後だけ青いメッセージを出す
        if st.query_params.get("logged_out") == "true":
            st.info("✅ ログアウトしました。")

        with st.form("login_form"):
            st.text_input("ユーザー名", key="username", placeholder="ユーザー名を入力してください")
            st.text_input("パスワード", type="password", key="password", placeholder="パスワードを入力してください")
            st.form_submit_button("ログイン", on_click=password_entered, width='stretch')
        
        # ★修正：パスワードが空（ログアウト直後など）の時はエラーを出さない
        if st.session_state.get("password_correct") == False and st.session_state.get("password") not in [None, ""]:
            st.error("😕 パスワードが正しくありません")
    return False

if not check_password():
    st.stop()

# --- 2. 共通サイドバー ---
with st.sidebar:
    current_user = st.session_state.get('login_user', 'guest')
    st.header("👤 ユーザー情報")
    st.write(f"ログイン中: **{current_user}**")
    
    if current_user == "admin":
        st.success("管理者モード: 全操作が可能")
    else:
        st.info("一般モード: 閲覧と投稿が可能")

    # --- サイドバー内のログアウトボタン部分 ---
    if st.button("ログアウト", width='stretch', type="primary"):
        # セッション状態（入力内容など）をすべて削除
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # URLに「ログアウトしたよ」という印を付けてリロード
        st.query_params["logged_out"] = "true"
        st.rerun()
    
    st.divider()
    
    st.header("📁 新規データ登録")
    with st.form("upload_form", clear_on_submit=True):
        subject = st.text_input("教科名")
        year = st.number_input("年度", min_value=2000, max_value=2100, value=2024)
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
# 署名付きURLの期限（1時間）より短い30分(1800秒)でキャッシュ更新
@st.cache_data(ttl=1800)
def fetch_all_data():
    exams = get_all_exams()
    demo_pdf_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    demo_exams = [
        {"exam_id": "demo1", "subject": "【デモ】数学", "year": 2024, "created_at": "2024-10-23T10:00:00", "file_url": demo_pdf_url, "file_key": "demo/1"},
        {"exam_id": "demo2", "subject": "【デモ】英語", "year": 2023, "created_at": "2024-12-07T15:30:00", "file_url": demo_pdf_url, "file_key": "demo/2"}
    ]
    return demo_exams + exams

# --- 4. メインコンテンツ ---
st.title("📝 過去問掲示サイト")
all_exams = fetch_all_data()

c1, c2 = st.columns([3, 1])
with c1:
    search_query = st.text_input("🔍 検索", placeholder="教科名を入力...")
with c2:
    years = sorted(list(set(int(exam['year']) for exam in all_exams)), reverse=True)
    year_filter = st.selectbox("📅 年度", ["すべて"] + years)

filtered_exams = [
    e for e in all_exams 
    if search_query.lower() in e['subject'].lower() and 
    (year_filter == "すべて" or int(e['year']) == year_filter)
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
        
        cols[3].link_button("開く", exam.get('file_url', '#'), width='stretch')
        
        with cols[4]:
            if "demo" in str(exam.get('exam_id', '')):
                st.button("固定", key=f"fixed_{i}", disabled=True, width='stretch')
            elif st.session_state.get("login_user") == "admin":
                with st.popover("削除", width='stretch'):
                    st.warning("消去しますか？")
                    eid = exam.get('exam_id')
                    fkey = exam.get('file_key')
                    if st.button("確定", key=f"del_{i}", type="primary", width='stretch'):
                        if eid and delete_exam(eid, fkey):
                            st.cache_data.clear()
                            st.rerun()
            else:
                st.write("🔒")
        st.divider()

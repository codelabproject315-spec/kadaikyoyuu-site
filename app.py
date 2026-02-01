import streamlit as st
import re
from utils.aws_helper import upload_exam, get_all_exams, delete_exam

# --- ページ設定 ---
st.set_page_config(page_title="大学別過去問ポータル", layout="wide", page_icon="📝")

# --- 大学ドメインの定義 (資料を基に構成) ---
# [cite: 6, 21, 25]
UNIVERSITY_DOMAINS = {
    "sit.ac.jp": "埼玉工業大学",       # 
    "gunma-u.ac.jp": "群馬大学",       # 
    "waseda.jp": "早稲田大学",         # [cite: 27]
    "tsukuba.ac.jp": "筑波大学",       # 
    "keio.ac.jp": "慶應義塾大学"       # [cite: 24]
}

def get_university_info(email):
    """
    メールアドレスからドメインを抽出し、大学名とIDを返す
    """
    match = re.search(r"@([\w\.-]+)$", email)
    if not match:
        return None, None
    
    domain = match.group(1).lower()
    
    # 辞書から大学名を取得
    univ_name = UNIVERSITY_DOMAINS.get(domain)
    
    # 資料にある www. 付きのドメイン形式への対応 [cite: 6, 10]
    if not univ_name:
        univ_name = UNIVERSITY_DOMAINS.get(f"www.{domain}")
        
    return univ_name, domain

# --- 1. ログイン・認証機能 ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    def login_entered():
        email = st.session_state.get("email_input", "").strip()
        password = st.session_state.get("password_input", "")
        
        univ_name, domain_id = get_university_info(email)
        correct_password = st.secrets.get("LOGIN_PASSWORD")
        
        if univ_name and password == correct_password:
            st.session_state["password_correct"] = True
            st.session_state["login_user"] = email
            st.session_state["univ_name"] = univ_name
            st.session_state["univ_id"] = domain_id
            # 入力情報をクリア
            st.session_state["email_input"] = ""
            st.session_state["password_input"] = ""
        else:
            st.session_state["password_correct"] = False
            if not univ_name:
                st.error("❌ 登録されていない大学ドメインです。")
            else:
                st.error("❌ パスワードが正しくありません。")

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.title("🔒 ログイン")
        st.info("所属大学のメールアドレスでログインしてください。")
        
        with st.form("login_form"):
            st.text_input("大学メールアドレス", key="email_input", placeholder="user@sit.ac.jp")
            st.text_input("パスワード", type="password", key="password_input")
            st.form_submit_button("ログイン", on_click=login_entered)
            
    return False

if not check_password():
    st.stop()

# --- 2. サイドバー (ユーザー情報とアップロード) ---
with st.sidebar:
    univ_name = st.session_state.get("univ_name")
    univ_id = st.session_state.get("univ_id")
    
    st.header("👤 ユーザー情報")
    st.success(f"所属: **{univ_name}**")
    st.write(f"ID: {st.session_state.get('login_user')}")
    
    if st.button("ログアウト", type="primary", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    st.divider()
    
    st.header("📁 新規過去問投稿")
    with st.form("upload_form", clear_on_submit=True):
        subject = st.text_input("教科名")
        year = st.number_input("年度", min_value=2000, max_value=2100, value=2024)
        file = st.file_uploader("ファイル(PDF/画像)", type=["pdf", "png", "jpg"])
        
        if st.form_submit_button("アップロード", use_container_width=True):
            if file and subject:
                with st.spinner("送信中..."):
                    # 大学ID(univ_id)を付与してアップロード
                    if upload_exam(file, subject, year, univ_id):
                        st.success(f"{univ_name}のデータとして保存しました！")
                        st.cache_data.clear()
                        st.rerun()
            else:
                st.warning("教科名とファイルは必須です。")

# --- 3. データ取得とフィルタリング ---
@st.cache_data(ttl=1800)
def fetch_my_university_data(target_univ_id):
    """
    全データから自分の大学IDに一致するものだけを抽出する
    """
    all_exams = get_all_exams()
    # 他大学のデータが混ざらないよう厳密にフィルタリング
    return [e for e in all_exams if e.get("university_id") == target_univ_id]

# --- 4. メインコンテンツ表示 ---
st.title(f"📝 {st.session_state['univ_name']} 過去問ポータル")
st.caption(f"現在は {st.session_state['univ_id']} ドメインのデータのみ表示しています。")

my_exams = fetch_my_university_data(st.session_state["univ_id"])

# 検索バー
search_q = st.text_input("🔍 学内過去問を検索", placeholder="教科名を入力...")
filtered = [e for e in my_exams if search_q.lower() in e['subject'].lower()]
filtered.sort(key=lambda x: x.get('year', ''), reverse=True)

# 一覧表示
st.header(f"過去問リスト ({len(filtered)}件)")

if not filtered:
    st.info(f"{st.session_state['univ_name']} の過去問はまだ登録されていません。")
else:
    # テーブル形式の表示
    cols = st.columns([3, 1, 2, 1])
    headers = ["教科名", "年度", "登録ID", "アクション"]
    for col, head in zip(cols, headers):
        col.write(f"**{head}**")
    st.divider()

    for i, exam in enumerate(filtered):
        c = st.columns([3, 1, 2, 1])
        c[0].write(exam['subject'])
        c[1].write(str(exam['year']))
        c[2].write(f"`{exam['exam_id'][:15]}...`") # キーの一部を表示
        
        # 閲覧ボタン
        c[3].link_button("開く", exam.get('file_url', '#'), use_container_width=True)
        st.divider()

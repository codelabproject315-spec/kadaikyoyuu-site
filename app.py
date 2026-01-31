import streamlit as st
from utils.aws_helper import upload_exam, get_all_exams

# --- UI設定 ---
st.set_page_config(page_title="過去問掲示サイト", layout="wide")

# --- 1. ログインチェック機能 ---
def check_password():
    """ユーザー名とパスワードが一致するか確認する関数"""
    def password_entered():
        # st.secrets から設定値を取得（.streamlit/secrets.toml または 管理画面の設定）
        auth_secrets = st.secrets.get("auth", {})
        correct_username = auth_secrets.get("username")
        correct_password = auth_secrets.get("password")

        if (
            st.session_state["username"] == correct_username
            and st.session_state["password"] == correct_password
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # セキュリティのため入力を消去
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        _, col, _ = st.columns([1, 2, 1])
        with col:
            st.title("🔒 ログインが必要です")
            st.text_input("ユーザー名", key="username")
            st.text_input("パスワード", type="password", key="password")
            st.button("ログイン", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        _, col, _ = st.columns([1, 2, 1])
        with col:
            st.title("🔒 ログインが必要です")
            st.text_input("ユーザー名", key="username")
            st.text_input("パスワード", type="password", key="password")
            st.button("ログイン", on_click=password_entered)
            st.error("😕 ユーザー名またはパスワードが正しくありません")
        return False
    else:
        return True

# ログインが通るまでこれ以降のコードを実行させない
if not check_password():
    st.stop()

# --- 2. メインアプリ部分 (ログイン成功後のみ表示) ---
st.title("📝 過去問掲示サイト")

# サイドバー：新規登録
st.sidebar.header("新規データ登録")
with st.sidebar.form("upload_form", clear_on_submit=True):
    subject = st.text_input("教科名 (例: 数学I)")
    year = st.number_input("年度", min_value=2000, max_value=2100, value=2024)
    uploaded_file = st.file_uploader("試験ファイル (PDF等)", type=["pdf", "png", "jpg", "jpeg"])
    
    submit_button = st.form_submit_button("アップロード")

    if submit_button:
        if uploaded_file and subject:
            with st.spinner("アップロード中..."):
                try:
                    if upload_exam(uploaded_file, subject, year):
                        st.success("アップロード完了！")
                        st.rerun()
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")
        else:
            st.sidebar.warning("教科名とファイルは必須です。")

# --- 3. データ取得と加工 ---
try:
    exams = get_all_exams()
except Exception as e:
    st.error(f"データ取得エラー: {e}")
    exams = []

# デモデータ
demo_exams = [
    {"subject": "【デモ】数学I", "year": 2023, "created_at": "2024-01-01T10:00:00", "file_url": "#"},
    {"subject": "【デモ】英語コミュニケーション", "year": 2022, "created_at": "2024-01-02T15:30:00", "file_url": "#"}
]

all_exams = demo_exams + exams

# --- 4. 検索・フィルタリング UI ---
st.header("登録済み試験一覧")

# 検索バーと年度フィルターを横並びに配置
c1, c2 = st.columns([3, 1])
with c1:
    search_query = st.text_input("🔍 教科名で検索", placeholder="教科名を入力してください...")
with c2:
    # データの年度をリスト化（重複排除）
    years = [exam['year'] for exam in all_exams]
    available_years = sorted(list(set(years)), reverse=True)
    year_filter = st.selectbox("年度で絞り込み", ["すべて"] + available_years)

# フィルタリング処理
filtered_exams = []
for exam in all_exams:
    match_subject = search_query.lower() in exam['subject'].lower()
    match_year = (year_filter == "すべて") or (exam['year'] == year_filter)
    if match_subject and match_year:
        filtered_exams.append(exam)

# ソート処理（新しいアップロード順）
filtered_exams.sort(key=lambda x: x.get('created_at', ''), reverse=True)

# --- 5. 一覧表示 ---
if not filtered_exams:
    st.info("条件に一致するデータが見つかりませんでした。")
else:
    # ヘッダー行
    h_col1, h_col2, h_col3, h_col4 = st.columns([2, 1, 2, 1])
    h_col1.write("**教科名**")
    h_col2.write("**年度**")
    h_col3.write("**登録日時**")
    h_col4.write("**アクション**")
    st.divider()

    for exam in filtered_exams:
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 1, 2, 1])
            col1.write(exam['subject'])
            col2.write(f"{exam['year']}年度")
            
            # 日時フォーマットの整形
            created_at = exam.get('created_at', '不明')[:16].replace('T', ' ')
            col3.write(created_at)
            
            col4.link_button("開く", exam['file_url'], use_container_width=True)
            st.divider()

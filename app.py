import streamlit as st
from utils.aws_helper import upload_exam, get_all_exams

# --- UI部分 (Streamlit) ---
st.set_page_config(page_title="過去問掲示サイト", layout="wide")
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
            st.warning("教科名とファイルは必須です。")

# メインエリア：一覧表示
st.header("登録済み試験一覧")

# AWSからデータを取得
try:
    exams = get_all_exams()
except Exception as e:
    st.error(f"データ取得エラー: {e}")
    exams = []

# --- デモデータの追加 ---
demo_exams = [
    {
        "subject": "【デモ】数学I",
        "year": 2023,
        "created_at": "2024-01-01T10:00:00",
        "file_url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    },
    {
        "subject": "【デモ】英語コミュニケーション",
        "year": 2022,
        "created_at": "2024-01-02T15:30:00",
        "file_url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    }
]

# デモと実データを合体
all_exams = demo_exams + exams

if not all_exams:
    st.info("登録されているデータはまだありません。")
else:
    for exam in all_exams:
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 1, 3, 1])
            col1.write(f"**{exam['subject']}**")
            col2.write(f"{exam['year']}年度")
            
            # 日時を整形（Tを除去、秒まで表示）
            created_at = exam.get('created_at', '不明')[:16].replace('T', ' ')
            col3.write(f"作成日: {created_at}")
            
            col4.link_button("ファイルを開く", exam['file_url'])
            st.divider()
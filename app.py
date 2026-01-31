import streamlit as st
from utils.aws_helper import upload_exam, get_all_exams

st.set_page_config(page_title="過去問シェア", layout="wide")
st.title("📚 過去問掲示板")

tab1, tab2 = st.tabs(["🔍 閲覧・検索", "📤 投稿"])

# --- 閲覧機能 ---
with tab1:
    st.header("過去問リスト")
    exams = get_all_exams()
    
    if not exams:
        st.info("まだ投稿がありません。")
    else:
        for exam in exams:
            with st.container():
                col1, col2, col3 = st.columns([2, 1, 1])
                col1.write(f"**{exam['subject']}** ({exam['year']}年度)")
                col2.write(exam['created_at'][:10])
                col3.link_button("PDFを開く", exam['file_url'])
                st.divider()

# --- 投稿機能 ---
with tab2:
    st.header("新しい過去問を投稿")
    with st.form("upload_form"):
        subject = st.text_input("科目名 (例: 線形代数)")
        year = st.number_input("年度", min_value=2000, max_value=2026, value=2024)
        file = st.file_uploader("ファイルを選択 (PDF推奨)", type=["pdf", "png", "jpg"])
        
        submit = st.form_submit_button("アップロード")
        
        if submit:
            if subject and file:
                with st.spinner("アップロード中..."):
                    upload_exam(file, subject, year)
                    st.success("投稿完了！")
                    st.rerun()
            else:
                st.error("科目名とファイルは必須です。")
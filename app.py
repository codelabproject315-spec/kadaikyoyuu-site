# --- 1. ログインチェック機能 ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    def password_entered():
        # .get() を使うことで、キーがない場合に KeyError になるのを防ぎます
        entered_username = st.session_state.get("username", "")
        entered_password = st.session_state.get("password", "")

        # 環境変数または st.secrets から取得
        correct_username = os.getenv("LOGIN_USERNAME") or st.secrets.get("auth", {}).get("username")
        correct_password = os.getenv("LOGIN_PASSWORD") or st.secrets.get("auth", {}).get("password")

        if (entered_username == correct_username and 
            entered_password == correct_password):
            st.session_state["password_correct"] = True
            # セキュリティのため入力をクリア
            st.session_state["password"] = ""
            st.session_state["username"] = ""
        else:
            st.session_state["password_correct"] = False

    if not st.session_state.get("password_correct", False):
        _, col, _ = st.columns([1, 2, 1])
        with col:
            st.title("🔒 Login")
            # 順番：まず入力欄を定義（これでsession_stateにキーが作られる）
            st.text_input("ユーザー名", key="username")
            st.text_input("パスワード", type="password", key="password", on_change=password_entered) 
            st.button("ログイン", on_click=password_entered, use_container_width=True)
            
            if st.session_state.get("password_correct") == False:
                st.error("😕 認証に失敗しました")
        return False
    return True

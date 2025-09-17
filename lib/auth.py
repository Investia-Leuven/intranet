from lib.backend import check_credentials, get_member_name
from dotenv import load_dotenv
import streamlit as st

def login_screen():
    load_dotenv()

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if check_credentials(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.display_name = get_member_name(username)
                st.rerun()
            else:
                st.error("Invalid username or password")
        st.stop()

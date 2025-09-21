"""
Authentication logic for the Investia Intranet application.
Handles user login and sets authentication status in Streamlit session state.
"""
from lib.backend import check_credentials, get_member_name
from dotenv import load_dotenv
import streamlit as st

def login_screen():
    """
    Display the login screen and authenticate users.
    If credentials are valid, update session state and rerun the app.
    """
    # Load environment variables (if needed for authentication)
    load_dotenv()

    # Initialise authentication flag in session state
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        # Display login form
        st.title("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            # Verify credentials and update session state
            if check_credentials(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.display_name = get_member_name(username)
                st.rerun()
            else:
                st.error("Invalid username or password")
        st.stop()

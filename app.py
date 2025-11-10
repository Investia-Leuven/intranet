"""
Main application file for the Investia Intranet Streamlit app.
Handles layout, routing, authentication, and page composition.
"""
import streamlit as st
import logging
from dotenv import load_dotenv

from lib.config import CALENDAR_URL_FULL, CALENDAR_URL_AGENDA, TOOL_LINKS
from lib.ui.auth import login_screen
from lib.ui.header import render_header
from lib.ui.footer import render_footer
from lib.ui.tools import render_internal_tools_section
from lib.ui.calendar import render_calendar_section
from lib.ui.announcements import render_announcement_section
from lib.ui.news import render_news_section
from lib.ui.settings import render_settings_page
from lib.cookies import restore_session_from_cookie, clear_auth_cookie
from extra_streamlit_components import CookieManager

# Ensure the CookieManager front-end component mounts so set/get work reliably
if "_cookie_manager" not in st.session_state:
    st.session_state._cookie_manager = CookieManager()
# Trigger a no-op read to mount the component in the browser
st.session_state._cookie_manager.get("init")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
def require_auth(func):
    """Decorator to enforce authentication before accessing a function."""
    def wrapper(*args, **kwargs):
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False
        # Try restoring the session from cookie before showing login
        if not st.session_state.authenticated:
            if restore_session_from_cookie():
                logger.info("Session restored from cookie")
        if not st.session_state.authenticated:
            login_screen()
            st.stop()
        logger.info("User authenticated")
        return func(*args, **kwargs)
    return wrapper

@st.cache_resource
def load_environment():
    """Load environment variables from .env file."""
    load_dotenv()

def logout():
    """Clear auth cookie and session, then rerun the app."""
    clear_auth_cookie()
    st.session_state.clear()
    st.rerun()

@require_auth
def main():
    """Main function to assemble and display the intranet interface."""
    logger.info("App started")
    st.set_page_config(page_title="Investia Intranet", page_icon="extra/investia_favicon.png", layout="wide")

    if "page" not in st.session_state: st.session_state.page = "home"
    if st.session_state.page == "settings":
        render_settings_page()
        return

    load_environment()
    logger.info("Environment loaded")

    render_header()
    st.markdown("")
    username = st.session_state.get("display_name", "member")
    st.markdown("")
    st.markdown(
        f"<p style='color:darkblue;'>Welcome {username} on Investia's intranet. From this page you can navigate to all internal digital tools.</p>",
        unsafe_allow_html=True
    )

    render_internal_tools_section()

    col1, col2 = st.columns(2)
    with col1:
        render_calendar_section()
    with col2:
        render_announcement_section()

    render_news_section()
    
    render_footer()

if __name__ == "__main__":
    main()

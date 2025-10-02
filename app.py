"""
Main application file for the Investia Intranet Streamlit app.
Handles layout, routing, authentication, and page composition.
"""
import streamlit as st
import logging
from dotenv import load_dotenv

from lib.auth import login_screen
from lib.config import CALENDAR_URL_FULL, CALENDAR_URL_AGENDA, TOOL_LINKS

from lib.ui.header import render_header
from lib.ui.footer import render_footer
from lib.ui.tools import render_internal_tools_section
from lib.ui.calendar import render_calendar_section
from lib.ui.announcements import render_announcement_section
from lib.ui.news import render_news_section
 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
def require_auth(func):
    """Decorator to enforce authentication before accessing a function."""
    def wrapper(*args, **kwargs):
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False
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

@require_auth
def main():
    """Main function to assemble and display the intranet interface."""
    logger.info("App started")
    st.set_page_config(page_title="Investia Intranet", page_icon="extra/investia_favicon.png", layout="wide")

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

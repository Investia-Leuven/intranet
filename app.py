import streamlit as st
import os
import json
from dotenv import load_dotenv
from lib.auth import login_screen
from lib.backend import get_member_name
from datetime import datetime

def display_header():
    """Display the app header with logo and title."""
    st.markdown(
        """
        <style>
        .header-container {
            display: flex;
            align-items: center;
            position: sticky;
            top: 0;
            background-color: white;
            padding: 10px 0;
            border-bottom: 1px solid #ddd;
            z-index: 1000;
        }
        .header-title {
            font-size: 20px;
            font-weight: bold;
            color: #333;
            text-align: center;
            flex-grow: 1;
            margin-right: 60px;
        }
        .block-container {
            padding-top: 60px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns([1, 6, 1])
    with col1:
        st.image("extra/logoinvestia.png", width=80)
    with col2:
        st.markdown(
            "<div class='header-title'>Investia intranet (bèta)</div>",
            unsafe_allow_html=True
        )
    with col3:
        if st.button("Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

def display_footer():
    """Display sticky footer."""
    st.markdown("""
        <style>
        .footer {
            position: fixed;
            left: 0;
            bottom: 0;
            width: 100%;
            text-align: center;
            background-color: white;
            padding: 10px;
            font-size: 0.85em;
            color: grey;
            z-index: 100;
            border-top: 1px solid #ddd;
        }
        </style>
        <div class="footer">
            <i>This is a bèta version. All rights reserved by Investia. 
            Suggestions or errors can be reported to the Investia development group.</i>
        </div>
    """, unsafe_allow_html=True)

def render_tool_button(label: str, icon: str, url: str) -> str:
    return f"""
        <div style="flex: 1; min-width: 200px; max-width: 300px; margin: 10px;">
            <a href="{url}" target="_blank" style="text-decoration: none;">
                <div style="display: flex; align-items: center; justify-content: center; border: 1px solid #ccc; border-radius: 8px; padding: 15px; background-color: #f9f9f9; height: 100%;">
                    <span style="font-size: 20px; margin-right: 10px;">{icon}</span>
                    <span style="font-size: 16px; color: black;">{label}</span>
                </div>
            </a>
        </div>
    """

def render_tool_buttons_row():
    st.subheader("Internal tools")
    buttons_html = ""
    buttons_html += render_tool_button("Member platform", "📊", "https://fund.investialeuven.be")
    buttons_html += render_tool_button("Member Drive", "📂", "https://drive.google.com/drive/folders/1VfsWiHpd1oS8lM5YK4j2ik-3WPiuvNWV?usp=share_link")
    buttons_html += render_tool_button("Industry scanner", "🔍", "https://industry.investialeuven.be")
    buttons_html += render_tool_button("Stock alert", "📈", "https://analyst.investialeuven.be")
    buttons_html += render_tool_button("Investia website", "🌐", "https://investialeuven.be")
    buttons_html += render_tool_button("Treasurer budget", "💲", "https://accounting-investia.streamlit.app")

    st.markdown(f"""
        <div style='display: flex; flex-wrap: wrap; justify-content: center; gap: 20px;'>
            {buttons_html}
        </div>
    """, unsafe_allow_html=True)

def render_calendar():
    st.subheader("Upcoming Events")
    st.markdown("""
    <div style="position: relative; padding-bottom: 380px; height: 0; overflow: hidden;">
        <iframe src="https://calendar.google.com/calendar/embed?src=279f066c8ef646730af43e10bb02220a499f739391184c437529eab94ce61061%40group.calendar.google.com&ctz=Europe%2FBrussels"
            style="position: absolute; top: 0; left: 0; width: 100%; height: 380px; border: 0;" frameborder="0" scrolling="no"></iframe>
    </div>
    """, unsafe_allow_html=True)

def render_announcement_feed():
    from lib.db import insert_message, fetch_messages

    st.subheader("Announcements")

    messages = fetch_messages(limit=4)
    messages.reverse()

    with st.container():
        for post in messages:
            with st.chat_message("user"):
                st.markdown(f"**{post['username']}** at {post['created_at']}\n\n{post['message']}")

    post_text = st.chat_input("Write a message")
    if post_text:
        insert_message(user_id="manual", username=st.session_state.display_name, message=post_text.strip())
        st.rerun()

def news_feed():
    st.subheader("News feed")
    st.markdown("Stay updated with the latest news in the financial world.")
    st.markdown("under construction...")

def main():
    st.set_page_config(page_title="Investia Stock Alert", page_icon="extra/investia_favicon.png", layout="wide")

    load_dotenv()

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        login_screen()
        st.stop()

    display_header()
    st.markdown("")
    username = st.session_state.get("display_name", "member")
    st.markdown("")
    st.markdown(
        f"<p style='color:darkblue;'>Welcome {username} on Investia's intranet. From this page you can navigate to all internal digital tools.</p>",
        unsafe_allow_html=True
    )

    render_tool_buttons_row()

    col1, col2 = st.columns(2)

    with col1:
        render_calendar()

    with col2:
        render_announcement_feed()

    news_feed()
    
    display_footer()

if __name__ == "__main__":
    main()

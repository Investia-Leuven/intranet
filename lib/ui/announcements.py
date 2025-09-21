"""
UI component: Announcements Section
"""

import streamlit as st
from lib.db import insert_message, fetch_messages


def render_announcement_section():
    """Display recent announcements and allow users to post new messages."""

    st.subheader("Announcements")

    @st.cache_data(ttl=10)
    def get_cached_messages():
        return fetch_messages(limit=4)

    messages = get_cached_messages()
    messages.reverse()

    with st.container():
        for post in messages:
            with st.chat_message("user"):
                st.markdown(f"**{post['username']}** at {post['created_at']}\n\n{post['message']}")

    post_text = st.chat_input("Write a message")
    if post_text:
        insert_message(user_id="manual", username=st.session_state.display_name, message=post_text.strip())
        st.rerun()
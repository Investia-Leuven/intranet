"""
UI component: Calendar Section
"""

import streamlit as st
from lib.config import CALENDAR_URL_FULL, CALENDAR_URL_AGENDA


def render_calendar_section():
    """Render a calendar section with toggle between agenda and full calendar view."""
    col1, col2 = st.columns([4, 1])
    with col1:
        st.subheader("Upcoming Events")
    with col2:
        calendar_view = st.toggle("Calendar view")

    if calendar_view:
        st.markdown(f"""
        <div style="position: relative; padding-bottom: 380px; height: 0; overflow: hidden;">
            <iframe src="{CALENDAR_URL_FULL}"
                style="position: absolute; top: 0; left: 0; width: 100%; height: 380px; border: 0;" frameborder="0" scrolling="no"></iframe>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="position: relative; padding-bottom: 380px; height: 0; overflow: hidden;">
            <iframe src="{CALENDAR_URL_AGENDA}" 
                style="position: absolute; top: 0; left: 0; width: 100%; height: 380px; border: 0;" frameborder="0" scrolling="no"></iframe>
        </div>
        """, unsafe_allow_html=True)
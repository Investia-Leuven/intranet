"""
UI component: Header
"""

import streamlit as st


def render_header():
    """Render the app header with logo, title, and logout button."""
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
        colA, colB = st.columns([1,1])
        with colA:
            if st.button("Settings"): 
                st.session_state.page = "settings"; st.rerun()
        with colB:
            if st.button("Logout", use_container_width=True):
                st.session_state.authenticated = False
                st.rerun()
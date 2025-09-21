"""
UI component: Footer
"""

import streamlit as st


def render_footer():
    """Render a fixed footer with disclaimer information."""
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
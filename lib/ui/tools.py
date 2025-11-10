"""
UI component: Internal Tools Section
"""

import streamlit as st
from lib.config import TOOL_LINKS
import logging

logger = logging.getLogger(__name__)


@st.cache_data
def render_tool_button(label: str, icon: str, url: str) -> str:
    """Generate HTML for a single internal tool button."""
    logger.debug(f"Rendering tool button: {label}")
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


def render_internal_tools_section():
    """Render the section containing all internal navigation tool buttons."""
    st.subheader("Internal tools")
    st.markdown("⚠️ *Some tools are hosted on free platforms and may take a minute to load when waking up. This saves us €90/year per tool. Please wait patiently and reload the site if nothing happens.*")
    
    buttons_html = ""
    for item in TOOL_LINKS:
        # Support both legacy 3-tuple and new 4-tuple (requires_board) entries
        if len(item) == 3:
            label, icon, url = item
            requires_board = False
        else:
            label, icon, url, requires_board = item
        # Skip tools that require board privileges if the user isn't a board member
        if requires_board and not st.session_state.get("is_board", False):
            continue
        buttons_html += render_tool_button(label, icon, url)

    st.markdown(f"""
        <div style='display: flex; flex-wrap: wrap; justify-content: center; gap: 20px;'>
            {buttons_html}
        </div>
    """, unsafe_allow_html=True)
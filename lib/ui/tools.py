"""
UI component: Internal Tools Section
"""

import streamlit as st
from lib.config import TOOL_LINKS
import logging

logger = logging.getLogger(__name__)


@st.cache_data
def render_tool_button(label: str, icon: str, url: str, is_maintenance: bool = False) -> str:
    """Generate HTML for a single internal tool button."""
    logger.debug(f"Rendering tool button: {label}")
    
    # Define styles and behavior based on maintenance status
    if is_maintenance:
        bg_color = "#eeeeee"
        opacity = "0.6"
        cursor = "not-allowed"
        # JavaScript alert for immediate feedback
        onclick = f"alert('The {label} is currently in service for maintenance. Please contact the Investia development group directly if you need immediate assistance.'); return false;"
        href = "#"
        badge = '<span style="position: absolute; top: -10px; right: -5px; background-color: #f39c12; color: white; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: bold; border: 1px solid white;">IN SERVICE</span>'
    else:
        bg_color = "#f9f9f9"
        opacity = "1.0"
        cursor = "pointer"
        onclick = ""
        href = url
        badge = ""

    return f"""
        <div style="flex: 1; min-width: 200px; max-width: 300px; margin: 10px; position: relative;">
            <a href="{href}" target="_blank" onclick="{onclick}" style="text-decoration: none; cursor: {cursor};">
                <div style="display: flex; align-items: center; justify-content: center; border: 1px solid #ccc; border-radius: 8px; padding: 15px; background-color: {bg_color}; height: 100%; opacity: {opacity}; transition: all 0.3s ease;">
                    {badge}
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
        # Support legacy 3-tuple, 4-tuple (requires_board), and new 5-tuple (is_maintenance) entries
        if len(item) == 3:
            label, icon, url = item
            requires_board = False
            is_maintenance = False
        elif len(item) == 4:
            label, icon, url, requires_board = item
            is_maintenance = False
        else:
            label, icon, url, requires_board, is_maintenance = item
            
        # Skip tools that require board privileges if the user isn't a board member
        if requires_board and not (st.session_state.get("is_board", False) or st.session_state.get("is_admin", False)):
            continue
        buttons_html += render_tool_button(label, icon, url, is_maintenance)

    st.markdown(f"""
        <div style='display: flex; flex-wrap: wrap; justify-content: center; gap: 20px;'>
            {buttons_html}
        </div>
    """, unsafe_allow_html=True)
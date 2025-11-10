import streamlit as st

from lib.db import list_member_amounts_due
print(list_member_amounts_due("your_username_here"))

def render_amounts_due_banner() -> None:
    """Show a simple red banner if the logged-in member has any amount due.
    Uses session state for identity and defers all data logic to the DB layer.
    """
    username = st.session_state.get("username")
    name = st.session_state.get("name")
    if not username:
        return

    # Expect this to be implemented later in lib.db
    # It should return a list of dicts with at least: amount (float), due_date (date/str), note (str)
    try:
        dues = list_member_amounts_due(username)
    except Exception:
        return

    if not dues:
        return

    total = sum(float(d.get("amount", 0.0)) for d in dues)
    earliest = min(dues, key=lambda d: d.get("due_date") or "")
    due_date = earliest.get("due_date", "")
    notes = [str(d.get("note", "")).strip() for d in dues if d.get("note")]
    note = " + ".join(notes)

    st.error(
        f"Hi {name or username}, it seems there’s still an open balance of €{total:.2f}. "
        f"Could you please make sure this is paid by {due_date}? "
        f"This relates to: {note}. "
        f"If you have any questions or believe you’ve already paid, please contact the treasurer."
    )
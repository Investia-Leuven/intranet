"""Settings page for users and admins, allowing profile updates and admin user management."""

import streamlit as st
import secrets, string
import time

from lib.db import get_member_by_username, update_username, update_email, update_password, list_members, delete_member, update_is_admin, create_member
from lib.backend import Member, generate_reset_code
from lib.send_email import send_email

def render_settings_page():
    st.title("Settings")

    # ================== Profile Section ==================
    member = get_member_by_username(st.session_state.username)
    st.subheader("Profile")
    with st.form("profile_form"):
        name = st.text_input("Full name", value=member.name, disabled=True)
        nickname = st.text_input("Nickname (username)", value=member.username)
        email = st.text_input("Email", value=member.email)
        new_password = st.text_input("New password", type="password")
        confirm_password = st.text_input("Confirm new password", type="password")
        save_changes = st.form_submit_button("Save changes")
        if save_changes:
            updated = False
            # Update nickname/username if changed and not taken
            if nickname != member.username:
                existing = get_member_by_username(nickname)
                if existing:
                    st.error("That username is already taken.")
                else:
                    update_username(member.username, nickname)  # Update username in DB
                    st.session_state.username = nickname  # Update session username
                    updated = True
                    st.success("Username updated.")
            # Update email if changed
            if email != member.email:
                update_email(nickname, email)  # Update email in DB
                updated = True
                st.success("Email updated.")
            # Update password if provided and valid
            if new_password or confirm_password:
                if new_password != confirm_password:
                    st.error("Passwords do not match.")
                elif not new_password:
                    st.error("Password cannot be empty.")
                else:
                    member.set_password(new_password)  # Hash new password
                    update_password(nickname, member.password_hash)  # Update password in DB
                    updated = True
                    st.success("Password updated.")
                    time.sleep(2)  # Pause briefly after password change
            if updated:
                st.rerun()  # Refresh page to reflect updates

    # ================== Admin Section ==================
    if st.session_state.get("is_admin"):
        st.markdown("---")
        st.subheader("Admin section")

        st.subheader("Help a friend out! Get a reset code for a member")
        members = list_members()
        options = {m["name"]: m["username"] for m in members}
        selected_name = st.selectbox("Select member", [""] + list(options.keys()))
        if selected_name:
            selected_username = options[selected_name]
            selected_member = get_member_by_username(selected_username)
            if selected_member and getattr(selected_member, "reset_code", None):
                st.info(f"Reset code: {selected_member.reset_code}")

        st.subheader("Create new user")
        with st.form("create_user_form"):
            new_name = st.text_input("Full name")
            new_email = st.text_input("Email")
            is_admin = st.checkbox("Admin privileges", value=False)
            create_btn = st.form_submit_button("Create user")
            if create_btn:
                if not new_name or not new_email:
                    st.error("Name and email are required.")
                else:
                    # Generate unique username based on name
                    base_username = new_name.strip().lower().replace(" ", "_").replace("-", "_")
                    base_username = base_username.replace("__", "_")
                    username = base_username
                    i = 1
                    while get_member_by_username(username):
                        username = f"{base_username}{i}"
                        i += 1
                    # Generate random password
                    alphabet = string.ascii_letters + string.digits
                    password = ''.join(secrets.choice(alphabet) for _ in range(12))
                    # Create a temporary Member object to hash the password
                    temp_member = Member(username=username, name=new_name, email=new_email, is_admin=is_admin, password_hash="")
                    hashed_pw = temp_member.set_password(password)
                    reset_code = generate_reset_code()

                    # Create the user in the database with hashed password and reset code
                    create_member(username, new_name, new_email, is_admin, hashed_pw, reset_code)
                    # Send welcome email with credentials and reset code
                    try:
                        send_email(
                            new_email,
                            subject="Welcome to the intranet",
                            html_body=f"""
                                <p>Hi {new_name},</p>
                                <p>Your account has been created.</p>
                                <p><b>Username:</b> {username}<br>
                                <b>Password:</b> {password}<br>
                                <b>Reset code:</b> {reset_code}</p>
                                <p>Please log in and change your password.</p>
                                <p>Kind regards,<br/>Investia</p>
                            """)
                        st.success(f"User created and email sent to {new_email}.")
                    except Exception as e:
                        st.warning(f"User created but failed to send email: {e}")

        st.subheader("Manage users")
        members = list_members()
        options = {m["name"]: m["username"] for m in members if m["username"] != st.session_state.username}
        selected_name = st.selectbox("Select user to manage", [""] + list(options.keys()))
        if selected_name:
            selected_manage_user = options[selected_name]
            user_obj = get_member_by_username(selected_manage_user)
            admin_status = st.checkbox("Admin", value=user_obj.is_admin, key=f"admin_{selected_manage_user}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Update role", key=f"update_role_{selected_manage_user}"):
                    update_is_admin(selected_manage_user, admin_status)  # Update admin status in DB
                    st.success("User role updated.")
                    st.rerun()
            with col2:
                if st.button("Delete user", key=f"delete_{selected_manage_user}"):
                    delete_member(selected_manage_user)  # Delete user from DB
                    st.success("User deleted.")
                    st.rerun()

    # ================== Return to homepage ==================
    st.markdown("---")
    if st.button("Return to homepage"):
        st.session_state.page = "home"
        st.rerun()
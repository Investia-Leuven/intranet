"""Settings page for users and admins, allowing profile updates and admin user management."""

import streamlit as st
import secrets, string
import time
import pandas as pd
import io

import json
from lib.db import get_member_by_username, update_member_profile, list_members, delete_member, update_is_admin, update_is_board, create_member, list_board_members, list_admin_members
from lib.backend import Member, generate_reset_code
from lib.send_email import send_email

def render_settings_page():
    st.title("Settings")

    # ================== Profile Section ==================
    member = get_member_by_username(st.session_state.username)
    
    # Parse existing address if present
    addr_dict = {}
    if member.address:
        try:
            addr_dict = json.loads(member.address)
        except json.JSONDecodeError:
            pass
            
    st.subheader("Profile")
    with st.form("profile_form"):
        col_basic_1, col_basic_2 = st.columns(2)
        with col_basic_1:
            name = st.text_input("Full name", value=member.name, disabled=True)
            nickname = st.text_input("Nickname (username)", value=member.username)
        with col_basic_2:
            email = st.text_input("Email", value=member.email)
            iban = "".join(st.text_input("IBAN", value=member.iban or "").split())

        st.caption("Address")
        col_addr_1, col_addr_2 = st.columns(2)
        with col_addr_1:
            street = st.text_input("Street & Number", value=addr_dict.get("street", ""))
            postal_code = st.text_input("Postal Code", value=addr_dict.get("postal_code", ""))
            country = st.text_input("Country", value=addr_dict.get("country", ""))
        with col_addr_2:
            city = st.text_input("City", value=addr_dict.get("city", ""))
            province = st.text_input("Province", value=addr_dict.get("province", ""))

        st.caption("Security")
        col_pwd_1, col_pwd_2 = st.columns(2)
        with col_pwd_1:
            new_password = st.text_input("New password", type="password")
        with col_pwd_2:
            confirm_password = st.text_input("Confirm new password", type="password")

        save_changes = st.form_submit_button("Save changes")
        
        if save_changes:
            updates = {}
            error_msg = None

            # 1. Validate Username
            if nickname != member.username:
                if not nickname:
                     error_msg = "Username cannot be empty."
                else:
                    existing = get_member_by_username(nickname)
                    if existing:
                        error_msg = "That username is already taken."
                    else:
                        updates["username"] = nickname

            # 2. Add other fields
            if email != member.email:
                updates["email"] = email
            
            if iban != (member.iban or ""):
                updates["iban"] = iban.replace(" ", "")

            # 3. Serialize Address
            new_addr_dict = {
                "street": street,
                "city": city,
                "postal_code": postal_code,
                "province": province,
                "country": country
            }
            # Only save if at least one field is filled, or if clearing previous data
            # Simplest approach: always save the structured dict, even if empty values
            new_addr_json = json.dumps(new_addr_dict)
            if new_addr_json != member.address:
                updates["address"] = new_addr_json

            # 4. Password validation
            if new_password or confirm_password:
                if new_password != confirm_password:
                    error_msg = "Passwords do not match."
                elif not new_password:
                    error_msg = "Password cannot be empty."
                else:
                    # Hash the new password using the Member method (assuming we have access or can create temp)
                    # We can use the existing member instance to hash
                    updates["password_hash"] = member.set_password(new_password)

            if error_msg:
                st.error(error_msg)
            elif not updates:
                st.info("No changes to save.")
            else:
                # Perform the update in one go
                success = update_member_profile(member.username, updates)
                
                if success:
                    # ONLY update session state if DB update succeeded
                    if "username" in updates:
                        st.session_state.username = updates["username"]
                    
                    st.success("Profile updated successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Failed to update profile. Please try again.")

    # ================== Admin Section ==================
    if st.session_state.get("is_admin"):
        st.markdown("---")
        st.subheader("Admin section")

        st.subheader("Help a friend out! Get a reset code for a member. With this reset code, they can set a new password.")
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
            is_board = st.checkbox("Board member", value=False)
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
                    temp_member = Member(username=username, name=new_name, email=new_email, is_admin=is_admin, is_board=is_board, password_hash="")
                    hashed_pw = temp_member.set_password(password)
                    reset_code = generate_reset_code()

                    # Create the user in the database with hashed password and reset code
                    create_member(username, new_name, new_email, is_admin, is_board, hashed_pw, reset_code)
                    # Send welcome email with credentials and reset code
                    try:
                        send_email(
                            new_email,
                            subject="Welcome to the intranet",
                            html_body=f"""
                                <p>Hi {new_name},</p>
                                <p>Welcome to Investia's digital world! Your account has been created. Find here your login credentials:</p>
                                <p><b>Username:</b> {username}<br>
                                <b>Password:</b> {password}<br>
                                <b>Reset code:</b> {reset_code}</p>
                                <p>Please log in and change your password. You can login via the 'FUND' button on the Investia Leuven website or using the link in this email.</p>
                                <p>Login link: https://intranet.investialeuven.be/</p>
                                <p>Enjoy your digital experience!</p>
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
            board_status = st.checkbox("Board member", value=getattr(user_obj, "is_board", False), key=f"board_{selected_manage_user}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Update role", key=f"update_role_{selected_manage_user}"):
                    update_is_admin(selected_manage_user, admin_status)
                    if hasattr(user_obj, "is_board"):
                        update_is_board(selected_manage_user, board_status)
                    st.success("User roles updated.")
                    st.rerun()
            with col2:
                if st.button("Delete user", key=f"delete_{selected_manage_user}"):
                    delete_member(selected_manage_user)  # Delete user from DB
                    st.success("User deleted.")
                    st.rerun()

        # Show quick overview tables for Board members and Admin users
        board_rows = list_board_members()
        admin_rows = list_admin_members()

        # Keep only compact, relevant columns
        board_df = pd.DataFrame(board_rows)[[c for c in ["name"] if c in (board_rows[0].keys() if board_rows else [])]]
        admin_df = pd.DataFrame(admin_rows)[[c for c in ["name"] if c in (admin_rows[0].keys() if admin_rows else [])]]

        col_a, col_b = st.columns(2)
        with col_a:
            st.caption("Board members")
            st.dataframe(board_df, use_container_width=True, hide_index=True)
        with col_b:
            st.caption("Admin users")
            st.dataframe(admin_df, use_container_width=True, hide_index=True)
            
        if st.session_state.get("is_admin") or st.session_state.get("is_board", False):
            st.divider()
            st.subheader("Export member data")
            members = list_members()
            
            # --- Excel Export ---
            st.caption("Download all member data")
            export_data = []
            for m in members:
                # Parse address
                addr_str = ""
                if m.get("address"):
                    try:
                        ad = json.loads(m["address"])
                        parts = [
                            ad.get("street"), 
                            ad.get("city"), 
                            ad.get("postal_code"), 
                            ad.get("country")
                        ]
                        # Filter out empty parts
                        addr_str = ", ".join([p for p in parts if p])
                    except:
                        addr_str = m["address"] # Fallback
                
                export_data.append({
                    "Name": m["name"],
                    "Email": m["email"],
                    "IBAN": m.get("iban", ""),
                    "Address": addr_str,
                    "Username": m["username"] # Added for completeness
                })
            
            df_export = pd.DataFrame(export_data)
            
            # Convert to Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_export.to_excel(writer, index=False, sheet_name='Members')
            
            st.download_button(
                label="Download member data (Excel)",
                data=buffer.getvalue(),
                file_name=f"investia_members_{time.strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.ms-excel"
            )

    # ================== Return to homepage ==================
    st.markdown("---")
    if st.button("Return to homepage"):
        st.session_state.page = "home"
        st.rerun()
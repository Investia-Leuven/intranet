"""
Authentication logic for the Investia Intranet application.
Handles user login and sets authentication status in Streamlit session state.
"""
from lib.db import get_member_by_username, get_member_by_full_name, set_reset_code, update_password
from lib.backend import generate_reset_code
from lib.backend import masked_email
from dotenv import load_dotenv
import streamlit as st
from lib.send_email import send_reset_email
import time

def login_screen():
    """
    Display the login screen and authenticate users.
    If credentials are valid, update session state and rerun the app.
    """
    # Load environment variables (if needed for authentication)
    load_dotenv()

    # Initialise session state variables for password reset steps and username
    if "reset_step" not in st.session_state:
        st.session_state.reset_step = "login"
    if "reset_username" not in st.session_state:
        st.session_state.reset_username = None

    # Initialise authentication flag in session state
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    # If user is not authenticated, proceed with login or password reset flow
    if not st.session_state.authenticated:
        if st.session_state.reset_step == "login":
            # LOGIN STEP: Display login form to enter username and password
            st.title("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                # Retrieve member by username and verify password
                member = get_member_by_username(username)
                if member and member.check_password(password):
                    # Successful login: update session state and rerun app
                    st.session_state.authenticated = True
                    st.session_state.username = member.username
                    st.session_state.display_name = member.name
                    st.session_state.is_admin = member.is_admin
                    st.rerun()
                else:
                    # Invalid credentials: show error message
                    st.error("Invalid username or password")
            if st.button("Forgot password?"):
                # Move to password reset name entry step
                st.session_state.reset_step = "enter_name"
                st.rerun()

        elif st.session_state.reset_step == "enter_name":
            # PASSWORD RESET STEP 1: Prompt user to enter full name for verification
            st.title("Password Reset")
            full_name = st.text_input("Enter your full name, e.g. 'John Doe'")
            if st.button("Submit"):
                # Lookup member by full name
                member = get_member_by_full_name(full_name)
                if member:
                    # Store username in session state and proceed to send code step
                    st.session_state.reset_username = member.username
                    st.session_state.reset_step = "send_code"
                    st.rerun()
                else:
                    # No matching member found: display error
                    st.error("No member found with that full name")

            if st.button("Back to login"):
                # Reset to login step and clear reset username
                st.session_state.reset_step = "login"
                st.session_state.reset_username = None
                st.rerun()

        elif st.session_state.reset_step == "send_code":
            # PASSWORD RESET STEP 2: Confirm username and send reset code email
            st.title("Password Reset")
            member = get_member_by_username(st.session_state.reset_username)
            st.write(f"Username found: **{st.session_state.reset_username}**")
            if st.button("Send reset email"):
                if member and member.email:
                    # Send reset code email to member's email address
                    send_reset_email(member.username, member.email, member.reset_code)
                    sensemail = masked_email(member.email)
                    st.success(f"An email with a reset code has been sent to {sensemail}.")
                else:
                    # No email on file: instruct user to contact admin
                    st.info("No email on file. Ask an admin for your reset code.")
                # Pause briefly before moving to next step
                time.sleep(5)
                st.session_state.reset_step = "enter_code"
                st.rerun()

            if st.button("Back to login"):
                # Reset to login step and clear reset username
                st.session_state.reset_step = "login"
                st.session_state.reset_username = None
                st.rerun()

        elif st.session_state.reset_step == "enter_code":
            # PASSWORD RESET STEP 3: Prompt user to enter reset code received by email or from admin
            st.title("Enter Reset Code")
            code_input = st.text_input("Enter the reset code sent to your email. You can also ask an admin member to retrieve a code for you. A code can only be used once.")
            if st.button("Submit code"):
                # Validate entered reset code against stored reset code
                member = get_member_by_username(st.session_state.reset_username)
                if member and hasattr(member, "reset_code") and member.reset_code == code_input:
                    # Valid code: move to set new password step
                    st.session_state.reset_step = "set_password"
                    # Generate and store a new reset code to invalidate the old one
                    new_reset_code = generate_reset_code()
                    set_reset_code(st.session_state.reset_username, new_reset_code)
                    st.rerun()
                else:
                    # Invalid reset code entered
                    st.error("Invalid reset code")

            if st.button("Back to login"):
                # Reset to login step and clear reset username
                st.session_state.reset_step = "login"
                st.session_state.reset_username = None
                st.rerun()

        elif st.session_state.reset_step == "set_password":
            # PASSWORD RESET STEP 4: Allow user to set a new password
            st.title("Set New Password")
            new_password = st.text_input("New password", type="password")
            confirm_password = st.text_input("Confirm new password", type="password")
            if st.button("Set password"):
                # Check that passwords match and are not empty
                if new_password != confirm_password:
                    st.error("Passwords do not match")
                elif len(new_password) == 0:
                    st.error("Password cannot be empty")
                else:
                    # Update member password hash in database
                    member = get_member_by_username(st.session_state.reset_username)
                    if member:
                        new_hash = member.set_password(new_password)
                        update_password(st.session_state.reset_username, new_hash)
                        st.success("Password updated successfully. Please login.")
                        # Reset to login step and clear reset username
                        st.session_state.reset_step = "login"
                        st.session_state.reset_username = None
                        st.rerun()
                    else:
                        # Member not found, display error
                        st.error("User not found. Please try again.")

            if st.button("Back to login"):
                # Reset to login step and clear reset username
                st.session_state.reset_step = "login"
                st.session_state.reset_username = None
                st.rerun()

        # Stop execution to prevent further UI rendering until rerun
        st.stop()

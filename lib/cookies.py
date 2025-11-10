"""
Cookie and JWT utilities for persistent login (24h) in the Investia Intranet.

This module provides helper functions to manage user authentication state using JWT (JSON Web Tokens) stored in browser cookies.
JWTs are digitally signed tokens that securely encode user identity and expiration information, allowing stateless authentication.
Cookies persist the JWT on the client side, enabling automatic login (auto-login) for a limited duration (24 hours by default),
without requiring the user to re-enter credentials on each visit.

Usage:
  - from lib.cookies import restore_session_from_cookie, write_login_cookie, clear_auth_cookie
  - Call restore_session_from_cookie() before showing the login form to attempt auto-login.
  - After successful login, call write_login_cookie(username) to set the JWT cookie.
  - On logout, call clear_auth_cookie() to remove the authentication cookie and end the session.
"""
import os
import datetime as dt
# using timezone-aware datetimes
from typing import Optional

import streamlit as st
from extra_streamlit_components import CookieManager
import jwt

from lib.db import get_member_by_username

# ---- Configuration ----
TOKEN_NAME = "auth_token"  # Name of the cookie to store the JWT token
TOKEN_DURATION_HOURS = 24  # Duration (in hours) for which the auto-login token is valid

def _get_jwt_secret() -> str:
    """
    Retrieve the secret key used to sign and verify JWT tokens.
    The secret is fetched exclusively from the environment variable JWT_SECRET,
    with a default fallback (should be changed in production).
    """
    return os.environ.get("JWT_SECRET", "change-me")

def _cookies() -> CookieManager:
    """
    Obtain a singleton CookieManager instance stored in Streamlit's session state.
    This manager handles setting, getting, and deleting cookies in the user's browser.
    """
    if "_cookie_manager" not in st.session_state:
        st.session_state._cookie_manager = CookieManager()
    return st.session_state._cookie_manager

# ---- Core helpers ----
def _encode_token(username: str, expires_at: dt.datetime) -> str:
    """
    Create a signed JWT token encoding the username and expiration time.

    Args:
        username: The username to encode in the token's subject claim.
        expires_at: The UTC datetime when the token should expire.

    Returns:
        A JWT string signed with the secret key.
    """
    payload = {"sub": username, "exp": expires_at}
    token = jwt.encode(payload, _get_jwt_secret(), algorithm="HS256")
    return token

def _decode_token(token: str) -> Optional[str]:
    """
    Decode and verify a JWT token, returning the username if valid.

    Args:
        token: The JWT token string from the cookie.

    Returns:
        The username encoded in the token if verification succeeds and token is not expired.
        Returns None if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, _get_jwt_secret(), algorithms=["HS256"])
        username = payload.get("sub")
        return username
    except jwt.ExpiredSignatureError:
        # Token has expired; user must re-authenticate
        return None
    except Exception as e:
        # Any other decoding error: treat as invalid token
        return None

# ---- Public API ----
def write_login_cookie(username: str, hours: int = TOKEN_DURATION_HOURS) -> None:
    """
    Create and set a signed JWT cookie for persistent login.

    This function is called after a successful login to issue a JWT token
    that will allow the user to remain logged in for the specified duration.

    Args:
        username: The authenticated user's username.
        hours: How long the token is valid (default 24 hours).
    """
    expires = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=hours)
    token = _encode_token(username, expires)
    # Set the cookie with the JWT token and expiration to enable auto-login
    _cookies().set(TOKEN_NAME, token)

def clear_auth_cookie() -> None:
    """
    Remove the authentication cookie from the user's browser.

    This function is called on logout to clear the persistent login token,
    ensuring the user must authenticate again next time.
    """
    _cookies().delete(TOKEN_NAME)

def restore_session_from_cookie() -> bool:
    """
    Attempt to restore the Streamlit session state from an existing JWT cookie.

    This function checks if an authentication cookie exists and contains a valid,
    unexpired JWT token. If so, it fetches the corresponding user from the database
    and populates Streamlit's session state with the user's authentication info.

    Returns:
        True if the session was successfully restored and the user is authenticated.
        False if no valid token was found or user could not be verified.
    """
    # If already authenticated in session, no need to restore
    if st.session_state.get("authenticated"):
        return True

    # Retrieve the JWT token from the cookie manager
    token = _cookies().get(TOKEN_NAME)
    if not token:
        # No token found; user is not authenticated
        return False

    username = _decode_token(token)
    if not username:
        # Token is invalid or expired; clear cookie and fail silently
        clear_auth_cookie()
        return False

    # Fetch user details from the database to verify user exists
    member = get_member_by_username(username)
    if not member:
        # User not found; clear cookie and fail silently
        clear_auth_cookie()
        return False

    # Populate Streamlit session state with user authentication info
    st.session_state.authenticated = True
    st.session_state.username = member.username
    st.session_state.display_name = member.name
    st.session_state.is_admin = member.is_admin
    st.session_state.is_board = member.is_board

    return True

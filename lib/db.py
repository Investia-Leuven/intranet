"""Supabase interaction functions for feed messages and user authentication.

This module contains all functions that interact with the Supabase backend to manage
feed messages and user authentication data. It includes operations to insert,
fetch, and delete feed messages, as well as retrieve and update member information
such as password hashes and reset codes.
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
from lib.backend import Member
from typing import Optional

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

SUPABASE_ANALYST_URL = os.getenv("SUPABASE_ANALYST_URL")
SUPABASE_ANALYST_KEY = os.getenv("SUPABASE_ANALYST_KEY")
supabase_analyst = create_client(SUPABASE_ANALYST_URL, SUPABASE_ANALYST_KEY)

# ====================== Feed Message Functions ======================

def insert_message(user_id: str, username: str, message: str):
    """
    Insert a message into the feed. Keeps only the latest 3 messages by deleting older ones.

    This function is used to add a new message to the intranet feed and ensures that
    the feed does not grow indefinitely by maintaining a maximum of 3 messages.
    """
    # Insert the new message record into the 'intranet_feed_messages' table
    supabase.table("intranet_feed_messages").insert({
        "user_id": user_id,
        "username": username,
        "message": message
    }).execute()

    # Retrieve all messages ordered by creation time (oldest first) to check message count
    result = supabase.table("intranet_feed_messages").select("id", count="exact").order("created_at").execute()
    messages = result.data

    # If more than 3 messages exist, delete the oldest to maintain only the latest 3
    if len(messages) > 3:
        oldest_id = messages[0]["id"]
        delete_message_by_id(oldest_id)

def fetch_messages(limit: int = 10):
    """
    Fetch recent feed messages, ordered by creation time descending.

    Returns up to 'limit' most recent messages for display in the feed.
    """
    # Query the latest messages ordered by descending creation time, limited by 'limit'
    response = supabase.table("intranet_feed_messages").select("*").order("created_at", desc=True).limit(limit).execute()
    return response.data if response.data else []

def delete_message_by_id(message_id: str):
    """
    Delete a feed message by its unique ID.

    Used internally to remove old messages when enforcing the message limit.
    """
    # Delete the message matching the given ID
    return supabase.table("intranet_feed_messages").delete().eq("id", message_id).execute()


# ====================== Authentication & Member Functions ======================

def get_member_by_username(username: str) -> Optional[Member]:
    """
    Fetch a member's authentication details by username.

    Queries the 'authentication' table for a user matching the given username.
    Returns a Member object if found, otherwise None.
    """
    # Query the authentication table for the username
    resp = (
        supabase.table("authentication")
        .select("username, name, email, is_admin, is_board, password, reset_code")
        .eq("username", username)
        .execute()
    )
    data = getattr(resp, "data", None)
    if not data:
        return None

    # Use the first record found for the given username
    record = data[0]

    # Construct and return a Member instance with the retrieved data
    return Member(
        username=record["username"],
        name=record["name"],
        email=record["email"],
        is_admin=record["is_admin"],
        is_board=record.get("is_board", False),
        password_hash=record["password"],
        reset_code=record.get("reset_code"),
    )

def get_member_by_full_name(full_name: str) -> Optional[Member]:
    """
    Fetch a member's authentication details by full name.

    Queries the 'authentication' table for users with the matching full name.
    Returns the first matching Member object or None if no match is found.
    """
    # Query the authentication table for the full name
    resp = (
        supabase.table("authentication")
        .select("username, name, email, is_admin, is_board, password, reset_code")
        .eq("name", full_name)
        .execute()
    )
    data = getattr(resp, "data", None)
    if not data:
        return None

    # Use the first record found for the given full name
    record = data[0]

    # Construct and return a Member instance with the retrieved data
    return Member(
        username=record["username"],
        name=record["name"],
        email=record["email"],
        is_admin=record["is_admin"],
        is_board=record.get("is_board", False),
        password_hash=record["password"],
        reset_code=record.get("reset_code"),
    )


def set_reset_code(username: str, code: str) -> bool:
    """
    Update the password reset code for the specified user.

    This is used during password recovery to store a reset code that can be verified later.
    Returns True if the update was successful.
    """
    # Update the reset_code field for the user with the given username
    resp = (
        supabase.table("authentication")
        .update({"reset_code": code})
        .eq("username", username)
        .execute()
    )
    return resp.data is not None


def update_password(username: str, new_hash: str) -> bool:
    """
    Update the password hash for the specified user.

    Used when a user changes or resets their password.
    Returns True if the update was successful.
    """
    # Update the password field for the user with the given username
    resp = (
        supabase.table("authentication")
        .update({"password": new_hash})
        .eq("username", username)
        .execute()
    )
    return resp.data is not None


# --- Settings page helper functions ---

def update_username(old_username: str, new_username: str) -> bool:
    """
    Update the username (nickname) for a user.
    Returns True if the update succeeded.
    """
    # Update the username from old_username to new_username
    resp = (
        supabase.table("authentication")
        .update({"username": new_username})
        .eq("username", old_username)
        .execute()
    )
    return resp.data is not None


def update_email(username: str, new_email: str) -> bool:
    """
    Update the email address for a user.
    Returns True if the update succeeded.
    """
    # Update the email for the given username
    resp = (
        supabase.table("authentication")
        .update({"email": new_email})
        .eq("username", username)
        .execute()
    )
    return resp.data is not None


def update_is_admin(username: str, is_admin: bool) -> bool:
    """
    Update the admin flag for a user.
    Returns True if the update succeeded.
    """
    # Update the is_admin flag for the given username
    resp = (
        supabase.table("authentication")
        .update({"is_admin": is_admin})
        .eq("username", username)
        .execute()
    )
    return resp.data is not None

def update_is_board(username: str, is_board: bool) -> bool:
    """
    Update the board member flag for a user.
    Returns True if the update succeeded.
    """
    resp = (
        supabase.table("authentication")
        .update({"is_board": is_board})
        .eq("username", username)
        .execute()
    )
    return resp.data is not None


def create_member(username: str, name: str, email: str, is_admin: bool, is_board: bool, password_hash: str, reset_code: str) -> bool:
    """
    Create a new user in the authentication table.
    Returns True if the insertion succeeded.
    """
    # Insert a new member record into the authentication table
    resp = (
        supabase.table("authentication")
        .insert({
            "username": username,
            "name": name,
            "email": email,
            "is_admin": is_admin,
            "is_board": is_board,
            "password": password_hash,
            "reset_code": reset_code
        })
        .execute()
    )
    return resp.data is not None


def delete_member(username: str) -> bool:
    """
    Delete a user from the authentication table by username.
    Returns True if the deletion succeeded.
    """
    # Delete the member record matching the given username
    resp = (
        supabase.table("authentication")
        .delete()
        .eq("username", username)
        .execute()
    )
    return resp.data is not None


def list_members():
    """
    Return a list of all members with their basic info.
    """
    # Retrieve all members ordered by name
    resp = (
        supabase.table("authentication")
        .select("username, name, email, is_admin, is_board, reset_code")
        .order("name")
        .execute()
    )
    return resp.data or []


def find_members_by_name_like(q: str):
    """
    Return members whose names contain the search query (case-insensitive).
    """
    # Search for members with names containing the query string (case-insensitive)
    resp = (
        supabase.table("authentication")
        .select("username, name, email, is_admin, is_board, reset_code")
        .ilike("name", f"%{q}%")
        .order("name")
        .execute()
    )
    return resp.data or []


def list_board_members():
    """
    Return a list of all board members with their basic info.
    """
    resp = (
        supabase.table("authentication")
        .select("username, name, email, is_admin, is_board, reset_code")
        .eq("is_board", True)
        .order("name")
        .execute()
    )
    return resp.data or []


# --- Admin members helper function ---
def list_admin_members():
    """
    Return a list of all admin members with their basic info.
    """
    resp = (
        supabase.table("authentication")
        .select("username, name, email, is_admin, is_board, reset_code")
        .eq("is_admin", True)
        .order("name")
        .execute()
    )
    return resp.data or []


# ====================== Amounts Due ======================

def list_member_amounts_due(username: str):
    """
    Return all outstanding amounts due for the specified member.

    Fetches from the 'amounts_due' table all records where member_username matches the given username.
    Each record includes at least: amount, due_date, and note.
    """
    if not username:
        return []

    resp = (
        supabase.table("amounts_due")
        .select("amount, due_date, note")
        .eq("member_username", username)
        .order("due_date")
        .execute()
    )
    return resp.data or []
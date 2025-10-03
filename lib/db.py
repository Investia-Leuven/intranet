"""Database functions for feed message operations via Supabase.

This module provides functions to interact with the Supabase backend for managing
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
    response = supabase.table("intranet_feed_messages").select("*").order("created_at", desc=True).limit(limit).execute()
    return response.data if response.data else []

def delete_message_by_id(message_id: str):
    """
    Delete a feed message by its unique ID.

    Used internally to remove old messages when enforcing the message limit.
    """
    return supabase.table("intranet_feed_messages").delete().eq("id", message_id).execute()


def get_member_by_username(username: str) -> Optional[Member]:
    """
    Fetch a member's authentication details by username.

    Queries the 'authentication' table for a user matching the given username.
    Returns a Member object if found, otherwise None.
    """
    resp = (
        supabase.table("authentication")
        .select("username, name, email, is_admin, password, reset_code")
        .eq("username", username)
        .single()  # Expecting a single record
        .execute()
    )
    data = getattr(resp, "data", None)
    if not data:
        return None

    # Construct and return a Member instance with the retrieved data
    return Member(
        username=data["username"],
        name=data["name"],
        email=data["email"],
        is_admin=data["is_admin"],
        password_hash=data["password"],
        reset_code=data.get("reset_code"),
    )

def get_member_by_full_name(full_name: str) -> Optional[Member]:
    """
    Fetch a member's authentication details by full name.

    Queries the 'authentication' table for users with the matching full name.
    Returns the first matching Member object or None if no match is found.
    """
    resp = (
        supabase.table("authentication")
        .select("username, name, email, is_admin, password, reset_code")
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
        password_hash=record["password"],
        reset_code=record.get("reset_code"),
    )


def set_reset_code(username: str, code: str) -> bool:
    """
    Update the password reset code for the specified user.

    This is used during password recovery to store a reset code that can be verified later.
    Returns True if the update was successful.
    """
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
    resp = (
        supabase.table("authentication")
        .update({"password": new_hash})
        .eq("username", username)
        .execute()
    )
    return resp.data is not None
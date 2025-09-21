"""Database functions for feed message operations via Supabase."""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def insert_message(user_id: str, username: str, message: str):
    """
    Insert a message. Keep only the latest 3 messages.
    """
    # Insert message
    supabase.table("intranet_feed_messages").insert({
        "user_id": user_id,
        "username": username,
        "message": message
    }).execute()

    # Keep max 3 messages
    result = supabase.table("intranet_feed_messages").select("id", count="exact").order("created_at").execute()
    messages = result.data
    if len(messages) > 3:
        oldest_id = messages[0]["id"]
        delete_message_by_id(oldest_id)

def fetch_messages(limit: int = 10):
    """
    Fetch recent messages.
    """
    response = supabase.table("intranet_feed_messages").select("*").order("created_at", desc=True).limit(limit).execute()
    return response.data if response.data else []

def delete_message_by_id(message_id: str):
    """
    Delete a message by ID.
    """
    return supabase.table("intranet_feed_messages").delete().eq("id", message_id).execute()
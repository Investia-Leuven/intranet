"""
Backend utility functions for authentication and user name resolution.
"""
import os
import json
from dotenv import load_dotenv

load_dotenv()

def get_credentials() -> dict:
    """
    Retrieve valid username-password pairs from environment variables.
    Returns:
        dict: A dictionary of valid credentials.
    """
    raw = os.getenv("VALID_USERNAME_PASSWORD_PAIRS", "{}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}

def get_user_display_names() -> dict:
    """
    Retrieve the mapping of usernames to display names from environment variables.
    Returns:
        dict: A dictionary mapping usernames to display names.
    """
    raw = os.getenv("USERNAME_TO_MEMBERNAME", "{}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}

def check_credentials(username: str, password: str) -> bool:
    """
    Check if the provided username and password match the valid credentials.
    
    Args:
        username (str): The username to check.
        password (str): The password to validate.
    
    Returns:
        bool: True if credentials are valid, False otherwise.
    """
    credentials = get_credentials()
    return username in credentials and credentials[username] == password

def get_member_name(username: str) -> str:
    """
    Get the display name for a given username.
    
    Args:
        username (str): The username to look up.
    
    Returns:
        str: The corresponding display name, or the username if no mapping is found.
    """
    names = get_user_display_names()
    return names.get(username, username)
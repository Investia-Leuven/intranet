import os
import json
from dotenv import load_dotenv

load_dotenv()

def get_credentials() -> dict:
    raw = os.getenv("VALID_USERNAME_PASSWORD_PAIRS", "{}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}

def get_user_display_names() -> dict:
    raw = os.getenv("USERNAME_TO_MEMBERNAME", "{}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}

def check_credentials(username: str, password: str) -> bool:
    credentials = get_credentials()
    return username in credentials and credentials[username] == password

def get_member_name(username: str) -> str:
    names = get_user_display_names()
    return names.get(username, username)
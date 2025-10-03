import os
import base64
import hashlib
import hmac
from typing import Optional

"""
This module provides backend utilities for authentication and user information encapsulation.
It includes functions for generating reset codes and a Member class that manages user data,
password hashing, and reset code handling.
"""

def generate_reset_code() -> str:
    """Return a unique 32-character base64 reset code (URL-safe).
    
    This code can be used as a token for password reset functionality,
    ensuring it is unique and safe to use in URLs.
    """
    return base64.urlsafe_b64encode(os.urandom(24)).decode('utf-8').rstrip('=')

class Member:
    """
    Represents a user/member with authentication details.
    Encapsulates username, name, email, admin status, password hash,
    and reset code management.
    """
    def __init__(self, username: str, name: str, email: str, is_admin: bool, password_hash: str, reset_code: Optional[str] = None, generate_reset: bool = False):
        self._username = username
        self._name = name
        self._email = email
        self._is_admin = is_admin
        self._password_hash = password_hash
        # Initialize reset code either from given code or generate a new one if requested
        if reset_code is not None:
            self._reset_code = reset_code
        elif generate_reset:
            self._reset_code = generate_reset_code()
        else:
            self._reset_code = None

    @property
    def username(self):
        """Return the user's username."""
        return self._username

    @property
    def name(self):
        """Return the user's full name."""
        return self._name

    @property
    def email(self):
        """Return the user's email address."""
        return self._email

    @property
    def is_admin(self):
        """Return True if the user has admin privileges, else False."""
        return self._is_admin

    @property
    def reset_code(self) -> Optional[str]:
        """Return the current password reset code if set, else None."""
        return self._reset_code


    def check_password(self, plain_password: str) -> bool:
        """
        Verify if the provided plain text password matches the stored password hash.
        
        Uses PBKDF2-HMAC-SHA256 with a salt (retrieved from environment variable SALT_B64)
        and 200,000 iterations for secure hashing. Compares the base64-encoded hashes
        using hmac.compare_digest to prevent timing attacks.
        """
        salt_b64 = os.getenv("SALT_B64")
        if not salt_b64:
            return False
        salt = base64.b64decode(salt_b64)
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt,
            200000
        )
        hashed_b64 = base64.b64encode(hashed).decode('utf-8')
        return hmac.compare_digest(hashed_b64, self._password_hash)

    def set_password(self, plain_password: str) -> str:
        """
        Hash the provided plain text password using PBKDF2-HMAC-SHA256 with the same salt and iteration count.
        
        Returns the base64-encoded hash string that can be stored as the password hash.
        Raises ValueError if the SALT_B64 environment variable is not set.
        """
        salt_b64 = os.getenv("SALT_B64")
        if not salt_b64:
            raise ValueError("SALT_B64 environment variable not set")
        salt = base64.b64decode(salt_b64)
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt,
            200000
        )
        return base64.b64encode(hashed).decode('utf-8')

    def set_reset_code(self, code: str):
        """
        Set the password reset code for the user.
        
        This code is typically generated when a user requests a password reset,
        and is used to verify the reset request.
        """
        self._reset_code = code

    def clear_reset_code(self):
        """
        Clear the password reset code.
        
        This is done after a successful password reset or when the reset code expires,
        to prevent reuse.
        """
        self._reset_code = None

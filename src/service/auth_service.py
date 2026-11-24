"""AuthService: users and login. Passwords are hashed with PBKDF2, never stored."""
import hashlib
import hmac
import os
from typing import Any

from src.db.db_manager import DBManager

ITERATIONS = 200_000
ROLES = ("Admin", "Student", "Faculty")


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    """Return (hash_hex, salt_hex). A new random salt is made if none is given."""
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return digest.hex(), salt.hex()


class AuthService:
    def __init__(self, db: DBManager) -> None:
        self.db = db

    def register(self, username: str, password: str, role: str, full_name: str) -> int:
        """Create a user. Raises ValueError with a clear message on bad input."""
        username = username.strip()
        if not username:
            raise ValueError("username is required")
        if len(password) < 6:
            raise ValueError("password must be at least 6 characters")
        if role not in ROLES:
            raise ValueError("role must be Admin, Student or Faculty")
        if not full_name.strip():
            raise ValueError("full name is required")
        pw_hash, salt = hash_password(password)
        return self.db.add_user(username, pw_hash, salt, role, full_name.strip())

    def login(self, username: str, password: str) -> dict[str, Any]:
        """Return the user (without the hash) or raise ValueError.
        The same message is used for a wrong username and a wrong password."""
        row = self.db.get_user(username.strip())
        if row is None:
            raise ValueError("invalid username or password")
        pw_hash, _ = hash_password(password, bytes.fromhex(row["salt"]))
        if not hmac.compare_digest(pw_hash, row["password_hash"]):
            raise ValueError("invalid username or password")
        return {"user_id": row["user_id"], "username": row["username"],
                "role": row["role"], "full_name": row["full_name"]}
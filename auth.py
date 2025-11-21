# auth.py

import json
from pathlib import Path
from datetime import datetime
import hashlib
import os
from typing import Dict, Any, Tuple

USERS_FILE = Path(__file__).with_name("users.json")


def _load_users() -> Dict[str, Any]:
    if not USERS_FILE.exists():
        return {"users": []}
    text = USERS_FILE.read_text(encoding="utf-8")
    if not text.strip():
        return {"users": []}
    return json.loads(text)


def _save_users(data: Dict[str, Any]) -> None:
    USERS_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _hash_password(password: str, salt: bytes = None) -> str:
    """
    Hash password with PBKDF2-HMAC-SHA256 + random salt.
    Stored format: HEX_SALT:HEX_HASH
    """
    if salt is None:
        salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, 100_000
    )
    return f"{salt.hex()}:{pwd_hash.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, hash_hex = stored.split(":")
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    expected_hash = bytes.fromhex(hash_hex)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, 100_000
    )
    return pwd_hash == expected_hash


def create_user(username: str, password: str) -> Tuple[bool, str]:
    """
    Create a new user with username + password.
    Returns (ok, message).
    """
    username = username.strip()
    if not username:
        return False, "Username cannot be empty."

    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    data = _load_users()
    for u in data["users"]:
        if u.get("username") == username:
            return False, "Username already exists."

    pwd_hash = _hash_password(password)
    data["users"].append(
        {
            "username": username,
            "password_hash": pwd_hash,
            "created_at": datetime.now().isoformat(),
        }
    )
    _save_users(data)
    return True, "User created successfully."


def verify_user(username: str, password: str) -> bool:
    """
    Check if username/password is correct.
    """
    username = username.strip()
    if not username:
        return False

    data = _load_users()
    for u in data["users"]:
        if u.get("username") == username:
            stored = u.get("password_hash", "")
            return _verify_password(password, stored)
    return False

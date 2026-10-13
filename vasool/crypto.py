"""Encryption at rest and password hashing.

* Every JSON document the store writes (transactions, profile, findings, cases, guardian,
  notifications) is sealed with AES-256-GCM before it touches SQLite. Opening `vasool.db` in a
  viewer shows ciphertext. Format: "enc1:" + base64(nonce[12] || ciphertext+tag).
* The data key is 32 random bytes. It comes from `VASOOL_SECRET_KEY` (base64) in `.env`, or is
  generated once into `data/.vasool.key` (owner-only permissions) — never committed, never logged.
* Passwords are never stored: PBKDF2-HMAC-SHA256, 200 000 iterations, 16-byte random salt.
* Legacy rows written before encryption (plain JSON) are still readable; they are re-sealed the
  next time they are saved.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path
from typing import Any, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parent.parent
PREFIX = "enc1:"
PBKDF2_ITERATIONS = 200_000
_key: Optional[bytes] = None


def key_path() -> Path:
    db = os.getenv("VASOOL_DB")
    base = Path(db).parent if db else ROOT / "data"
    return base / ".vasool.key"


def data_key() -> bytes:
    """The 32-byte AES key: env first, else a file created once. Cached for the process."""
    global _key
    if _key:
        return _key
    env = os.getenv("VASOOL_SECRET_KEY", "").strip()
    if env:
        raw = base64.urlsafe_b64decode(env + "=" * (-len(env) % 4))
        if len(raw) != 32:
            raise ValueError("VASOOL_SECRET_KEY must decode to 32 bytes")
        _key = raw
        return _key
    p = key_path()
    if p.exists():
        _key = base64.urlsafe_b64decode(p.read_text().strip())
        return _key
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = AESGCM.generate_key(bit_length=256)
    p.write_text(base64.urlsafe_b64encode(raw).decode())
    try:
        os.chmod(p, 0o600)
    except Exception:
        pass
    _key = raw
    return _key


def seal(obj: Any) -> str:
    """JSON → AES-256-GCM ciphertext string."""
    nonce = secrets.token_bytes(12)
    ct = AESGCM(data_key()).encrypt(nonce, json.dumps(obj, ensure_ascii=False).encode("utf-8"), None)
    return PREFIX + base64.b64encode(nonce + ct).decode()


def open_(s: Optional[str], default: Any = None) -> Any:
    """Ciphertext or legacy plain JSON → object. `default` when the column is empty."""
    if s is None or s == "":
        return default
    if isinstance(s, str) and s.startswith(PREFIX):
        raw = base64.b64decode(s[len(PREFIX):])
        pt = AESGCM(data_key()).decrypt(raw[:12], raw[12:], None)
        return json.loads(pt.decode("utf-8"))
    return json.loads(s)


def is_sealed(s: Optional[str]) -> bool:
    return isinstance(s, str) and s.startswith(PREFIX)


# ----- passwords -------------------------------------------------------------------------- #
def hash_password(password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
    """→ (salt_b64, hash_b64). Never store the password."""
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return base64.b64encode(salt).decode(), base64.b64encode(dk).decode()


def verify_password(password: str, salt_b64: str, hash_b64: str) -> bool:
    salt = base64.b64decode(salt_b64)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return hmac.compare_digest(base64.b64encode(dk).decode(), hash_b64)


def new_token() -> str:
    return secrets.token_urlsafe(32)

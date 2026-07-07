import hashlib
import secrets
from datetime import datetime

from shared.shared_lib.config import settings

PREFIX_LENGTH = 11

def generate_api_key() -> tuple[str, str, str]:
    """
    Generate new API key
    """
    random_part = secrets.token_urlsafe(18)
    raw_key = f"{settings.API_KEY_PREFIX}-{random_part}"
    key_prefix = raw_key[:PREFIX_LENGTH]
    key_hash = _hash_key(raw_key)
    return raw_key, key_prefix, key_hash

def _hash_key(raw_key: str) -> str:
    """hash SHA-256"""
    return hashlib.sha256(raw_key.encode()).hexdigest()

def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    """compare key hashs"""
    return secrets.compare_digest(_hash_key(raw_key), stored_hash)


def is_expired(expires_at: datetime | None) -> bool:
    """check expiration (None is infinite)"""
    if expires_at is None:
        return False
    return datetime.utcnow() > expires_at

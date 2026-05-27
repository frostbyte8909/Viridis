import hashlib
import os
import uuid
import base58

from app.config import settings
from app.models.db import ApiKey

def issue_raw_key() -> str:
    """Generates a secure random 32-byte key and base58 encodes it."""
    random_bytes = os.urandom(32)
    return f"viridis_{base58.b58encode(random_bytes).decode('utf-8')}"

def hash_key(raw_key: str) -> str:
    """Hashes the raw key using PBKDF2-HMAC-SHA256 and the server pepper."""
    salt = settings.server_pepper.encode()
    key_material = raw_key.encode()
    return hashlib.pbkdf2_hmac('sha256', key_material, salt, 100000).hex()

def create_api_key_record(tenant_id: uuid.UUID, plan_id: uuid.UUID, raw_key: str) -> ApiKey:
    """Creates an ApiKey ORM model from a raw key."""
    key_hash = hash_key(raw_key)
    # The prefix is the first 8 characters after 'viridis_'
    prefix = raw_key[8:16]
    
    return ApiKey(
        tenant_id=tenant_id,
        plan_id=plan_id,
        key_hash=key_hash,
        key_prefix=prefix
    )

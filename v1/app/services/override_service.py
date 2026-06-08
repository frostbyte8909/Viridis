import hmac
import hashlib

from app.config import settings

def verify_override_signature(nonce: str, override_type: str, api_key_id: str, expires_at: str, signature: str) -> bool:
    """
    Verifies the HMAC-SHA256 signature of an override command.
    Payload = nonce + override_type + api_key_id + expires_at
    """
    payload = f"{nonce}{override_type}{api_key_id}{expires_at}".encode()
    signing_key = settings.admin_token.encode()  # Assuming admin token is the signing key here for local testing
    
    expected_mac = hmac.new(signing_key, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_mac, signature)

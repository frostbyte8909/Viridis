import pytest
import jwt
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
import hashlib
import json
import asyncio

from app.middleware.jwt_auth import verify_jwt, JWTClaims
from app.config import settings
from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerError, execute_with_circuit_breaker
from app.services.audit_export import verify_export_chain

@pytest.fixture
def rsa_key_pair():
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    public_key = private_key.public_key()
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return pem, pub_pem

def test_jwt_verification(rsa_key_pair):
    priv, pub = rsa_key_pair
    # Setup settings for static PEM testing
    settings.jwks_url = None
    settings.jwt_static_pem = pub.decode("utf-8")
    
    token = jwt.encode(
        {"tenant_id": "tenant123", "api_key_id": "key123", "exp": 9999999999, "iat": 1600000000},
        priv,
        algorithm="RS256"
    )
    
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    claims = verify_jwt(credentials)
    
    assert claims.tenant_id == "tenant123"
    assert claims.api_key_id == "key123"
    
def test_jwt_missing_claims(rsa_key_pair):
    priv, pub = rsa_key_pair
    settings.jwt_static_pem = pub.decode("utf-8")
    
    token = jwt.encode(
        {"exp": 9999999999, "iat": 1600000000}, # missing tenant_id and api_key_id
        priv,
        algorithm="RS256"
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    
    with pytest.raises(HTTPException) as exc:
        verify_jwt(credentials)
    assert exc.value.status_code == 401

@pytest.mark.asyncio
async def test_circuit_breaker_transitions():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
    
    assert cb.state == "CLOSED"
    assert cb.allow_request() is True
    
    # Simulate failures
    cb.record_failure()
    cb.record_failure()
    
    assert cb.state == "OPEN"
    assert cb.allow_request() is False
    
    # Wait for recovery timeout
    await asyncio.sleep(1.1)
    
    # Should transition to HALF-OPEN and allow one test request
    assert cb.allow_request() is True
    assert cb.state == "HALF-OPEN"
    
    # If successful, should CLOSE
    cb.record_success()
    assert cb.state == "CLOSED"

@pytest.mark.asyncio
async def test_circuit_breaker_context_manager():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1)
    
    with pytest.raises(ValueError):
        async with execute_with_circuit_breaker(cb):
            raise ValueError("DB down")
            
    assert cb.state == "OPEN"
    
    with pytest.raises(CircuitBreakerError):
        async with execute_with_circuit_breaker(cb):
            pass # Request denied

def test_audit_hash_chain_verification():
    record1 = {"id": "1", "decision": "ALLOW"}
    record2 = {"id": "2", "decision": "DENY"}
    
    # genesis
    prev_hash = "0" * 64
    
    # entry 1
    r1_json = json.dumps(record1, sort_keys=True)
    h1 = hashlib.sha256(f"{r1_json}{prev_hash}".encode()).hexdigest()
    
    # entry 2
    r2_json = json.dumps(record2, sort_keys=True)
    h2 = hashlib.sha256(f"{r2_json}{h1}".encode()).hexdigest()
    
    lines = [
        json.dumps({"record": record1, "previous_hash": prev_hash, "hash": h1}),
        json.dumps({"record": record2, "previous_hash": h1, "hash": h2})
    ]
    
    assert verify_export_chain(lines) is True
    
    # tamper
    lines_tampered = [
        json.dumps({"record": record1, "previous_hash": prev_hash, "hash": h1}),
        json.dumps({"record": {"id": "2", "decision": "ALLOW"}, "previous_hash": h1, "hash": h2})
    ]
    assert verify_export_chain(lines_tampered) is False

import pytest
from app.services.payload_scanner import scan_payload

@pytest.mark.parametrize("payload,expected_reason", [
    # SQLi payloads
    ("' OR '1'='1", "SQL_INJECTION"),
    ("UNION SELECT * FROM users", "SQL_INJECTION"),
    ("'; DROP TABLE users;", "SQL_INJECTION"),
    ("1=1", "SQL_INJECTION"),
    
    # XSS payloads
    ("<script>alert('xss')</script>", "XSS"),
    ("javascript:alert('xss')", "XSS"),
    ("<img onerror='alert(1)'>", "XSS"),
    ("<iframe src='evil.com'>", "XSS"),
    
    # PII payloads
    ("1234 5678 9012 3456", "PII_LEAKAGE"),  # Credit card
    ("123-45-6789", "PII_LEAKAGE"),  # SSN
    
    # Safe payloads
    ("Hello, world!", "SAFE"),
    ('{"name": "John"}', "SAFE"),
    ("SELECT * FROM users WHERE id = 1", "SAFE"),  # Legitimate SQL (no malicious intent based on our basic regex)
])
def test_payload_scanner(payload: str, expected_reason: str):
    """Test payload scanner detects SQLi/XSS/PII."""
    is_safe, reason = scan_payload(payload)
    
    if expected_reason == "SAFE":
        assert is_safe is True
        assert reason == "SAFE"
    else:
        assert is_safe is False
        assert reason == expected_reason

def test_payload_scanner_empty_payload():
    """Test scanner allows empty payload."""
    is_safe, reason = scan_payload("")
    assert is_safe is True
    assert reason == "SAFE"

def test_payload_scanner_none_payload():
    """Test scanner allows None payload."""
    is_safe, reason = scan_payload(None)
    assert is_safe is True
    assert reason == "SAFE"

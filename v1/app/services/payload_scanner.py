import re
from functools import lru_cache
from typing import Tuple

# Pre-compiled regex (module load, not per-request)
SQLI_PATTERNS = [
    re.compile(r"(?i)union\s+select", re.IGNORECASE),
    re.compile(r"(?i)'\s*or\s*'", re.IGNORECASE),
    re.compile(r"(?i)--\s*$", re.IGNORECASE),
    re.compile(r"(?i);\s*drop\s+table", re.IGNORECASE),
    re.compile(r"(?i);\s*delete\s+from", re.IGNORECASE),
    re.compile(r"(?i);\s*update\s+.*\s+set", re.IGNORECASE),
    re.compile(r"(?i);\s*insert\s+into", re.IGNORECASE),
    re.compile(r"(?i)'\s*and\s*'", re.IGNORECASE),
    re.compile(r"(?i)1\s*=\s*1", re.IGNORECASE),
    re.compile(r"(?i)null\s*=\s*null", re.IGNORECASE),
]

XSS_PATTERNS = [
    re.compile(r"(?i)<script", re.IGNORECASE),
    re.compile(r"(?i)javascript:", re.IGNORECASE),
    re.compile(r"(?i)on\w+\s*=", re.IGNORECASE),  # onclick, onload, onerror
    re.compile(r"(?i)<img\s+.*onerror", re.IGNORECASE),
    re.compile(r"(?i)<iframe", re.IGNORECASE),
    re.compile(r"(?i)<object", re.IGNORECASE),
    re.compile(r"(?i)<embed", re.IGNORECASE),
    re.compile(r"(?i)document\.cookie", re.IGNORECASE),
    re.compile(r"(?i)document\.location", re.IGNORECASE),
]

PII_PATTERNS = [
    re.compile(r"\b\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\b"),  # Credit card (16 digits)
    re.compile(r"\b\d{3}\s*\d{2}\s*\d{4}\b"),  # SSN (9 digits)
]

# LRU cache for repeated payloads
@lru_cache(maxsize=1000)
def cache_scan(payload: str, pattern_type: str) -> bool:
    """Cache scan results for repeated payloads."""
    if pattern_type == "sqli":
        return any(p.search(payload) for p in SQLI_PATTERNS)
    elif pattern_type == "xss":
        return any(p.search(payload) for p in XSS_PATTERNS)
    elif pattern_type == "pii":
        return any(p.search(payload) for p in PII_PATTERNS)
    return False

def scan_payload(payload: str | None) -> Tuple[bool, str]:
    """
    Scan payload for SQLi, XSS, PII.
    
    Returns:
        Tuple[is_safe, reason]
        - (True, "SAFE") if payload is clean
        - (False, "SQL_INJECTION") if SQLi detected
        - (False, "XSS") if XSS detected
        - (False, "PII_LEAKAGE") if PII detected
    """
    if not payload:
        return True, "SAFE"
    
    # Check cache first (O(1) for repeated payloads)
    if cache_scan(payload, "sqli"):
        return False, "SQL_INJECTION"
    
    if cache_scan(payload, "xss"):
        return False, "XSS"
    
    if cache_scan(payload, "pii"):
        return False, "PII_LEAKAGE"
    
    return True, "SAFE"

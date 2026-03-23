"""
pii_detector.py — Regex-based PII detection.

Detects: SSN, credit card numbers, email addresses, phone numbers,
         Indian Aadhaar numbers, PAN card numbers, passport numbers.
Returns a PIIResult with: detected entities, redacted text, and a boolean flag.
"""

import re
from dataclasses import dataclass, field

# ─────────────────────────────────────────────
# PII Pattern library
# ─────────────────────────────────────────────

PII_PATTERNS: dict[str, str] = {
    "SSN":          r"\b(?!000|666|9\d{2})\d{3}[- ]?\d{2}[- ]?\d{4}\b",
    "CREDIT_CARD":  r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12})\b",
    "EMAIL":        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
    "PHONE_US":     r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "PHONE_IN":     r"\b(?:\+91[-.\s]?)?[6-9]\d{9}\b",
    "AADHAAR":      r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b",
    "PAN":          r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
    "PASSPORT":     r"\b[A-Z][0-9]{7}\b",
    "IP_ADDRESS":   r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "DATE_OF_BIRTH":r"\b(?:0[1-9]|[12]\d|3[01])[-/.](?:0[1-9]|1[0-2])[-/.](?:19|20)\d{2}\b",
}


@dataclass
class PIIResult:
    has_pii: bool
    detected: list[str] = field(default_factory=list)    # entity types found
    redacted_text: str = ""                               # text with PII masked
    details: list[dict] = field(default_factory=list)    # [{type, match}, ...]


def detect_pii(text: str) -> PIIResult:
    """
    Scan `text` for PII patterns.
    Returns a PIIResult with all findings and a redacted copy of the text.
    """
    detected_types: list[str] = []
    details: list[dict] = []
    redacted = text

    for entity_type, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, text)
        if matches:
            detected_types.append(entity_type)
            for m in matches:
                details.append({"type": entity_type, "match": m})
            # Replace with [REDACTED_<TYPE>]
            redacted = re.sub(pattern, f"[REDACTED_{entity_type}]", redacted)

    return PIIResult(
        has_pii=len(detected_types) > 0,
        detected=detected_types,
        redacted_text=redacted,
        details=details,
    )


def redact(text: str) -> str:
    """Convenience: returns only the redacted string."""
    return detect_pii(text).redacted_text

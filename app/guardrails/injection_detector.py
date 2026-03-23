"""
injection_detector.py — Prompt injection attack detection.

Uses a curated pattern library of known adversarial prompt techniques:
  - Instruction overrides ("ignore previous", "disregard above")
  - Jailbreak triggers ("act as DAN", "DAN mode", "pretend you have no rules")
  - Role hijacking ("you are now", "your new instructions")
  - System prompt extraction ("repeat your system prompt", "print your instructions")
  - Separator injection ("---\nSystem:", "[INST]", "<|im_start|>system")
"""

import re
from dataclasses import dataclass

# ─────────────────────────────────────────────
# Injection pattern library
# ─────────────────────────────────────────────

INJECTION_PATTERNS: list[tuple[str, str]] = [
    # Instruction override
    ("INSTRUCTION_OVERRIDE",    r"(?i)ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|context|rules?)"),
    ("INSTRUCTION_OVERRIDE",    r"(?i)disregard\s+(all\s+)?(your\s+)?(instructions?|system\s+prompt|previous)"),
    ("INSTRUCTION_OVERRIDE",    r"(?i)forget\s+(everything|all)\s+(you|i|we)\s+(told|said|wrote|instructed)"),
    ("INSTRUCTION_OVERRIDE",    r"(?i)override\s+(your\s+)?(instructions?|rules?|guidelines?)"),

    # Jailbreak
    ("JAILBREAK",               r"(?i)\bdan\s+mode\b"),
    ("JAILBREAK",               r"(?i)\bact\s+as\s+(dan|jailbreak|evil|unrestricted|uncensored)\b"),
    ("JAILBREAK",               r"(?i)\bpretend\s+(you\s+have\s+no\s+(rules?|restrictions?|ethics?)|you\s+are\s+(free|unfiltered|evil))"),
    ("JAILBREAK",               r"(?i)\byou\s+are\s+no\s+longer\s+(an?\s+)?(ai|assistant|chatbot)\b"),
    ("JAILBREAK",               r"(?i)\bdo\s+anything\s+now\b"),
    ("JAILBREAK",               r"(?i)\bjailbreak\b"),

    # Role hijacking
    ("ROLE_HIJACK",             r"(?i)you\s+are\s+now\s+(a|an|my)?\s+(hacker|attacker|adversary|evil|unrestricted)"),
    ("ROLE_HIJACK",             r"(?i)(from\s+now\s+on|starting\s+now)\s*[,:]?\s*you\s+(will|must|should|are)\s+(act|behave|respond|answer)"),
    ("ROLE_HIJACK",             r"(?i)your\s+(new\s+)?(role|persona|identity|instructions?|rules?)\s+(is|are|will\s+be)"),

    # System prompt extraction
    ("PROMPT_EXTRACTION",       r"(?i)(print|repeat|show|reveal|tell\s+me|output|display)\s+(your\s+)?(system\s+prompt|initial\s+instructions?|original\s+prompt|full\s+instructions?)"),
    ("PROMPT_EXTRACTION",       r"(?i)what\s+(are|were)\s+your\s+(original|initial|exact|full|original)\s+instructions?"),
    ("PROMPT_EXTRACTION",       r"(?i)leak\s+(your\s+)?(system|internal|hidden)\s+(prompt|message|instructions?)"),

    # Separator / delimiter injection
    ("SEPARATOR_INJECTION",     r"(?i)(---+|===+|\*\*\*+)\s*\n\s*(system|human|assistant|user|instruction)\s*:"),
    ("SEPARATOR_INJECTION",     r"\[INST\]|\[\/INST\]|<\|im_start\|>|<\|im_end\|>|<\|system\|>"),
    ("SEPARATOR_INJECTION",     r"(?i)##\s*(system|instruction|override)\s*:"),

    # Credential / password fishing
    ("CREDENTIAL_FISHING",      r"(?i)(show|list|print|tell\s+me)\s+(all\s+)?(user|admin|system)\s+(passwords?|credentials?|login\s+info)"),
    ("CREDENTIAL_FISHING",      r"(?i)what\s+(is|are)\s+(the\s+)?(admin|root|master)\s+password"),
]


@dataclass
class InjectionResult:
    is_injection: bool
    attack_type: str = ""
    matched_pattern: str = ""


def detect_injection(text: str) -> InjectionResult:
    """
    Scan `text` for prompt injection signatures.
    Returns InjectionResult with the attack type if detected.
    """
    for attack_type, pattern in INJECTION_PATTERNS:
        if re.search(pattern, text):
            return InjectionResult(
                is_injection=True,
                attack_type=attack_type,
                matched_pattern=pattern,
            )
    return InjectionResult(is_injection=False)

"""
scope_filter.py — Out-of-scope query detection for a financial enterprise assistant.

FinSolve-AI should only answer questions relevant to:
  - Company finance, budgets, revenue, expenses
  - HR policies, leave, payroll, performance
  - Engineering systems, architecture, incidents
  - Marketing campaigns, metrics, brand
  - General company policies and procedures

Anything outside these domains (general trivia, personal advice,
cooking, entertainment, etc.) is considered out-of-scope.
"""

import re
from dataclasses import dataclass

# ─────────────────────────────────────────────
# In-scope keyword sets (at least one must match)
# ─────────────────────────────────────────────

IN_SCOPE_KEYWORDS: list[str] = [
    # Finance
    "revenue", "budget", "expense", "profit", "loss", "invoice", "payroll",
    "salary", "cost", "financial", "quarter", "fiscal", "accounting", "audit",
    "balance sheet", "cash flow", "tax", "investment", "valuation",
    # HR
    "leave", "vacation", "policy", "employee", "hire", "onboard", "offboard",
    "performance review", "appraisal", "benefit", "insurance", "hr", "human resource",
    "resignation", "termination", "training", "learning",
    # Engineering
    "system", "architecture", "api", "deployment", "incident", "bug", "feature",
    "sprint", "release", "codebase", "infrastructure", "database", "microservice",
    "pipeline", "devops", "kubernetes", "docker", "cloud",
    # Marketing
    "campaign", "marketing", "brand", "lead", "conversion", "ctr", "roi",
    "social media", "seo", "content", "customer acquisition", "funnel",
    # General company
    "company", "finsolve", "department", "meeting", "report", "team", "manager",
    "project", "deadline", "roadmap", "strategy", "vision", "mission", "quarter",
]

# ─────────────────────────────────────────────
# Explicitly out-of-scope patterns
# ─────────────────────────────────────────────

OUT_OF_SCOPE_PATTERNS: list[tuple[str, str]] = [
    ("GENERAL_TRIVIA",      r"(?i)(what\s+is\s+the\s+(capital|population|area)\s+of|who\s+(invented|discovered|wrote)|which\s+year\s+was\s+.{1,50}\s+(born|founded|built))"),
    ("PERSONAL_ADVICE",     r"(?i)(advise\s+me\s+on\s+my\s+(relationship|life|health)|what\s+should\s+i\s+(eat|wear|do\s+for\s+fun)|how\s+do\s+i\s+lose\s+weight)"),
    ("ENTERTAINMENT",       r"(?i)(recommend\s+(a\s+)?(movie|show|book|song|game|restaurant)|best\s+(netflix|spotify|youtube)|top\s+10\s+(movies|songs|games))"),
    ("RELIGION_POLITICS",   r"(?i)(which\s+(religion|political\s+party)\s+is\s+better|is\s+(god|allah|jesus|modi|biden|trump)\s+(real|good|bad|right))"),
    ("ILLEGAL_ACTIVITY",    r"(?i)(how\s+to\s+(hack|crack|pirate|steal|bypass\s+security|launder\s+money))"),
    ("MEDICAL_ADVICE",      r"(?i)(diagnose\s+(my|the)\s+(symptom|disease|illness)|what\s+(medicine|drug)\s+should\s+i\s+take)"),
]


@dataclass
class ScopeResult:
    in_scope: bool
    reason: str = ""
    matched_keyword: str = ""


def is_in_scope(text: str, role: str = "employee") -> ScopeResult:
    """
    Determine if a query is within the scope of a financial enterprise assistant.

    Strategy:
    1. Check explicit out-of-scope patterns → reject immediately
    2. Check if at least one in-scope keyword is present → allow
    3. Very short queries (< 5 words) get the benefit of the doubt → allow
    4. Default: block if no scoped keywords matched and query is long enough
    """
    text_lower = text.lower()

    # Step 1: Hard out-of-scope patterns
    for category, pattern in OUT_OF_SCOPE_PATTERNS:
        if re.search(pattern, text):
            return ScopeResult(
                in_scope=False,
                reason=f"Query appears to be about {category.lower().replace('_', ' ')}, which is outside FinSolve-AI's scope.",
            )

    # Step 2: In-scope keyword check
    for kw in IN_SCOPE_KEYWORDS:
        if kw in text_lower:
            return ScopeResult(in_scope=True, matched_keyword=kw)

    # Step 3: Short queries allowed (greetings, simple follow-ups)
    word_count = len(text.strip().split())
    if word_count <= 5:
        return ScopeResult(in_scope=True, reason="Short query, allowing by default.")

    # Step 4: Ambiguous longer query — block
    return ScopeResult(
        in_scope=False,
        reason="Query does not appear to relate to company operations, finance, HR, engineering, or marketing.",
    )

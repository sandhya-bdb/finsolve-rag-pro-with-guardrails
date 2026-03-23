"""
rbac.py — Role-Based Access Control with hierarchy and permission matrix.

Roles (highest → lowest privilege):
  c-levelexecutives > finance > hr > engineering > marketing > employee

Each role can access its own documents PLUS any role below it in the hierarchy.
"""

from typing import Optional

# ─────────────────────────────────────────────
# Role definitions & hierarchy
# ─────────────────────────────────────────────

ROLE_HIERARCHY: dict[str, int] = {
    "c-levelexecutives": 100,
    "finance": 70,
    "hr": 60,
    "engineering": 50,
    "marketing": 40,
    "employee": 10,
}

# Which document namespaces each role can retrieve (additive / inherited)
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "c-levelexecutives": ["finance", "hr", "engineering", "marketing", "general", "c-levelexecutives"],
    "finance":           ["finance", "general"],
    "hr":                ["hr", "general"],
    "engineering":       ["engineering", "general"],
    "marketing":         ["marketing", "general"],
    "employee":          ["general"],
}

# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def get_allowed_namespaces(role: str) -> list[str]:
    """Return the list of document namespaces this role may access."""
    role = role.lower().strip()
    return ROLE_PERMISSIONS.get(role, ["general"])


def get_chroma_filter(role: str) -> Optional[dict]:
    """
    Build a ChromaDB $in metadata filter for the role's allowed namespaces.
    C-level execs get no filter (access everything).
    """
    role = role.lower().strip()
    if role == "c-levelexecutives":
        return None  # unrestricted — Chroma returns all docs

    allowed = get_allowed_namespaces(role)
    if len(allowed) == 1:
        return {"role": allowed[0]}
    return {"role": {"$in": allowed}}


def get_role_level(role: str) -> int:
    """Return numeric privilege level for a role."""
    return ROLE_HIERARCHY.get(role.lower().strip(), 0)


def can_access(user_role: str, required_role: str) -> bool:
    """True if user_role has at least as much privilege as required_role."""
    return get_role_level(user_role) >= get_role_level(required_role)


def is_valid_role(role: str) -> bool:
    return role.lower().strip() in ROLE_HIERARCHY

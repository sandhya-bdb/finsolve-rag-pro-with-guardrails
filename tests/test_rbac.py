"""test_rbac.py - Unit tests for the RBAC module."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from services.rbac import (
    can_access,
    get_allowed_namespaces,
    get_chroma_filter,
    get_role_level,
    is_valid_role,
)


class TestRBAC:
    def test_clevel_gets_no_filter(self):
        assert get_chroma_filter("c-levelexecutives") is None

    def test_finance_gets_finance_filter(self):
        chroma_filter = get_chroma_filter("finance")
        assert "finance" in (chroma_filter.get("role", {}).get("$in", [chroma_filter.get("role")])) or chroma_filter.get("role") == "finance"

    def test_employee_only_gets_general(self):
        ns = get_allowed_namespaces("employee")
        assert ns == ["general"]

    def test_hr_gets_hr_and_general(self):
        ns = get_allowed_namespaces("hr")
        assert "hr" in ns
        assert "general" in ns

    def test_clevel_gets_all_namespaces(self):
        ns = get_allowed_namespaces("c-levelexecutives")
        assert len(ns) > 4

    def test_role_hierarchy_levels(self):
        assert get_role_level("c-levelexecutives") > get_role_level("finance")
        assert get_role_level("finance") > get_role_level("employee")
        assert get_role_level("hr") > get_role_level("employee")

    def test_can_access_own_level(self):
        assert can_access("finance", "finance") is True

    def test_high_role_can_access_low_role(self):
        assert can_access("c-levelexecutives", "employee") is True

    def test_low_role_cannot_access_high_role(self):
        assert can_access("employee", "c-levelexecutives") is False

    def test_valid_role_check(self):
        assert is_valid_role("finance") is True
        assert is_valid_role("superadmin") is False
        assert is_valid_role("FINANCE") is True

    def test_unknown_role_gets_general_only(self):
        ns = get_allowed_namespaces("unknown_role")
        assert ns == ["general"]

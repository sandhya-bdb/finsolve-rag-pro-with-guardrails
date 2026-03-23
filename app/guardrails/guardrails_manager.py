"""
guardrails_manager.py — Unified guardrails pipeline.

Runs checks in order (fast-fail):
  1. Prompt injection detection  (security-critical, checked first)
  2. PII detection               (privacy, reject or redact)
  3. Scope filtering             (product boundary)

Also provides output-side guardrails for LLM responses.
"""

from dataclasses import dataclass
from .pii_detector import detect_pii, PIIResult
from .injection_detector import detect_injection, InjectionResult
from .scope_filter import is_in_scope, ScopeResult


@dataclass
class GuardrailResult:
    passed: bool
    blocked_reason: str = ""
    block_type: str = ""          # "INJECTION" | "PII" | "SCOPE" | "OUTPUT_PII"
    sanitized_input: str = ""     # redacted version if PII found but not blocked
    pii_result: PIIResult = None
    injection_result: InjectionResult = None
    scope_result: ScopeResult = None


class GuardrailsManager:
    """
    Configurable guardrails pipeline.

    Parameters
    ----------
    block_on_pii : bool
        If True, queries containing PII are blocked outright.
        If False, PII is redacted and the sanitized query is forwarded.
    """

    def __init__(self, block_on_pii: bool = True):
        self.block_on_pii = block_on_pii

    # ─────────────────────────────────────────
    # Input checks
    # ─────────────────────────────────────────

    def check_input(self, text: str, role: str = "employee") -> GuardrailResult:
        """
        Run all input guardrails. Returns a GuardrailResult.
        Short-circuits on first failure.
        """

        # 1. Injection detection — highest priority
        inj = detect_injection(text)
        if inj.is_injection:
            return GuardrailResult(
                passed=False,
                blocked_reason=(
                    f"Your message contains patterns associated with prompt injection "
                    f"attacks ({inj.attack_type}). This request has been blocked and logged."
                ),
                block_type="INJECTION",
                sanitized_input="",
                injection_result=inj,
            )

        # 2. PII detection
        pii = detect_pii(text)
        if pii.has_pii:
            if self.block_on_pii:
                entity_types = ", ".join(pii.detected)
                return GuardrailResult(
                    passed=False,
                    blocked_reason=(
                        f"Your message appears to contain sensitive personal information "
                        f"({entity_types}). Please remove PII before continuing."
                    ),
                    block_type="PII",
                    sanitized_input=pii.redacted_text,
                    pii_result=pii,
                )
            else:
                # Redact and allow through
                text = pii.redacted_text

        # 3. Scope filtering
        scope = is_in_scope(text, role)
        if not scope.in_scope:
            return GuardrailResult(
                passed=False,
                blocked_reason=(
                    f"FinSolve-AI is an enterprise assistant and can only answer questions "
                    f"related to company operations. {scope.reason}"
                ),
                block_type="SCOPE",
                sanitized_input="",
                scope_result=scope,
            )

        return GuardrailResult(
            passed=True,
            sanitized_input=text,
            pii_result=pii,
            injection_result=inj,
            scope_result=scope,
        )

    # ─────────────────────────────────────────
    # Output checks
    # ─────────────────────────────────────────

    def check_output(self, text: str) -> GuardrailResult:
        """
        Scan LLM output for accidentally leaked PII.
        Redacts rather than blocking (we always return something).
        """
        pii = detect_pii(text)
        if pii.has_pii:
            return GuardrailResult(
                passed=True,   # output still returned, but redacted
                block_type="OUTPUT_PII",
                sanitized_input=pii.redacted_text,
                pii_result=pii,
                blocked_reason=f"Output contained PII ({', '.join(pii.detected)}), auto-redacted.",
            )
        return GuardrailResult(passed=True, sanitized_input=text)


# Singleton for use across the app
guardrails = GuardrailsManager(block_on_pii=True)

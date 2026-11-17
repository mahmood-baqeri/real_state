"""Minimal state machine for enforcing valid status transitions."""
from typing import Dict, Set, Type


class InvalidTransitionError(ValueError):
    pass


class StateMachine:
    """
    Usage:
        class DealStatusSM(StateMachine):
            transitions = {
                "CALCULATED": {"MANAGER_APPROVED", "REVERSED"},
                "MANAGER_APPROVED": {"FINANCE_APPROVED", "REVERSED"},
                "FINANCE_APPROVED": {"SETTLED", "REVERSED"},
                "SETTLED": {"REVERSED"},
                "REVERSED": set(),
            }
            @classmethod
            def transition(cls, current, target, label="status"):
                cls.validate(current, target, label)
                return target
    """

    transitions: Dict[str, Set[str]] = {}

    @classmethod
    def validate(cls, current: str, target: str, label: str = "status") -> None:
        if current == target:
            return
        allowed = cls.transitions.get(current, set())
        if target not in allowed:
            raise InvalidTransitionError(
                f"انتقال نامعتبر برای {label}: «{current}» → «{target}» مجاز نیست. "
                f"گزینه‌های مجاز: {', '.join(sorted(allowed)) or 'هیچ'}"
            )
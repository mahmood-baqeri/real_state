# Path: backend/fastapi_core/app/core/state.py

"""
State machine helpers — generic. Domain-specific transitions
تعریف می‌شوند در `django_core/common/state_machine.py`.
"""


class InvalidTransitionError(ValueError):
    pass
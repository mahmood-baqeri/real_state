"""
Django Core Domain Services Facade.
All business rules, atomic DB transactions, double-entry accounting invariants,
and tenant-scoped domain mutations live inside Django Core.
"""
from apps.audit.services import record_audit_event

__all__ = ["record_audit_event"]

"""Deterministic, explainable CRM sales-intelligence calculations for Phase 3."""
from collections import Counter
from datetime import timedelta
from django.db.models import Q
from django.utils import timezone

from apps.customers.models import Customer
from apps.crm.models import CustomerInteractionLog, FollowUpTask
from apps.negotiations.models import Negotiation
from common.permissions import get_active_membership, has_agency_permission, is_super_admin


TERMINAL = {"ACCEPTED", "REJECTED", "CANCELLED", "WITHDRAWN", "EXPIRED"}
ADVANCED = {"BARGAINING", "PRE_AGREEMENT", "AWAITING_FINAL_APPROVAL", "OWNER_COUNTERED", "BUYER_OFFERED"}


def _readable_customers(*, user, agency_id):
    qs = Customer.objects.all_tenants().filter(agency_id=agency_id, is_deleted=False, is_active=True)
    if is_super_admin(user):
        return qs
    membership = get_active_membership(user, agency_id)
    if not membership:
        return qs.none()
    if membership.role.code == "BRANCH_MANAGER":
        return qs.filter(assigned_membership__branch_id=membership.branch_id) if membership.branch_id else qs.none()
    if not has_agency_permission(user, agency_id, "customer.view_all_agency"):
        qs = qs.filter(Q(assigned_membership=membership) | Q(shares__membership=membership, shares__expires_at__isnull=True) | Q(shares__membership=membership, shares__expires_at__gt=timezone.now())).distinct()
    return qs


def score_customer(customer, interactions, open_tasks, negotiations, now=None):
    """Rule-based 0..100 score. Returned factors make it transparent; not a trained model."""
    now = now or timezone.now()
    score = 20
    factors = [{"label": "امتیاز پایه", "delta": 20}]
    req_count = sum(1 for req in customer.requirements.all() if req.is_active)
    if req_count:
        score += 15
        factors.append({"label": f"نیاز فعال ثبت‌شده ({req_count})", "delta": 15})
    recent = [i for i in interactions if i.created_at >= now - timedelta(days=30)]
    if recent:
        delta = min(20, len(recent) * 4)
        score += delta
        factors.append({"label": f"تعامل در ۳۰ روز اخیر ({len(recent)})", "delta": delta})
    if interactions:
        age = (now - interactions[0].created_at).days
        if age <= 3:
            delta = 15
        elif age <= 7:
            delta = 10
        elif age <= 30:
            delta = 5
        else:
            delta = 0
        if delta:
            score += delta
            factors.append({"label": f"آخرین تعامل {age} روز قبل", "delta": delta})
    overdue = [t for t in open_tasks if t.due_at < now]
    if overdue:
        delta = -min(20, len(overdue) * 5)
        score += delta
        factors.append({"label": f"وظیفه عقب‌افتاده ({len(overdue)})", "delta": delta})
    active_neg = [n for n in negotiations if n.status not in TERMINAL]
    if active_neg:
        score += 15
        factors.append({"label": f"مذاکره فعال ({len(active_neg)})", "delta": 15})
        if any(n.status in ADVANCED for n in active_neg):
            score += 10
            factors.append({"label": "مذاکره در مرحله پیشرفته", "delta": 10})
    score = max(0, min(100, score))
    level = "HOT" if score >= 80 else "HIGH" if score >= 65 else "MEDIUM" if score >= 40 else "LOW"
    return score, level, factors


def get_sales_intelligence(*, user, agency_id):
    now = timezone.now()
    customers = list(_readable_customers(user=user, agency_id=agency_id).select_related("assigned_membership__user").prefetch_related("requirements"))
    ids = [c.id for c in customers]
    interactions_by_customer = {}
    iq = CustomerInteractionLog.objects.all_tenants().filter(agency_id=agency_id, customer_id__in=ids).select_related("membership__user").order_by("-created_at")
    if not is_super_admin(user) and not has_agency_permission(user, agency_id, "crm.private_note.view"):
        membership = get_active_membership(user, agency_id)
        iq = iq.filter(Q(is_private=False) | Q(created_by=user) | Q(membership=membership))
    for item in iq:
        interactions_by_customer.setdefault(item.customer_id, []).append(item)
    membership = get_active_membership(user, agency_id) if not is_super_admin(user) else None
    task_q = FollowUpTask.objects.all_tenants().filter(agency_id=agency_id, customer_id__in=ids, status=FollowUpTask.Status.OPEN).select_related("assigned_membership__user", "assigned_membership__branch")
    if membership and membership.role.code == "BRANCH_MANAGER":
        task_q = task_q.filter(assigned_membership__branch_id=membership.branch_id) if membership.branch_id else task_q.none()
    elif membership and not has_agency_permission(user, agency_id, "customer.view_all_agency"):
        task_q = task_q.filter(assigned_membership=membership)
    task_by_customer = {}
    for task in task_q:
        task_by_customer.setdefault(task.customer_id, []).append(task)
    negotiation_q = Negotiation.objects.all_tenants().filter(agency_id=agency_id, customer_id__in=ids).select_related("property__branch", "agent_membership__branch").order_by("-created_at")
    if membership and membership.role.code == "BRANCH_MANAGER":
        negotiation_q = negotiation_q.filter(property__branch_id=membership.branch_id) if membership.branch_id else negotiation_q.none()
    elif membership and not has_agency_permission(user, agency_id, "customer.view_all_agency"):
        negotiation_q = negotiation_q.filter(agent_membership=membership)
    neg_by_customer = {}
    for n in negotiation_q:
        neg_by_customer.setdefault(n.customer_id, []).append(n)
    rows = []
    lost_reasons = Counter()
    inactive = []
    for c in customers:
        interactions = interactions_by_customer.get(c.id, [])
        tasks = task_by_customer.get(c.id, [])
        negotiations = neg_by_customer.get(c.id, [])
        score, level, factors = score_customer(c, interactions, tasks, negotiations, now)
        active_negotiation_count = sum(1 for n in negotiations if n.status not in TERMINAL)
        # Explainable heuristic estimate; explicitly not a trained/calibrated prediction.
        conversion_probability = min(85, max(5, round(score * 0.55 + (15 if active_negotiation_count else 0))))
        last_interaction = interactions[0].created_at if interactions else None
        idle_days = (now - last_interaction).days if last_interaction else (now - c.created_at).days
        has_open_task = bool(tasks)
        is_inactive = idle_days >= 30 and not has_open_task and not any(n.status not in TERMINAL for n in negotiations)
        if is_inactive:
            inactive.append({"customer_id": str(c.id), "customer_name": c.full_name, "agent_name": c.assigned_membership.user.full_name if c.assigned_membership else "بدون مسئول", "idle_days": idle_days, "score": score})
        if is_inactive and idle_days >= 60:
            action = "بازفعال‌سازی مشتری را با تماس شخصی شروع کنید."
            title = "تماس برای بازفعال‌سازی مشتری"
        elif tasks and any(t.due_at < now for t in tasks):
            action = "وظایف عقب‌افتاده را بررسی و نتیجه تماس را ثبت کنید."
            title = "پیگیری وظیفه عقب‌افتاده مشتری"
        elif not interactions or idle_days >= 7:
            action = "با مشتری تماس بگیرید و وضعیت نیاز و بودجه را به‌روزرسانی کنید."
            title = "تماس و به‌روزرسانی نیاز مشتری"
        elif score >= 65 and not tasks:
            action = "یک پیگیری زمان‌بندی‌شده ثبت کنید تا مشتری در مرحله بعدی بماند."
            title = "پیگیری مشتری با اولویت بالا"
        else:
            action = "نیاز مشتری را مرور و قدم بعدی را مشخص کنید."
            title = "مرور نیاز و اقدام بعدی مشتری"
        rows.append({"customer_id": str(c.id), "customer_name": c.full_name, "agent_name": c.assigned_membership.user.full_name if c.assigned_membership else "بدون مسئول", "score": score, "readiness_level": level, "conversion_probability": conversion_probability, "score_factors": factors, "last_interaction_at": last_interaction.isoformat() if last_interaction else None, "idle_days": idle_days, "is_inactive": is_inactive, "open_tasks": len(tasks), "overdue_tasks": sum(1 for t in tasks if t.due_at < now), "active_negotiations": sum(1 for n in negotiations if n.status not in TERMINAL), "next_action": action, "suggested_task_title": title})
        for n in negotiations:
            if n.status in {"REJECTED", "CANCELLED", "WITHDRAWN", "EXPIRED"} and n.outcome_reason.strip():
                lost_reasons[n.outcome_reason.strip()] += 1
    rows.sort(key=lambda r: (-r["score"], r["idle_days"]))
    return {"generated_at": now.isoformat(), "method": "rule_based_v1", "summary": {"customers": len(rows), "hot": sum(r["readiness_level"] == "HOT" for r in rows), "high": sum(r["readiness_level"] == "HIGH" for r in rows), "inactive": len(inactive), "overdue_followups": sum(r["overdue_tasks"] for r in rows), "lost_with_reason": sum(lost_reasons.values())}, "customers": rows, "inactive_customers": sorted(inactive, key=lambda r: -r["idle_days"]), "lost_reasons": [{"reason": k, "count": v} for k, v in lost_reasons.most_common()]}

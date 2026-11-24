"""Daily Work Hub aggregation. All source querysets are permission-scoped before serialization."""
from datetime import datetime, timedelta
from django.utils import timezone
from common.permissions import get_active_membership, has_agency_permission, is_super_admin
from apps.crm.models import FollowUpTask
from apps.appointments.services import list_appointments
from apps.customers.services import list_customers
from apps.properties.services import list_agency_properties



def get_daily_work_hub(*, user, agency_id, branch_id=None, agent_membership_id=None):
    if not agency_id:
        return {"date": timezone.localdate().isoformat(), "tasks": [], "hot_customers": [], "new_properties": [], "today_viewings": [], "next_actions": [], "filters": {"branch_id": None, "agent_membership_id": None}}
    now = timezone.now()
    today = timezone.localdate()
    day_start = timezone.make_aware(datetime.combine(today, datetime.min.time()), timezone.get_current_timezone())
    day_end = day_start + timedelta(days=1)
    membership = get_active_membership(user, agency_id)
    superuser = is_super_admin(user)
    can_branch_filter = superuser or (membership and membership.role.code in ("AGENCY_MANAGER", "BRANCH_MANAGER")) or has_agency_permission(user, agency_id, "customer.view_all_agency")
    can_agent_filter = superuser or has_agency_permission(user, agency_id, "customer.view_all_agency") or (membership and membership.role.code in ("AGENCY_MANAGER", "BRANCH_MANAGER"))
    if branch_id and not can_branch_filter:
        branch_id = None
    if agent_membership_id and not can_agent_filter:
        agent_membership_id = None

    # Follow-up task scope: own assignments by default, branch for branch managers,
    # and agency-wide only with the explicit view-all permission.
    tasks_qs = FollowUpTask.objects.all_tenants().filter(agency_id=agency_id, status=FollowUpTask.Status.OPEN, due_at__lte=now + timedelta(days=1)).select_related("customer", "assigned_membership__user", "assigned_membership__branch")
    if not superuser and membership:
        if membership.role.code == "BRANCH_MANAGER":
            tasks_qs = tasks_qs.filter(assigned_membership__branch_id=membership.branch_id) if membership.branch_id else tasks_qs.none()
        elif not has_agency_permission(user, agency_id, "customer.view_all_agency"):
            tasks_qs = tasks_qs.filter(assigned_membership=membership)
    elif not superuser and not membership:
        tasks_qs = tasks_qs.none()
    if branch_id:
        tasks_qs = tasks_qs.filter(assigned_membership__branch_id=branch_id)
    if agent_membership_id:
        tasks_qs = tasks_qs.filter(assigned_membership_id=agent_membership_id)
    task_items = [{"id": str(t.id), "title": t.title, "due_at": t.due_at.isoformat(), "status": t.status,
                  "customer_id": str(t.customer_id), "customer_name": t.customer.full_name,
                  "assigned_name": getattr(t.assigned_membership.user, "full_name", ""),
                  "is_overdue": t.due_at < now, "href": f"/dashboard/customers/{t.customer_id}"} for t in tasks_qs.order_by("due_at")[:100]
    ]

    # Reuse the centralized customer visibility rules, then select hot/priority records.
    customers_qs = list_customers(user=user, agency_id=agency_id).filter(is_active=True)
    if branch_id:
        customers_qs = customers_qs.filter(assigned_membership__branch_id=branch_id)
    if agent_membership_id:
        customers_qs = customers_qs.filter(assigned_membership_id=agent_membership_id)
    from django.db.models import Q
    hot_qs = customers_qs.filter(Q(readiness_level="HOT") | Q(lead_score__gte=80))
    hot_items = [{"id": str(c.id), "name": c.full_name, "readiness": c.readiness_level, "score": c.lead_score,
                 "assigned": getattr(getattr(c.assigned_membership, "user", None), "full_name", ""),
                 "href": f"/dashboard/customers/{c.id}"} for c in hot_qs.distinct().order_by("-lead_score", "-created_at")[:50]
    ]

    properties_qs = list_agency_properties(user=user, agency_id=agency_id, status_filter=None)
    properties_qs = properties_qs.filter(created_at__gte=now - timedelta(days=7))
    if branch_id:
        properties_qs = properties_qs.filter(branch_id=branch_id)
    if agent_membership_id:
        properties_qs = properties_qs.filter(agent_assignments__membership_id=agent_membership_id)
    property_items = [{"id": str(p.id), "title": p.title, "created_at": p.created_at.isoformat(), "status": p.status,
                     "city": getattr(getattr(p, "location", None), "city", ""), "href": f"/dashboard/properties/{p.id}"}
                    for p in properties_qs.order_by("-created_at").distinct()[:50]
    ]

    appts_source = list_appointments(user=user, agency_id=agency_id)
    if hasattr(appts_source, "filter"):
        appts_qs = appts_source.filter(scheduled_start__gte=day_start, scheduled_start__lt=day_end).exclude(status__in=["CANCELLED", "REJECTED"])
        if branch_id:
            appts_qs = appts_qs.filter(agent_membership__branch_id=branch_id)
        if agent_membership_id:
            appts_qs = appts_qs.filter(agent_membership_id=agent_membership_id)
        appt_list = list(appts_qs.order_by("scheduled_start")[:100])
    else:
        appt_list = [a for a in appts_source if day_start <= a.scheduled_start < day_end and a.status not in ("CANCELLED", "REJECTED")]
    viewings = [{"id": str(a.id), "start_at": a.scheduled_start.isoformat(), "end_at": a.scheduled_end.isoformat(),
                 "status": a.status, "property_id": str(a.property_id), "property_title": a.property.title,
                 "customer_id": str(a.customer_id), "customer_name": a.customer.full_name,
                 "agent_name": getattr(a.agent_membership.user, "full_name", ""), "href": "/dashboard/appointments"} for a in appt_list]

    next_actions = []
    for t in task_items:
        if t["is_overdue"]:
            next_actions.append({"type": "OVERDUE_TASK", "priority": "HIGH", "title": "پیگیری عقب‌افتاده", "detail": t["title"], "href": t["href"]})
    for c in hot_items:
        if not any(t["customer_id"] == c["id"] for t in task_items):
            next_actions.append({"type": "HOT_CUSTOMER_NO_TASK", "priority": "HIGH", "title": "مشتری داغ بدون پیگیری", "detail": c["name"], "href": c["href"]})
    for a in viewings:
        next_actions.append({"type": "TODAY_VIEWING", "priority": "NORMAL", "title": "آمادگی برای بازدید امروز", "detail": f"{a['property_title']} — {a['customer_name']}", "href": a["href"]})
    return {"date": today.isoformat(), "tasks": task_items, "hot_customers": hot_items,
            "new_properties": property_items, "today_viewings": viewings,
            "next_actions": next_actions[:100], "filters": {"branch_id": str(branch_id) if branch_id else None, "agent_membership_id": str(agent_membership_id) if agent_membership_id else None}}

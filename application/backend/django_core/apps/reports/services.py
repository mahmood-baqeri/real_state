from datetime import timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID
from django.db.models import Count, Sum
from django.utils import timezone
from apps.accounting.models import (
    BankAccount,
    CashBox,
    ChequeInstrument,
    JournalEntry,
)
from apps.accounts.models import AgencyMembership, User
from apps.agencies.models import Agency
from apps.appointments.models import ViewingAppointment
from apps.audit.models import AuditLog
from apps.commissions.models import CommissionShare
from apps.contracts.models import Contract
from apps.customers.models import Customer
from apps.leads.models import Lead
from apps.negotiations.models import Negotiation
from apps.payroll.models import PayrollCycle
from apps.properties.models import Property
from apps.subscriptions.models import AgencySubscription
from apps.transactions.models import Deal
from common.permissions import get_active_membership, is_super_admin
from common.tenant.context import tenant_bypass


def get_dashboard_summary(
    *, user: User, agency_id: Optional[UUID], period_days: int = 30
) -> dict:
    now = timezone.now()
    since = now - timedelta(days=max(1, min(period_days, 365)))
    next_7_days = now + timedelta(days=7)

    if is_super_admin(user) and not agency_id:
        with tenant_bypass():
            pending_agencies = Agency.objects.filter(
                is_deleted=False, status=Agency.Status.PENDING_REVIEW
            ).count()
            suspended_agencies = Agency.objects.filter(
                is_deleted=False, status=Agency.Status.SUSPENDED
            ).count()
            recent_logs = list(
                AuditLog.objects.select_related("actor")
                .order_by("-created_at")[:8]
            )
            alerts = []
            if pending_agencies > 0:
                alerts.append(
                    {
                        "level": "warning",
                        "title": "آژانس‌های در انتظار تایید",
                        "count": pending_agencies,
                        "href": "/dashboard/admin",
                    }
                )
            if suspended_agencies > 0:
                alerts.append(
                    {
                        "level": "danger",
                        "title": "آژانس‌های تعلیق‌شده",
                        "count": suspended_agencies,
                        "href": "/dashboard/agencies",
                    }
                )
            return {
                "role_view": "SUPER_ADMIN",
                "period_days": period_days,
                "total_agencies": Agency.objects.filter(is_deleted=False).count(),
                "active_agencies": Agency.objects.filter(
                    is_deleted=False, status=Agency.Status.ACTIVE
                ).count(),
                "pending_agencies": pending_agencies,
                "total_users": User.objects.filter(status=User.Status.ACTIVE).count(),
                "total_properties": Property.objects.all_tenants()
                .filter(is_deleted=False)
                .count(),
                "period_properties": Property.objects.all_tenants()
                .filter(is_deleted=False, created_at__gte=since)
                .count(),
                "total_deals": Deal.objects.all_tenants().count(),
                "period_deals": Deal.objects.all_tenants()
                .filter(created_at__gte=since)
                .count(),
                "active_subscriptions": AgencySubscription.objects.filter(
                    status=AgencySubscription.Status.ACTIVE
                ).count(),
                "total_deal_volume": str(
                    Deal.objects.all_tenants().aggregate(s=Sum("deal_value"))["s"]
                    or Decimal("0")
                ),
                "alerts": alerts,
                "recent_activity": [
                    {
                        "id": str(l.id),
                        "action": l.action,
                        "resource_type": l.resource_type,
                        "actor_name": l.actor.full_name if l.actor else "سیستم",
                        "created_at": l.created_at.isoformat(),
                    }
                    for l in recent_logs
                ],
                "upcoming_tasks": [],
            }

    membership = get_active_membership(user, agency_id) if agency_id else None
    if membership and membership.role.code in (
        "AGENCY_MANAGER",
        "BRANCH_MANAGER",
        "AGENCY_ACCOUNTANT",
    ):
        active_props = (
            Property.objects.all_tenants()
            .filter(agency_id=agency_id, is_deleted=False, status=Property.Status.PUBLISHED)
            .count()
        )
        pending_props = (
            Property.objects.all_tenants()
            .filter(
                agency_id=agency_id, is_deleted=False, status=Property.Status.PENDING_APPROVAL
            )
            .count()
        )
        customers_count = (
            Customer.objects.all_tenants()
            .filter(agency_id=agency_id, is_deleted=False)
            .count()
        )
        leads_count = Lead.objects.all_tenants().filter(agency_id=agency_id).count()
        deals_qs = Deal.objects.all_tenants().filter(agency_id=agency_id)
        comm_total = (
            CommissionShare.objects.all_tenants()
            .filter(
                agency_id=agency_id,
                beneficiary_type=CommissionShare.BeneficiaryType.AGENCY,
            )
            .aggregate(s=Sum("calculated_amount"))["s"]
            or Decimal("0")
        )

        # Accounting & Treasury figures
        bank_balance = (
            BankAccount.objects.all_tenants()
            .filter(agency_id=agency_id, is_active=True)
            .aggregate(s=Sum("current_balance"))["s"]
            or Decimal("0")
        )
        cash_balance = (
            CashBox.objects.all_tenants()
            .filter(agency_id=agency_id, is_active=True)
            .aggregate(s=Sum("current_balance"))["s"]
            or Decimal("0")
        )
        held_cheques_due_soon = (
            ChequeInstrument.objects.all_tenants()
            .filter(
                agency_id=agency_id,
                status=ChequeInstrument.Status.HELD,
                due_date__lte=next_7_days,
            )
            .count()
        )
        held_receivable_total = (
            ChequeInstrument.objects.all_tenants()
            .filter(
                agency_id=agency_id,
                direction=ChequeInstrument.Direction.RECEIVABLE,
                status=ChequeInstrument.Status.HELD,
            )
            .aggregate(s=Sum("amount"))["s"]
            or Decimal("0")
        )
        posted_entries_count = (
            JournalEntry.objects.all_tenants()
            .filter(agency_id=agency_id, status=JournalEntry.Status.POSTED)
            .count()
        )
        payroll_runs_count = (
            PayrollCycle.objects.all_tenants().filter(agency_id=agency_id).count()
        )
        draft_contracts = (
            Contract.objects.all_tenants()
            .filter(agency_id=agency_id, status=Contract.Status.DRAFT)
            .count()
        )

        upcoming_appts = list(
            ViewingAppointment.objects.all_tenants()
            .filter(
                agency_id=agency_id,
                status__in=["REQUESTED", "CONFIRMED"],
            )
            .select_related("property", "customer")
            .order_by("scheduled_start")[:5]
        )
        recent_logs = list(
            AuditLog.objects.filter(agency_id=agency_id)
            .select_related("actor")
            .order_by("-created_at")[:6]
        )

        alerts = []
        if pending_props > 0:
            alerts.append(
                {
                    "level": "warning",
                    "title": "فایل‌های در انتظار تایید مدیر",
                    "count": pending_props,
                    "href": "/dashboard/properties",
                }
            )
        if held_cheques_due_soon > 0:
            alerts.append(
                {
                    "level": "danger",
                    "title": "چک‌های نزدیک به سررسید (۷ روز آینده)",
                    "count": held_cheques_due_soon,
                    "href": "/dashboard/accounting",
                }
            )
        if draft_contracts > 0:
            alerts.append(
                {
                    "level": "info",
                    "title": "قراردادهای پیش‌نویس نیازمند تکمیل",
                    "count": draft_contracts,
                    "href": "/dashboard/contracts",
                }
            )

        return {
            "role_view": membership.role.code,
            "period_days": period_days,
            "agency_name": membership.agency.name,
            "branch_name": membership.branch.name if membership.branch else None,
            "active_properties": active_props,
            "pending_approval_properties": pending_props,
            "total_customers": customers_count,
            "total_leads": leads_count,
            "active_deals": deals_qs.exclude(status=Deal.Status.VOIDED).count(),
            "period_deals": deals_qs.filter(created_at__gte=since).count(),
            "agency_commission_revenue": str(comm_total),
            "agents_count": AgencyMembership.objects.filter(
                agency_id=agency_id, status="ACTIVE"
            ).count(),
            "scheduled_viewings": ViewingAppointment.objects.all_tenants()
            .filter(agency_id=agency_id, status__in=["REQUESTED", "CONFIRMED"])
            .count(),
            "treasury_total": str(bank_balance + cash_balance),
            "held_receivable_cheques_total": str(held_receivable_total),
            "posted_journal_entries": posted_entries_count,
            "payroll_runs_count": payroll_runs_count,
            "alerts": alerts,
            "upcoming_tasks": [
                {
                    "id": str(a.id),
                    "title": f"بازدید {a.property.title} ({a.customer.full_name})",
                    "due_at": a.scheduled_start.isoformat(),
                    "status": a.status,
                    "href": "/dashboard/appointments",
                }
                for a in upcoming_appts
            ],
            "recent_activity": [
                {
                    "id": str(l.id),
                    "action": l.action,
                    "resource_type": l.resource_type,
                    "actor_name": l.actor.full_name if l.actor else "سیستم",
                    "created_at": l.created_at.isoformat(),
                }
                for l in recent_logs
            ],
        }

    if membership:
        my_props = (
            Property.objects.all_tenants()
            .filter(agency_id=agency_id, is_deleted=False, agent_assignments__membership=membership)
            .count()
        )
        my_customers = (
            Customer.objects.all_tenants()
            .filter(agency_id=agency_id, is_deleted=False, assigned_membership=membership)
            .count()
        )
        my_leads = (
            Lead.objects.all_tenants()
            .filter(agency_id=agency_id, assigned_membership=membership)
            .count()
        )
        my_comm = (
            CommissionShare.objects.all_tenants()
            .filter(agency_id=agency_id, beneficiary_membership=membership)
            .aggregate(s=Sum("calculated_amount"))["s"]
            or Decimal("0")
        )
        upcoming_appts = list(
            ViewingAppointment.objects.all_tenants()
            .filter(
                agency_id=agency_id,
                agent_membership=membership,
                status__in=["REQUESTED", "CONFIRMED"],
            )
            .select_related("property", "customer")
            .order_by("scheduled_start")[:5]
        )
        return {
            "role_view": "AGENT",
            "period_days": period_days,
            "agency_name": membership.agency.name,
            "my_properties": my_props,
            "my_customers": my_customers,
            "my_leads": my_leads,
            "my_scheduled_viewings": len(upcoming_appts),
            "my_commission_total": str(my_comm),
            "alerts": [],
            "upcoming_tasks": [
                {
                    "id": str(a.id),
                    "title": f"بازدید {a.property.title} ({a.customer.full_name})",
                    "due_at": a.scheduled_start.isoformat(),
                    "status": a.status,
                    "href": "/dashboard/appointments",
                }
                for a in upcoming_appts
            ],
            "recent_activity": [],
        }

    with tenant_bypass():
        my_appts = list(
            ViewingAppointment.objects.all_tenants()
            .filter(customer__user=user)
            .select_related("property")
            .order_by("-scheduled_start")[:5]
        )
        published_count = (
            Property.objects.all_tenants()
            .filter(is_deleted=False, status=Property.Status.PUBLISHED)
            .count()
        )
    return {
        "role_view": "CUSTOMER",
        "period_days": period_days,
        "my_viewings_count": len(my_appts),
        "published_properties_count": published_count,
        "alerts": [],
        "upcoming_tasks": [
            {
                "id": str(a.id),
                "title": f"بازدید: {a.property.title}",
                "due_at": a.scheduled_start.isoformat(),
                "status": a.status,
                "href": "/dashboard/appointments",
            }
            for a in my_appts
        ],
        "recent_activity": [],
    }


def get_agency_analytics(
    *, user: User, agency_id: Optional[UUID], period_days: int = 30
) -> dict:
    since = timezone.now() - timedelta(days=max(1, min(period_days, 365)))
    if not agency_id and is_super_admin(user):
        with tenant_bypass():
            props_by_status = list(
                Property.objects.all_tenants()
                .filter(is_deleted=False)
                .values("status")
                .annotate(count=Count("id"))
            )
            deals_by_status = list(
                Deal.objects.all_tenants()
                .filter(created_at__gte=since)
                .values("status")
                .annotate(count=Count("id"), volume=Sum("deal_value"))
            )
        return {
            "period_days": period_days,
            "properties_by_status": props_by_status,
            "deals_by_status": [
                {"status": d["status"], "count": d["count"], "volume": str(d["volume"] or 0)}
                for d in deals_by_status
            ],
            "agent_leaderboard": [],
        }

    props_by_status = list(
        Property.objects.all_tenants()
        .filter(agency_id=agency_id, is_deleted=False)
        .values("status")
        .annotate(count=Count("id"))
    )
    deals_by_status = list(
        Deal.objects.all_tenants()
        .filter(agency_id=agency_id, created_at__gte=since)
        .values("status")
        .annotate(count=Count("id"), volume=Sum("deal_value"))
    )
    leads_by_status = list(
        Lead.objects.all_tenants()
        .filter(agency_id=agency_id)
        .values("status")
        .annotate(count=Count("id"))
    )
    agent_shares = list(
        CommissionShare.objects.all_tenants()
        .filter(agency_id=agency_id, beneficiary_type=CommissionShare.BeneficiaryType.AGENT)
        .values(
            "beneficiary_membership_id",
            "beneficiary_membership__user__first_name",
            "beneficiary_membership__user__last_name",
        )
        .annotate(total_commission=Sum("calculated_amount"), deals_count=Count("id"))
        .order_by("-total_commission")
    )
    leaderboard = [
        {
            "membership_id": str(row["beneficiary_membership_id"]),
            "agent_name": f"{row['beneficiary_membership__user__first_name']} {row['beneficiary_membership__user__last_name']}".strip(),
            "total_commission": str(row["total_commission"] or 0),
            "deals_count": row["deals_count"],
        }
        for row in agent_shares
    ]
    return {
        "period_days": period_days,
        "properties_by_status": props_by_status,
        "deals_by_status": [
            {"status": d["status"], "count": d["count"], "volume": str(d["volume"] or 0)}
            for d in deals_by_status
        ],
        "leads_by_status": leads_by_status,
        "negotiations_count": Negotiation.objects.all_tenants().filter(agency_id=agency_id).count(),
        "agent_leaderboard": leaderboard,
    }

import csv
from datetime import timedelta
from decimal import Decimal, InvalidOperation
import io
from typing import Any, Optional
from uuid import UUID
import openpyxl
from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from apps.accounting.models import (
    BankAccount,
    CashBox,
    ChequeInstrument,
    JournalEntry,
    JournalEntryLine,
)
from apps.accounts.models import AgencyMembership, User
from apps.agencies.models import Agency
from apps.appointments.models import ViewingAppointment
from apps.audit.models import AuditLog
from apps.audit.services import record_audit_event
from apps.branches.models import Branch
from apps.commissions.models import CommissionShare
from apps.complaints.models import Complaint
from apps.contracts.models import Contract
from apps.crm.models import CustomerPipelineItem, FollowUpTask, PipelineStage
from apps.customers.models import Customer
from apps.leads.models import Lead
from apps.negotiations.models import Negotiation
from apps.payroll.models import PayrollCycle
from apps.properties.models import DealType, Property, PropertyLocation, PropertyType
from apps.subscriptions.models import AgencySubscription
from apps.support.models import Ticket
from apps.transactions.models import Deal
from common.exceptions import PermissionDeniedDomainError, ValidationDomainError
from common.permissions import get_active_membership, has_agency_permission, is_super_admin
from common.tenant.context import tenant_bypass
from .models import DashboardLayout, ImportJob, OnboardingProgress

DEFAULT_WIDGETS_BY_ROLE: dict[str, list[dict[str, Any]]] = {
    "SUPER_ADMIN": [
        {"id": "kpis", "title": "شاخص‌های کلان پلتفرم", "enabled": True},
        {"id": "alerts", "title": "هشدارهای عملیاتی", "enabled": True},
        {"id": "bi_trend", "title": "روند معاملات و درآمد", "enabled": True},
        {"id": "activity", "title": "رویدادهای ممیزی اخیر", "enabled": True},
    ],
    "AGENCY_MANAGER": [
        {"id": "kpis", "title": "شاخص‌های کلیدی آژانس", "enabled": True},
        {"id": "alerts", "title": "هشدارها و پیگیری‌های فوری", "enabled": True},
        {"id": "bi_trend", "title": "نمودار عملکرد مالی و فروش", "enabled": True},
        {"id": "funnel", "title": "قیف فروش و تبدیل سرنخ", "enabled": True},
        {"id": "leaderboard", "title": "رتبه‌بندی مشاوران", "enabled": True},
        {"id": "upcoming", "title": "برنامه بازدیدها و کارها", "enabled": True},
    ],
    "SALES_MANAGER": [
        {"id": "kpis", "title": "عملکرد تیم فروش و پایپ‌لاین", "enabled": True},
        {"id": "funnel", "title": "قیف فروش و تبدیل مشتری", "enabled": True},
        {"id": "leaderboard", "title": "عملکرد و کمیسیون مشاوران", "enabled": True},
        {"id": "upcoming", "title": "بازدیدهای در جریان", "enabled": True},
    ],
    "BRANCH_MANAGER": [
        {"id": "kpis", "title": "شاخص‌های شعبه", "enabled": True},
        {"id": "alerts", "title": "هشدارهای شعبه", "enabled": True},
        {"id": "leaderboard", "title": "مشاوران فعال", "enabled": True},
        {"id": "upcoming", "title": "بازدیدهای پیش‌رو", "enabled": True},
    ],
    "AGENCY_ACCOUNTANT": [
        {"id": "kpis", "title": "تراز خزانه، اسناد و چک‌ها", "enabled": True},
        {"id": "alerts", "title": "چک‌های نزدیک به سررسید", "enabled": True},
        {"id": "bi_trend", "title": "روند درآمد و هزینه", "enabled": True},
        {"id": "activity", "title": "اسناد حسابداری اخیر", "enabled": True},
    ],
    "SUPPORT_AGENT": [
        {"id": "kpis", "title": "تیکت‌ها، شکایات و SLA", "enabled": True},
        {"id": "alerts", "title": "موارد فوری پشتیبانی", "enabled": True},
        {"id": "upcoming", "title": "تیکت‌های منتظر پاسخ", "enabled": True},
    ],
    "AGENT": [
        {"id": "kpis", "title": "عملکرد شخصی مشاور", "enabled": True},
        {"id": "upcoming", "title": "بازدیدها و پیگیری‌های امروز", "enabled": True},
        {"id": "funnel", "title": "مشتریان در قیف فروش", "enabled": True},
    ],
    "CUSTOMER": [
        {"id": "kpis", "title": "خلاصه درخواست‌ها و بازدیدها", "enabled": True},
        {"id": "upcoming", "title": "بازدیدهای رزروشده من", "enabled": True},
    ],
}

ONBOARDING_STEPS_BY_ROLE: dict[str, list[dict[str, str]]] = {
    "SUPER_ADMIN": [
        {"key": "review_agencies", "title": "بررسی آژانس‌های ثبت‌نام‌شده و پلن‌ها", "href": "/dashboard/admin"},
        {"key": "check_ops", "title": "پایش مرکز عملیات و سلامت مالی پلتفرم", "href": "/dashboard/operations"},
        {"key": "audit_review", "title": "بازبینی گزارش‌های ممیزی و امنیت", "href": "/dashboard/audit"},
    ],
    "AGENCY_MANAGER": [
        {"key": "setup_team", "title": "تعریف شعب و بررسی دسترسی مشاوران", "href": "/dashboard/team"},
        {"key": "approve_listings", "title": "تأیید و انتشار فایل‌های ملکی", "href": "/dashboard/properties"},
        {"key": "review_bi", "title": "بررسی داشبورد تحلیلی و تراز مالی", "href": "/dashboard/reports"},
    ],
    "SALES_MANAGER": [
        {"key": "check_pipeline", "title": "پایش قیف فروش کانبان و امتیاز سرنخ‌ها", "href": "/dashboard/crm"},
        {"key": "review_negotiations", "title": "بررسی مذاکرات و پیشنهادهای قیمت", "href": "/dashboard/negotiations"},
        {"key": "track_targets", "title": "ارزیابی عملکرد مشاوران و نرخ تبدیل", "href": "/dashboard/reports"},
    ],
    "BRANCH_MANAGER": [
        {"key": "branch_props", "title": "بررسی موجودی فایل‌های شعبه", "href": "/dashboard/properties"},
        {"key": "branch_calendar", "title": "هماهنگی تقویم بازدیدهای شعبه", "href": "/dashboard/calendar"},
    ],
    "AGENCY_ACCOUNTANT": [
        {"key": "check_cheques", "title": "بررسی وضعیت چک‌های نزدیک سررسید", "href": "/dashboard/accounting"},
        {"key": "verify_commissions", "title": "تأیید اسناد کمیسیون و حقوق", "href": "/dashboard/commissions"},
    ],
    "SUPPORT_AGENT": [
        {"key": "triage_tickets", "title": "رسیدگی به تیکت‌های با اولویت بالا", "href": "/dashboard/tickets"},
        {"key": "review_complaints", "title": "پیگیری شکایات ثبت‌شده", "href": "/dashboard/complaints"},
    ],
    "AGENT": [
        {"key": "add_property", "title": "ثبت فایل ملکی یا به‌روزرسانی قیمت", "href": "/dashboard/properties"},
        {"key": "follow_crm", "title": "پیگیری وظایف روزانه و تطبیق مشتری", "href": "/dashboard/crm"},
        {"key": "check_calendar", "title": "بررسی تقویم یکپارچه بازدیدها", "href": "/dashboard/calendar"},
    ],
    "CUSTOMER": [
        {"key": "explore_properties", "title": "جستجوی فایل‌های تأییدشده روی نقشه", "href": "/search"},
        {"key": "track_visits", "title": "پیگیری زمان بازدیدها و تیکت‌ها", "href": "/dashboard/appointments"},
    ],
}


def _resolve_role_code(user: User, agency_id: Optional[UUID]) -> str:
    if is_super_admin(user) and not agency_id:
        return "SUPER_ADMIN"
    membership = get_active_membership(user, agency_id) if agency_id else None
    if membership:
        return membership.role.code
    if is_super_admin(user):
        return "AGENCY_MANAGER"
    if user.platform_role == User.PlatformRole.CUSTOMER:
        return "CUSTOMER"
    return "AGENT"


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
            open_tickets = Ticket.objects.filter(
                status__in=[Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS]
            ).count()
            open_complaints = Complaint.objects.filter(
                status__in=[Complaint.Status.OPEN, Complaint.Status.IN_PROGRESS, Complaint.Status.ESCALATED]
            ).count()
            recent_logs = list(
                AuditLog.objects.select_related("actor").order_by("-created_at")[:8]
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
            if open_tickets > 0:
                alerts.append(
                    {
                        "level": "info",
                        "title": "تیکت‌های باز پشتیبانی",
                        "count": open_tickets,
                        "href": "/dashboard/tickets",
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
                "open_tickets": open_tickets,
                "open_complaints": open_complaints,
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
    role_code = membership.role.code if membership else ("AGENCY_MANAGER" if is_super_admin(user) and agency_id else "CUSTOMER")

    if role_code == "SUPPORT_AGENT" and agency_id:
        open_tickets = Ticket.objects.filter(
            agency_id=agency_id, status__in=[Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS]
        )
        urgent_tickets = open_tickets.filter(priority__in=[Ticket.Priority.HIGH, Ticket.Priority.URGENT]).count()
        open_complaints = Complaint.objects.filter(
            agency_id=agency_id, status__in=[Complaint.Status.OPEN, Complaint.Status.IN_PROGRESS, Complaint.Status.ESCALATED]
        ).count()
        alerts = []
        if urgent_tickets > 0:
            alerts.append(
                {
                    "level": "danger",
                    "title": "تیکت‌های فوری نیازمند پاسخ",
                    "count": urgent_tickets,
                    "href": "/dashboard/tickets",
                }
            )
        if open_complaints > 0:
            alerts.append(
                {
                    "level": "warning",
                    "title": "شکایات باز در حال رسیدگی",
                    "count": open_complaints,
                    "href": "/dashboard/complaints",
                }
            )
        return {
            "role_view": "SUPPORT_AGENT",
            "period_days": period_days,
            "agency_name": membership.agency.name if membership else "",
            "open_tickets": open_tickets.count(),
            "urgent_tickets": urgent_tickets,
            "open_complaints": open_complaints,
            "resolved_tickets_period": Ticket.objects.filter(
                agency_id=agency_id, status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED], updated_at__gte=since
            ).count(),
            "alerts": alerts,
            "upcoming_tasks": [
                {
                    "id": str(t.id),
                    "title": f"[{t.ticket_number}] {t.subject}",
                    "due_at": t.created_at.isoformat(),
                    "status": t.priority,
                    "href": "/dashboard/tickets",
                }
                for t in open_tickets.order_by("-created_at")[:6]
            ],
            "recent_activity": [],
        }

    if role_code in (
        "AGENCY_MANAGER",
        "BRANCH_MANAGER",
        "SALES_MANAGER",
        "AGENCY_ACCOUNTANT",
    ) and agency_id:
        branch_filter = {"branch_id": membership.branch_id} if (role_code == "BRANCH_MANAGER" and membership and membership.branch_id) else {}
        active_props = (
            Property.objects.all_tenants()
            .filter(agency_id=agency_id, is_deleted=False, status=Property.Status.PUBLISHED, **branch_filter)
            .count()
        )
        pending_props = (
            Property.objects.all_tenants()
            .filter(agency_id=agency_id, is_deleted=False, status=Property.Status.PENDING_APPROVAL, **branch_filter)
            .count()
        )
        customers_count = (
            Customer.objects.all_tenants().filter(agency_id=agency_id, is_deleted=False).count()
        )
        leads_count = Lead.objects.all_tenants().filter(agency_id=agency_id).count()
        converted_leads = Lead.objects.all_tenants().filter(agency_id=agency_id, status="CONVERTED").count()
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
        active_negotiations = Negotiation.objects.all_tenants().filter(
            agency_id=agency_id, status="OPEN"
        ).count()

        upcoming_appts = list(
            ViewingAppointment.objects.all_tenants()
            .filter(agency_id=agency_id, status__in=["REQUESTED", "CONFIRMED"])
            .select_related("property", "customer")
            .order_by("scheduled_start")[:5]
        )
        recent_logs = list(
            AuditLog.objects.filter(agency_id=agency_id).select_related("actor").order_by("-created_at")[:6]
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

        lead_conv_rate = round((converted_leads / leads_count) * 100, 1) if leads_count > 0 else 0.0

        return {
            "role_view": role_code,
            "period_days": period_days,
            "agency_name": membership.agency.name if membership else "",
            "branch_name": membership.branch.name if (membership and membership.branch) else None,
            "active_properties": active_props,
            "pending_approval_properties": pending_props,
            "total_customers": customers_count,
            "total_leads": leads_count,
            "lead_conversion_rate": lead_conv_rate,
            "active_negotiations": active_negotiations,
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
    *,
    user: User,
    agency_id: Optional[UUID],
    period_days: int = 30,
    branch_id: Optional[UUID] = None,
    agent_membership_id: Optional[UUID] = None,
) -> dict:
    now = timezone.now()
    days = max(7, min(period_days, 365))
    since = now - timedelta(days=days)
    prev_since = since - timedelta(days=days)

    def _build_scope_filters():
        pf: dict[str, Any] = {"is_deleted": False}
        df: dict[str, Any] = {}
        lf: dict[str, Any] = {}
        if agency_id:
            pf["agency_id"] = agency_id
            df["agency_id"] = agency_id
            lf["agency_id"] = agency_id
        if branch_id:
            pf["branch_id"] = branch_id
        if agent_membership_id:
            pf["agent_assignments__membership_id"] = agent_membership_id
            df["primary_agent_membership_id"] = agent_membership_id
            lf["assigned_membership_id"] = agent_membership_id
        return pf, df, lf

    pf, df, lf = _build_scope_filters()

    with tenant_bypass():
        props_qs = Property.objects.all_tenants().filter(**pf)
        deals_qs = Deal.objects.all_tenants().filter(**df)
        leads_qs = Lead.objects.all_tenants().filter(**lf)

        props_by_status = list(props_qs.values("status").annotate(count=Count("id")))
        deals_by_status = list(
            deals_qs.filter(created_at__gte=since)
            .values("status")
            .annotate(count=Count("id"), volume=Sum("deal_value"))
        )
        leads_by_status = list(leads_qs.values("status").annotate(count=Count("id")))

        # Sales Funnel
        total_leads_cnt = leads_qs.count()
        total_cust_cnt = Customer.objects.all_tenants().filter(
            **({"agency_id": agency_id} if agency_id else {})
        ).count()
        appts_cnt = ViewingAppointment.objects.all_tenants().filter(
            **({"agency_id": agency_id} if agency_id else {})
        ).count()
        neg_cnt = Negotiation.objects.all_tenants().filter(
            **({"agency_id": agency_id} if agency_id else {})
        ).count()
        closed_deals_cnt = deals_qs.exclude(status=Deal.Status.VOIDED).count()

        sales_funnel = [
            {"stage": "سرنخ ورودی", "count": total_leads_cnt},
            {"stage": "مشتری ثبت‌شده", "count": total_cust_cnt},
            {"stage": "بازدید هماهنگ‌شده", "count": appts_cnt},
            {"stage": "مذاکره فعال", "count": neg_cnt},
            {"stage": "قرارداد و معامله", "count": closed_deals_cnt},
        ]

        # District Geo Breakdown
        district_breakdown = [
            {
                "district": r["location__district"] or "مرکزی",
                "count": r["count"],
                "avg_price_per_sqm": str(int(r["avg_sqm"] or 0)),
            }
            for r in props_qs.filter(price_per_sqm__gt=Decimal("0"))
            .values("location__district")
            .annotate(count=Count("id"), avg_sqm=Avg("price_per_sqm"))
            .order_by("-count")[:8]
        ]

        # Period-over-Period Comparison
        cur_vol = deals_qs.filter(created_at__gte=since).aggregate(s=Sum("deal_value"))["s"] or Decimal("0")
        prev_vol = deals_qs.filter(created_at__gte=prev_since, created_at__lt=since).aggregate(s=Sum("deal_value"))["s"] or Decimal("0")
        cur_cnt = deals_qs.filter(created_at__gte=since).count()
        prev_cnt = deals_qs.filter(created_at__gte=prev_since, created_at__lt=since).count()

        # Weekly buckets for Line / Area / Financial Revenue-Expense chart
        bucket_count = 6
        step = max(1, days // bucket_count)
        timeline_series = []
        for idx in range(bucket_count):
            b_start = since + timedelta(days=idx * step)
            b_end = now if idx == bucket_count - 1 else b_start + timedelta(days=step)
            b_deals = deals_qs.filter(created_at__gte=b_start, created_at__lt=b_end)
            vol = b_deals.aggregate(s=Sum("deal_value"))["s"] or Decimal("0")
            rev = (
                JournalEntryLine.objects.filter(
                    journal_entry__status=JournalEntry.Status.POSTED,
                    journal_entry__created_at__gte=b_start,
                    journal_entry__created_at__lt=b_end,
                    account__account_type="REVENUE",
                    **({"journal_entry__agency_id": agency_id} if agency_id else {}),
                ).aggregate(s=Sum("credit"))["s"]
                or Decimal("0")
            )
            exp = (
                JournalEntryLine.objects.filter(
                    journal_entry__status=JournalEntry.Status.POSTED,
                    journal_entry__created_at__gte=b_start,
                    journal_entry__created_at__lt=b_end,
                    account__account_type="EXPENSE",
                    **({"journal_entry__agency_id": agency_id} if agency_id else {}),
                ).aggregate(s=Sum("debit"))["s"]
                or Decimal("0")
            )
            p_cnt = props_qs.filter(created_at__gte=b_start, created_at__lt=b_end).count()
            timeline_series.append(
                {
                    "label": f"بازه {idx + 1}",
                    "deals_count": b_deals.count(),
                    "properties_added": p_cnt,
                    "deal_volume": str(vol),
                    "revenue": str(rev),
                    "expense": str(exp),
                }
            )

        # Agent Leaderboard
        comm_filter: dict[str, Any] = {"beneficiary_type": CommissionShare.BeneficiaryType.AGENT}
        if agency_id:
            comm_filter["agency_id"] = agency_id
        agent_shares = list(
            CommissionShare.objects.all_tenants()
            .filter(**comm_filter)
            .values(
                "beneficiary_membership_id",
                "beneficiary_membership__user__first_name",
                "beneficiary_membership__user__last_name",
            )
            .annotate(total_commission=Sum("calculated_amount"), deals_count=Count("id"))
            .order_by("-total_commission")[:10]
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

        # Branch comparison
        branch_comparison = [
            {
                "branch_id": str(b.id),
                "branch_name": b.name,
                "properties_count": Property.objects.all_tenants().filter(branch=b, is_deleted=False).count(),
                "members_count": AgencyMembership.objects.filter(branch=b, status="ACTIVE").count(),
            }
            for b in Branch.objects.all_tenants().filter(**({"agency_id": agency_id} if agency_id else {}))[:10]
        ]

        # Weekly Activity Heatmap (7 weekdays x 3 time slots from AuditLog + Appointments)
        heatmap = []
        weekdays = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه"]
        slots = ["صبح", "ظهر", "عصر"]
        appts_list = list(
            ViewingAppointment.objects.all_tenants()
            .filter(**({"agency_id": agency_id} if agency_id else {}))
            .values_list("scheduled_start", flat=True)[:200]
        )
        for d_idx, d_name in enumerate(weekdays):
            row_slots = []
            for s_idx, s_name in enumerate(slots):
                count = 0
                for dt in appts_list:
                    py_wd = (dt.weekday() + 2) % 7
                    hr = dt.hour
                    slot = 0 if hr < 12 else (1 if hr < 16 else 2)
                    if py_wd == d_idx and slot == s_idx:
                        count += 1
                row_slots.append({"slot": s_name, "count": count})
            heatmap.append({"day": d_name, "slots": row_slots})

    # Enforce 10-domain AgencyAccessPolicy on performance & financial visibility
    if agency_id and not is_super_admin(user):
        from apps.agencies.models import AgencyAccessPolicy
        from common.permissions import get_agency_policy

        membership = get_active_membership(user, agency_id)
        policy = get_agency_policy(agency_id)
        is_mgr = bool(
            membership
            and membership.role.code in ("AGENCY_MANAGER", "BRANCH_MANAGER", "SALES_MANAGER", "AGENCY_ACCOUNTANT")
        )
        if policy and not is_mgr:
            if policy.agent_performance_visibility == AgencyAccessPolicy.PerformanceVisibility.OWN_ONLY:
                own_id = str(membership.id) if membership else ""
                leaderboard = [row for row in leaderboard if row["membership_id"] == own_id]
            elif policy.agent_performance_visibility == AgencyAccessPolicy.PerformanceVisibility.RANKING_ONLY:
                own_id = str(membership.id) if membership else ""
                leaderboard = [
                    {
                        **row,
                        "agent_name": row["agent_name"]
                        if row["membership_id"] == own_id
                        else f"مشاور رتبه {idx}",
                    }
                    for idx, row in enumerate(leaderboard, start=1)
                ]
            if (
                policy.financial_visibility != AgencyAccessPolicy.StandardVisibility.PERMISSION_BASED
                or not has_agency_permission(user, agency_id, "accounting.view")
            ):
                for bucket in timeline_series:
                    bucket["revenue"] = "0"
                    bucket["expense"] = "0"

    return {
        "period_days": period_days,
        "properties_by_status": props_by_status,
        "deals_by_status": [
            {"status": d["status"], "count": d["count"], "volume": str(d["volume"] or 0)}
            for d in deals_by_status
        ],
        "leads_by_status": leads_by_status,
        "sales_funnel": sales_funnel,
        "district_breakdown": district_breakdown,
        "timeline_series": timeline_series,
        "branch_comparison": branch_comparison,
        "activity_heatmap": heatmap,
        "period_comparison": {
            "current_volume": str(cur_vol),
            "previous_volume": str(prev_vol),
            "current_deals_count": cur_cnt,
            "previous_deals_count": prev_cnt,
        },
        "negotiations_count": neg_cnt,
        "agent_leaderboard": leaderboard,
    }


def get_operations_center(*, user: User, agency_id: Optional[UUID]) -> dict:
    now = timezone.now()
    soon_14 = now + timedelta(days=14)
    soon_7 = now + timedelta(days=7)

    super_admin = is_super_admin(user)
    if not agency_id and not super_admin:
        raise PermissionDeniedDomainError("دسترسی به مرکز عملیات نیازمند انتخاب آژانس یا نقش مدیر کل است.")

    with tenant_bypass():
        scope = {"agency_id": agency_id} if agency_id else {}

        overdue_tasks = [
            {
                "id": str(t.id),
                "title": t.title,
                "customer_name": t.customer.full_name,
                "agent_name": t.assigned_membership.user.full_name,
                "due_at": t.due_at.isoformat(),
                "is_overdue": t.due_at < now,
                "href": "/dashboard/crm",
            }
            for t in FollowUpTask.objects.all_tenants()
            .filter(status="PENDING", **scope)
            .select_related("customer", "assigned_membership__user")
            .order_by("due_at")[:15]
        ]

        expiring_contracts = [
            {
                "id": str(c.id),
                "contract_number": c.contract_number,
                "property_title": c.property.title if c.property else "",
                "end_date": c.end_date.isoformat() if c.end_date else None,
                "status": c.status,
                "href": "/dashboard/contracts",
            }
            for c in Contract.objects.all_tenants()
            .filter(end_date__isnull=False, end_date__lte=soon_14.date(), **scope)
            .exclude(status__in=["TERMINATED", "CANCELLED"])
            .select_related("property")
            .order_by("end_date")[:15]
        ]

        due_cheques = [
            {
                "id": str(ch.id),
                "cheque_number": ch.cheque_number,
                "direction": ch.direction,
                "amount": str(ch.amount),
                "due_date": ch.due_date.isoformat(),
                "status": ch.status,
                "href": "/dashboard/accounting",
            }
            for ch in ChequeInstrument.objects.all_tenants()
            .filter(status__in=[ChequeInstrument.Status.HELD, ChequeInstrument.Status.BOUNCED], due_date__lte=soon_7, **scope)
            .order_by("due_date")[:15]
        ]

        urgent_tickets = [
            {
                "id": str(t.id),
                "ticket_number": t.ticket_number,
                "subject": t.subject,
                "priority": t.priority,
                "status": t.status,
                "created_at": t.created_at.isoformat(),
                "href": "/dashboard/tickets",
            }
            for t in Ticket.objects
            .filter(status__in=[Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS, Ticket.Status.WAITING_USER], **scope)
            .order_by("-priority", "-created_at")[:15]
        ]

        pending_properties = [
            {
                "id": str(p.id),
                "property_code": p.property_code,
                "title": p.title,
                "total_price": str(p.total_price),
                "created_at": p.created_at.isoformat(),
                "href": f"/dashboard/properties/{p.id}",
            }
            for p in Property.objects.all_tenants()
            .filter(is_deleted=False, status=Property.Status.PENDING_APPROVAL, **scope)
            .order_by("-created_at")[:10]
        ]

    return {
        "summary": {
            "overdue_tasks_count": sum(1 for t in overdue_tasks if t["is_overdue"]),
            "pending_tasks_count": len(overdue_tasks),
            "expiring_contracts_count": len(expiring_contracts),
            "due_cheques_count": len(due_cheques),
            "urgent_tickets_count": len(urgent_tickets),
            "pending_properties_count": len(pending_properties),
        },
        "overdue_tasks": overdue_tasks,
        "expiring_contracts": expiring_contracts,
        "due_cheques": due_cheques,
        "urgent_tickets": urgent_tickets,
        "pending_properties": pending_properties,
    }


def get_or_save_dashboard_layout(
    *,
    user: User,
    agency_id: Optional[UUID],
    widgets: Optional[list[dict]] = None,
    default_period_days: Optional[int] = None,
) -> dict:
    role_code = _resolve_role_code(user, agency_id)
    default_widgets = DEFAULT_WIDGETS_BY_ROLE.get(role_code, DEFAULT_WIDGETS_BY_ROLE["AGENT"])
    layout, _ = DashboardLayout.objects.get_or_create(
        user=user,
        agency_id=agency_id,
        role_code=role_code,
        defaults={"widgets_json": default_widgets, "default_period_days": 30, "created_by": user},
    )
    if widgets is not None or default_period_days is not None:
        if widgets is not None:
            layout.widgets_json = widgets
        if default_period_days is not None:
            layout.default_period_days = max(7, min(365, int(default_period_days)))
        layout.updated_by = user
        layout.save()
    return {
        "role_code": layout.role_code,
        "widgets": layout.widgets_json or default_widgets,
        "default_period_days": layout.default_period_days,
    }


def get_or_update_onboarding(
    *,
    user: User,
    agency_id: Optional[UUID],
    toggle_step_key: Optional[str] = None,
    dismissed: Optional[bool] = None,
) -> dict:
    role_code = _resolve_role_code(user, agency_id)
    steps = ONBOARDING_STEPS_BY_ROLE.get(role_code, ONBOARDING_STEPS_BY_ROLE["AGENT"])
    progress, _ = OnboardingProgress.objects.get_or_create(
        user=user,
        agency_id=agency_id,
        role_code=role_code,
        defaults={"completed_steps_json": [], "dismissed": False, "created_by": user},
    )
    completed = list(progress.completed_steps_json or [])
    if toggle_step_key:
        if toggle_step_key in completed:
            completed.remove(toggle_step_key)
        else:
            completed.append(toggle_step_key)
        progress.completed_steps_json = completed
    if dismissed is not None:
        progress.dismissed = dismissed
    if toggle_step_key is not None or dismissed is not None:
        progress.updated_by = user
        progress.save()

    return {
        "role_code": role_code,
        "dismissed": progress.dismissed,
        "completed_steps": completed,
        "steps": [{**s, "completed": s["key"] in completed} for s in steps],
    }


def parse_spreadsheet_bytes(*, filename: str, content: bytes) -> tuple[list[str], list[dict[str, Any]]]:
    lower = filename.lower()
    if lower.endswith(".xlsx"):
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return [], []
        headers = [str(c).strip() if c is not None else f"col_{idx}" for idx, c in enumerate(rows[0])]
        records = []
        for row in rows[1:]:
            if all(v is None or str(v).strip() == "" for v in row):
                continue
            records.append({headers[i]: (str(row[i]).strip() if i < len(row) and row[i] is not None else "") for i in range(len(headers))})
        return headers, records

    if lower.endswith(".csv"):
        text = content.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        headers = list(reader.fieldnames or [])
        records = [{k: (v or "").strip() for k, v in row.items() if k is not None} for row in reader]
        return headers, records

    raise ValidationDomainError("فقط فایل‌های Excel (.xlsx) یا CSV (.csv) پشتیبانی می‌شوند.")


@transaction.atomic
def preview_or_execute_import(
    *,
    user: User,
    agency_id: UUID,
    module: str,
    filename: str,
    content: bytes,
    column_mapping: Optional[dict[str, str]] = None,
    commit: bool = False,
) -> dict:
    if not (
        is_super_admin(user)
        or has_agency_permission(user, agency_id, "property.create")
        or has_agency_permission(user, agency_id, "property.edit_all_agency")
        or has_agency_permission(user, agency_id, "customer.edit_all_agency")
    ):
        raise PermissionDeniedDomainError("عدم مجوز ورود دسته‌ای اطلاعات.")
    if module not in ("properties", "customers"):
        raise ValidationDomainError("ماژول انتخاب‌شده برای ایمپورت پشتیبانی نمی‌شود.")

    headers, records = parse_spreadsheet_bytes(filename=filename, content=content)
    mapping = column_mapping or {}
    errors: list[dict] = []
    duplicates = 0
    imported = 0

    def _val(row: dict, field: str, fallbacks: tuple[str, ...] = ()) -> str:
        mapped_col = mapping.get(field)
        if mapped_col and mapped_col in row:
            return row[mapped_col]
        if field in row:
            return row[field]
        for fb in fallbacks:
            if fb in row:
                return row[fb]
        return ""

    if module == "properties":
        existing_codes = set(
            Property.objects.all_tenants().filter(agency_id=agency_id).values_list("property_code", flat=True)
        )
        default_pt = PropertyType.objects.first()
        default_dt = DealType.objects.first()
        seen_in_file: set[str] = set()
        for idx, row in enumerate(records, start=2):
            code = _val(row, "property_code", ("کد فایل", "کد ملک", "code"))
            title = _val(row, "title", ("عنوان", "نام ملک"))
            city = _val(row, "city", ("شهر",)) or "تهران"
            district = _val(row, "district", ("منطقه", "محله"))
            raw_price = _val(row, "total_price", ("قیمت کل", "قیمت", "price")) or "0"
            raw_area = _val(row, "built_area_sqm", ("متراژ", "زیربنا", "area")) or "0"

            if not code or not title:
                errors.append({"row": idx, "reason": "کد ملک و عنوان الزامی هستند."})
                continue
            if code in existing_codes or code in seen_in_file:
                duplicates += 1
                errors.append({"row": idx, "reason": f"کد ملک تکراری است: {code}"})
                continue
            try:
                price_dec = Decimal(raw_price.replace(",", ""))
                area_dec = Decimal(raw_area.replace(",", ""))
            except InvalidOperation:
                errors.append({"row": idx, "reason": "فرمت عددی قیمت یا متراژ نامعتبر است."})
                continue

            seen_in_file.add(code)
            if commit and default_pt and default_dt:
                prop = Property.objects.create(
                    agency_id=agency_id,
                    property_code=code,
                    title=title,
                    property_type=default_pt,
                    deal_type=default_dt,
                    total_price=price_dec,
                    built_area_sqm=area_dec,
                    currency_id="IRT",
                    status=Property.Status.DRAFT,
                    created_by=user,
                )
                prop.recalculate_price_per_sqm()
                prop.save()
                PropertyLocation.objects.create(property=prop, province=city, city=city, district=district)
            imported += 1

    elif module == "customers":
        existing_phones = set(
            Customer.objects.all_tenants().filter(agency_id=agency_id).values_list("primary_phone", flat=True)
        )
        seen_phones: set[str] = set()
        membership = get_active_membership(user, agency_id)
        for idx, row in enumerate(records, start=2):
            name = _val(row, "full_name", ("نام و نام خانوادگی", "نام", "name"))
            phone = _val(row, "primary_phone", ("شماره تماس", "موبایل", "phone"))
            ctype = (_val(row, "customer_type", ("نوع مشتری",)) or "BUYER").upper()
            if ctype not in ("BUYER", "SELLER", "OWNER", "TENANT", "LANDLORD", "INVESTOR"):
                ctype = "BUYER"
            if not name or not phone:
                errors.append({"row": idx, "reason": "نام و شماره تماس الزامی هستند."})
                continue
            if phone in existing_phones or phone in seen_phones:
                duplicates += 1
                errors.append({"row": idx, "reason": f"شماره تماس تکراری است: {phone}"})
                continue
            seen_phones.add(phone)
            if commit:
                Customer.objects.create(
                    agency_id=agency_id,
                    full_name=name,
                    primary_phone=phone,
                    customer_type=ctype,
                    assigned_membership=membership,
                    created_by=user,
                )
            imported += 1

    job = ImportJob.objects.create(
        agency_id=agency_id,
        module=module,
        file_name=filename,
        total_rows=len(records),
        imported_rows=imported if commit else 0,
        duplicate_rows=duplicates,
        error_rows=len(errors),
        column_mapping_json=mapping,
        errors_json=errors[:50],
        status=ImportJob.Status.COMPLETED if commit else ImportJob.Status.PREVIEWED,
        created_by=user,
    )
    if commit:
        record_audit_event(
            action="BULK_IMPORT_EXECUTED",
            resource_type="ImportJob",
            resource_id=str(job.id),
            actor=user,
            agency_id=agency_id,
            after_state={"module": module, "imported": imported, "duplicates": duplicates},
        )

    return {
        "job_id": str(job.id),
        "status": job.status,
        "headers": headers,
        "preview_rows": records[:10],
        "total_rows": len(records),
        "valid_rows": imported,
        "duplicate_rows": duplicates,
        "error_rows": len(errors),
        "errors": errors[:50],
    }


def _mask_phone_for_export(phone: str) -> str:
    clean = (phone or "").strip()
    if len(clean) <= 6:
        return "***"
    return f"{clean[:4]}***{clean[-3:]}"


def export_module_workbook(*, user: User, agency_id: Optional[UUID], module: str, fmt: str = "xlsx") -> tuple[bytes, str, str]:
    if not agency_id and not is_super_admin(user):
        raise PermissionDeniedDomainError("دسترسی به خروجی اطلاعات مجاز نیست.")

    headers: list[str] = []
    rows: list[list[Any]] = []
    scope = {"agency_id": agency_id} if agency_id else {}
    membership = get_active_membership(user, agency_id) if agency_id else None
    is_mgr_or_admin = is_super_admin(user) or (
        membership is not None and membership.role.code in ("AGENCY_MANAGER", "BRANCH_MANAGER")
    )

    if module == "properties":
        headers = ["کد فایل", "عنوان", "نوع ملک", "نوع معامله", "شهر", "منطقه", "متراژ", "قیمت کل", "وضعیت"]
        for p in Property.objects.all_tenants().filter(is_deleted=False, **scope).select_related("property_type", "deal_type", "location"):
            loc = getattr(p, "location", None)
            rows.append([
                p.property_code,
                p.title,
                p.property_type.name_fa,
                p.deal_type.name_fa,
                loc.city if loc else "",
                loc.district if loc else "",
                str(p.built_area_sqm),
                str(p.total_price),
                p.status,
            ])
    elif module == "customers":
        can_export_full_phone = is_mgr_or_admin or (
            agency_id is not None and has_agency_permission(user, agency_id, "owner.view_pii")
        )
        headers = ["نام کامل", "تلفن", "نوع مشتری", "امتیاز سرنخ", "سطح آمادگی"]
        qs = Customer.objects.all_tenants().filter(is_deleted=False, **scope)
        if not is_mgr_or_admin and agency_id and not has_agency_permission(user, agency_id, "customer.view_all_agency"):
            if membership:
                qs = qs.filter(Q(assigned_membership=membership) | Q(shares__membership=membership)).distinct()
            else:
                qs = qs.none()
        for c in qs:
            phone_val = c.primary_phone if can_export_full_phone else _mask_phone_for_export(c.primary_phone)
            rows.append([c.full_name, phone_val, c.customer_type, c.lead_score, c.readiness_level])
    elif module == "accounting":
        if not is_super_admin(user) and agency_id and not (
            (membership and membership.role.code in ("AGENCY_MANAGER", "AGENCY_ACCOUNTANT"))
            or has_agency_permission(user, agency_id, "accounting.view")
        ):
            raise PermissionDeniedDomainError("عدم مجوز دریافت خروجی مالی.")
        headers = ["شماره سند", "تاریخ", "شرح", "وضعیت", "ارز"]
        for j in JournalEntry.objects.all_tenants().filter(**scope):
            rows.append([j.entry_number, j.entry_date.isoformat(), j.description, j.status, j.currency_id])
    else:
        raise ValidationDomainError("ماژول خروجی نامعتبر است.")

    record_audit_event(
        action="DATA_EXPORTED",
        resource_type="Export",
        resource_id=module,
        actor=user,
        agency_id=agency_id,
        after_state={"module": module, "format": fmt, "row_count": len(rows)},
    )

    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(headers)
        writer.writerows(rows)
        return buf.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8", f"{module}-export.csv"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = module[:30]
    ws.sheet_view.rightToLeft = True
    ws.append(headers)
    for r in rows:
        ws.append(r)
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"{module}-export.xlsx"

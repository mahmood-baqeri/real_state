from decimal import Decimal
from typing import Optional
from uuid import UUID
from django.db.models import Count, Sum
from apps.accounts.models import AgencyMembership, User
from apps.agencies.models import Agency
from apps.appointments.models import ViewingAppointment
from apps.commissions.models import CommissionShare
from apps.customers.models import Customer
from apps.leads.models import Lead
from apps.negotiations.models import Negotiation
from apps.properties.models import Property
from apps.subscriptions.models import AgencySubscription
from apps.transactions.models import Deal
from common.permissions import get_active_membership, is_super_admin
from common.tenant.context import tenant_bypass


def get_dashboard_summary(*, user: User, agency_id: Optional[UUID]) -> dict:
    if is_super_admin(user) and not agency_id:
        with tenant_bypass():
            return {
                "role_view": "SUPER_ADMIN",
                "total_agencies": Agency.objects.filter(is_deleted=False).count(),
                "active_agencies": Agency.objects.filter(
                    is_deleted=False, status=Agency.Status.ACTIVE
                ).count(),
                "pending_agencies": Agency.objects.filter(
                    is_deleted=False, status=Agency.Status.PENDING_REVIEW
                ).count(),
                "total_users": User.objects.filter(status=User.Status.ACTIVE).count(),
                "total_properties": Property.objects.all_tenants().filter(is_deleted=False).count(),
                "total_deals": Deal.objects.all_tenants().count(),
                "active_subscriptions": AgencySubscription.objects.filter(
                    status=AgencySubscription.Status.ACTIVE
                ).count(),
                "total_deal_volume": str(
                    Deal.objects.all_tenants().aggregate(s=Sum("deal_value"))["s"] or Decimal("0")
                ),
            }

    membership = get_active_membership(user, agency_id) if agency_id else None
    if membership and membership.role.code in ("AGENCY_MANAGER", "AGENCY_ACCOUNTANT"):
        active_props = Property.objects.all_tenants().filter(
            agency_id=agency_id, is_deleted=False, status=Property.Status.PUBLISHED
        ).count()
        pending_props = Property.objects.all_tenants().filter(
            agency_id=agency_id, is_deleted=False, status=Property.Status.PENDING_APPROVAL
        ).count()
        customers_count = Customer.objects.all_tenants().filter(
            agency_id=agency_id, is_deleted=False
        ).count()
        leads_count = Lead.objects.all_tenants().filter(agency_id=agency_id).count()
        deals_qs = Deal.objects.all_tenants().filter(agency_id=agency_id)
        comm_total = CommissionShare.objects.all_tenants().filter(
            agency_id=agency_id, beneficiary_type=CommissionShare.BeneficiaryType.AGENCY
        ).aggregate(s=Sum("calculated_amount"))["s"] or Decimal("0")
        return {
            "role_view": membership.role.code,
            "agency_name": membership.agency.name,
            "active_properties": active_props,
            "pending_approval_properties": pending_props,
            "total_customers": customers_count,
            "total_leads": leads_count,
            "active_deals": deals_qs.exclude(status=Deal.Status.VOIDED).count(),
            "agency_commission_revenue": str(comm_total),
            "agents_count": AgencyMembership.objects.filter(
                agency_id=agency_id, status="ACTIVE"
            ).count(),
            "scheduled_viewings": ViewingAppointment.objects.all_tenants().filter(
                agency_id=agency_id, status__in=["REQUESTED", "CONFIRMED"]
            ).count(),
        }

    if membership:
        my_props = Property.objects.all_tenants().filter(
            agency_id=agency_id, is_deleted=False, agent_assignments__membership=membership
        ).count()
        my_customers = Customer.objects.all_tenants().filter(
            agency_id=agency_id, is_deleted=False, assigned_membership=membership
        ).count()
        my_comm = CommissionShare.objects.all_tenants().filter(
            agency_id=agency_id, beneficiary_membership=membership
        ).aggregate(s=Sum("calculated_amount"))["s"] or Decimal("0")
        my_viewings = ViewingAppointment.objects.all_tenants().filter(
            agency_id=agency_id, agent_membership=membership, status__in=["REQUESTED", "CONFIRMED"]
        ).count()
        return {
            "role_view": "AGENT",
            "agency_name": membership.agency.name,
            "my_properties": my_props,
            "my_customers": my_customers,
            "my_scheduled_viewings": my_viewings,
            "my_commission_total": str(my_comm),
        }

    with tenant_bypass():
        my_appts = ViewingAppointment.objects.all_tenants().filter(customer__user=user).count()
    return {
        "role_view": "CUSTOMER",
        "my_viewings_count": my_appts,
    }


def get_agency_analytics(*, user: User, agency_id: Optional[UUID]) -> dict:
    if not agency_id and is_super_admin(user):
        with tenant_bypass():
            props_by_status = list(
                Property.objects.all_tenants()
                .filter(is_deleted=False)
                .values("status")
                .annotate(count=Count("id"))
            )
            deals_by_status = list(
                Deal.objects.all_tenants().values("status").annotate(count=Count("id"), volume=Sum("deal_value"))
            )
        return {
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
        .filter(agency_id=agency_id)
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
        .values("beneficiary_membership_id", "beneficiary_membership__user__first_name", "beneficiary_membership__user__last_name")
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
        "properties_by_status": props_by_status,
        "deals_by_status": [
            {"status": d["status"], "count": d["count"], "volume": str(d["volume"] or 0)}
            for d in deals_by_status
        ],
        "leads_by_status": leads_by_status,
        "negotiations_count": Negotiation.objects.all_tenants().filter(agency_id=agency_id).count(),
        "agent_leaderboard": leaderboard,
    }

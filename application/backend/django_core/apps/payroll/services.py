from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import AgencyMembership, User
from apps.audit.services import record_audit_event
from apps.commissions.models import CommissionShare
from apps.employees.models import CompensationPlan, EmployeeProfile
from common.exceptions import ConflictDomainError, NotFoundDomainError, PermissionDeniedDomainError
from common.permissions import get_active_membership, has_agency_permission, is_super_admin
from .models import PayrollCycle, Payslip, PayslipLineItem


def list_employees(*, user: User, agency_id: UUID) -> list[EmployeeProfile]:
    if not (is_super_admin(user) or has_agency_permission(user, agency_id, "agency.manage_policy")
            or has_agency_permission(user, agency_id, "accounting.view")):
        raise PermissionDeniedDomainError("فقط مدیر آژانس یا حسابدار مجاز به مشاهده پرونده پرسنلی است.")
    return list(
        EmployeeProfile.objects.all_tenants()
        .filter(agency_id=agency_id)
        .select_related("membership__user", "membership__role", "membership__branch")
        .prefetch_related("compensation_plans")
        .order_by("employee_code")
    )


@transaction.atomic
def create_employee_profile(*, user: User, agency_id: UUID, data: dict) -> EmployeeProfile:
    if not (is_super_admin(user) or has_agency_permission(user, agency_id, "agency.manage_policy")):
        raise PermissionDeniedDomainError("عدم مجوز ثبت پرونده پرسنلی.")
    if EmployeeProfile.objects.all_tenants().filter(agency_id=agency_id, employee_code=data["employee_code"]).exists():
        raise ConflictDomainError("کد پرسنلی تکراری است.")
    membership = AgencyMembership.objects.filter(id=data["membership_id"], agency_id=agency_id).first()
    if not membership:
        raise NotFoundDomainError("عضویت آژانس یافت نشد.")
    emp = EmployeeProfile.objects.all_tenants().create(
        agency_id=agency_id,
        membership=membership,
        employee_code=data["employee_code"].strip(),
        job_title=data.get("job_title", "مشاور املاک"),
        employment_type=data.get("employment_type", EmployeeProfile.EmploymentType.COMMISSION_AGENT),
        hire_date=data.get("hire_date") or date.today(),
        monthly_sales_target=Decimal(data.get("monthly_sales_target", "0")),
        created_by=user,
    )
    if data.get("base_salary") is not None:
        CompensationPlan.objects.all_tenants().create(
            agency_id=agency_id,
            employee=emp,
            model_type=data.get("model_type", CompensationPlan.ModelType.FIXED_PLUS_COMMISSION),
            base_salary=Decimal(data["base_salary"]),
            commission_multiplier=Decimal(data.get("commission_multiplier", "1.0000")),
            effective_from=emp.hire_date,
            created_by=user,
        )
    return emp


@transaction.atomic
def create_compensation_plan(*, user: User, agency_id: UUID, employee_id: UUID, data: dict) -> CompensationPlan:
    if not (
        is_super_admin(user)
        or has_agency_permission(user, agency_id, "accounting.post")
        or has_agency_permission(user, agency_id, "agency.manage_policy")
    ):
        raise PermissionDeniedDomainError("عدم مجوز تعریف طرح جبران خدمت.")
    emp = EmployeeProfile.objects.all_tenants().filter(id=employee_id, agency_id=agency_id).first()
    if not emp:
        raise NotFoundDomainError("پرونده پرسنلی یافت نشد.")
    CompensationPlan.objects.all_tenants().filter(employee=emp, is_active=True).update(is_active=False)
    return CompensationPlan.objects.all_tenants().create(
        agency_id=agency_id,
        employee=emp,
        model_type=data["model_type"],
        currency_id=data.get("currency_id", "IRT"),
        base_salary=Decimal(data.get("base_salary", "0")),
        commission_multiplier=Decimal(data.get("commission_multiplier", "1.0000")),
        effective_from=data.get("effective_from") or date.today(),
        created_by=user,
    )


def list_payroll_cycles(*, user: User, agency_id: UUID):
    qs = (
        PayrollCycle.objects.all_tenants()
        .filter(agency_id=agency_id)
        .prefetch_related("payslips__employee__membership__user", "payslips__items")
        .order_by("-period_end")
    )
    if (
        is_super_admin(user)
        or has_agency_permission(user, agency_id, "accounting.view")
        or has_agency_permission(user, agency_id, "agency.manage_policy")
    ):
        return list(qs)
    raise PermissionDeniedDomainError("فقط مدیر آژانس یا حسابدار مجاز به مشاهده فیش‌های حقوق و دستمزد است.")


@transaction.atomic
def create_and_calculate_payroll_cycle(
    *, user: User, agency_id: UUID, title: str, period_start: datetime, period_end: datetime
) -> PayrollCycle:
    if not (
        is_super_admin(user)
        or has_agency_permission(user, agency_id, "accounting.post")
        or has_agency_permission(user, agency_id, "agency.manage_policy")
    ):
        raise PermissionDeniedDomainError("عدم مجوز اجرای دوره حقوق و دستمزد.")

    if PayrollCycle.objects.all_tenants().filter(agency_id=agency_id, title=title).exists():
        raise ConflictDomainError("دوره حقوق با این عنوان قبلاً ثبت شده است.")

    if period_end <= period_start:
        raise ConflictDomainError("پایان دوره حقوق باید بعد از شروع آن باشد.")
    cycle = PayrollCycle.objects.all_tenants().create(
        agency_id=agency_id, title=title.strip(), period_start=period_start,
        period_end=period_end, status=PayrollCycle.Status.OPEN, created_by=user,
    )

    employees = EmployeeProfile.objects.all_tenants().filter(agency_id=agency_id, is_active=True).select_related(
        "membership"
    )
    for emp in employees:
        plan = emp.compensation_plans.filter(
            is_active=True, effective_from__lte=period_end.date()
        ).order_by("-effective_from").first()
        base_salary = (
            plan.base_salary if plan and plan.model_type != CompensationPlan.ModelType.PURE_COMMISSION
            else Decimal("0.00")
        )
        multiplier = plan.commission_multiplier if plan else Decimal("1.0000")

        pending_shares = list(
            CommissionShare.objects.all_tenants().select_for_update().filter(
                agency_id=agency_id, beneficiary_membership=emp.membership,
                is_included_in_payroll=False,
                deal_commission__status="FINANCE_APPROVED",
                deal_commission__created_at__gte=period_start,
                deal_commission__created_at__lt=period_end,
            ).select_related("deal_commission__deal")
        )
        comm_total = sum(((s.calculated_amount * multiplier) for s in pending_shares), Decimal("0.00"))
        gross_total = base_salary + comm_total
        from apps.settings.services import get_setting_value
        tax_rate = Decimal(str(get_setting_value("payroll.tax_rate_percent", "0") or "0"))
        if tax_rate < 0 or tax_rate > 100:
            raise ConflictDomainError("نرخ مالیات حقوق باید بین صفر تا صد تنظیم شود.")
        tax_amt = (gross_total * tax_rate / Decimal("100")).quantize(Decimal("1"))
        net_payable = max(Decimal("0.00"), gross_total - tax_amt)

        payslip = Payslip.objects.all_tenants().create(
            agency_id=agency_id,
            cycle=cycle,
            employee=emp,
            base_salary_amount=base_salary,
            commission_amount=comm_total,
            tax_amount=tax_amt,
            net_payable=net_payable,
            status=Payslip.Status.DRAFT,
            created_by=user,
        )
        if base_salary > 0:
            PayslipLineItem.objects.create(
                payslip=payslip,
                item_type=PayslipLineItem.ItemType.BASE_SALARY,
                description="حقوق پایه ماهانه",
                amount=base_salary,
                created_by=user,
            )
        for share in pending_shares:
            PayslipLineItem.objects.create(
                payslip=payslip,
                item_type=PayslipLineItem.ItemType.COMMISSION,
                description=f"پورسانت معامله {share.deal_commission.deal.deal_code}",
                amount=(share.calculated_amount * multiplier),
                commission_share=share,
                created_by=user,
            )
            share.is_included_in_payroll = True
            share.save(update_fields=["is_included_in_payroll", "updated_at"])

        if tax_amt > 0:
            PayslipLineItem.objects.create(
                payslip=payslip,
                item_type=PayslipLineItem.ItemType.TAX,
                description=f"مالیات/کسور تنظیم‌شده ({tax_rate}٪)",
                amount=tax_amt,
                created_by=user,
            )

    cycle.status = PayrollCycle.Status.CALCULATED
    cycle.save(update_fields=["status", "updated_at"])
    record_audit_event(
        action="PAYROLL_CYCLE_CALCULATED",
        resource_type="PayrollCycle",
        resource_id=str(cycle.id),
        actor=user,
        agency_id=agency_id,
    )
    return cycle


@transaction.atomic
def update_payroll_cycle_status(*, user: User, agency_id: UUID, cycle_id: UUID, status_value: str) -> PayrollCycle:
    if not (
        is_super_admin(user)
        or has_agency_permission(user, agency_id, "accounting.post")
        or has_agency_permission(user, agency_id, "agency.manage_policy")
    ):
        raise PermissionDeniedDomainError("عدم مجوز تأیید یا پرداخت دوره حقوق.")
    cycle = PayrollCycle.objects.all_tenants().select_for_update().filter(id=cycle_id, agency_id=agency_id).first()
    if not cycle:
        raise NotFoundDomainError("دوره حقوق یافت نشد.")
    allowed = {
        PayrollCycle.Status.OPEN: {PayrollCycle.Status.CALCULATED, PayrollCycle.Status.CANCELLED},
        PayrollCycle.Status.CALCULATED: {PayrollCycle.Status.APPROVED, PayrollCycle.Status.CANCELLED},
        PayrollCycle.Status.APPROVED: {PayrollCycle.Status.PAID, PayrollCycle.Status.CANCELLED},
        PayrollCycle.Status.PAID: set(),
        PayrollCycle.Status.CANCELLED: set(),
    }
    if status_value not in PayrollCycle.Status.values or status_value not in allowed.get(cycle.status, set()):
        raise ConflictDomainError(f"انتقال وضعیت دوره حقوق از {cycle.status} به {status_value} مجاز نیست.")
    if status_value == PayrollCycle.Status.CANCELLED:
        if Payslip.objects.all_tenants().filter(cycle=cycle, status=Payslip.Status.PAID).exists():
            raise ConflictDomainError("دوره دارای فیش پرداخت‌شده قابل لغو نیست.")
        shares = list(
            CommissionShare.objects.all_tenants().select_for_update().filter(
                payslip_item__payslip__cycle=cycle
            )
        )
        CommissionShare.objects.all_tenants().filter(
            id__in=[share.id for share in shares]
        ).update(is_included_in_payroll=False)
        PayslipLineItem.objects.filter(
            payslip__cycle=cycle, commission_share__isnull=False
        ).update(commission_share=None)
        Payslip.objects.all_tenants().filter(cycle=cycle).update(status=Payslip.Status.CANCELLED)
    cycle.status = status_value
    cycle.updated_by = user
    cycle.save(update_fields=["status", "updated_by", "updated_at"])
    if status_value in (PayrollCycle.Status.APPROVED, PayrollCycle.Status.PAID):
        Payslip.objects.all_tenants().filter(cycle=cycle).update(status=status_value)
    return cycle

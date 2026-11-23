from datetime import timedelta
from decimal import Decimal
import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import AgencyMembership, Role, User
from apps.accounts.services import register_user, request_password_reset_otp, confirm_password_reset_otp
from apps.accounting.models import ChartOfAccount, FiscalPeriod, FiscalYear, JournalEntry
from apps.accounting.services import create_and_post_journal_entry, list_journal_entries, reverse_journal_entry
from apps.agencies.models import Agency, AgencyAccessPolicy
from apps.appointments.models import ViewingAppointment
from apps.commissions.models import CommissionPolicy, CommissionPolicyVersion
from apps.commissions.services import calculate_deal_commission, update_commission_status
from apps.contracts.models import Contract
from apps.customers.models import Customer
from apps.customers.services import create_lead, convert_lead_to_customer, list_customers
from apps.properties.models import DealType, Property, PropertyLocation, PropertyType
from apps.properties.services import list_agency_properties, list_public_properties
from apps.settings.models import Country, Currency
from apps.transactions.models import Deal
from common.exceptions import PermissionDeniedDomainError
from common.localization.calendar import CalendarAdapter
from common.localization.currency import CurrencyConversionService


@pytest.fixture
def seed_base(db):
    Country.objects.create(code="IR", name_fa="ایران", name_en="Iran")
    Currency.objects.create(
        code="IRT", name_fa="تومان", name_en="Toman", symbol="تومان", decimal_places=0, base_unit_factor=Decimal("10")
    )
    Currency.objects.create(
        code="IRR", name_fa="ریال", name_en="Rial", symbol="ریال", decimal_places=0, base_unit_factor=Decimal("1")
    )
    apt = PropertyType.objects.create(code="APARTMENT", name_fa="آپارتمان", name_en="Apartment")
    sale = DealType.objects.create(code="SALE", name_fa="فروش", name_en="Sale")
    role_mgr = Role.objects.create(code="AGENCY_MANAGER", name="Manager", is_system_role=True)
    role_agent = Role.objects.create(code="REAL_ESTATE_AGENT", name="Agent", is_system_role=True)

    u_super = User.objects.create_superuser("09120000001", "Pass@1234")
    u_mgr_a = User.objects.create_user("09120000010", "Pass@1234", platform_role=User.PlatformRole.AGENCY_USER)
    u_agent_a = User.objects.create_user("09120000011", "Pass@1234", platform_role=User.PlatformRole.AGENCY_USER)
    u_agent_b = User.objects.create_user("09120000022", "Pass@1234", platform_role=User.PlatformRole.AGENCY_USER)
    u_cust = User.objects.create_user("09120000033", "Pass@1234", platform_role=User.PlatformRole.CUSTOMER)

    agency_a = Agency.objects.create(name="Agency A", slug="agency-a", owner_user=u_mgr_a, status="ACTIVE")
    agency_b = Agency.objects.create(name="Agency B", slug="agency-b", owner_user=u_agent_b, status="ACTIVE")
    AgencyAccessPolicy.objects.create(agency=agency_a)
    AgencyAccessPolicy.objects.create(agency=agency_b)

    m_mgr_a = AgencyMembership.objects.create(user=u_mgr_a, agency=agency_a, role=role_mgr)
    m_agent_a = AgencyMembership.objects.create(user=u_agent_a, agency=agency_a, role=role_agent)
    m_agent_b = AgencyMembership.objects.create(user=u_agent_b, agency=agency_b, role=role_agent)

    return {
        "apt": apt,
        "sale": sale,
        "u_super": u_super,
        "u_mgr_a": u_mgr_a,
        "u_agent_a": u_agent_a,
        "u_agent_b": u_agent_b,
        "u_cust": u_cust,
        "agency_a": agency_a,
        "agency_b": agency_b,
        "m_mgr_a": m_mgr_a,
        "m_agent_a": m_agent_a,
        "m_agent_b": m_agent_b,
    }


def test_1_multi_tenant_isolation_agent_a_cannot_access_agency_b(seed_base):
    prop_b = Property.objects.all_tenants().create(
        agency=seed_base["agency_b"],
        property_code="B-1",
        title="Secret Agency B Property",
        property_type=seed_base["apt"],
        deal_type=seed_base["sale"],
        status=Property.Status.DRAFT,
        visibility=Property.Visibility.PRIVATE_AGENCY,
        total_price=Decimal("10000000000"),
    )
    qs_a = list_agency_properties(user=seed_base["u_agent_a"], agency_id=seed_base["agency_a"].id)
    assert not qs_a.filter(id=prop_b.id).exists()
    qs_b_from_a = list_agency_properties(user=seed_base["u_agent_a"], agency_id=seed_base["agency_b"].id)
    assert qs_b_from_a.count() == 0


def test_2_customer_cannot_access_accounting_service(seed_base):
    with pytest.raises(PermissionDeniedDomainError):
        list_journal_entries(user=seed_base["u_cust"], agency_id=seed_base["agency_a"].id)


def test_3_public_portal_only_exposes_published_public_properties(seed_base):
    pub = Property.objects.all_tenants().create(
        agency=seed_base["agency_a"],
        property_code="A-PUB",
        title="Public Apt",
        property_type=seed_base["apt"],
        deal_type=seed_base["sale"],
        status=Property.Status.PUBLISHED,
        visibility=Property.Visibility.PUBLIC_PORTAL,
        total_price=Decimal("10000000000"),
    )
    priv = Property.objects.all_tenants().create(
        agency=seed_base["agency_a"],
        property_code="A-PRIV",
        title="Private Draft Apt",
        property_type=seed_base["apt"],
        deal_type=seed_base["sale"],
        status=Property.Status.DRAFT,
        visibility=Property.Visibility.PRIVATE_AGENCY,
        total_price=Decimal("10000000000"),
    )
    PropertyLocation.objects.create(
        property=pub,
        province="تهران",
        city="تهران",
        district="زعفرانیه",
        full_address="خیابان سرّی پلاک ۹۹",
        hide_exact_address=True,
    )
    public_ids = list(list_public_properties().values_list("id", flat=True))
    assert pub.id in public_ids
    assert priv.id not in public_ids


def test_4_double_entry_balance_and_reversal(seed_base):
    now = timezone.now()
    fy = FiscalYear.objects.all_tenants().create(
        agency=seed_base["agency_a"], title="1405", start_date=now, end_date=now + timedelta(days=365)
    )
    fp = FiscalPeriod.objects.all_tenants().create(
        agency=seed_base["agency_a"], fiscal_year=fy, name="M1", start_date=now, end_date=now + timedelta(days=30)
    )
    acc1 = ChartOfAccount.objects.all_tenants().create(
        agency=seed_base["agency_a"], code="1101", name="Cash", account_type="ASSET"
    )
    acc2 = ChartOfAccount.objects.all_tenants().create(
        agency=seed_base["agency_a"], code="4101", name="Revenue", account_type="REVENUE"
    )

    with pytest.raises(ValidationError):
        create_and_post_journal_entry(
            agency=seed_base["agency_a"],
            fiscal_period=fp,
            entry_number="JE-BAD-1",
            description="Unbalanced entry",
            lines=[
                {"account": acc1, "debit": Decimal("1000"), "credit": Decimal("0")},
                {"account": acc2, "debit": Decimal("0"), "credit": Decimal("900")},
            ],
        )
    assert JournalEntry.objects.all_tenants().filter(entry_number="JE-BAD-1").count() == 0

    good = create_and_post_journal_entry(
        agency=seed_base["agency_a"],
        fiscal_period=fp,
        entry_number="JE-OK-1",
        description="Balanced entry",
        lines=[
            {"account": acc1, "debit": Decimal("1000"), "credit": Decimal("0")},
            {"account": acc2, "debit": Decimal("0"), "credit": Decimal("1000")},
        ],
    )
    with pytest.raises(ValidationError):
        good.delete()
    rev = reverse_journal_entry(original_entry=good, reversal_number="REV-JE-OK-1")
    assert rev.status == JournalEntry.Status.POSTED


def test_5_commission_precision_and_agent_cannot_approve(seed_base):
    now = timezone.now()
    prop = Property.objects.all_tenants().create(
        agency=seed_base["agency_a"],
        property_code="A-DEAL-1",
        title="Deal Property",
        property_type=seed_base["apt"],
        deal_type=seed_base["sale"],
        status=Property.Status.SOLD,
        total_price=Decimal("10000000003"),
    )
    cnt = Contract.objects.all_tenants().create(
        agency=seed_base["agency_a"],
        contract_number="C-1",
        internal_tracking_code="T-1",
        property=prop,
        deal_type=seed_base["sale"],
        amount=Decimal("10000000003"),
        start_date=now,
        status=Contract.Status.ACTIVE,
    )
    deal = Deal.objects.all_tenants().create(
        agency=seed_base["agency_a"],
        deal_code="D-1",
        contract=cnt,
        property=prop,
        primary_agent=seed_base["m_agent_a"],
        co_agent=seed_base["m_mgr_a"],
        deal_value=Decimal("10000000003"),
    )
    policy = CommissionPolicy.objects.all_tenants().create(
        agency=seed_base["agency_a"], deal_type=seed_base["sale"], name="Std"
    )
    ver = CommissionPolicyVersion.objects.create(
        policy=policy,
        version_number=1,
        gross_rate_percent=Decimal("1.0000"),
        primary_agent_percent=Decimal("50.0000"),
        co_agent_split_ratio=Decimal("33.3333"),
    )
    dc = calculate_deal_commission(deal=deal, policy_version=ver)
    total_shares = sum((s.calculated_amount for s in dc.shares.all()), Decimal("0"))
    assert total_shares == dc.net_distributable

    with pytest.raises(ValidationError):
        calculate_deal_commission(deal=deal, policy_version=ver)

    with pytest.raises(PermissionDeniedDomainError):
        update_commission_status(
            user=seed_base["u_agent_a"],
            agency_id=seed_base["agency_a"].id,
            commission_id=dc.id,
            status_value="SETTLED",
        )


def test_6_viewing_conflict_lead_conversion_and_otp_reset(seed_base):
    now = timezone.now()
    prop = Property.objects.all_tenants().create(
        agency=seed_base["agency_a"],
        property_code="A-V-1",
        title="Viewing Prop",
        property_type=seed_base["apt"],
        deal_type=seed_base["sale"],
        status=Property.Status.PUBLISHED,
        total_price=Decimal("5000000000"),
    )
    lead = create_lead(
        user=seed_base["u_agent_a"],
        agency_id=seed_base["agency_a"].id,
        data={"full_name": "Test Buyer", "phone_number": "09128889900", "property_id": prop.id},
    )
    _, cust = convert_lead_to_customer(
        user=seed_base["u_agent_a"], agency_id=seed_base["agency_a"].id, lead_id=lead.id
    )
    assert list_customers(user=seed_base["u_agent_a"], agency_id=seed_base["agency_a"].id).filter(id=cust.id).exists()

    ViewingAppointment.schedule_safely(
        agency=seed_base["agency_a"],
        property=prop,
        customer=cust,
        agent_membership=seed_base["m_agent_a"],
        scheduled_start=now + timedelta(hours=2),
        scheduled_end=now + timedelta(hours=3),
        status=ViewingAppointment.Status.CONFIRMED,
    )
    with pytest.raises(ValidationError):
        ViewingAppointment.schedule_safely(
            agency=seed_base["agency_a"],
            property=prop,
            customer=cust,
            agent_membership=seed_base["m_agent_a"],
            scheduled_start=now + timedelta(hours=2, minutes=30),
            scheduled_end=now + timedelta(hours=3, minutes=30),
            status=ViewingAppointment.Status.CONFIRMED,
        )

    u = register_user(phone_number="09129998877", password="OldPassword123")
    otp_info = request_password_reset_otp(phone_number="09129998877")
    assert otp_info["sandbox_otp"] is not None
    confirm_password_reset_otp(
        phone_number="09129998877", otp_code=otp_info["sandbox_otp"], new_password="NewPassword123"
    )
    u.refresh_from_db()
    assert u.check_password("NewPassword123")


def test_localization_currency_and_jalali_adapter():
    assert CurrencyConversionService.convert_rial_toman(Decimal("1000"), "IRT", "IRR") == Decimal("10000")
    assert CurrencyConversionService.convert_rial_toman(Decimal("10000"), "IRR", "IRT") == Decimal("1000")
    start_utc, end_utc = CalendarAdapter.jalali_month_bounds_utc(1405, 1)
    assert end_utc > start_utc


def test_7_accounting_statements_general_ledger_and_period_close(seed_base):
    from apps.accounting.services import (
        close_fiscal_period,
        get_financial_statements,
        get_general_ledger,
        get_trial_balance,
    )

    now = timezone.now()
    fy = FiscalYear.objects.all_tenants().create(
        agency=seed_base["agency_a"], title="1405-FS", start_date=now, end_date=now + timedelta(days=365)
    )
    fp = FiscalPeriod.objects.all_tenants().create(
        agency=seed_base["agency_a"], fiscal_year=fy, name="M2", start_date=now, end_date=now + timedelta(days=30)
    )
    cash = ChartOfAccount.objects.all_tenants().create(
        agency=seed_base["agency_a"], code="1101", name="Cash", account_type=ChartOfAccount.AccountType.ASSET
    )
    liability = ChartOfAccount.objects.all_tenants().create(
        agency=seed_base["agency_a"], code="2101", name="Payable", account_type=ChartOfAccount.AccountType.LIABILITY
    )
    revenue = ChartOfAccount.objects.all_tenants().create(
        agency=seed_base["agency_a"], code="4101", name="Commission Rev", account_type=ChartOfAccount.AccountType.REVENUE
    )
    expense = ChartOfAccount.objects.all_tenants().create(
        agency=seed_base["agency_a"], code="5101", name="Rent Expense", account_type=ChartOfAccount.AccountType.EXPENSE
    )

    create_and_post_journal_entry(
        agency=seed_base["agency_a"],
        fiscal_period=fp,
        entry_number="JE-FS-1",
        description="Commission received",
        lines=[
            {"account": cash, "debit": Decimal("5000"), "credit": Decimal("0")},
            {"account": revenue, "debit": Decimal("0"), "credit": Decimal("5000")},
        ],
    )
    create_and_post_journal_entry(
        agency=seed_base["agency_a"],
        fiscal_period=fp,
        entry_number="JE-FS-2",
        description="Office expense",
        lines=[
            {"account": expense, "debit": Decimal("1500"), "credit": Decimal("0")},
            {"account": cash, "debit": Decimal("0"), "credit": Decimal("500")},
            {"account": liability, "debit": Decimal("0"), "credit": Decimal("1000")},
        ],
    )

    tb = get_trial_balance(user=seed_base["u_mgr_a"], agency_id=seed_base["agency_a"].id)
    assert tb["totals"]["is_balanced"] is True
    assert Decimal(tb["totals"]["debit_turnover"]) == Decimal("6500")
    assert Decimal(tb["totals"]["credit_turnover"]) == Decimal("6500")

    fs = get_financial_statements(user=seed_base["u_mgr_a"], agency_id=seed_base["agency_a"].id)
    assert fs["income_statement"]["net_income"] == "3500.00"
    assert fs["balance_sheet"]["is_balanced"] is True
    assert Decimal(fs["balance_sheet"]["total_assets"]) == Decimal("4500")
    assert Decimal(fs["balance_sheet"]["total_liabilities_and_equity"]) == Decimal("4500")

    gl = get_general_ledger(
        user=seed_base["u_mgr_a"], agency_id=seed_base["agency_a"].id, account_id=cash.id
    )
    assert len(gl["lines"]) == 2
    assert Decimal(gl["lines"][0]["running_balance"]) == Decimal("5000")
    assert Decimal(gl["closing_balance"]) == Decimal("4500")

    closed = close_fiscal_period(
        user=seed_base["u_mgr_a"], agency_id=seed_base["agency_a"].id, period_id=fp.id
    )
    assert closed.is_closed is True

    with pytest.raises(ValidationError):
        create_and_post_journal_entry(
            agency=seed_base["agency_a"],
            fiscal_period=fp,
            entry_number="JE-FS-AFTER-CLOSE",
            description="Should be blocked",
            lines=[
                {"account": cash, "debit": Decimal("100"), "credit": Decimal("0")},
                {"account": revenue, "debit": Decimal("0"), "credit": Decimal("100")},
            ],
        )


def test_8_dashboard_summary_role_and_period_filter(seed_base):
    from apps.reports.services import get_dashboard_summary

    mgr_summary = get_dashboard_summary(
        user=seed_base["u_mgr_a"], agency_id=seed_base["agency_a"].id, period_days=7
    )
    assert mgr_summary["role_view"] == "AGENCY_MANAGER"
    assert mgr_summary["period_days"] == 7
    assert "treasury_total" in mgr_summary
    assert "alerts" in mgr_summary

    agent_summary = get_dashboard_summary(
        user=seed_base["u_agent_a"], agency_id=seed_base["agency_a"].id, period_days=30
    )
    assert agent_summary["role_view"] == "AGENT"

    cust_summary = get_dashboard_summary(user=seed_base["u_cust"], agency_id=None, period_days=30)
    assert cust_summary["role_view"] == "CUSTOMER"


def test_9_tickets_complaints_surveys_and_ai_isolation(seed_base):
    from apps.ai_assistant.services import draft_property_listing, summarize_customer_crm
    from apps.complaints.services import (
        add_complaint_note,
        create_complaint,
        list_complaints,
        track_public_complaint,
        update_complaint_status,
    )
    from apps.customers.models import Customer
    from apps.support.services import add_ticket_message, create_ticket, get_ticket, submit_ticket_rating
    from apps.surveys.services import create_survey, get_survey_analytics, submit_survey_response
    from common.exceptions import ConflictDomainError, NotFoundDomainError

    # 1. Ticket + internal note isolation
    t = create_ticket(
        user=seed_base["u_cust"],
        agency_id=seed_base["agency_a"].id,
        data={"scope": "AGENCY", "subject": "سؤال بازدید", "body": "جزئیات بازدید", "priority": "HIGH"},
    )
    add_ticket_message(
        user=seed_base["u_mgr_a"],
        agency_id=seed_base["agency_a"].id,
        ticket_id=t.id,
        data={"body": "یادداشت داخلی تیم پشتیبانی", "is_internal_note": True},
    )
    add_ticket_message(
        user=seed_base["u_mgr_a"],
        agency_id=seed_base["agency_a"].id,
        ticket_id=t.id,
        data={"body": "پاسخ رسمی برای مشتری", "is_internal_note": False},
    )
    cust_t, can_internal = get_ticket(user=seed_base["u_cust"], agency_id=seed_base["agency_a"].id, ticket_id=t.id)
    assert can_internal is False
    assert cust_t.messages.filter(is_internal_note=False).count() == 2
    submit_ticket_rating(
        user=seed_base["u_cust"],
        agency_id=seed_base["agency_a"].id,
        ticket_id=t.id,
        rating=5,
        comment="پاسخ سریع و عالی",
    )
    t.refresh_from_db()
    assert t.satisfaction_rating == 5

    # 2. Complaint confidentiality + public tracking
    comp = create_complaint(
        user=seed_base["u_cust"],
        agency_id=seed_base["agency_a"].id,
        data={
            "target_type": "AGENCY",
            "target_title": "شعبه مرکزی",
            "subject": "گزارش محرمانه",
            "description": "شرح تخلف احتمالی",
            "is_confidential": True,
        },
    )
    # Confidential complaint is NOT visible to agency manager
    assert not list_complaints(user=seed_base["u_mgr_a"], agency_id=seed_base["agency_a"].id).filter(id=comp.id).exists()
    # Visible to super admin
    assert list_complaints(user=seed_base["u_super"], agency_id=None).filter(id=comp.id).exists()

    add_complaint_note(
        user=seed_base["u_super"],
        complaint_id=comp.id,
        note="بررسی بازرس ویژه",
    )
    update_complaint_status(
        user=seed_base["u_super"],
        complaint_id=comp.id,
        to_status="RESOLVED",
        resolution_summary="تذکر کتبی صادر شد.",
    )
    tracked = track_public_complaint(
        tracking_code=comp.tracking_code,
        phone_number=seed_base["u_cust"].phone_number,
    )
    assert tracked["status"] == "RESOLVED"
    assert "بررسی بازرس ویژه" not in str(tracked)

    # 3. Survey 8 types, duplicate rejection, NPS calculation
    survey = create_survey(
        user=seed_base["u_mgr_a"],
        agency_id=seed_base["agency_a"].id,
        data={
            "title": "نظرسنجی تست جامع",
            "slug": "test-comprehensive-survey",
            "questions": [
                {"question_text": "ستاره", "question_type": "STARS"},
                {"question_text": "NPS", "question_type": "NPS"},
                {"question_text": "تک انتخابی", "question_type": "SINGLE_SELECT", "options": ["عالی", "خوب"]},
                {"question_text": "چند انتخابی", "question_type": "MULTI_SELECT", "options": ["سرعت", "دقت"]},
                {"question_text": "بله خیر", "question_type": "YES_NO"},
                {"question_text": "متن", "question_type": "TEXT", "is_required": False},
            ],
        },
    )
    qs = list(survey.questions.all())
    submit_survey_response(
        slug="test-comprehensive-survey",
        user=None,
        respondent_identifier="anon-1",
        respondent_name="مهمان ۱",
        answers=[
            {"question_id": qs[0].id, "answer_number": 5},
            {"question_id": qs[1].id, "answer_number": 10},
            {"question_id": qs[2].id, "selected_options": ["عالی"]},
            {"question_id": qs[3].id, "selected_options": ["سرعت", "دقت"]},
            {"question_id": qs[4].id, "answer_text": "YES"},
        ],
    )
    with pytest.raises(ConflictDomainError):
        submit_survey_response(
            slug="test-comprehensive-survey",
            user=None,
            respondent_identifier="anon-1",
            respondent_name="مهمان ۱",
            answers=[
                {"question_id": qs[0].id, "answer_number": 5},
                {"question_id": qs[1].id, "answer_number": 10},
                {"question_id": qs[2].id, "selected_options": ["عالی"]},
                {"question_id": qs[3].id, "selected_options": ["سرعت"]},
                {"question_id": qs[4].id, "answer_text": "YES"},
            ],
        )
    analytics = get_survey_analytics(user=seed_base["u_mgr_a"], agency_id=seed_base["agency_a"].id, survey_id=survey.id)
    assert analytics["total_responses"] == 1
    assert analytics["nps_score"] == 100.0

    # 4. Tenant-isolated AI assistant
    prop_b = Property.objects.all_tenants().create(
        agency=seed_base["agency_b"],
        property_code="B-AI-1",
        title="Secret Agency B Villa",
        property_type=seed_base["apt"],
        deal_type=seed_base["sale"],
        status=Property.Status.DRAFT,
        total_price=Decimal("9000000000"),
    )
    cust_b = Customer.objects.all_tenants().create(
        agency=seed_base["agency_b"],
        full_name="Secret Client B",
        primary_phone="09127776655",
    )
    with pytest.raises(NotFoundDomainError):
        draft_property_listing(
            user=seed_base["u_mgr_a"], agency_id=seed_base["agency_a"].id, property_id=prop_b.id
        )
    with pytest.raises(NotFoundDomainError):
        summarize_customer_crm(
            user=seed_base["u_mgr_a"], agency_id=seed_base["agency_a"].id, customer_id=cust_b.id
        )


def test_10_cms_workflow_redirects_and_agency_cooperation_approval(seed_base):
    from apps.agencies.models import Agency
    from apps.cms.models import Article
    from apps.cms.services import (
        create_article,
        create_redirect,
        list_public_articles,
        review_cooperation_request,
        submit_contact_inquiry,
        submit_cooperation_request,
        track_contact_inquiry,
        transition_article_status,
    )
    from common.exceptions import PermissionDeniedDomainError

    art = create_article(
        user=seed_base["u_mgr_a"],
        data={
            "title": "راهنمای سرمایه‌گذاری مسکن",
            "slug": "housing-investment-guide-test",
            "content_body": "محتوای تحلیلی جامع برای تست گردش کار تحریریه و انتشار در پورتال عمومی.",
        },
    )
    assert art.status == Article.Status.DRAFT
    assert art.versions.count() == 1

    # Manager sends to REVIEW, cannot directly PUBLISH
    transition_article_status(user=seed_base["u_mgr_a"], article_id=art.id, to_status=Article.Status.REVIEW)
    with pytest.raises(PermissionDeniedDomainError):
        transition_article_status(user=seed_base["u_mgr_a"], article_id=art.id, to_status=Article.Status.PUBLISHED)

    # Super admin approves & publishes
    transition_article_status(user=seed_base["u_super"], article_id=art.id, to_status=Article.Status.APPROVED)
    transition_article_status(user=seed_base["u_super"], article_id=art.id, to_status=Article.Status.PUBLISHED)
    assert list_public_articles().filter(id=art.id).exists()

    redir = create_redirect(user=seed_base["u_super"], from_path="/old-blog", to_path="/blog", status_code=301)
    assert redir.status_code == 301

    inq = submit_contact_inquiry(
        data={
            "full_name": "مهدی کریمی",
            "phone_number": "09128881122",
            "subject": "مشاوره خرید",
            "message": "تماس برای خرید آپارتمان",
        }
    )
    found_inq = track_contact_inquiry(tracking_code=inq.tracking_code, phone_number="09128881122")
    assert found_inq.id == inq.id

    coop = submit_cooperation_request(
        data={
            "agency_name": "املاک نوین تست",
            "city": "تهران",
            "manager_name": "حمید رضایی",
            "manager_phone": "09129991122",
            "agents_count": 12,
        }
    )
    approved_coop = review_cooperation_request(
        user=seed_base["u_super"], request_id=coop.id, decision="APPROVED"
    )
    assert approved_coop.approved_agency_id is not None
    assert Agency.objects.filter(id=approved_coop.approved_agency_id, status=Agency.Status.ACTIVE).exists()


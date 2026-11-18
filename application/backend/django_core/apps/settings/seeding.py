import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Any, Callable, Optional
from django.apps import apps as dj_apps
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import (
    AgencyMembership,
    LoginAttemptLog,
    MembershipPermissionOverride,
    Permission,
    Role,
    RolePermission,
    User,
    UserSession,
)
from apps.accounting.models import (
    BankAccount,
    CashBox,
    ChartOfAccount,
    ChequeInstrument,
    CostCenter,
    DealFinancialLedger,
    FiscalPeriod,
    FiscalYear,
    JournalEntry,
    JournalEntryLine,
)
from apps.accounting.services import create_and_post_journal_entry
from apps.agencies.models import Agency, AgencyAccessPolicy, AgencyCooperation
from apps.ai_assistant.models import AiInteractionLog
from apps.appointments.models import ViewingAppointment
from apps.audit.models import AuditLog
from apps.branches.models import Branch
from apps.cms.models import (
    AgencyCooperationRequest,
    Article,
    AuthorProfile,
    ContactInquiry,
    ContentCategory,
    ContentVersion,
    FaqItem,
    JobOpening,
    RedirectRule,
    Tag,
)
from apps.commissions.models import CommissionPolicy, CommissionPolicyVersion
from apps.commissions.services import calculate_deal_commission
from apps.complaints.models import Complaint, ComplaintNote
from apps.contracts.models import (
    Contract,
    ContractParty,
    ContractStatusHistory,
    ContractTemplate,
)
from apps.crm.models import (
    CustomerInteractionLog,
    CustomerPipelineItem,
    FollowUpTask,
    PipelineStage,
)
from apps.customers.models import Customer, CustomerRequirement, CustomerShare
from apps.documents.models import Document, DocumentDownloadLog, DocumentVersion
from apps.employees.models import CompensationPlan, EmployeeProfile
from apps.leads.models import Lead
from apps.negotiations.models import Negotiation, NegotiationOfferVersion
from apps.notifications.models import (
    NotificationMessage,
    NotificationPreference,
    PushSubscription,
)
from apps.payments.models import PaymentGatewayTransaction
from apps.payroll.models import PayrollCycle, Payslip, PayslipLineItem
from apps.properties.models import (
    Amenity,
    DealType,
    Property,
    PropertyAgentAssignment,
    PropertyLocation,
    PropertyOwner,
    PropertyPriceHistory,
    PropertyStatusHistory,
    PropertyType,
)
from apps.property_media.models import PropertyMedia
from apps.search.models import SavedSearch
from apps.settings.models import Country, Currency, PlatformSetting, ProviderConfiguration
from apps.subscriptions.models import AgencySubscription, SubscriptionPlan
from apps.support.models import (
    CannedReply,
    Ticket,
    TicketAttachment,
    TicketMessage,
    TicketStatusHistory,
)
from apps.surveys.models import Survey, SurveyAnswer, SurveyQuestion, SurveyResponse
from apps.transactions.models import Deal


def _ensure_user(
    *,
    phone_number: str,
    password: str,
    first_name: str,
    last_name: str,
    email: str,
    platform_role: str,
    is_staff: bool = False,
    is_superuser: bool = False,
) -> User:
    user, created = User.objects.get_or_create(
        phone_number=phone_number,
        defaults={
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "platform_role": platform_role,
            "is_staff": is_staff,
            "is_superuser": is_superuser,
            "is_phone_verified": True,
            "status": User.Status.ACTIVE,
        },
    )
    if created:
        user.set_password(password)
        user.save()
    return user


def collect_domain_model_counts() -> dict[str, int]:
    """Counts rows across every installed domain model (excluding Django built-ins)."""
    counts: dict[str, int] = {}
    excluded_apps = {"admin", "auth", "contenttypes", "sessions", "messages"}
    for model in dj_apps.get_models():
        if model._meta.app_label in excluded_apps:
            continue
        manager = model.objects
        if hasattr(manager, "all_tenants"):
            qs = manager.all_tenants()
        else:
            qs = manager.all()
        counts[f"{model._meta.app_label}.{model.__name__}"] = qs.count()
    return counts


@transaction.atomic
def seed_all_platform_data(
    *,
    log_fn: Optional[Callable[[str], None]] = None,
    verify_all: bool = True,
) -> dict[str, Any]:
    now = timezone.now()

    def _log(msg: str) -> None:
        if log_fn:
            log_fn(msg)

    # 1. Countries, Currencies & Platform Settings
    Country.objects.get_or_create(
        code="IR",
        defaults={
            "name_fa": "ایران",
            "name_en": "Iran",
            "default_currency_code": "IRT",
            "default_calendar": "jalali",
            "default_timezone": "Asia/Tehran",
            "phone_prefix": "+98",
        },
    )
    Country.objects.get_or_create(
        code="AE",
        defaults={
            "name_fa": "امارات متحده عربی",
            "name_en": "United Arab Emirates",
            "default_currency_code": "AED",
            "default_calendar": "gregorian",
            "default_timezone": "Asia/Dubai",
            "phone_prefix": "+971",
        },
    )

    for code, nfa, nen, sym, dp, factor in [
        ("IRT", "تومان", "Iranian Toman", "تومان", 0, Decimal("10.000000")),
        ("IRR", "ریال", "Iranian Rial", "ریال", 0, Decimal("1.000000")),
        ("USD", "دلار آمریکا", "US Dollar", "$", 2, Decimal("1.000000")),
        ("EUR", "یورو", "Euro", "€", 2, Decimal("1.000000")),
        ("AED", "درهم امارات", "UAE Dirham", "AED", 2, Decimal("1.000000")),
    ]:
        Currency.objects.get_or_create(
            code=code,
            defaults={
                "name_fa": nfa,
                "name_en": nen,
                "symbol": sym,
                "decimal_places": dp,
                "base_unit_factor": factor,
            },
        )

    for key, val, desc in [
        (
            "platform.localization_defaults",
            {"country": "IR", "language": "fa", "calendar": "jalali", "currency": "IRT"},
            "تنظیمات پیش‌فرض بومی‌سازی سراسری پلتفرم",
        ),
        (
            "platform.security_policy",
            {"access_ttl_minutes": 30, "refresh_ttl_days": 7, "mask_owner_pii_public": True},
            "سیاست‌های امنیتی احراز هویت و حفاظت اطلاعات مالک",
        ),
        (
            "platform.support_sla",
            {"urgent_hours": 4, "high_hours": 12, "normal_hours": 24},
            "توافق‌نامه سطح خدمات پشتیبانی تیکت‌ها",
        ),
    ]:
        PlatformSetting.objects.get_or_create(
            key=key, defaults={"value_json": val, "description": desc}
        )

    # 2. Catalog Types & Amenities
    apt_type, _ = PropertyType.objects.get_or_create(
        code="APARTMENT", defaults={"name_fa": "آپارتمان", "name_en": "Apartment"}
    )
    villa_type, _ = PropertyType.objects.get_or_create(
        code="VILLA", defaults={"name_fa": "خانه ویلایی", "name_en": "Villa"}
    )
    office_type, _ = PropertyType.objects.get_or_create(
        code="OFFICE",
        defaults={"name_fa": "دفتر کار", "name_en": "Office", "category": "COMMERCIAL"},
    )
    PropertyType.objects.get_or_create(
        code="LAND", defaults={"name_fa": "زمین", "name_en": "Land", "category": "LAND"}
    )

    sale_deal, _ = DealType.objects.get_or_create(
        code="SALE", defaults={"name_fa": "فروش", "name_en": "Sale", "is_rental": False}
    )
    rent_deal, _ = DealType.objects.get_or_create(
        code="MORTGAGE_RENT",
        defaults={"name_fa": "رهن و اجاره", "name_en": "Mortgage & Rent", "is_rental": True},
    )

    amenities_data = [
        ("PARKING", "پارکینگ", "Parking"),
        ("ELEVATOR", "آسانسور", "Elevator"),
        ("STORAGE", "انباری", "Storage"),
        ("BALCONY", "بالکن", "Balcony"),
        ("POOL", "استخر", "Pool"),
        ("SMART_HOME", "هوشمندسازی", "Smart Home"),
    ]
    amenities = {}
    for code, nfa, nen in amenities_data:
        obj, _ = Amenity.objects.get_or_create(
            code=code, defaults={"name_fa": nfa, "name_en": nen}
        )
        amenities[code] = obj

    # 3. Permissions & System Roles (Including BRANCH_MANAGER)
    perm_codes = [
        ("agency.manage_policy", "agencies", "مدیریت سیاست‌های دسترسی آژانس"),
        ("agency.manage_branches", "agencies", "مدیریت شعب آژانس"),
        ("property.view_all_agency", "properties", "مشاهده تمام املاک آژانس"),
        ("property.edit_all_agency", "properties", "ویرایش تمام املاک آژانس"),
        ("property.publish", "properties", "تأیید و انتشار عمومی ملک"),
        ("customer.view_all_agency", "customers", "مشاهده تمام مشتریان آژانس"),
        ("customer.edit_all_agency", "customers", "ویرایش تمام مشتریان آژانس"),
        ("customer.share", "customers", "اشتراک‌گذاری مشتری با سایر مشاوران"),
        ("owner.view_pii", "properties", "مشاهده اطلاعات هویتی و تماس مالک"),
        ("appointment.view_all_agency", "appointments", "مشاهده تقویم کل آژانس"),
        ("deal.view_all_agency", "transactions", "مشاهده تمام معاملات آژانس"),
        ("commission.view_all_agency", "commissions", "مشاهده تمام کمیسیون‌های آژانس"),
        ("accounting.view", "accounting", "مشاهده دفاتر حسابداری"),
        ("accounting.post", "accounting", "ثبت و قطعی‌سازی اسناد حسابداری"),
        ("audit.view", "audit", "مشاهده لاگ ممیزی آژانس"),
    ]
    for code, mod, desc in perm_codes:
        Permission.objects.get_or_create(
            code=code, defaults={"module": mod, "description": desc}
        )

    mgr_role, _ = Role.objects.get_or_create(
        code="AGENCY_MANAGER",
        agency=None,
        defaults={"name": "مدیر آژانس", "scope": Role.Scope.AGENCY, "is_system_role": True},
    )
    branch_mgr_role, _ = Role.objects.get_or_create(
        code="BRANCH_MANAGER",
        agency=None,
        defaults={"name": "مدیر شعبه", "scope": Role.Scope.AGENCY, "is_system_role": True},
    )
    agent_role, _ = Role.objects.get_or_create(
        code="REAL_ESTATE_AGENT",
        agency=None,
        defaults={"name": "مشاور املاک", "scope": Role.Scope.AGENCY, "is_system_role": True},
    )
    acct_role, _ = Role.objects.get_or_create(
        code="AGENCY_ACCOUNTANT",
        agency=None,
        defaults={"name": "حسابدار آژانس", "scope": Role.Scope.AGENCY, "is_system_role": True},
    )

    for p in Permission.objects.all():
        RolePermission.objects.get_or_create(role=mgr_role, permission=p)

    for p in Permission.objects.filter(
        code__in=[
            "agency.manage_branches",
            "property.view_all_agency",
            "property.publish",
            "customer.view_all_agency",
            "customer.share",
            "owner.view_pii",
            "appointment.view_all_agency",
            "deal.view_all_agency",
            "commission.view_all_agency",
        ]
    ):
        RolePermission.objects.get_or_create(role=branch_mgr_role, permission=p)

    for p in Permission.objects.filter(
        code__in=[
            "accounting.view",
            "accounting.post",
            "commission.view_all_agency",
            "deal.view_all_agency",
        ]
    ):
        RolePermission.objects.get_or_create(role=acct_role, permission=p)

    # 4. All 7 Platform & Agency Demo Accounts
    super_admin = _ensure_user(
        phone_number="09120000001",
        password="Admin@12345",
        first_name="سهراب",
        last_name="مدیری",
        email="admin@realestate-erp.ir",
        platform_role=User.PlatformRole.SUPER_ADMIN,
        is_staff=True,
        is_superuser=True,
    )
    mgr_a = _ensure_user(
        phone_number="09121111111",
        password="Manager@12345",
        first_name="امیرحسین",
        last_name="کیانی",
        email="manager@parsnegin.ir",
        platform_role=User.PlatformRole.AGENCY_USER,
    )
    mgr_b = _ensure_user(
        phone_number="09123333333",
        password="Manager@12345",
        first_name="مریم",
        last_name="شریفی",
        email="manager@aryahome.ir",
        platform_role=User.PlatformRole.AGENCY_USER,
    )
    branch_mgr = _ensure_user(
        phone_number="09125555555",
        password="Branch@12345",
        first_name="پارسا",
        last_name="سهرابی",
        email="branch@parsnegin.ir",
        platform_role=User.PlatformRole.AGENCY_USER,
    )
    agent_a1 = _ensure_user(
        phone_number="09122222222",
        password="Agent@12345",
        first_name="نیما",
        last_name="فرهادی",
        email="nima@parsnegin.ir",
        platform_role=User.PlatformRole.AGENCY_USER,
    )
    accountant_user = _ensure_user(
        phone_number="09126666666",
        password="Accountant@12345",
        first_name="سعیده",
        last_name="حسینی",
        email="finance@parsnegin.ir",
        platform_role=User.PlatformRole.AGENCY_USER,
    )
    customer_user = _ensure_user(
        phone_number="09124444444",
        password="Customer@12345",
        first_name="آرش",
        last_name="صادقی",
        email="arash@customer.ir",
        platform_role=User.PlatformRole.CUSTOMER,
    )

    # Seed UserSessions, LoginAttemptLogs & NotificationPreferences
    for usr, dev in [
        (super_admin, "Admin Console — Chrome"),
        (mgr_a, "Manager MacBook — Safari"),
        (branch_mgr, "Branch Terminal — Edge"),
        (accountant_user, "Finance Workstation — Chrome"),
        (agent_a1, "iPhone 15 — Mobile PWA"),
        (customer_user, "Public Portal — Web Browser"),
    ]:
        if not UserSession.objects.filter(user=usr).exists():
            UserSession.objects.create(
                user=usr,
                device_name=dev,
                ip_address="127.0.0.1",
                user_agent="Mozilla/5.0 BonyanMelk-Client",
                last_active_at=now - timedelta(minutes=15),
            )
        if not LoginAttemptLog.objects.filter(identifier=usr.phone_number).exists():
            LoginAttemptLog.objects.create(
                identifier=usr.phone_number,
                user=usr,
                ip_address="127.0.0.1",
                succeeded=True,
            )
        NotificationPreference.objects.get_or_create(
            user=usr,
            defaults={
                "in_app_enabled": True,
                "push_enabled": True,
                "sms_enabled": True,
                "email_enabled": True,
            },
        )

    PushSubscription.objects.get_or_create(
        endpoint="https://push.bonyanmelk.ir/sub/demo-manager-1",
        defaults={
            "user": mgr_a,
            "p256dh": "BOr7demoP256dhKeySample001",
            "auth": "demoAuthSecret001",
            "device_label": "مرورگر دسکتاپ مدیر آژانس",
            "is_active": True,
            "last_used_at": now - timedelta(hours=2),
        },
    )

    # 5. Subscription Plans & Providers
    SubscriptionPlan.objects.get_or_create(
        code="BASIC",
        defaults={
            "name_fa": "پلن پایه",
            "name_en": "Basic",
            "monthly_price": Decimal("1800000"),
            "annual_price": Decimal("18000000"),
            "max_agents": 10,
            "max_branches": 2,
            "max_active_listings": 150,
            "features_json": {
                "crm_pipeline": True,
                "public_portal": True,
                "double_entry_accounting": False,
                "multi_branch": False,
            },
        },
    )
    pro_plan, _ = SubscriptionPlan.objects.get_or_create(
        code="PRO",
        defaults={
            "name_fa": "پلن حرفه‌ای",
            "name_en": "Professional",
            "monthly_price": Decimal("4500000"),
            "annual_price": Decimal("45000000"),
            "max_agents": 30,
            "max_branches": 5,
            "max_active_listings": 500,
            "features_json": {
                "crm_pipeline": True,
                "public_portal": True,
                "double_entry_accounting": True,
                "multi_branch": True,
            },
        },
    )
    SubscriptionPlan.objects.get_or_create(
        code="ENTERPRISE",
        defaults={
            "name_fa": "پلن سازمانی ویژه",
            "name_en": "Enterprise",
            "monthly_price": Decimal("12000000"),
            "annual_price": Decimal("120000000"),
            "max_agents": 250,
            "max_branches": 25,
            "max_active_listings": 5000,
            "features_json": {
                "crm_pipeline": True,
                "public_portal": True,
                "double_entry_accounting": True,
                "multi_branch": True,
                "dedicated_sla": True,
            },
        },
    )

    ProviderConfiguration.objects.get_or_create(
        agency=None,
        category=ProviderConfiguration.Category.PAYMENT,
        provider_key="sandbox",
        defaults={"display_name": "درگاه آزمایشی (Sandbox)", "is_active": True, "is_sandbox": True},
    )
    ProviderConfiguration.objects.get_or_create(
        agency=None,
        category=ProviderConfiguration.Category.SMS,
        provider_key="console",
        defaults={"display_name": "سرویس پیامک توسعه", "is_active": True, "is_sandbox": True},
    )
    ProviderConfiguration.objects.get_or_create(
        agency=None,
        category=ProviderConfiguration.Category.MAP,
        provider_key="osm",
        defaults={"display_name": "OpenStreetMap", "is_active": True, "is_sandbox": True},
    )

    # 6. Agencies, Branches & Memberships (All 7 Roles Wired)
    agency_a, _ = Agency.objects.get_or_create(
        slug="pars-negin",
        defaults={
            "name": "گروه مشاورین املاک پارس نگین",
            "registration_number": "IR-TEH-88412",
            "phone": "02122334455",
            "email": "info@parsnegin.ir",
            "owner_user": mgr_a,
            "status": Agency.Status.ACTIVE,
        },
    )
    AgencyAccessPolicy.objects.get_or_create(agency=agency_a)
    if not AgencySubscription.objects.filter(agency=agency_a, plan=pro_plan).exists():
        AgencySubscription.objects.create(
            agency=agency_a,
            plan=pro_plan,
            starts_at=now - timedelta(days=10),
            expires_at=now + timedelta(days=355),
            status=AgencySubscription.Status.ACTIVE,
        )
    branch_a, _ = Branch.objects.get_or_create(
        agency=agency_a,
        code="TEH-N1",
        defaults={
            "name": "شعبه مرکزی زعفرانیه",
            "province": "تهران",
            "city": "تهران",
            "address": "زعفرانیه، خیابان مقدس اردبیلی",
            "phone": "02122334455",
            "is_main": True,
        },
    )
    branch_a2, _ = Branch.objects.get_or_create(
        agency=agency_a,
        code="TEH-N2",
        defaults={
            "name": "شعبه نیاوران و فرمانیه",
            "province": "تهران",
            "city": "تهران",
            "address": "نیاوران، خیابان باهنر، پلاک ۱۰۸",
            "phone": "02122889900",
            "is_main": False,
        },
    )

    mem_mgr_a, _ = AgencyMembership.objects.get_or_create(
        user=mgr_a, agency=agency_a, defaults={"role": mgr_role, "branch": branch_a}
    )
    mem_branch_mgr, _ = AgencyMembership.objects.get_or_create(
        user=branch_mgr,
        agency=agency_a,
        defaults={"role": branch_mgr_role, "branch": branch_a2},
    )
    mem_agent_a1, _ = AgencyMembership.objects.get_or_create(
        user=agent_a1, agency=agency_a, defaults={"role": agent_role, "branch": branch_a}
    )
    mem_accountant, _ = AgencyMembership.objects.get_or_create(
        user=accountant_user,
        agency=agency_a,
        defaults={"role": acct_role, "branch": branch_a},
    )

    perm_pub = Permission.objects.get(code="property.publish")
    MembershipPermissionOverride.objects.get_or_create(
        membership=mem_branch_mgr,
        permission=perm_pub,
        defaults={"effect": MembershipPermissionOverride.Effect.ALLOW},
    )

    agency_b, _ = Agency.objects.get_or_create(
        slug="arya-home",
        defaults={
            "name": "آژانس املاک آریا",
            "registration_number": "IR-TEH-99105",
            "phone": "02188776655",
            "email": "info@aryahome.ir",
            "owner_user": mgr_b,
            "status": Agency.Status.ACTIVE,
        },
    )
    AgencyAccessPolicy.objects.get_or_create(agency=agency_b)
    branch_b, _ = Branch.objects.get_or_create(
        agency=agency_b,
        code="TEH-S1",
        defaults={
            "name": "شعبه مرکزی الهیه",
            "province": "تهران",
            "city": "تهران",
            "address": "الهیه، خیابان فرشته، پلاک ۴۰",
            "is_main": True,
        },
    )
    AgencyMembership.objects.get_or_create(
        user=mgr_b, agency=agency_b, defaults={"role": mgr_role, "branch": branch_b}
    )

    # 7. Customers, Shares & 12-Stage Pipeline
    owner_cust, _ = Customer.objects.all_tenants().get_or_create(
        agency=agency_a,
        primary_phone="09125551010",
        defaults={
            "customer_type": Customer.CustomerType.OWNER,
            "full_name": "مهندس فریدون راد",
            "assigned_membership": mem_agent_a1,
            "source": "REFERRAL",
        },
    )
    buyer_cust, _ = Customer.objects.all_tenants().get_or_create(
        agency=agency_a,
        primary_phone="09124444444",
        defaults={
            "user": customer_user,
            "customer_type": Customer.CustomerType.BUYER,
            "full_name": "آرش صادقی",
            "assigned_membership": mem_agent_a1,
            "lead_score": 88,
            "readiness_level": "HOT",
            "source": "PORTAL",
        },
    )
    CustomerShare.objects.get_or_create(
        customer=buyer_cust,
        membership=mem_branch_mgr,
        defaults={"access_level": CustomerShare.AccessLevel.VIEW},
    )
    CustomerRequirement.objects.all_tenants().get_or_create(
        agency=agency_a,
        customer=buyer_cust,
        deal_type=sale_deal,
        property_type=apt_type,
        defaults={
            "target_city": "تهران",
            "target_districts": ["زعفرانیه", "فرشته", "نیاوران"],
            "min_area_sqm": Decimal("140.00"),
            "max_area_sqm": Decimal("240.00"),
            "min_budget": Decimal("20000000000"),
            "max_budget": Decimal("45000000000"),
            "min_bedrooms": 3,
        },
    )

    stage_defs = [
        ("NEW_LEAD", "مشتری جدید", 1, False, False),
        ("INITIAL_CONTACT", "تماس اولیه", 2, False, False),
        ("NEEDS_ASSESSMENT", "بررسی نیاز", 3, False, False),
        ("PROPERTY_SUGGESTION", "معرفی ملک", 4, False, False),
        ("VIEWING_SCHEDULED", "برنامه‌ریزی بازدید", 5, False, False),
        ("VIEWING_COMPLETED", "بازدید انجام شده", 6, False, False),
        ("NEGOTIATION", "مذاکره", 7, False, False),
        ("PRICE_OFFER", "پیشنهاد قیمت", 8, False, False),
        ("INITIAL_AGREEMENT", "توافق اولیه", 9, False, False),
        ("CONTRACTING", "قرارداد", 10, False, False),
        ("CLOSED_WON", "معامله موفق", 11, True, False),
        ("CLOSED_LOST", "معامله ناموفق", 12, False, True),
    ]
    stages = {}
    for code, name, order, won, lost in stage_defs:
        st, _ = PipelineStage.objects.all_tenants().get_or_create(
            agency=agency_a,
            code=code,
            defaults={
                "name": name,
                "sort_order": order,
                "is_terminal_won": won,
                "is_terminal_lost": lost,
            },
        )
        stages[code] = st

    CustomerPipelineItem.objects.all_tenants().get_or_create(
        agency=agency_a,
        customer=buyer_cust,
        defaults={"stage": stages["VIEWING_SCHEDULED"], "assigned_membership": mem_agent_a1},
    )
    if not CustomerInteractionLog.objects.all_tenants().filter(agency=agency_a, customer=buyer_cust).exists():
        CustomerInteractionLog.objects.all_tenants().create(
            agency=agency_a,
            customer=buyer_cust,
            membership=mem_agent_a1,
            channel=CustomerInteractionLog.Channel.CALL,
            summary="تماس تلفنی اول و هماهنگی بازدید پنت‌هاوس ۱۸۵ متری زعفرانیه؛ بودجه تا ۴۰ میلیارد تومان تأیید شد.",
            is_private=False,
        )
    FollowUpTask.objects.all_tenants().get_or_create(
        agency=agency_a,
        customer=buyer_cust,
        assigned_membership=mem_agent_a1,
        title="پیگیری نتیجه بازدید واحد زعفرانیه",
        defaults={"due_at": now + timedelta(hours=18)},
    )

    # 8. Properties (Published & Rich Architectural Media + Histories)
    sample_props = [
        {
            "code": "PN-1001",
            "branch": branch_a,
            "title": "پنت‌هاوس ۱۸۵ متری نوساز با تراس پانوراما در زعفرانیه",
            "ptype": apt_type,
            "dtype": sale_deal,
            "area": Decimal("185.00"),
            "beds": 3,
            "floor": 7,
            "floors": 8,
            "age": 1,
            "total": Decimal("38850000000"),
            "deposit": Decimal("0"),
            "rent": Decimal("0"),
            "city": "تهران",
            "district": "زعفرانیه",
            "neighborhood": "آصف",
            "addr": "خیابان آصف، کوچه بهار، پلاک ۱۴ واحد ۷",
            "lat": Decimal("35.804120"),
            "lng": Decimal("51.416530"),
            "status": Property.Status.PUBLISHED,
            "vis": Property.Visibility.PUBLIC_PORTAL,
            "feat": True,
            "img": "/images/hero-penthouse-tehran.jpg",
        },
        {
            "code": "PN-1002",
            "branch": branch_a,
            "title": "آپارتمان ۱۴۰ متری خوش‌نقشه در فرشته",
            "ptype": apt_type,
            "dtype": sale_deal,
            "area": Decimal("140.00"),
            "beds": 3,
            "floor": 4,
            "floors": 6,
            "age": 4,
            "total": Decimal("29400000000"),
            "deposit": Decimal("0"),
            "rent": Decimal("0"),
            "city": "تهران",
            "district": "فرشته",
            "neighborhood": "بوسنی هرزگوین",
            "addr": "خیابان مریم غربی، پلاک ۲۲",
            "lat": Decimal("35.792400"),
            "lng": Decimal("51.423900"),
            "status": Property.Status.PUBLISHED,
            "vis": Property.Visibility.PUBLIC_PORTAL,
            "feat": True,
            "img": "/images/prop-fereshteh.jpg",
        },
        {
            "code": "PN-1003",
            "branch": branch_a,
            "title": "واحد اداری مدرن ۱۱۰ متری در سعادت‌آباد",
            "ptype": office_type,
            "dtype": rent_deal,
            "area": Decimal("110.00"),
            "beds": 2,
            "floor": 5,
            "floors": 10,
            "age": 2,
            "total": Decimal("0"),
            "deposit": Decimal("1200000000"),
            "rent": Decimal("85000000"),
            "city": "تهران",
            "district": "سعادت‌آباد",
            "neighborhood": "کاج",
            "addr": "میدان کاج، سرو غربی، ساختمان نگین",
            "lat": Decimal("35.781200"),
            "lng": Decimal("51.375400"),
            "status": Property.Status.PUBLISHED,
            "vis": Property.Visibility.PUBLIC_PORTAL,
            "feat": False,
            "img": "/images/studio-agency-office.jpg",
        },
        {
            "code": "PN-1005",
            "branch": branch_a2,
            "title": "ویلای مدرن ۳۱۰ متری با نمای سنگ و حیاط مشجر در نیاوران",
            "ptype": villa_type,
            "dtype": sale_deal,
            "area": Decimal("310.00"),
            "beds": 4,
            "floor": 1,
            "floors": 2,
            "age": 2,
            "total": Decimal("65100000000"),
            "deposit": Decimal("0"),
            "rent": Decimal("0"),
            "city": "تهران",
            "district": "نیاوران",
            "neighborhood": "جماران",
            "addr": "نیاوران، خیابان جماران، کوچه سوم، پلاک ۸",
            "lat": Decimal("35.816500"),
            "lng": Decimal("51.459200"),
            "status": Property.Status.PUBLISHED,
            "vis": Property.Visibility.PUBLIC_PORTAL,
            "feat": True,
            "img": "/images/modern-villa-facade.jpg",
        },
        {
            "code": "PN-1004",
            "branch": branch_a2,
            "title": "ویلای دوبلکس ۴۲۰ متری در لواسان",
            "ptype": villa_type,
            "dtype": sale_deal,
            "area": Decimal("420.00"),
            "beds": 4,
            "floor": 1,
            "floors": 2,
            "age": 3,
            "total": Decimal("68000000000"),
            "deposit": Decimal("0"),
            "rent": Decimal("0"),
            "city": "تهران",
            "district": "لواسان",
            "neighborhood": "سبو بزرگ",
            "addr": "بلوار امام، کوچه سروستان پلاک ۵",
            "lat": Decimal("35.821100"),
            "lng": Decimal("51.630500"),
            "status": Property.Status.PENDING_APPROVAL,
            "vis": Property.Visibility.PRIVATE_AGENCY,
            "feat": False,
            "img": "/images/prop-villa.jpg",
        },
    ]

    created_props = []
    for item in sample_props:
        prop, is_new = Property.objects.all_tenants().get_or_create(
            agency=agency_a,
            property_code=item["code"],
            defaults={
                "branch": item["branch"],
                "title": item["title"],
                "description": "دارای سند تک‌برگ، نورگیری عالی، مشاعات کامل و آماده انتقال.",
                "property_type": item["ptype"],
                "deal_type": item["dtype"],
                "built_area_sqm": item["area"],
                "land_area_sqm": item["area"],
                "bedrooms": item["beds"],
                "bathrooms": 2,
                "floor_number": item["floor"],
                "total_floors": item["floors"],
                "building_age": item["age"],
                "total_price": item["total"],
                "deposit_amount": item["deposit"],
                "rent_amount": item["rent"],
                "status": item["status"],
                "visibility": item["vis"],
                "is_featured": item["feat"],
                "created_by": agent_a1,
            },
        )
        if is_new:
            prop.recalculate_price_per_sqm()
            prop.save()
            prop.amenities.set(
                [amenities["PARKING"], amenities["ELEVATOR"], amenities["STORAGE"]]
            )
            PropertyLocation.objects.create(
                property=prop,
                province="تهران",
                city=item["city"],
                district=item["district"],
                neighborhood=item["neighborhood"],
                full_address=item["addr"],
                latitude=item["lat"],
                longitude=item["lng"],
                hide_exact_address=True,
            )
            PropertyOwner.objects.create(property=prop, owner_customer=owner_cust)
            PropertyAgentAssignment.objects.create(
                property=prop,
                membership=mem_agent_a1 if item["branch"] == branch_a else mem_branch_mgr,
                role=PropertyAgentAssignment.Role.PRIMARY,
            )
            PropertyMedia.objects.create(
                property=prop,
                url=item["img"],
                title=item["title"],
                is_cover=True,
                is_public=True,
            )
        else:
            PropertyMedia.objects.filter(
                property=prop, url__startswith="/images/prop-", url__endswith=".svg"
            ).update(url=item["img"])
        created_props.append(prop)

    if not PropertyPriceHistory.objects.filter(property=created_props[0]).exists():
        PropertyPriceHistory.objects.create(
            property=created_props[0],
            previous_price=Decimal("39500000000"),
            new_price=created_props[0].total_price,
            currency_code="IRT",
            changed_by=mgr_a,
        )
    if not PropertyStatusHistory.objects.filter(property=created_props[0]).exists():
        PropertyStatusHistory.objects.create(
            property=created_props[0],
            from_status=Property.Status.PENDING_APPROVAL,
            to_status=Property.Status.PUBLISHED,
            reason="تأیید مدارک مالکیت و انتشار در پورتال عمومی",
            changed_by=mgr_a,
        )

    # 9. Viewing, Contract (+Parties/History), Deal, Commission, Accounting (+CostCenter), Payroll
    if not ViewingAppointment.objects.all_tenants().filter(agency=agency_a).exists():
        ViewingAppointment.schedule_safely(
            agency=agency_a,
            property=created_props[0],
            customer=buyer_cust,
            agent_membership=mem_agent_a1,
            scheduled_start=now + timedelta(days=1, hours=10),
            scheduled_end=now + timedelta(days=1, hours=11),
            status=ViewingAppointment.Status.CONFIRMED,
        )

    tpl, _ = ContractTemplate.objects.get_or_create(
        agency=agency_a,
        title="مبایعه‌نامه رسمی املاک مسکونی",
        defaults={
            "contract_type": Contract.ContractType.SALE,
            "body_template": "قرارداد فروش ملک {{property_title}} به مبلغ {{amount}}",
            "is_manager_verified": True,
        },
    )
    contract, _ = Contract.objects.all_tenants().get_or_create(
        agency=agency_a,
        contract_number="CNT-1405-001",
        defaults={
            "internal_tracking_code": "TRK-90124",
            "contract_type": Contract.ContractType.SALE,
            "property": created_props[1],
            "deal_type": sale_deal,
            "template": tpl,
            "amount": Decimal("29400000000"),
            "advance_payment": Decimal("5000000000"),
            "remaining_amount": Decimal("24400000000"),
            "start_date": now - timedelta(days=5),
            "status": Contract.Status.ACTIVE,
        },
    )
    if not ContractParty.objects.filter(contract=contract).exists():
        ContractParty.objects.create(
            contract=contract,
            customer=owner_cust,
            full_name=owner_cust.full_name,
            party_role=ContractParty.Role.OWNER,
            signed_at=now - timedelta(days=4),
        )
        ContractParty.objects.create(
            contract=contract,
            customer=buyer_cust,
            full_name=buyer_cust.full_name,
            party_role=ContractParty.Role.COUNTERPARTY,
            signed_at=now - timedelta(days=4),
        )
    if not ContractStatusHistory.objects.filter(contract=contract).exists():
        ContractStatusHistory.objects.create(
            contract=contract,
            from_status=Contract.Status.DRAFT,
            to_status=Contract.Status.ACTIVE,
            reason="تأیید و امضای طرفین معامله",
            changed_by=mgr_a,
        )

    deal, _ = Deal.objects.all_tenants().get_or_create(
        agency=agency_a,
        deal_code="DEAL-1405-001",
        defaults={
            "contract": contract,
            "property": created_props[1],
            "primary_agent": mem_agent_a1,
            "deal_value": Decimal("29400000000"),
            "status": Deal.Status.CLOSED_WON,
            "closed_at": now - timedelta(days=2),
        },
    )

    policy, _ = CommissionPolicy.objects.all_tenants().get_or_create(
        agency=agency_a, deal_type=sale_deal, name="تعرفه استاندارد فروش مسکونی"
    )
    policy_ver, _ = CommissionPolicyVersion.objects.get_or_create(
        policy=policy,
        version_number=1,
        defaults={
            "gross_rate_percent": Decimal("1.0000"),
            "tax_rate_percent": Decimal("10.0000"),
            "agency_house_percent": Decimal("50.0000"),
            "primary_agent_percent": Decimal("50.0000"),
        },
    )
    if not hasattr(deal, "commission"):
        calculate_deal_commission(deal=deal, policy_version=policy_ver, actor=mgr_a)

    fy, _ = FiscalYear.objects.all_tenants().get_or_create(
        agency=agency_a,
        title="سال مالی ۱۴۰۵",
        defaults={
            "start_date": now - timedelta(days=200),
            "end_date": now + timedelta(days=165),
        },
    )
    fp, _ = FiscalPeriod.objects.all_tenants().get_or_create(
        agency=agency_a,
        fiscal_year=fy,
        name="آبان ۱۴۰۵",
        defaults={"start_date": now - timedelta(days=15), "end_date": now + timedelta(days=15)},
    )
    cc_main, _ = CostCenter.objects.all_tenants().get_or_create(
        agency=agency_a, code="CC-ZAF", defaults={"name": "مرکز هزینه شعبه زعفرانیه"}
    )
    CostCenter.objects.all_tenants().get_or_create(
        agency=agency_a, code="CC-NIA", defaults={"name": "مرکز هزینه شعبه نیاوران"}
    )

    ar_acc, _ = ChartOfAccount.objects.all_tenants().get_or_create(
        agency=agency_a,
        code="1103",
        defaults={"name": "حساب‌های دریافتنی مشتریان", "account_type": "ASSET"},
    )
    rev_acc, _ = ChartOfAccount.objects.all_tenants().get_or_create(
        agency=agency_a,
        code="4101",
        defaults={"name": "درآمد کمیسیون معاملات", "account_type": "REVENUE"},
    )
    comm_pay_acc, _ = ChartOfAccount.objects.all_tenants().get_or_create(
        agency=agency_a,
        code="2104",
        defaults={"name": "کمیسیون پرداختنی مشاوران", "account_type": "LIABILITY"},
    )
    bank_coa, _ = ChartOfAccount.objects.all_tenants().get_or_create(
        agency=agency_a,
        code="1102",
        defaults={"name": "موجودی بانک‌ها", "account_type": "ASSET"},
    )

    if not JournalEntry.objects.all_tenants().filter(agency=agency_a, entry_number="JE-1405-001").exists():
        je = create_and_post_journal_entry(
            agency=agency_a,
            fiscal_period=fp,
            entry_number="JE-1405-001",
            description="شناسایی کمیسیون معامله DEAL-1405-001",
            lines=[
                {
                    "account": ar_acc,
                    "debit": Decimal("294000000"),
                    "credit": Decimal("0"),
                    "description": "طلب کمیسیون از طرفین معامله",
                },
                {
                    "account": rev_acc,
                    "debit": Decimal("0"),
                    "credit": Decimal("147000000"),
                    "description": "سهم درآمد آژانس (۵۰٪)",
                },
                {
                    "account": comm_pay_acc,
                    "debit": Decimal("0"),
                    "credit": Decimal("147000000"),
                    "description": "سهم پورسانت مشاور (۵۰٪)",
                },
            ],
            source_type="DEAL_COMMISSION",
            source_id=str(deal.id),
            actor=accountant_user,
        )
        JournalEntryLine.objects.filter(journal_entry=je, cost_center__isnull=True).update(
            cost_center=cc_main
        )

    BankAccount.objects.all_tenants().get_or_create(
        agency=agency_a,
        account_number="0105884290001",
        defaults={
            "bank_name": "بانک سامان شعبه زعفرانیه",
            "iban": "IR420560081180001058842901",
            "coa_account": bank_coa,
            "current_balance": Decimal("2450000000"),
        },
    )
    CashBox.objects.all_tenants().get_or_create(
        agency=agency_a,
        name="صندوق تنخواه شعبه مرکزی",
        defaults={"coa_account": bank_coa, "current_balance": Decimal("45000000")},
    )
    ChequeInstrument.objects.all_tenants().get_or_create(
        agency=agency_a,
        cheque_number="CHQ-845120",
        defaults={
            "direction": ChequeInstrument.Direction.RECEIVABLE,
            "bank_name": "بانک ملت",
            "due_date": now + timedelta(days=14),
            "amount": Decimal("294000000"),
            "deal": deal,
            "status": ChequeInstrument.Status.HELD,
        },
    )
    DealFinancialLedger.objects.all_tenants().get_or_create(
        agency=agency_a,
        deal=deal,
        defaults={
            "deal_amount": deal.deal_value,
            "total_received": Decimal("5000000000"),
            "gross_commission": Decimal("294000000"),
            "agency_share": Decimal("147000000"),
            "agents_share": Decimal("147000000"),
            "net_profit": Decimal("147000000"),
            "settlement_status": DealFinancialLedger.SettlementStatus.PARTIAL,
        },
    )

    # Employee, Compensation Plan & Payroll
    emp, _ = EmployeeProfile.objects.all_tenants().get_or_create(
        agency=agency_a,
        membership=mem_agent_a1,
        defaults={
            "employee_code": "EMP-101",
            "job_title": "مشاور ارشد فروش و املاک لوکس",
            "hire_date": (now - timedelta(days=365)).date(),
            "monthly_sales_target": Decimal("30000000000"),
        },
    )
    CompensationPlan.objects.all_tenants().get_or_create(
        agency=agency_a,
        employee=emp,
        effective_from=(now - timedelta(days=365)).date(),
        defaults={
            "model_type": CompensationPlan.ModelType.FIXED_PLUS_COMMISSION,
            "base_salary": Decimal("18000000"),
        },
    )

    cycle, cycle_new = PayrollCycle.objects.all_tenants().get_or_create(
        agency=agency_a,
        title="حقوق و پورسانت آبان ۱۴۰۵",
        defaults={
            "period_start": now - timedelta(days=30),
            "period_end": now,
            "status": PayrollCycle.Status.APPROVED,
        },
    )
    if cycle_new:
        ps = Payslip.objects.all_tenants().create(
            agency=agency_a,
            cycle=cycle,
            employee=emp,
            base_salary_amount=Decimal("18000000"),
            commission_amount=Decimal("147000000"),
            tax_amount=Decimal("8250000"),
            net_payable=Decimal("156750000"),
            status=Payslip.Status.APPROVED,
        )
        PayslipLineItem.objects.create(
            payslip=ps,
            item_type=PayslipLineItem.ItemType.BASE_SALARY,
            description="حقوق ثابت ماهانه",
            amount=Decimal("18000000"),
        )
        PayslipLineItem.objects.create(
            payslip=ps,
            item_type=PayslipLineItem.ItemType.COMMISSION,
            description="پورسانت معامله DEAL-1405-001",
            amount=Decimal("147000000"),
        )

    # 10. Leads, Negotiations, Documents, Payments, Cooperation, SavedSearch, Notifications & Audit
    if not Lead.objects.all_tenants().filter(agency=agency_a, phone_number="09127778899").exists():
        Lead.objects.all_tenants().create(
            agency=agency_a,
            phone_number="09127778899",
            full_name="مهندس کاوه تهرانی",
            request_type="BUY",
            property=created_props[0],
            source="PORTAL",
            assigned_membership=mem_agent_a1,
            status=Lead.Status.QUALIFIED,
            notes="متقاضی خرید پنت‌هاوس بالای ۱۸۰ متر در زعفرانیه",
        )
    if not Lead.objects.all_tenants().filter(agency=agency_a, phone_number="09126665544").exists():
        Lead.objects.all_tenants().create(
            agency=agency_a,
            phone_number="09126665544",
            full_name="سارا بهرامی",
            request_type="RENT",
            property=created_props[2],
            source="INSTAGRAM",
            assigned_membership=mem_agent_a1,
            status=Lead.Status.NEW,
            notes="درخواست بازدید دفتر کار سعادت‌آباد",
        )

    neg, neg_new = Negotiation.objects.all_tenants().get_or_create(
        agency=agency_a,
        property=created_props[0],
        customer=buyer_cust,
        defaults={
            "agent_membership": mem_agent_a1,
            "deal_type": sale_deal,
            "status": Negotiation.Status.COUNTER_OFFERED,
            "notes": "مذاکره قیمت و شرایط پرداخت دو مرحله‌ای",
        },
    )
    if neg_new:
        NegotiationOfferVersion.objects.create(
            negotiation=neg,
            version_number=1,
            offered_by=NegotiationOfferVersion.OfferedBy.BUYER,
            proposed_price=Decimal("36500000000"),
            status=NegotiationOfferVersion.Status.SUPERSEDED,
        )
        NegotiationOfferVersion.objects.create(
            negotiation=neg,
            version_number=2,
            offered_by=NegotiationOfferVersion.OfferedBy.SELLER,
            proposed_price=Decimal("37900000000"),
            status=NegotiationOfferVersion.Status.PENDING,
        )

    doc, doc_new = Document.objects.all_tenants().get_or_create(
        agency=agency_a,
        title="تصویر سند تک‌برگ ملک PN-1001",
        defaults={
            "category": "TITLE_DEED",
            "access_level": Document.AccessLevel.CONFIDENTIAL,
            "property": created_props[0],
            "created_by": mgr_a,
        },
    )
    if doc_new:
        DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_key="docs/pn-1001-deed-v1.pdf",
            mime_type="application/pdf",
            file_size_bytes=842100,
        )
    if not DocumentDownloadLog.objects.filter(document=doc).exists():
        DocumentDownloadLog.objects.create(document=doc, user=mgr_a, ip_address="127.0.0.1")

    SavedSearch.objects.get_or_create(
        user=customer_user,
        title="آپارتمان ۳ خواب زعفرانیه و فرشته",
        defaults={
            "filters_json": {
                "city": "تهران",
                "district": "زعفرانیه",
                "deal_type": "SALE",
                "min_bedrooms": 3,
            },
            "notify_on_match": True,
        },
    )

    sub = AgencySubscription.objects.filter(agency=agency_a).first()
    if sub and not PaymentGatewayTransaction.objects.filter(agency=agency_a).exists():
        PaymentGatewayTransaction.objects.create(
            agency=agency_a,
            subscription=sub,
            provider_key="sandbox",
            authority="AUTH-1405-0001",
            reference_id="REF-991042",
            amount=Decimal("45000000"),
            status=PaymentGatewayTransaction.Status.PAID,
        )

    AgencyCooperation.objects.get_or_create(
        requester_agency=agency_a,
        provider_agency=agency_b,
        defaults={
            "default_split_percent": Decimal("50.00"),
            "status": AgencyCooperation.Status.ACTIVE,
        },
    )

    if not NotificationMessage.objects.filter(recipient=mgr_a).exists():
        NotificationMessage.objects.create(
            recipient=mgr_a,
            agency=agency_a,
            channel=NotificationMessage.Channel.IN_APP,
            title="ثبت درخواست بازدید جدید",
            body="مشتری آرش صادقی برای بازدید پنت‌هاوس زعفرانیه (PN-1001) زمان‌بندی شد.",
            delivery_status=NotificationMessage.DeliveryStatus.DELIVERED,
        )
        NotificationMessage.objects.create(
            recipient=agent_a1,
            agency=agency_a,
            channel=NotificationMessage.Channel.IN_APP,
            title="تأیید پورسانت معامله DEAL-1405-001",
            body="سهم پورسانت شما در معامله فرشته محاسبه و در فیش حقوقی آبان ۱۴۰۵ لحاظ شد.",
            delivery_status=NotificationMessage.DeliveryStatus.DELIVERED,
        )

    if not AuditLog.objects.filter(agency_id=agency_a.id).exists():
        AuditLog.objects.create(
            agency_id=agency_a.id,
            actor=mgr_a,
            action="PLATFORM_BOOTSTRAPPED",
            resource_type="Agency",
            resource_id=str(agency_a.id),
            after_state={"status": "ACTIVE"},
        )

    # 11. Tickets (+Attachments), Complaints, Surveys, AI Assistant Logs
    CannedReply.objects.get_or_create(
        agency=agency_a,
        title="پیگیری وضعیت تایید فایل ملکی",
        defaults={
            "category": Ticket.Category.AGENCY_OPS,
            "body": "با سلام، فایل ثبت‌شده شما در صف بررسی مدیر آژانس قرار دارد و حداکثر ظرف ۲ ساعت آینده تایید و منتشر خواهد شد.",
        },
    )
    t1, t1_new = Ticket.objects.get_or_create(
        ticket_number="TKT-1405-1001",
        defaults={
            "scope": Ticket.Scope.AGENCY,
            "agency": agency_a,
            "created_by_user": agent_a1,
            "assigned_to_user": mgr_a,
            "category": Ticket.Category.AGENCY_OPS,
            "priority": Ticket.Priority.HIGH,
            "status": Ticket.Status.IN_PROGRESS,
            "subject": "درخواست تایید فوری آگهی پنت‌هاوس زعفرانیه",
            "sla_due_at": now + timedelta(hours=8),
        },
    )
    if t1_new:
        first_msg = TicketMessage.objects.create(
            ticket=t1,
            sender=agent_a1,
            body="مدارک مالکیت و تصاویر باکیفیت پنت‌هاوس زعفرانیه بارگذاری شد. لطفاً جهت انتشار در پورتال عمومی بررسی فرمایید.",
        )
        TicketAttachment.objects.create(
            message=first_msg,
            file_name="deed-scan-pn1001.pdf",
            file_url="/docs/pn-1001-deed-v1.pdf",
            mime_type="application/pdf",
            file_size_bytes=421000,
        )
        TicketMessage.objects.create(
            ticket=t1,
            sender=mgr_a,
            body="تاییدیه اولیه انجام شد و واحد حقوقی در حال تطبیق سند است.",
            is_internal_note=True,
        )
        TicketStatusHistory.objects.create(
            ticket=t1, from_status="", to_status=Ticket.Status.OPEN, changed_by=agent_a1
        )
        TicketStatusHistory.objects.create(
            ticket=t1,
            from_status=Ticket.Status.OPEN,
            to_status=Ticket.Status.IN_PROGRESS,
            changed_by=mgr_a,
        )

    c1, c1_new = Complaint.objects.get_or_create(
        tracking_code="CMP-1405-1001",
        defaults={
            "complainant_user": customer_user,
            "complainant_name": "آرش صادقی",
            "complainant_phone": "09124444444",
            "agency": agency_a,
            "target_type": Complaint.TargetType.AGENCY,
            "target_title": "شعبه مرکزی زعفرانیه",
            "subject": "تاخیر در ارسال پیش‌نویس مبایعه‌نامه",
            "description": "قرار بود نسخه اولیه مبایعه‌نامه روز گذشته ارسال شود اما تا این لحظه دریافت نشده است.",
            "is_confidential": False,
            "status": Complaint.Status.IN_PROGRESS,
            "assigned_to_user": mgr_a,
        },
    )
    if c1_new:
        ComplaintNote.objects.create(
            complaint=c1,
            author=mgr_a,
            note="با واحد قراردادها هماهنگ شد؛ نسخه نهایی تا عصر ارسال می‌شود.",
            is_confidential=True,
        )

    survey, s_new = Survey.objects.get_or_create(
        slug="agency-visit-feedback",
        defaults={
            "agency": agency_a,
            "title": "نظرسنجی ارزیابی کیفیت بازدید و مشاوره املاک",
            "description": "دیدگاه شما برای ارتقای کیفیت خدمات مشاوره و شفافیت اطلاعات املاک ارزشمند است.",
            "target_audience": Survey.TargetAudience.ALL,
            "crm_trigger_event": Survey.CrmTriggerEvent.VIEWING_COMPLETED,
            "is_active": True,
            "allow_anonymous": True,
        },
    )
    if s_new:
        q_stars = SurveyQuestion.objects.create(
            survey=survey,
            sort_order=1,
            question_text="رضایت کلی شما از کیفیت بازدید ملک چقدر بود؟",
            question_type=SurveyQuestion.QuestionType.STARS,
        )
        q_nps = SurveyQuestion.objects.create(
            survey=survey,
            sort_order=2,
            question_text="چقدر احتمال دارد بنیان ملک را به دوستان خود معرفی کنید؟ (۰ تا ۱۰)",
            question_type=SurveyQuestion.QuestionType.NPS,
        )
        q_yn = SurveyQuestion.objects.create(
            survey=survey,
            sort_order=3,
            question_text="آیا اطلاعات و تصاویر آگهی با واقعیت ملک مطابقت داشت؟",
            question_type=SurveyQuestion.QuestionType.YES_NO,
        )
        q_single = SurveyQuestion.objects.create(
            survey=survey,
            sort_order=4,
            question_text="کدام بخش از خدمات بیشترین ارزش را برای شما داشت؟",
            question_type=SurveyQuestion.QuestionType.SINGLE_SELECT,
            options=[
                "دقت اطلاعات ملک",
                "برخورد حرفه‌ای مشاور",
                "سرعت هماهنگی بازدید",
                "شفافیت قیمت",
            ],
        )
        q_text = SurveyQuestion.objects.create(
            survey=survey,
            sort_order=5,
            question_text="پیشنهاد یا نکته تکمیلی شما چیست؟",
            question_type=SurveyQuestion.QuestionType.TEXT,
            is_required=False,
        )
        resp = SurveyResponse.objects.create(
            survey=survey,
            respondent_user=customer_user,
            respondent_identifier=f"user:{customer_user.id}",
            respondent_name="آرش صادقی",
        )
        SurveyAnswer.objects.create(response=resp, question=q_stars, answer_number=Decimal("5"))
        SurveyAnswer.objects.create(response=resp, question=q_nps, answer_number=Decimal("9"))
        SurveyAnswer.objects.create(response=resp, question=q_yn, answer_text="YES")
        SurveyAnswer.objects.create(
            response=resp, question=q_single, selected_options=["برخورد حرفه‌ای مشاور"]
        )
        SurveyAnswer.objects.create(
            response=resp, question=q_text, answer_text="بسیار منظم و حرفه‌ای بود."
        )

    if not AiInteractionLog.objects.filter(agency=agency_a).exists():
        AiInteractionLog.objects.create(
            agency=agency_a,
            user=agent_a1,
            tool_type=AiInteractionLog.ToolType.PROPERTY_COPY,
            resource_type="Property",
            resource_id=str(created_props[0].id),
            prompt_summary="تولید متن معرفی استاندارد و سئو شده برای پنت‌هاوس ۱۸۵ متری زعفرانیه",
            draft_output={
                "headline": "پنت‌هاوس نوساز ۱۸۵ متری زعفرانیه با تراس پانوراما",
                "highlights": ["سند تک‌برگ", "۳ خواب مستر", "نورگیری دوطرفه شمالی-جنوبی"],
            },
        )

    # 12. CMS Categories, Articles, News, Redirects, FAQs, Jobs & Public Requests
    cat_market, _ = ContentCategory.objects.get_or_create(
        slug="market-analysis",
        defaults={
            "name": "تحلیل بازار مسکن",
            "description": "گزارش‌های دوره‌ای قیمت و روند معاملات مسکن",
            "sort_order": 1,
        },
    )
    cat_legal, _ = ContentCategory.objects.get_or_create(
        slug="legal-contracts",
        defaults={
            "name": "حقوقی و قراردادها",
            "description": "راهنمای تنظیم مبایعه‌نامه، اجاره‌نامه و قوانین کمیسیون",
            "sort_order": 2,
        },
    )
    cat_tech, _ = ContentCategory.objects.get_or_create(
        slug="proptech-guide",
        defaults={
            "name": "مدیریت هوشمند آژانس",
            "description": "راهکارهای CRM، حسابداری دوطرفه و تحول دیجیتال املاک",
            "sort_order": 3,
        },
    )
    author_chief, _ = AuthorProfile.objects.get_or_create(
        user=super_admin,
        defaults={
            "display_name": "دکتر سامان فرهادی",
            "role_title": "سردبیر و تحلیل‌گر ارشد اقتصاد مسکن",
            "bio": "پژوهشگر بازار املاک و سیستم‌های مدیریت آژانس‌های چندشعبه‌ای.",
        },
    )
    tag_tehran, _ = Tag.objects.get_or_create(
        slug="tehran-real-estate", defaults={"name": "بازار تهران"}
    )
    tag_crm, _ = Tag.objects.get_or_create(slug="agency-crm", defaults={"name": "CRM املاک"})

    cms_samples = [
        {
            "slug": "tehran-luxury-market-report-1405",
            "title": "تحلیل جامع روند قیمت آپارتمان‌های شمال تهران در نیمه دوم ۱۴۰۵",
            "article_type": Article.ArticleType.NEWS,
            "category": cat_market,
            "summary": "بررسی تغییرات میانگین قیمت هر متر مربع در مناطق زعفرانیه، فرشته و نیاوران و پیش‌بینی تقاضای فصلی خریداران.",
            "content_body": (
                "بازار مسکن مناطق شمالی تهران در سال ۱۴۰۵ شاهد افزایش تقاضا برای واحدهای نوساز با سند تک‌برگ و امکانات کامل مشاعات بوده است.\n\n"
                "داده‌های ثبت‌شده در پلتفرم بنیان ملک نشان می‌دهد شفافیت در نرخ کمیسیون، قیمت‌گذاری واقعی مبتنی بر معاملات قطعی و زمان‌بندی دقیق بازدیدها، "
                "میانگین زمان به نتیجه رسیدن مذاکرات را تا ۲۸ درصد کاهش داده است.\n\n"
                "برای آژانس‌های حرفه‌ای، تفکیک فایل‌های انحصاری و تطبیق خودکار نیازهای خریداران با موجودی فایل‌ها مهم‌ترین مزیت رقابتی محسوب می‌شود."
            ),
            "cover_image_url": "/images/hero-penthouse-tehran.jpg",
            "meta_title": "تحلیل قیمت مسکن شمال تهران ۱۴۰۵ | مجله بنیان ملک",
            "meta_description": "گزارش تحلیلی قیمت هر متر مربع و روند معاملات املاک در زعفرانیه و فرشته در نیمه دوم ۱۴۰۵.",
        },
        {
            "slug": "real-estate-contract-checklist",
            "title": "چک‌لیست ۱۲ گانه حقوقی پیش از امضای مبایعه‌نامه و اجاره‌نامه رسمی",
            "article_type": Article.ArticleType.ARTICLE,
            "category": cat_legal,
            "summary": "از استعلام اصالت سند و کد رهگیری تا بررسی نحوه پرداخت چک‌های بانکی و تعهدات تحویل ملک.",
            "content_body": (
                "تنظیم قرارداد دقیق و بدون ابهام، مهم‌ترین وظیفه حرفه‌ای یک آژانس املاک معتبر است.\n\n"
                "پیش از هرگونه امضا، مطابقت مشخصات هویتی مالک و سند رسمی، وضعیت رهن یا بازداشت احتمالی، تسویه عوارض شهرداری و مفاصاحساب دارایی باید در پرونده اسناد ثبت شود.\n\n"
                "در بنیان ملک، تمام قالب‌های قرارداد با نظارت مدیر آژانس استانداردسازی شده و هر نسخه از مذاکره قیمتی با تاریخچه کامل ذخیره می‌گردد."
            ),
            "cover_image_url": "/images/modern-villa-facade.jpg",
            "meta_title": "چک‌لیست حقوقی مبایعه‌نامه و اجاره‌نامه | بنیان ملک",
            "meta_description": "راهنمای کامل بررسی اسناد، چک‌ها و بندهای کلیدی پیش از امضای قرارداد ملکی.",
        },
        {
            "slug": "double-entry-accounting-for-agencies",
            "title": "چرا آژانس‌های املاک چندشعبه‌ای به حسابداری دوطرفه و تقسیم خودکار کمیسیون نیاز دارند؟",
            "article_type": Article.ArticleType.ARTICLE,
            "category": cat_tech,
            "summary": "مدیریت شفاف سهم مشاور اول، مشاور همکار، مالیات بر ارزش افزوده و خزانه‌داری چک‌ها در یک دفتر کل یکپارچه.",
            "content_body": (
                "خطاهای محاسباتی در تقسیم پورسانت معاملات مشارکتی و عدم تطبیق چک‌های دریافتنی با اسناد حسابداری، بزرگ‌ترین چالش مالی آژانس‌های در حال رشد است.\n\n"
                "با بهره‌گیری از موتور حسابداری دوطرفه، هم‌زمان با تایید کمیسیون یک معامله، سند حسابداری متوازن با سهم دقیق آژانس و مشاوران صادر می‌شود و در پایان ماه مستقیم به فیش حقوقی منتقل می‌گردد."
            ),
            "cover_image_url": "/images/studio-agency-office.jpg",
            "meta_title": "حسابداری دوطرفه و کمیسیون در آژانس املاک | بنیان ملک",
            "meta_description": "آشنایی با استانداردهای حسابداری دوبل، خزانه‌داری چک و تسویه شفاف کمیسیون مشاوران املاک.",
        },
    ]

    for item in cms_samples:
        art, art_new = Article.objects.get_or_create(
            slug=item["slug"],
            defaults={
                "title": item["title"],
                "article_type": item["article_type"],
                "category": item["category"],
                "author": author_chief,
                "summary": item["summary"],
                "content_body": item["content_body"],
                "cover_image_url": item["cover_image_url"],
                "status": Article.Status.PUBLISHED,
                "published_at": now - timedelta(days=3),
                "meta_title": item["meta_title"],
                "meta_description": item["meta_description"],
                "reading_time_minutes": 4,
                "created_by": super_admin,
            },
        )
        if art_new:
            art.tags.add(tag_tehran, tag_crm)
            ContentVersion.objects.create(
                article=art,
                version_number=1,
                title=art.title,
                content_body=art.content_body,
                edited_by=super_admin,
                change_note="انتشار نسخه اولیه در پورتال",
            )

    RedirectRule.objects.get_or_create(
        from_path="/listings",
        defaults={"to_path": "/properties", "status_code": 301, "is_active": True},
    )

    faq_samples = [
        (
            "عمومی و ثبت آگهی",
            "آیا تمام املاک منتشرشده در پورتال عمومی بنیان ملک دارای مالکیت احراز‌شده هستند؟",
            "بله؛ پیش از انتشار عمومی هر ملک، مشخصات سند و فایل توسط مدیر آژانس بررسی و تایید می‌شود و آدرس دقیق تا پیش از هماهنگی بازدید محافظت می‌گردد.",
            1,
        ),
        (
            "آژانس‌ها و اشتراک",
            "چگونه آژانس املاک خود را در شبکه بنیان ملک ثبت کنیم؟",
            "از طریق صفحه درخواست همکاری آژانس (/agency-application) اطلاعات دفتر و پروانه کسب را ثبت کنید تا پس از تایید بازرسی پلتفرم، پنل اختصاصی آژانس شما فعال شود.",
            2,
        ),
        (
            "کمیسیون و مالی",
            "محاسبه سهم مشاور اول، همکار و حسابداری چگونه انجام می‌شود؟",
            "مدیر آژانس سیاست‌های نسخه‌دار کمیسیون را تعریف می‌کند؛ پس از بسته‌شدن معامله، سهم‌ها با دقت اعشاری محاسبه و سند حسابداری دوطرفه صادر می‌شود.",
            3,
        ),
        (
            "پشتیبانی و پیگیری",
            "چگونه می‌توانم وضعیت درخواست یا شکایت ثبت‌شده خود را پیگیری کنم؟",
            "با داشتن کد رهگیری (REQ-... یا CMP-...) و شماره موبایل ثبت‌شده، از بخش پیگیری درخواست (/requests/track) یا پیگیری شکایت (/complaints/track) آخرین وضعیت را مشاهده کنید.",
            4,
        ),
    ]
    for cat_name, q_txt, a_txt, order in faq_samples:
        FaqItem.objects.get_or_create(
            question=q_txt,
            defaults={"category": cat_name, "answer": a_txt, "sort_order": order, "is_active": True},
        )

    job_samples = [
        (
            "مهندس ارشد بک‌اند (Django & FastAPI)",
            "فنی و زیرساخت",
            "تهران / هیبرید",
            "تمام‌وقت",
            "توسعه ماژول‌های مالی، معماری چندمستاجری و بهینه‌سازی کوئری‌های جستجو.",
        ),
        (
            "کارشناس محصول و تحلیل کسب‌وکار املاک",
            "محصول",
            "تهران",
            "تمام‌وقت",
            "طراحی جریان‌های کار آژانس‌های بزرگ و استانداردسازی فرایندهای CRM و قرارداد.",
        ),
        (
            "کارشناس ارشد موفقیت مشتریان سازمانی",
            "عملیات و پشتیبانی",
            "تهران / ریموت",
            "تمام‌وقت",
            "آموزش و استقرار آژانس‌های جدید، مدیریت SLA تیکت‌ها و پایش شاخص رضایت NPS.",
        ),
    ]
    for j_title, dept, loc, emp_t, desc in job_samples:
        JobOpening.objects.get_or_create(
            title=j_title,
            defaults={
                "department": dept,
                "location": loc,
                "employment_type": emp_t,
                "description": desc,
                "is_active": True,
            },
        )

    ContactInquiry.objects.get_or_create(
        tracking_code="REQ-1405-1001",
        defaults={
            "full_name": "مهندس سهراب رضایی",
            "phone_number": "09123004050",
            "inquiry_type": ContactInquiry.InquiryType.ENTERPRISE_DEMO,
            "subject": "درخواست دموی سازمانی برای ۳ شعبه در تهران",
            "message": "مایل به راه‌اندازی پنل یکپارچه برای ۳۰ مشاور و ۳ شعبه هستیم.",
            "status": ContactInquiry.Status.IN_PROGRESS,
            "staff_response": "جلسه دموی آنلاین برای روز سه‌شنبه ساعت ۱۱ هماهنگ شد.",
        },
    )
    AgencyCooperationRequest.objects.get_or_create(
        tracking_code="COOP-1405-1001",
        defaults={
            "agency_name": "املاک بزرگ الهیه",
            "city": "تهران",
            "manager_name": "بهرام کاظمی",
            "manager_phone": "09125006070",
            "agents_count": 18,
            "license_number": "LIC-TEH-4421",
            "notes": "متخصص املاک مسکونی و اداری منطقه ۱ تهران",
            "status": AgencyCooperationRequest.Status.UNDER_REVIEW,
        },
    )

    counts = collect_domain_model_counts()
    empty_models = [name for name, cnt in counts.items() if cnt == 0]
    _log(f"Seeded {len(counts)} domain models ({len(counts) - len(empty_models)} populated, {len(empty_models)} empty).")
    if verify_all and empty_models:
        raise RuntimeError(f"Empty domain models detected after seed_all: {empty_models}")
    return {"counts": counts, "empty_models": empty_models}

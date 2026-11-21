import os
import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Any, Callable, Optional
from django.apps import apps as dj_apps
from django.conf import settings
from django.core.management.base import CommandError
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
    LegalAcceptanceRecord,
    LegalDocument,
    LegalDocumentVersion,
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
from apps.negotiations.models import Negotiation, NegotiationActivity, NegotiationOfferVersion
from apps.notifications.models import (
    NotificationMessage,
    NotificationPreference,
    PushSubscription,
    SmsDeliveryLog,
    SmsTemplate,
)
from apps.payments.models import PaymentGatewayTransaction
from apps.payroll.models import PayrollCycle, Payslip, PayslipLineItem
from apps.properties.models import (
    Amenity,
    AmenityCategory,
    DealType,
    Property,
    PropertyAgentAssignment,
    PropertyAmenityValue,
    PropertyLocation,
    PropertyOwner,
    PropertyPriceHistory,
    PropertyStatusHistory,
    PropertyType,
    PropertyVerification,
    PropertyVerificationHistory,
    PropertyViolationReport,
)
from apps.property_media.models import PropertyMedia
from apps.reports.models import DashboardLayout, ImportJob, OnboardingProgress
from apps.search.models import SavedSearch, SavedView
from apps.settings.models import (
    BrandMediaSlot,
    CalendarSystem,
    City,
    Country,
    Currency,
    District,
    ExchangeRate,
    ExchangeRateHistory,
    Neighborhood,
    PlatformSetting,
    ProviderConfiguration,
    Province,
    SiteContentBlock,
    SystemSetting,
    SystemSettingHistory,
)
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


DEMO_PHONES = [
    "09120000001",
    "09121111111",
    "09123333333",
    "09125555555",
    "09122222222",
    "09126666666",
    "09124444444",
    "09127777777",
    "09128888888",
]

DEMO_AGENCY_SLUGS = ["pars-negin", "arya-home"]


def assert_non_production_environment() -> None:
    env_name = os.environ.get("DJANGO_ENV", os.environ.get("ENV", "")).strip().lower()
    settings_mod = os.environ.get("DJANGO_SETTINGS_MODULE", "").strip().lower()
    if env_name == "production" or settings_mod.endswith("production"):
        raise CommandError("اجرای دستورات داده آزمایشی در محیط Production مجاز نیست.")


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
    assert_non_production_environment()
    now = timezone.now()

    def _log(msg: str) -> None:
        if log_fn:
            log_fn(msg)

    # 1. Calendars, Countries, Currencies, FX Rates & Platform Settings
    CalendarSystem.objects.update_or_create(
        code="jalali",
        defaults={
            "name_fa": "تقویم هجری شمسی (جلالی)",
            "name_en": "Jalali (Solar Hijri)",
            "date_format": "YYYY/MM/DD",
            "datetime_format": "YYYY/MM/DD HH:mm",
            "is_default": True,
            "is_active": True,
            "sort_order": 1,
        },
    )
    CalendarSystem.objects.update_or_create(
        code="gregorian",
        defaults={
            "name_fa": "تقویم میلادی (Gregorian)",
            "name_en": "Gregorian",
            "date_format": "YYYY-MM-DD",
            "datetime_format": "YYYY-MM-DD HH:mm",
            "is_default": False,
            "is_active": True,
            "sort_order": 2,
        },
    )

    Country.objects.update_or_create(
        code="IR",
        defaults={
            "alpha3_code": "IRN",
            "name_fa": "ایران",
            "name_en": "Iran",
            "default_currency_code": "IRT",
            "default_calendar": "jalali",
            "supported_calendars": ["jalali", "gregorian"],
            "default_language": "fa",
            "supported_languages": ["fa", "en"],
            "default_timezone": "Asia/Tehran",
            "phone_prefix": "+98",
            "sort_order": 1,
            "is_active": True,
        },
    )
    Country.objects.update_or_create(
        code="AE",
        defaults={
            "alpha3_code": "ARE",
            "name_fa": "امارات متحده عربی",
            "name_en": "United Arab Emirates",
            "default_currency_code": "AED",
            "default_calendar": "gregorian",
            "supported_calendars": ["gregorian", "jalali"],
            "default_language": "en",
            "supported_languages": ["en", "ar", "fa"],
            "default_timezone": "Asia/Dubai",
            "phone_prefix": "+971",
            "sort_order": 2,
            "is_active": True,
        },
    )

    currency_map = {}
    for code, nfa, nen, sym, dp, minor, desc, factor, sord in [
        ("IRT", "تومان", "Iranian Toman", "تومان", 0, "ريال", "واحد پول رایج معاملات ملکی ایران", Decimal("10.000000"), 1),
        ("IRR", "ریال", "Iranian Rial", "ریال", 0, "", "واحد پایه درگاه‌های پرداخت بانکی ایران", Decimal("1.000000"), 2),
        ("USD", "دلار آمریکا", "US Dollar", "$", 2, "سنت", "ارز مرجع بین‌المللی معاملات", Decimal("650000.000000"), 3),
        ("EUR", "یورو", "Euro", "€", 2, "سنت", "ارز رسمی اتحادیه اروپا", Decimal("705000.000000"), 4),
        ("AED", "درهم امارات", "UAE Dirham", "AED", 2, "فلس", "واحد پول امارات متحده عربی", Decimal("177000.000000"), 5),
    ]:
        cur_obj, _ = Currency.objects.update_or_create(
            code=code,
            defaults={
                "name_fa": nfa,
                "name_en": nen,
                "symbol": sym,
                "decimal_places": dp,
                "minor_unit": minor,
                "description": desc,
                "base_unit_factor": factor,
                "sort_order": sord,
                "is_active": True,
            },
        )
        currency_map[code] = cur_obj

    fx_pairs = [
        ("IRT", "IRR", Decimal("10.000000"), "CENTRAL_BANK"),
        ("IRR", "IRT", Decimal("0.100000"), "CENTRAL_BANK"),
        ("USD", "IRT", Decimal("65000.000000"), "MARKET_REF"),
        ("IRT", "USD", Decimal("0.000015"), "MARKET_REF"),
        ("AED", "IRT", Decimal("17700.000000"), "MARKET_REF"),
        ("IRT", "AED", Decimal("0.000056"), "MARKET_REF"),
        ("EUR", "IRT", Decimal("70500.000000"), "MARKET_REF"),
        ("USD", "AED", Decimal("3.672500"), "FIXED_PEG"),
    ]
    for b_code, q_code, r_val, src in fx_pairs:
        ExchangeRate.objects.get_or_create(
            base_currency=currency_map[b_code],
            quote_currency=currency_map[q_code],
            defaults={"rate": r_val, "effective_at": now, "source": src, "is_active": True},
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

    # 1.5 Hierarchical Geography (Province -> City -> District -> Neighborhood)
    prov_tehran, _ = Province.objects.get_or_create(
        country_id="IR",
        name_fa="تهران",
        defaults={"code": "TEH", "name_en": "Tehran", "slug": "prov-tehran", "center_lat": Decimal("35.689200"), "center_lng": Decimal("51.389000"), "sort_order": 1},
    )
    prov_alborz, _ = Province.objects.get_or_create(
        country_id="IR",
        name_fa="البرز",
        defaults={"code": "ALB", "name_en": "Alborz", "slug": "prov-alborz", "center_lat": Decimal("35.832700"), "center_lng": Decimal("50.991500"), "sort_order": 2},
    )
    prov_isfahan, _ = Province.objects.get_or_create(
        country_id="IR",
        name_fa="اصفهان",
        defaults={"code": "ISF", "name_en": "Isfahan", "slug": "prov-isfahan", "center_lat": Decimal("32.653900"), "center_lng": Decimal("51.666000"), "sort_order": 3},
    )
    prov_fars, _ = Province.objects.get_or_create(
        country_id="IR",
        name_fa="فارس",
        defaults={"code": "FRS", "name_en": "Fars", "slug": "prov-fars", "center_lat": Decimal("29.591800"), "center_lng": Decimal("52.583700"), "sort_order": 4},
    )
    prov_khorasan, _ = Province.objects.get_or_create(
        country_id="IR",
        name_fa="خراسان رضوی",
        defaults={"code": "KHR", "name_en": "Razavi Khorasan", "slug": "prov-khorasan", "center_lat": Decimal("36.297200"), "center_lng": Decimal("59.606700"), "sort_order": 5},
    )
    prov_mazandaran, _ = Province.objects.get_or_create(
        country_id="IR",
        name_fa="مازندران",
        defaults={"code": "MZN", "name_en": "Mazandaran", "slug": "prov-mazandaran", "center_lat": Decimal("36.565900"), "center_lng": Decimal("53.058600"), "sort_order": 6},
    )

    city_tehran, _ = City.objects.get_or_create(
        province=prov_tehran,
        name_fa="تهران",
        defaults={"name_en": "Tehran", "slug": "city-tehran", "center_lat": Decimal("35.757500"), "center_lng": Decimal("51.410000"), "sort_order": 1},
    )
    city_lavasan, _ = City.objects.get_or_create(
        province=prov_tehran,
        name_fa="لواسان",
        defaults={"name_en": "Lavasan", "slug": "city-lavasan", "center_lat": Decimal("35.821100"), "center_lng": Decimal("51.630500"), "sort_order": 2},
    )
    city_karaj, _ = City.objects.get_or_create(
        province=prov_alborz,
        name_fa="کرج",
        defaults={"name_en": "Karaj", "slug": "city-karaj", "center_lat": Decimal("35.832700"), "center_lng": Decimal("50.991500"), "sort_order": 1},
    )
    city_isfahan, _ = City.objects.get_or_create(
        province=prov_isfahan,
        name_fa="اصفهان",
        defaults={"name_en": "Isfahan", "slug": "city-isfahan", "center_lat": Decimal("32.653900"), "center_lng": Decimal("51.666000"), "sort_order": 1},
    )
    city_shiraz, _ = City.objects.get_or_create(
        province=prov_fars,
        name_fa="شیراز",
        defaults={"name_en": "Shiraz", "slug": "city-shiraz", "center_lat": Decimal("29.591800"), "center_lng": Decimal("52.583700"), "sort_order": 1},
    )
    city_mashhad, _ = City.objects.get_or_create(
        province=prov_khorasan,
        name_fa="مشهد",
        defaults={"name_en": "Mashhad", "slug": "city-mashhad", "center_lat": Decimal("36.297200"), "center_lng": Decimal("59.606700"), "sort_order": 1},
    )
    city_sari, _ = City.objects.get_or_create(
        province=prov_mazandaran,
        name_fa="نوشهر",
        defaults={"name_en": "Nowshahr", "slug": "city-nowshahr", "center_lat": Decimal("36.649000"), "center_lng": Decimal("51.496200"), "sort_order": 1},
    )

    district_defs = [
        (city_tehran, "زعفرانیه", "Zafaranieh", Decimal("35.804120"), Decimal("51.416530"), 1, [("آصف", "Asef"), ("مقدس اردبیلی", "Moghaddas Ardabili"), ("ماکویی‌پور", "Makouipour")]),
        (city_tehran, "فرشته", "Fereshteh", Decimal("35.792400"), Decimal("51.423900"), 2, [("بوسنی هرزگوین", "Bosnia"), ("مریم غربی", "Maryam Gharbi"), ("چناران", "Chenaran")]),
        (city_tehran, "نیاوران", "Niavaran", Decimal("35.816500"), Decimal("51.459200"), 3, [("جماران", "Jamaran"), ("کاشانک", "Kashanak"), ("صاحبقرانیه", "Sahebgharanieh")]),
        (city_tehran, "سعادت‌آباد", "Saadat Abad", Decimal("35.781200"), Decimal("51.375400"), 4, [("کاج", "Kaj"), ("صرافها", "Sarrafha"), ("علامه", "Allameh")]),
        (city_tehran, "الهیه", "Elahieh", Decimal("35.790100"), Decimal("51.428500"), 5, [("مریم شرقی", "Maryam Sharghi"), ("تختی", "Takhti")]),
        (city_tehran, "ولنجک", "Velenjak", Decimal("35.807200"), Decimal("51.400500"), 6, [("بلوار دانشجو", "Daneshjoo"), ("ساسان", "Sasan")]),
        (city_tehran, "شهرک غرب", "Shahrak Gharb", Decimal("35.758000"), Decimal("51.372000"), 7, [("فاز یک", "Phase 1"), ("دادمان", "Dadman")]),
        (city_tehran, "لواسان", "Lavasan", Decimal("35.821100"), Decimal("51.630500"), 8, [("سبو بزرگ", "Saboo"), ("گلندوک", "Golandook")]),
        (city_karaj, "مهرشهر", "Mehrshahr", Decimal("35.802000"), Decimal("50.913000"), 1, [("بلوار ارم", "Eram"), ("فاز دو", "Phase 2")]),
        (city_isfahan, "مرداویج", "Mardavij", Decimal("32.628500"), Decimal("51.662000"), 1, [("شیخ کلینی", "Sheikh Koleini")]),
        (city_shiraz, "معالی‌آباد", "Maali Abad", Decimal("29.669000"), Decimal("52.473000"), 1, [("دوستاران", "Doostaran")]),
        (city_mashhad, "وکیل‌آباد", "Vakil Abad", Decimal("36.322000"), Decimal("59.495000"), 1, [("هاشمیه", "Hashemieh")]),
    ]
    geo_districts: dict[str, District] = {}
    geo_neighborhoods: dict[str, Neighborhood] = {}
    for city_obj, d_fa, d_en, d_lat, d_lng, d_ord, nbrs in district_defs:
        dist_obj, _ = District.objects.get_or_create(
            city=city_obj,
            name_fa=d_fa,
            defaults={
                "name_en": d_en,
                "slug": f"dist-{d_en.lower().replace(' ', '-')}",
                "center_lat": d_lat,
                "center_lng": d_lng,
                "sort_order": d_ord,
            },
        )
        geo_districts[d_fa] = dist_obj
        for n_idx, (n_fa, n_en) in enumerate(nbrs, start=1):
            nbr_obj, _ = Neighborhood.objects.get_or_create(
                district=dist_obj,
                name_fa=n_fa,
                defaults={
                    "name_en": n_en,
                    "slug": f"nbr-{n_en.lower().replace(' ', '-')}",
                    "center_lat": d_lat,
                    "center_lng": d_lng,
                    "sort_order": n_idx,
                },
            )
            geo_neighborhoods[f"{d_fa}:{n_fa}"] = nbr_obj

    # 2. Catalog Types & Categorized Extensible Amenities
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

    cat_defs = [
        ("GENERAL_BUILDING", "امکانات عمومی ساختمان", "Building Essentials", "building", 1),
        ("INTERIOR_LUXURY", "امکانات داخلی واحد", "Interior & Finishes", "sparkles", 2),
        ("WELFARE_RECREATION", "امکانات رفاهی و مشاعات", "Welfare & Recreation", "waves", 3),
        ("SECURITY_SAFETY", "امکانات امنیتی و ایمنی", "Security & Safety", "shield", 4),
        ("ACCESS_PARKING", "پارکینگ و دسترسی", "Parking & Access", "car", 5),
        ("SMART_TECH", "تجهیزات هوشمند و فنی", "Smart & Technical", "cpu", 6),
        ("SPECIAL_FEATURES", "ویژگی‌های شاخص ملک", "Special Features", "star", 7),
    ]
    amenity_cats = {}
    for code, nfa, nen, icon, ord_no in cat_defs:
        cat_obj, _ = AmenityCategory.objects.update_or_create(
            code=code,
            defaults={"name_fa": nfa, "name_en": nen, "icon_name": icon, "sort_order": ord_no, "is_active": True},
        )
        amenity_cats[code] = cat_obj

    amenities_data = [
        ("ELEVATOR", "GENERAL_BUILDING", "آسانسور", "Elevator", Amenity.ValueType.INTEGER, "لاین", [], 1),
        ("STORAGE", "GENERAL_BUILDING", "انباری سندی", "Storage", Amenity.ValueType.BOOLEAN, "", [], 2),
        ("BALCONY", "GENERAL_BUILDING", "تراس / بالکن قابل چیدمان", "Balcony", Amenity.ValueType.INTEGER, "عدد", [], 3),
        ("LOBBY", "GENERAL_BUILDING", "لابی مجلل", "Lobby", Amenity.ValueType.BOOLEAN, "", [], 4),
        ("LOBBY_CONCIERGE", "GENERAL_BUILDING", "لابی‌من ۲۴ ساعته", "24/7 Concierge", Amenity.ValueType.BOOLEAN, "", [], 5),
        ("MEETING_HALL", "GENERAL_BUILDING", "سالن اجتماعات", "Meeting Hall", Amenity.ValueType.BOOLEAN, "", [], 6),
        ("HEATING_SYSTEM", "INTERIOR_LUXURY", "سیستم گرمایش", "Heating System", Amenity.ValueType.CHOICE, "", ["داکت اسپلیت", "چیلر مرکزی", "شوفاژ پکیج", "گرمایش از کف"], 10),
        ("COOLING_SYSTEM", "INTERIOR_LUXURY", "سیستم سرمایش", "Cooling System", Amenity.ValueType.CHOICE, "", ["چیلر مرکزی", "داکت اسپلیت", "اسپلیت", "کولر آبی"], 11),
        ("KITCHEN_CABINETS", "INTERIOR_LUXURY", "کابینت آشپزخانه", "Cabinets", Amenity.ValueType.CHOICE, "", ["ممبران کلاسیک", "های‌گلاس", "انزو", "چوب طبیعی"], 12),
        ("MASTER_BEDROOM", "INTERIOR_LUXURY", "اتاق خواب مستر", "Master Suite", Amenity.ValueType.INTEGER, "خواب", [], 13),
        ("LAUNDRY_ROOM", "INTERIOR_LUXURY", "لاندری روم", "Laundry Room", Amenity.ValueType.BOOLEAN, "", [], 14),
        ("FIREPLACE", "INTERIOR_LUXURY", "شومینه", "Fireplace", Amenity.ValueType.BOOLEAN, "", [], 15),
        ("POOL", "WELFARE_RECREATION", "استخر، سونا و جکوزی", "Pool & Spa", Amenity.ValueType.BOOLEAN, "", [], 20),
        ("GYM", "WELFARE_RECREATION", "باشگاه بدنسازی اختصاصی", "Gym", Amenity.ValueType.BOOLEAN, "", [], 21),
        ("ROOF_GARDEN", "WELFARE_RECREATION", "روف‌گاردن چهارفصل", "Roof Garden", Amenity.ValueType.BOOLEAN, "", [], 22),
        ("GAME_ROOM", "WELFARE_RECREATION", "سالن بازی و بیلیارد", "Game Room", Amenity.ValueType.BOOLEAN, "", [], 23),
        ("CCTV", "SECURITY_SAFETY", "دوربین مداربسته", "CCTV", Amenity.ValueType.BOOLEAN, "", [], 30),
        ("SECURITY_GUARD", "SECURITY_SAFETY", "نگهبانی ۲۴ ساعته", "24/7 Guard", Amenity.ValueType.BOOLEAN, "", [], 31),
        ("ARMORED_DOOR", "SECURITY_SAFETY", "درب ضد سرقت", "Armored Door", Amenity.ValueType.BOOLEAN, "", [], 32),
        ("FIRE_ALARM", "SECURITY_SAFETY", "سیستم اعلام و اطفای حریق", "Fire Suppression", Amenity.ValueType.BOOLEAN, "", [], 33),
        ("PARKING", "ACCESS_PARKING", "پارکینگ سندی مسقف", "Covered Parking", Amenity.ValueType.INTEGER, "واحد", [], 40),
        ("EV_CHARGER", "ACCESS_PARKING", "شارژر خودروی برقی", "EV Charger", Amenity.ValueType.BOOLEAN, "", [], 41),
        ("HIGHWAY_ACCESS", "ACCESS_PARKING", "دسترسی سریع به اتوبان", "Highway Access", Amenity.ValueType.BOOLEAN, "", [], 42),
        ("SMART_HOME", "SMART_TECH", "سیستم خانه هوشمند (BMS)", "Smart Home BMS", Amenity.ValueType.BOOLEAN, "", [], 50),
        ("CENTRAL_VACUUM", "SMART_TECH", "جاروبرقی مرکزی", "Central Vacuum", Amenity.ValueType.BOOLEAN, "", [], 51),
        ("POWER_GENERATOR", "SMART_TECH", "ژنراتور برق اضطراری", "Backup Generator", Amenity.ValueType.BOOLEAN, "", [], 52),
        ("PANORAMIC_VIEW", "SPECIAL_FEATURES", "ویو ابدی شهر / کوهستان", "Panoramic View", Amenity.ValueType.BOOLEAN, "", [], 60),
        ("CORNER_TWO_SIDED", "SPECIAL_FEATURES", "نورگیری دوطرفه (نبش)", "Two-Sided Light", Amenity.ValueType.BOOLEAN, "", [], 61),
    ]
    amenities = {}
    for code, cat_code, nfa, nen, vtype, unit_lbl, opts, sort_ord in amenities_data:
        obj, _ = Amenity.objects.update_or_create(
            code=code,
            defaults={
                "category": amenity_cats[cat_code],
                "name_fa": nfa,
                "name_en": nen,
                "value_type": vtype,
                "unit_label": unit_lbl,
                "options_json": opts,
                "sort_order": sort_ord,
                "is_active": True,
            },
        )
        amenities[code] = obj

    # 3. Permissions & System Roles (All 7 Agency/Platform Staff & Customer Roles)
    perm_codes = [
        ("agency.manage_policy", "agencies", "مدیریت سیاست‌های دسترسی آژانس"),
        ("agency.manage_branches", "agencies", "مدیریت شعب آژانس"),
        ("property.create", "properties", "ثبت فایل ملک جدید"),
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
    sales_mgr_role, _ = Role.objects.get_or_create(
        code="SALES_MANAGER",
        agency=None,
        defaults={"name": "مدیر فروش", "scope": Role.Scope.AGENCY, "is_system_role": True},
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
    support_role, _ = Role.objects.get_or_create(
        code="SUPPORT_AGENT",
        agency=None,
        defaults={"name": "پشتیبان", "scope": Role.Scope.AGENCY, "is_system_role": True},
    )

    for p in Permission.objects.all():
        RolePermission.objects.get_or_create(role=mgr_role, permission=p)

    for p in Permission.objects.filter(
        code__in=[
            "agency.manage_branches",
            "property.create",
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
            "property.create",
            "property.view_all_agency",
            "property.edit_all_agency",
            "property.publish",
            "customer.view_all_agency",
            "customer.edit_all_agency",
            "customer.share",
            "appointment.view_all_agency",
            "deal.view_all_agency",
            "commission.view_all_agency",
        ]
    ):
        RolePermission.objects.get_or_create(role=sales_mgr_role, permission=p)

    for p in Permission.objects.filter(code__in=["property.create"]):
        RolePermission.objects.get_or_create(role=agent_role, permission=p)

    for p in Permission.objects.filter(
        code__in=[
            "accounting.view",
            "accounting.post",
            "commission.view_all_agency",
            "deal.view_all_agency",
        ]
    ):
        RolePermission.objects.get_or_create(role=acct_role, permission=p)

    for p in Permission.objects.filter(
        code__in=["customer.view_all_agency", "appointment.view_all_agency"]
    ):
        RolePermission.objects.get_or_create(role=support_role, permission=p)

    # 4. All 9 Platform, Agency & Customer Demo Accounts
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
    sales_mgr = _ensure_user(
        phone_number="09127777777",
        password="Sales@12345",
        first_name="مهدی",
        last_name="اکبری",
        email="sales@parsnegin.ir",
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
    support_user = _ensure_user(
        phone_number="09128888888",
        password="Support@12345",
        first_name="زهرا",
        last_name="محمدی",
        email="support@parsnegin.ir",
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
        (sales_mgr, "Sales Cockpit — Chrome"),
        (accountant_user, "Finance Workstation — Chrome"),
        (support_user, "Support Desk — Firefox"),
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

    for cat, pkey, dname, desc, prio, active, sbx, cfg_json in [
        (ProviderConfiguration.Category.PAYMENT, "sandbox", "درگاه آزمایشی داخلی (Sandbox)", "شبیه‌سازی امن پرداخت اشتراک و تست جریان تسویه", 1, True, True, {}),
        (ProviderConfiguration.Category.PAYMENT, "zarinpal", "درگاه زرین‌پال (Zarinpal v4)", "درگاه پرداخت رسمی ایران با پشتیبانی سندباکس", 2, True, True, {"currency": "IRR"}),
        (ProviderConfiguration.Category.PAYMENT, "zibal", "درگاه زیبال (Zibal v1)", "درگاه پرداخت مستقیم با تسویه سریع", 3, True, True, {"currency": "IRR"}),
        (ProviderConfiguration.Category.PAYMENT, "idpay", "درگاه آیدی‌پی (IDPay v1.1)", "درگاه پرداخت REST با پشتیبانی سندباکس", 4, False, True, {"currency": "IRR"}),
        (ProviderConfiguration.Category.SMS, "console", "سرویس پیامک توسعه (Console Fallback)", "ثبت پیامک در لاگ داخلی در محیط توسعه و پشتیبان قطع سرویس", 99, True, True, {}),
        (ProviderConfiguration.Category.SMS, "kavenegar", "کاوه‌نگار (Kavenegar)", "ارسال سریع OTP و پیامک اطلاع‌رسانی با خط اختصاصی", 1, False, False, {"sender_line": "10008663"}),
        (ProviderConfiguration.Category.SMS, "melipayamak", "ملی‌پیامک (Melipayamak)", "سرویس پیامک خدماتی و وب‌سرویس الگو", 2, False, False, {"sender_line": "50004000"}),
        (ProviderConfiguration.Category.SMS, "smsir", "پیامک ایرانیان (SMS.ir)", "ارسال وریفای کد پرسرعت و گزارش تحویل لحظه‌ای", 3, False, False, {"sender_line": "30007732"}),
        (ProviderConfiguration.Category.MAP, "osm", "OpenStreetMap استاندارد", "لایه نقشه آزاد بین‌المللی با پشتیبانی تم روشن و تیره", 1, True, False, {}),
        (ProviderConfiguration.Category.MAP, "carto", "CartoDB Architectural", "لایه مینیمال معماری با کنتراست بالا", 2, False, False, {}),
        (ProviderConfiguration.Category.MAP, "neshan", "نقشه بومی نشان (Neshan)", "نقشه فارسی ویژه ایران (نیازمند API Key)", 3, False, True, {}),
        (ProviderConfiguration.Category.AI, "gapgpt", "هوش مصنوعی GapGPT", "دروازه واحد مدل‌های GPT-4o، Claude Sonnet و Gemini", 1, True, False, {"base_url": "https://api.gapgpt.app/v1", "default_model": "gpt-4o"}),
    ]:
        ProviderConfiguration.objects.get_or_create(
            agency=None,
            category=cat,
            provider_key=pkey,
            defaults={
                "display_name": dname,
                "description": desc,
                "priority": prio,
                "is_active": active,
                "is_sandbox": sbx,
                "config_json": cfg_json,
            },
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
    mem_sales_mgr, _ = AgencyMembership.objects.get_or_create(
        user=sales_mgr, agency=agency_a, defaults={"role": sales_mgr_role, "branch": branch_a}
    )
    mem_agent_a1, _ = AgencyMembership.objects.get_or_create(
        user=agent_a1, agency=agency_a, defaults={"role": agent_role, "branch": branch_a}
    )
    mem_accountant, _ = AgencyMembership.objects.get_or_create(
        user=accountant_user,
        agency=agency_a,
        defaults={"role": acct_role, "branch": branch_a},
    )
    mem_support, _ = AgencyMembership.objects.get_or_create(
        user=support_user, agency=agency_a, defaults={"role": support_role, "branch": branch_a}
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
        d_obj = geo_districts.get(item["district"])
        n_obj = geo_neighborhoods.get(f"{item['district']}:{item['neighborhood']}")
        c_obj = city_lavasan if item["district"] == "لواسان" else city_tehran
        if is_new:
            prop.recalculate_price_per_sqm()
            prop.save()
            prop.amenities.set(
                [
                    amenities["PARKING"],
                    amenities["ELEVATOR"],
                    amenities["STORAGE"],
                    amenities["BALCONY"],
                    amenities["LOBBY"],
                    amenities["CCTV"],
                    amenities["HEATING_SYSTEM"],
                    amenities["SMART_HOME"],
                ]
            )
            PropertyLocation.objects.create(
                property=prop,
                province_ref=prov_tehran,
                city_ref=c_obj,
                district_ref=d_obj,
                neighborhood_ref=n_obj,
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
            loc_obj = getattr(prop, "location", None)
            if loc_obj and not loc_obj.province_ref_id:
                loc_obj.province_ref = prov_tehran
                loc_obj.city_ref = c_obj
                loc_obj.district_ref = d_obj
                loc_obj.neighborhood_ref = n_obj
                loc_obj.save()

        # Ensure rich amenity attribute values exist
        for am_code, val_txt, val_num in [
            ("PARKING", "۲ پارکینگ سندی باکس", Decimal("2")),
            ("ELEVATOR", "۲ لاین آسانسور KONE", Decimal("2")),
            ("BALCONY", "تراس بزرگ قابل چیدمان", Decimal("1")),
            ("HEATING_SYSTEM", "چیلر مرکزی", None),
        ]:
            PropertyAmenityValue.objects.get_or_create(
                property=prop,
                amenity=amenities[am_code],
                defaults={"value_text": val_txt, "value_number": val_num},
            )
            prop.amenities.add(amenities[am_code])
        created_props.append(prop)

    # Ensure rich multi-photo gallery for visual detail & lightbox experience
    gallery_extras = [
        "/images/prop-penthouse.jpg",
        "/images/prop-fereshteh.jpg",
        "/images/modern-villa-facade.jpg",
    ]
    for prop_obj in created_props[:3]:
        if prop_obj.media_items.count() < 3:
            for idx, extra_url in enumerate(gallery_extras, start=1):
                if not prop_obj.media_items.filter(url=extra_url).exists():
                    PropertyMedia.objects.create(
                        property=prop_obj,
                        url=extra_url,
                        title=f"نمای تکمیلی {idx} — {prop_obj.property_code}",
                        is_cover=False,
                        is_public=True,
                        sort_order=idx + 1,
                    )

    if PropertyPriceHistory.objects.filter(property=created_props[0]).count() < 2:
        PropertyPriceHistory.objects.filter(property=created_props[0]).delete()
        for prev_p, new_p, days_ago in [
            (Decimal("41000000000"), Decimal("40200000000"), 45),
            (Decimal("40200000000"), Decimal("39500000000"), 22),
            (Decimal("39500000000"), created_props[0].total_price, 6),
        ]:
            ph = PropertyPriceHistory.objects.create(
                property=created_props[0],
                previous_price=prev_p,
                new_price=new_p,
                currency_code="IRT",
                changed_by=mgr_a,
            )
            PropertyPriceHistory.objects.filter(id=ph.id).update(changed_at=now - timedelta(days=days_ago))

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
            "owner_customer": owner_cust,
            "agent_membership": mem_agent_a1,
            "deal_type": sale_deal,
            "status": Negotiation.Status.BARGAINING,
            "asking_price": created_props[0].total_price,
            "initial_proposed_price": Decimal("36500000000"),
            "latest_proposed_price": Decimal("37900000000"),
            "next_action": "جلسه جمع‌بندی قیمت نهایی با حضور مالک و خریدار",
            "next_followup_at": now + timedelta(days=1),
            "last_activity_at": now - timedelta(hours=3),
            "notes": "مذاکره قیمت و شرایط پرداخت دو مرحله‌ای",
        },
    )
    if neg_new:
        NegotiationOfferVersion.objects.create(
            negotiation=neg,
            version_number=1,
            offered_by=NegotiationOfferVersion.OfferedBy.BUYER,
            recipient_role="SELLER",
            proposed_price=Decimal("36500000000"),
            notes="پیشنهاد اولیه خریدار با پرداخت ۶۰٪ نقد هنگام مبایعه‌نامه",
            status=NegotiationOfferVersion.Status.SUPERSEDED,
        )
        NegotiationOfferVersion.objects.create(
            negotiation=neg,
            version_number=2,
            offered_by=NegotiationOfferVersion.OfferedBy.SELLER,
            recipient_role="BUYER",
            proposed_price=Decimal("37900000000"),
            notes="پاسخ متقابل مالک در صورت تسویه ۴۵ روزه",
            status=NegotiationOfferVersion.Status.PENDING,
        )
    else:
        if not neg.owner_customer_id:
            neg.owner_customer = owner_cust
            neg.asking_price = created_props[0].total_price
            neg.initial_proposed_price = Decimal("36500000000")
            neg.latest_proposed_price = Decimal("37900000000")
            neg.status = Negotiation.Status.BARGAINING
            neg.next_action = "جلسه جمع‌بندی قیمت نهایی با حضور مالک و خریدار"
            neg.next_followup_at = now + timedelta(days=1)
            neg.last_activity_at = now - timedelta(hours=3)
            neg.save()

    if not NegotiationActivity.objects.filter(negotiation=neg).exists():
        NegotiationActivity.objects.create(
            negotiation=neg,
            activity_type=NegotiationActivity.ActivityType.CALL,
            title="تماس تلفنی ارائه پیشنهاد ۳۶.۵ میلیاردی به مالک",
            description="مالک با اصل فروش موافق است اما روی رقم ۳۷.۹ میلیارد با تسویه کوتاه‌مدت نظر دارد.",
            outcome="پیشنهاد متقابل ثبت شد",
            next_action="هماهنگی جلسه حضوری در شعبه زعفرانیه",
            next_action_due_at=now + timedelta(days=1),
            assigned_membership=mem_agent_a1,
            created_by=agent_a1,
        )
        NegotiationActivity.objects.create(
            negotiation=neg,
            activity_type=NegotiationActivity.ActivityType.MEETING,
            title="نشست کارشناسی بررسی شرایط چک‌های پرداختی",
            description="توافق بر سر استعلام سند تک‌برگ پیش از امضای توافق اولیه.",
            outcome="مثبت و رو به جلو",
            assigned_membership=mem_agent_a1,
            created_by=mgr_a,
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

    # 13. Saved Views, Dashboard Layouts, Onboarding Progress & ImportJob Samples
    SavedView.objects.get_or_create(
        user=mgr_a,
        agency=agency_a,
        module="properties",
        title="فایل‌های در انتظار تایید",
        defaults={
            "filters_json": {"status": "PENDING_APPROVAL"},
            "sort_by": "-created_at",
            "is_default": False,
        },
    )
    DashboardLayout.objects.get_or_create(
        user=mgr_a,
        agency=agency_a,
        role_code="AGENCY_MANAGER",
        defaults={
            "widgets_json": [
                {"id": "kpis", "title": "شاخص‌های کلیدی عملکرد", "visible": True},
                {"id": "analytics_trend", "title": "روند فروش و درآمد آژانس", "visible": True},
                {"id": "alerts", "title": "هشدارها و موارد فوری", "visible": True},
                {"id": "upcoming", "title": "برنامه بازدیدها و پیگیری‌ها", "visible": True},
                {"id": "leaderboard", "title": "رتبه‌بندی مشاوران", "visible": True},
            ],
            "default_period_days": 30,
        },
    )
    OnboardingProgress.objects.get_or_create(
        user=mgr_a,
        agency=agency_a,
        role_code="AGENCY_MANAGER",
        defaults={"completed_steps_json": ["review_policy"], "dismissed": False},
    )
    ImportJob.objects.get_or_create(
        agency=agency_a,
        module="properties",
        file_name="demo-tehran-listings.xlsx",
        defaults={
            "total_rows": 5,
            "imported_rows": 5,
            "duplicate_rows": 0,
            "error_rows": 0,
            "status": ImportJob.Status.COMPLETED,
            "created_by": mgr_a,
        },
    )

    # 14. Global Settings Registry (48+ PostgreSQL-Backed Controls + History)
    if not ExchangeRateHistory.objects.exists():
        ExchangeRateHistory.objects.create(
            base_currency_code="USD",
            quote_currency_code="IRT",
            previous_rate=Decimal("64000.000000"),
            new_rate=Decimal("65000.000000"),
            source="MARKET_REF",
            change_reason="ثبت نرخ مرجع اولیه سامانه",
            changed_by=super_admin,
            created_by=super_admin,
        )

    settings_catalog = [
        # GENERAL
        ("general.platform_name_fa", "نام فارسی پلتفرم", "Platform Name (FA)", "نام اصلی نمایش‌داده‌شده در هدر، عناوین و ایمیل‌ها", "GENERAL", "IDENTITY", "STRING", "بنیان ملک", "PUBLIC", {}, 1),
        ("general.platform_name_en", "نام انگلیسی پلتفرم", "Platform Name (EN)", "عنوان انگلیسی پلتفرم در متادیتا و اسناد", "GENERAL", "IDENTITY", "STRING", "Bonyan Melk", "PUBLIC", {}, 2),
        ("general.platform_tagline", "شعار کوتاه برند", "Brand Tagline", "زیرعنوان پورتال عمومی و صفحه اصلی", "GENERAL", "IDENTITY", "STRING", "پلتفرم جامع مدیریت هوشمند آژانس‌های املاک و معاملات شفاف", "PUBLIC", {}, 3),
        ("general.support_phone", "تلفن پشتیبانی پلتفرم", "Support Phone", "شماره تماس رسمی واحد پشتیبانی", "GENERAL", "CONTACT", "STRING", "021-88990011", "PUBLIC", {}, 4),
        ("general.support_email", "ایمیل رسمی پشتیبانی", "Support Email", "نشانی ایمیل ارتباط با پشتیبانی", "GENERAL", "CONTACT", "STRING", "support@bonyanmelk.ir", "PUBLIC", {}, 5),
        ("general.office_address", "نشانی دفتر مرکزی", "Office Address", "آدرس پستی نمایش‌داده‌شده در پاورقی و صفحه تماس", "GENERAL", "CONTACT", "STRING", "تهران، بلوار نلسون ماندلا، برج فناوری، طبقه ۸", "PUBLIC", {}, 6),
        ("general.maintenance_mode", "حالت تعمیرات و به‌روزرسانی سامانه", "Maintenance Mode", "مسدودسازی موقت درخواست‌های غیرادمین هنگام نگهداری", "GENERAL", "OPERATIONS", "BOOLEAN", False, "PUBLIC", {}, 7),
        ("general.allow_public_registration", "امکان ثبت‌نام عمومی کاربران", "Allow Public Registration", "فعال یا غیرفعال‌کردن فرم ثبت‌نام خریداران و کاربران جدید", "GENERAL", "ACCESS", "BOOLEAN", True, "PUBLIC", {}, 8),
        # BRANDING
        ("branding.default_theme_preset", "سبک بصری پیش‌فرض پلتفرم", "Default Theme Preset", "یکی از ۴ سبک طراحی سازمانی سیستم", "BRANDING", "THEME", "SELECT", "architectural", "PUBLIC", {"choices": ["architectural", "executive", "editorial", "sand"]}, 10),
        ("branding.default_color_mode", "حالت روشنایی پیش‌فرض", "Default Color Mode", "حالت پیش‌فرض روشن یا تیره برای بازدیدکنندگان جدید", "BRANDING", "THEME", "SELECT", "light", "PUBLIC", {"choices": ["light", "dark", "system"]}, 11),
        ("branding.copyright_text", "متن کپی‌رایت پاورقی", "Footer Copyright", "متن حقوقی نمایش‌داده‌شده در انتهای تمام صفحات", "BRANDING", "FOOTER", "STRING", "© تمامی حقوق این پلتفرم متعلق به سامانه بنیان ملک است.", "PUBLIC", {}, 12),
        # LOCALIZATION
        ("localization.default_country", "کشور پیش‌فرض سیستم", "Default Country", "کد دوحرفی ISO کشور پیش‌فرض", "LOCALIZATION", "DEFAULTS", "STRING", "IR", "PUBLIC", {}, 20),
        ("localization.default_language", "زبان پیش‌فرض سامانه", "Default Language", "کد زبان پیش‌فرض رابط کاربری", "LOCALIZATION", "DEFAULTS", "SELECT", "fa", "PUBLIC", {"choices": ["fa", "en", "ar"]}, 21),
        ("localization.default_calendar", "تقویم پیش‌فرض تاریخ‌ها", "Default Calendar", "تقویم پیش‌فرض نمایش و ثبت تاریخ در سیستم", "LOCALIZATION", "DEFAULTS", "SELECT", "jalali", "PUBLIC", {"choices": ["jalali", "gregorian"]}, 22),
        ("localization.default_area_unit", "واحد مساحت پیش‌فرض", "Area Unit", "واحد پیش‌فرض متراژ املاک", "LOCALIZATION", "UNITS", "SELECT", "sqm", "PUBLIC", {"choices": ["sqm", "sqft"]}, 23),
        # PROPERTY & PORTAL
        ("property.default_currency", "ارز پیش‌فرض ثبت آگهی", "Default Property Currency", "ارز پیش‌فرض هنگام ایجاد فایل جدید", "PROPERTY", "PRICING", "STRING", "IRT", "PUBLIC", {}, 30),
        ("property.max_media_per_listing", "حداکثر تعداد تصویر هر ملک", "Max Media Per Listing", "محدودیت تعداد عکس و ویدیوی قابل آپلود در هر فایل", "PROPERTY", "MEDIA", "INTEGER", 25, "INTERNAL", {"min": 1, "max": 100}, 31),
        ("property.max_media_size_mb", "حداکثر حجم هر فایل رسانه (مگابایت)", "Max Media Size MB", "حداکثر حجم مجاز بارگذاری تصویر یا ویدیو", "PROPERTY", "MEDIA", "INTEGER", 10, "INTERNAL", {"min": 1, "max": 100}, 32),
        ("property.auto_mask_exact_address_public", "مخفی‌سازی نشانی دقیق در پورتال عمومی", "Mask Exact Address Public", "عدم نمایش پلاک و آدرس دقیق به کاربران عمومی", "PROPERTY", "PRIVACY", "BOOLEAN", True, "PUBLIC", {}, 33),
        ("property.default_featured_limit_agency", "سقف آگهی‌های ویژه هر آژانس", "Max Featured Listings", "تعداد هم‌زمان املاک ویژه در پلن استاندارد", "PROPERTY", "QUOTAS", "INTEGER", 15, "INTERNAL", {"min": 0, "max": 500}, 34),
        # FINANCE & COMMISSION
        ("finance.base_currency", "ارز پایه گزارش‌های مالی و حسابداری", "Base Reporting Currency", "ارز مرجع دفتر کل و محاسبات نرخ تبدیل", "FINANCE", "CURRENCY", "STRING", "IRT", "PUBLIC", {}, 40),
        ("finance.default_vat_percent", "نرخ مالیات بر ارزش افزوده پیش‌فرض (%)", "Default VAT Percent", "درصد مالیات بر ارزش افزوده در محاسبه فاکتور و کمیسیون", "FINANCE", "TAX", "DECIMAL", "10.00", "INTERNAL", {"min": "0", "max": "50"}, 41),
        ("finance.commission_default_agency_share_percent", "سهم پیش‌فرض آژانس از کمیسیون (%)", "Default Agency Split %", "نسبت پایه تقسیم کارمزد بین آژانس و مشاوران", "FINANCE", "COMMISSION", "DECIMAL", "50.00", "INTERNAL", {"min": "0", "max": "100"}, 42),
        ("finance.require_deal_dual_approval", "نیاز به تایید دومرحله‌ای بسته‌شدن معامله", "Require Dual Approval", "الزام تایید مدیر یا حسابدار برای قطعی‌شدن سند معامله", "FINANCE", "WORKFLOW", "BOOLEAN", False, "INTERNAL", {}, 43),
        # SECURITY & SESSIONS
        ("security.password_min_length", "حداقل طول رمز عبور", "Min Password Length", "حداقل تعداد کاراکترهای الزامی هنگام ثبت‌نام یا تغییر رمز", "SECURITY", "PASSWORD", "INTEGER", 8, "PUBLIC", {"min": 6, "max": 64}, 50),
        ("security.password_require_uppercase", "الزام حرف بزرگ انگلیسی در رمز عبور", "Require Uppercase", "نیاز به حداقل یک حرف A-Z در رمز عبور", "SECURITY", "PASSWORD", "BOOLEAN", False, "PUBLIC", {}, 51),
        ("security.password_require_digit", "الزام عدد در رمز عبور", "Require Digit", "نیاز به حداقل یک رقم 0-9 در رمز عبور", "SECURITY", "PASSWORD", "BOOLEAN", False, "PUBLIC", {}, 52),
        ("security.password_require_special", "الزام کاراکتر ویژه در رمز عبور", "Require Special Char", "نیاز به کاراکترهایی مانند @ # $ ! در رمز عبور", "SECURITY", "PASSWORD", "BOOLEAN", False, "PUBLIC", {}, 53),
        ("security.brute_force_max_fails", "حداکثر تلاش ناموفق ورود پیش از قفل", "Max Failed Logins", "تعداد دفعات مجاز ورود اشتباه قبل از مسدودسازی موقت", "SECURITY", "LOCKOUT", "INTEGER", 5, "INTERNAL", {"min": 3, "max": 50}, 54),
        ("security.brute_force_lockout_seconds", "مدت قفل موقت پس از تلاش ناموفق (ثانیه)", "Lockout Duration (s)", "مدت زمان محدودیت ورود پس از رسیدن به حد نصاب خطا", "SECURITY", "LOCKOUT", "INTEGER", 600, "INTERNAL", {"min": 60, "max": 86400}, 55),
        ("security.mfa_policy", "سیاست احراز هویت دوعاملی (MFA)", "MFA Enforcement Policy", "تعیین اجباری یا اختیاری بودن کد TOTP", "SECURITY", "MFA", "SELECT", "OPTIONAL", "INTERNAL", {"choices": ["OPTIONAL", "ADMINS_REQUIRED", "ALL_REQUIRED"]}, 56),
        ("security.access_token_ttl_minutes", "اعتبار توکن دسترسی JWT (دقیقه)", "JWT Access TTL (min)", "طول عمر توکن دسترسی برای نشست‌های جدید", "SECURITY", "TOKENS", "INTEGER", 30, "INTERNAL", {"min": 5, "max": 1440}, 57),
        ("security.refresh_token_ttl_days", "اعتبار توکن تازه‌سازی (روز)", "JWT Refresh TTL (days)", "طول عمر توکن Refresh در نشست‌های فعال", "SECURITY", "TOKENS", "INTEGER", 7, "INTERNAL", {"min": 1, "max": 90}, 58),
        ("security.session_idle_timeout_minutes", "مهلت عدم فعالیت نشست (دقیقه)", "Session Idle Timeout", "ابطال خودکار نشست در صورت نبود فعالیت کاربر", "SECURITY", "SESSIONS", "INTEGER", 480, "INTERNAL", {"min": 5, "max": 10080}, 59),
        ("security.max_concurrent_sessions", "حداکثر نشست هم‌زمان هر کاربر", "Max Concurrent Sessions", "تعداد دستگاه‌های مجاز به‌طور هم‌زمان برای یک حساب", "SECURITY", "SESSIONS", "INTEGER", 5, "INTERNAL", {"min": 1, "max": 50}, 60),
        ("security.rate_limit_default_rpm", "سقف نرخ درخواست عمومی (در دقیقه)", "Default Rate Limit RPM", "حداکثر درخواست مجاز در هر دقیقه برای هر IP", "SECURITY", "RATE_LIMIT", "INTEGER", 180, "INTERNAL", {"min": 30, "max": 5000}, 61),
        ("security.rate_limit_auth_rpm", "سقف نرخ درخواست ورود و ثبت‌نام (در دقیقه)", "Auth Rate Limit RPM", "حداکثر درخواست مجاز مسیرهای Auth در هر دقیقه", "SECURITY", "RATE_LIMIT", "INTEGER", 30, "INTERNAL", {"min": 5, "max": 500}, 62),
        # SMS CENTER
        ("sms.enabled", "فعال‌سازی سراسری سامانه پیامک", "Enable SMS Dispatch", "کلید اصلی روشن/خاموش تمام ارسال‌های پیامکی پلتفرم", "SMS", "GLOBAL", "BOOLEAN", True, "INTERNAL", {}, 70),
        ("sms.daily_cap", "سقف ارسال روزانه پیامک", "Daily SMS Cap", "حداکثر پیامک قابل ارسال در شبانه‌روز", "SMS", "QUOTA", "INTEGER", 5000, "INTERNAL", {"min": 10, "max": 1000000}, 71),
        ("sms.cost_per_segment", "تعرفه تخمینی هر پیامک (تومان)", "Cost Per Segment", "مبلغ محاسبه هزینه در لاگ ارسال پیامک", "SMS", "COST", "DECIMAL", "950", "INTERNAL", {"min": "0", "max": "100000"}, 72),
        ("sms.fallback_enabled", "فعال‌سازی سرویس پشتیبان پیامک (Fallback)", "SMS Fallback Enabled", "ارسال خودکار از خط پشتیبان در صورت خطای سرویس اول", "SMS", "FAILOVER", "BOOLEAN", True, "INTERNAL", {}, 73),
        ("sms.event.otp_login", "پیامک کد یک‌بارمصرف ورود (OTP)", "SMS Event: OTP", "ارسال پیامکی کد تایید ورود", "SMS", "EVENTS", "BOOLEAN", True, "INTERNAL", {}, 74),
        ("sms.event.register", "پیامک خوش‌آمدگویی ثبت‌نام", "SMS Event: Register", "ارسال پیامک پس از تکمیل ثبت‌نام کاربر", "SMS", "EVENTS", "BOOLEAN", True, "INTERNAL", {}, 75),
        ("sms.event.password_reset", "پیامک بازیابی رمز عبور", "SMS Event: Password Reset", "ارسال کد تایید تغییر رمز عبور", "SMS", "EVENTS", "BOOLEAN", True, "INTERNAL", {}, 76),
        ("sms.event.appointment", "پیامک زمان‌بندی بازدید ملک", "SMS Event: Appointment", "اطلاع‌رسانی خودکار زمان بازدید به خریدار و مشاور", "SMS", "EVENTS", "BOOLEAN", True, "INTERNAL", {}, 77),
        ("sms.event.crm_followup", "پیامک یادآوری پیگیری CRM", "SMS Event: CRM Follow-up", "ارسال یادآور پیگیری مشتریان", "SMS", "EVENTS", "BOOLEAN", True, "INTERNAL", {}, 78),
        ("sms.event.deal_contract", "پیامک وضعیت قرارداد و معامله", "SMS Event: Deal & Contract", "اعلان ثبت یا تایید قرارداد به طرفین", "SMS", "EVENTS", "BOOLEAN", True, "INTERNAL", {}, 79),
        ("sms.event.payment_finance", "پیامک تراکنش مالی و اشتراک", "SMS Event: Payment", "اطلاع‌رسانی واریز موفق یا سررسید چک", "SMS", "EVENTS", "BOOLEAN", True, "INTERNAL", {}, 80),
        ("sms.event.admin_alert", "پیامک هشدارهای امنیتی و ادمین", "SMS Event: Admin Alert", "هشدار رویدادهای بحرانی به مدیران سیستم", "SMS", "EVENTS", "BOOLEAN", True, "INTERNAL", {}, 81),
        ("sms.event.notification", "پیامک اعلان‌های عمومی سامانه", "SMS Event: Notification", "ارسال اعلان‌های مهم به‌صورت پیامک", "SMS", "EVENTS", "BOOLEAN", True, "INTERNAL", {}, 82),
        # LEGAL & COMPLIANCE GOVERNANCE
        ("compliance.require_property_verification_before_publish", "الزام احراز اصالت ملک پیش از انتشار عمومی", "Require Verification Before Publish", "مسدودسازی انتشار عمومی ملک تا تکمیل وجود فیزیکی، سند و رضایت مالک", "LEGAL", "AUTHENTICITY", "BOOLEAN", True, "PUBLIC", {}, 90),
        ("compliance.require_physical_verification", "الزام تأیید وجود فیزیکی ملک", "Require Physical Verification", "اجباری‌بودن تیک بازدید و تطبیق فیزیکی ملک", "LEGAL", "AUTHENTICITY", "BOOLEAN", True, "INTERNAL", {}, 91),
        ("compliance.require_deed_verification", "الزام بررسی و احراز سند رسمی", "Require Deed Verification", "اجباری‌بودن بررسی سند مالکیت پیش از انتشار", "LEGAL", "AUTHENTICITY", "BOOLEAN", True, "INTERNAL", {}, 92),
        ("compliance.require_owner_consent", "الزام ثبت رضایت مالک برای آگهی", "Require Owner Consent", "اجباری‌بودن اخذ رضایت مالک جهت انتشار", "LEGAL", "AUTHENTICITY", "BOOLEAN", True, "INTERNAL", {}, 93),
        ("compliance.enable_duplicate_and_price_anomaly_detection", "پایش هوشمند آگهی تکراری و قیمت غیرواقعی", "Duplicate & Price Anomaly Detection", "تشخیص خودکار کدپستی/مختصات تکراری و ناهنجاری قیمت هر متر", "LEGAL", "ANTI_FRAUD", "BOOLEAN", True, "INTERNAL", {}, 94),
        ("compliance.require_terms_acceptance_on_register", "الزام پذیرش شرایط استفاده و حریم خصوصی در ثبت‌نام", "Require Legal Acceptance", "نمایش و الزام تأیید اسناد حقوقی در هنگام عضویت", "LEGAL", "CONSENT", "BOOLEAN", True, "PUBLIC", {}, 95),
        # NOTIFICATIONS & AI
        ("notifications.enable_web_push", "فعال‌سازی اعلان‌های لحظه‌ای مرورگر (Web Push)", "Enable Web Push", "ارسال پوش نوتیفیکیشن برای رویدادهای فوری", "NOTIFICATIONS", "CHANNELS", "BOOLEAN", True, "PUBLIC", {}, 100),
        ("ai.enable_assistant", "فعال‌سازی دستیار هوشمند تولید متن و تحلیل آژانس", "Enable AI Assistant", "فعال‌سازی ابزارهای هوشمند در داشبورد آژانس", "AI", "FEATURES", "BOOLEAN", True, "PUBLIC", {}, 110),
        ("ai.default_model", "مدل پیش‌فرض هوش مصنوعی", "Default AI Model", "شناسه مدل انتخابی در Gateway هوش مصنوعی", "AI", "MODELS", "STRING", "gpt-4o", "INTERNAL", {}, 111),
    ]

    for key, tfa, ten, desc, cat, subcat, vtype, val, sens, schema, sord in settings_catalog:
        SystemSetting.objects.get_or_create(
            key=key,
            agency=None,
            country_code="",
            defaults={
                "title_fa": tfa,
                "title_en": ten,
                "description": desc,
                "category": cat,
                "subcategory": subcat,
                "value_type": vtype,
                "value_json": {"value": val},
                "default_value_json": {"value": val},
                "validation_schema": schema,
                "sensitivity_level": sens,
                "is_active": True,
                "is_editable": True,
                "requires_restart": False,
                "sort_order": sord,
            },
        )

    if not SystemSettingHistory.objects.exists():
        SystemSettingHistory.objects.create(
            setting_key="compliance.require_property_verification_before_publish",
            agency_id_snapshot=None,
            previous_value_json={"value": False},
            new_value_json={"value": True},
            is_secret=False,
            change_reason="فعال‌سازی سیاست الزامی احراز اصالت ملک در راه‌اندازی اولیه",
            changed_by=super_admin,
            created_by=super_admin,
        )

    # 15. Brand Media Slots & Editable Site Content Blocks
    for slot_key, cat, title_fa, desc, img_url, dark_url, alt_txt, sord in [
        ("site_logo_light", "LOGO", "لوگوی اصلی پلتفرم (تم روشن)", "تصویر لوگوی نمایش‌داده‌شده در هدر و صفحات روشن", "/images/brand-mark.svg", "/images/brand-mark.svg", "لوگوی بنیان ملک", 1),
        ("site_logo_dark", "LOGO", "لوگوی پلتفرم (تم تیره)", "تصویر لوگوی بهینه‌شده برای پس‌زمینه تیره", "/images/brand-mark.svg", "/images/brand-mark.svg", "لوگوی بنیان ملک در حالت تیره", 2),
        ("hero_banner", "BANNER", "تصویر شاخص صفحه اصلی (Hero)", "بنر معماری نمایش‌داده‌شده در بخش اول پورتال عمومی", "/images/hero-penthouse-tehran.jpg", "/images/hero-penthouse-tehran.jpg", "پنت‌هاوس لوکس معماری در شمال تهران", 3),
        ("auth_banner", "BANNER", "تصویر جانبی صفحات ورود و ثبت‌نام", "تصویر معماری نمایش‌داده‌شده در کنار فرم‌های احراز هویت", "/images/modern-villa-facade.jpg", "/images/modern-villa-facade.jpg", "نمای ویلای مدرن بنیان ملک", 4),
        ("about_banner", "BANNER", "تصویر معرفی پلتفرم (درباره ما)", "تصویر دفتر مدیریت آژانس در صفحه درباره بنیان ملک", "/images/studio-agency-office.jpg", "/images/studio-agency-office.jpg", "دفتر مدرن آژانس املاک بنیان ملک", 5),
    ]:
        BrandMediaSlot.objects.get_or_create(
            slot_key=slot_key,
            defaults={
                "category": cat,
                "title_fa": title_fa,
                "description": desc,
                "image_url": img_url,
                "dark_image_url": dark_url,
                "alt_text": alt_txt,
                "is_active": True,
                "sort_order": sord,
            },
        )

    for slug_key, pkey, skey, title_fa, subtitle_fa, body_html, cta_lbl, cta_href, items_json, sord in [
        (
            "home_hero",
            "HOME",
            "HERO",
            "اکوسیستم یکپارچه املاک، معاملات شفاف و مدیریت هوشمند آژانس‌ها",
            "جستجوی دقیق روی نقشه تعاملی، استعلام فایل‌های احراز اصالت‌شده و داشبورد مالی دوطرفه ویژه مدیران و مشاوران املاک",
            "<p>پلتفرم بنیان ملک زیرساختی امن و مبتنی بر معماری چندشعبه‌ای برای کشف املاک منتخب و مدیریت کامل چرخه CRM، قرارداد، پورسانت و حسابداری است.</p>",
            "مشاهده املاک احراز‌شده",
            "/properties",
            [],
            1,
        ),
        (
            "home_features",
            "HOME",
            "FEATURES",
            "چرا آژانس‌های پیشرو و خریداران حرفه‌ای بنیان ملک را انتخاب می‌کنند؟",
            "استانداردسازی کل چرخه از بازدید فیزیکی و تأیید سند تا دفتر کل دوطرفه",
            "",
            "درخواست همکاری آژانس",
            "/agency-application",
            [
                {"title": "احراز اصالت سه‌مرحله‌ای", "description": "تطبیق وجود فیزیکی، اصالت سند و رضایت مالک پیش از انتشار عمومی هر آگهی"},
                {"title": "حسابداری دوطرفه و کمیسیون", "description": "محاسبه دقیق اعشاری سهم آژانس و مشاوران به همراه مدیریت چک‌ها"},
                {"title": "شفافیت قیمت و نرخ ارز پویا", "description": "پشتیبانی چندارزی با ثبت نرخ لحظه‌ای در اسناد معامله و پرداخت"},
            ],
            2,
        ),
        (
            "home_cta",
            "HOME",
            "CTA",
            "آماده ارتقای آژانس املاک خود به استاندارد سازمانی هستید؟",
            "پنل اختصاصی چندشعبه‌ای خود را با امکانات کامل CRM، قرارداد هوشمند و پورتال عمومی راه‌اندازی کنید.",
            "",
            "شروع همکاری سازمانی",
            "/agency-application",
            [],
            3,
        ),
        (
            "about_overview",
            "ABOUT",
            "INTRO",
            "درباره پلتفرم سازمانی بنیان ملک",
            "زیرساخت مدرن مدیریت آژانس‌های املاک، شفافیت معاملاتی و حفاظت از حقوق خریداران و مالکان",
            "<p>بنیان ملک با هدف حذف آگهی‌های غیرواقعی، ایجاد شفافیت در محاسبه حق‌الزحمه و یکپارچه‌سازی عملیات شعب املاک طراحی شده است. تمامی تنظیمات، اسناد حقوقی، تقویم‌ها و ساختارهای مالی این پلتفرم به‌صورت پویا از پایگاه‌داده مرکزی مدیریت می‌شوند.</p>",
            "مطالعه قوانین و مقررات پلتفرم",
            "/terms",
            [],
            10,
        ),
        (
            "contact_banner",
            "CONTACT",
            "HEADER",
            "ارتباط مستقیم با تیم عملیات، پشتیبانی و فروش سازمانی",
            "سوالات خود درباره عضویت آژانس‌ها، گزارش تخلف یا دموی سازمانی را ثبت و با کد رهگیری پیگیری کنید.",
            "",
            "پیگیری درخواست ثبت‌شده",
            "/requests/track",
            [],
            20,
        ),
        (
            "register_intro",
            "AUTH",
            "REGISTER",
            "عضویت در پلتفرم بنیان ملک",
            "حساب کاربری شما با رعایت کامل خط‌مشی رمزنگاری، احراز هویت و حریم خصوصی راه‌اندازی می‌شود.",
            "",
            "مطالعه شرایط استفاده",
            "/terms-of-use",
            [],
            30,
        ),
    ]:
        SiteContentBlock.objects.get_or_create(
            slug_key=slug_key,
            defaults={
                "page_key": pkey,
                "section_key": skey,
                "title_fa": title_fa,
                "subtitle_fa": subtitle_fa,
                "body_html": body_html,
                "cta_label": cta_lbl,
                "cta_href": cta_href,
                "items_json": items_json,
                "status": SiteContentBlock.Status.PUBLISHED,
                "sort_order": sord,
                "is_active": True,
            },
        )

    # 16. SMS Templates & Initial Delivery Log
    for tpl_key, ev_type, name_fa, body_tpl, tokens in [
        ("otp_login", SmsTemplate.EventType.OTP_LOGIN, "کد ورود یک‌بارمصرف", "کد ورود شما به بنیان ملک: {{code}}\nاین کد تا ۲ دقیقه معتبر است.", ["code"]),
        ("password_reset", SmsTemplate.EventType.PASSWORD_RESET, "بازیابی رمز عبور", "کد تایید تغییر رمز عبور در بنیان ملک: {{code}}", ["code"]),
        ("viewing_scheduled", SmsTemplate.EventType.APPOINTMENT, "هماهنگی بازدید ملک", "{{name}} گرامی، بازدید ملک {{property_code}} در تاریخ {{date}} تنظیم شد.", ["name", "property_code", "date"]),
        ("deal_closed", SmsTemplate.EventType.DEAL_CONTRACT, "تایید معامله و قرارداد", "قرارداد شماره {{deal_code}} در آژانس {{agency}} با موفقیت ثبت و تایید شد.", ["deal_code", "agency"]),
        ("crm_followup", SmsTemplate.EventType.CRM_FOLLOWUP, "یادآور پیگیری مشاور", "یادآور پیگیری مشتری {{customer_name}} در زمان {{due_at}} ثبت شده است.", ["customer_name", "due_at"]),
        ("admin_alert", SmsTemplate.EventType.ADMIN_ALERT, "هشدار امنیتی و مدیریتی", "هشدار سامانه بنیان ملک: {{message}}", ["message"]),
    ]:
        SmsTemplate.objects.get_or_create(
            key=tpl_key,
            defaults={
                "event_type": ev_type,
                "name_fa": name_fa,
                "body_template": body_tpl,
                "sample_tokens": tokens,
                "is_active": True,
            },
        )

    if not SmsDeliveryLog.objects.exists():
        SmsDeliveryLog.objects.create(
            recipient_masked="0912***4444",
            recipient_hash="demo_seed_hash_09124444444",
            event_type="APPOINTMENT",
            template_key="viewing_scheduled",
            provider_key="console",
            status=SmsDeliveryLog.DeliveryStatus.SENT,
            message_id="SMS-SEED-1001",
            cost_amount=Decimal("950.00"),
            agency=agency_a,
            actor=agent_a1,
        )

    # 17. Property Verification Records & Sample Violation Report
    for p_obj in created_props:
        is_pub = p_obj.status == Property.Status.PUBLISHED
        ver, ver_new = PropertyVerification.objects.get_or_create(
            property=p_obj,
            defaults={
                "physical_verified": is_pub,
                "physical_notes": "بازدید حضوری توسط کارشناس آژانس و انطباق متراژ انجام شد." if is_pub else "در انتظار بازدید تکمیلی کارشناس شعبه",
                "deed_verified": is_pub,
                "deed_notes": "تطبیق تصویر سند تک‌برگ با مالکیت ثبت‌شده انجام شد." if is_pub else "",
                "owner_consent_verified": is_pub,
                "owner_consent_notes": "رضایت‌نامه مالک برای انتشار پورتال اخذ گردید." if is_pub else "",
                "verification_status": PropertyVerification.VerificationStatus.VERIFIED if is_pub else PropertyVerification.VerificationStatus.PENDING,
                "verified_by": mgr_a if is_pub else None,
                "verified_at": now - timedelta(days=2) if is_pub else None,
                "evidence_document": doc if (is_pub and p_obj.property_code == "PN-1001") else None,
                "created_by": mgr_a,
            },
        )
        if ver_new:
            PropertyVerificationHistory.objects.create(
                verification=ver,
                from_status=PropertyVerification.VerificationStatus.UNVERIFIED,
                to_status=ver.verification_status,
                notes="ثبت نتیجه بررسی اصالت فایل ملکی",
                changed_by=mgr_a,
                created_by=mgr_a,
            )

    if created_props and not PropertyViolationReport.objects.exists():
        PropertyViolationReport.objects.create(
            property=created_props[3],
            reporter=customer_user,
            reason_type=PropertyViolationReport.ReasonType.OTHER,
            details="درخواست بررسی انطباق امکانات مشاعات ثبت‌شده با وضعیت فعلی ملک.",
            status=PropertyViolationReport.ReportStatus.RESOLVED_DISMISSED,
            inspector=super_admin,
            resolution_note="مستندات و تصاویر ملک توسط بازرس پلتفرم تطبیق داده شد و اطلاعات صحیح است.",
            resolved_at=now - timedelta(days=1),
            created_by=customer_user,
        )

    # 18. 12 Comprehensive Legal, Policy & Compliance Documents (PostgreSQL CMS)
    legal_docs_seed = [
        (
            "terms-of-use",
            "TERMS",
            "شرایط استفاده از سامانه بنیان ملک",
            "Terms of Use",
            "چارچوب رسمی استفاده از خدمات پورتال و داشبورد سازمانی بنیان ملک برای کاربران، خریداران و آژانس‌ها.",
            "<h3>۱. تعاریف و قلمرو اجرایی</h3><p>استفاده از پلتفرم بنیان ملک به معنای پذیرش کامل ضوابط ثبت اطلاعات، احراز هویت و مسئولیت‌های قانونی کاربران و آژانس‌های عضو است.</p><h3>۲. تعهدات کاربران</h3><p>کاربران متعهد می‌شوند از ثبت اطلاعات نادرست، استفاده خودکار غیرمجاز (Scraping) و نقض حقوق مالکیت فکری سامانه خودداری نمایند.</p>",
            True,
            1,
        ),
        (
            "privacy-policy",
            "PRIVACY",
            "سیاست حریم خصوصی و حفاظت از داده‌ها",
            "Privacy Policy",
            "نحوه گردآوری، نگهداری، رمزنگاری و حفاظت از اطلاعات هویتی، شماره تماس و مستندات کاربران و مالکان.",
            "<h3>۱. محرمانگی شماره تماس و اطلاعات مالک</h3><p>شماره تماس و نشانی دقیق مالکان در پورتال عمومی مخفی نگه داشته می‌شود و فقط برای نقش‌های مجاز طبق سیاست دسترسی آژانس قابل مشاهده است.</p><h3>۲. رمزنگاری و ممیزی خروجی‌ها</h3><p>تمام کلیدهای محرمانه با استاندارد Fernet رمزنگاری شده و هرگونه دریافت خروجی اکسل یا CSV در لاگ ممیزی ثبت می‌گردد.</p>",
            True,
            2,
        ),
        (
            "platform-rules",
            "RULES",
            "قوانین و مقررات جامع پلتفرم بنیان ملک",
            "Platform Rules & Governance",
            "مقررات عملیاتی ناظر بر ثبت فایل، صداقت قیمت‌گذاری، حقوق مشاوران و نظارت بازرسان پلتفرم.",
            "<h3>۱. شفافیت آگهی و قیمت‌گذاری</h3><p>درج قیمت واقعی، متراژ صحیح و عدم انتشار آگهی‌های تکراری یا فریبنده الزامی است.</p><h3>۲. انطباق سیستمی قوانین</h3><p>ضوابط این سند مستقیماً در موتور اعتبارسنجی انتشار ملک و کنترل تخلفات Backend اعمال می‌شوند.</p>",
            True,
            3,
        ),
        (
            "property-authenticity-policy",
            "COMPLIANCE",
            "ضوابط احراز اصالت فایل‌های ملکی",
            "Property Authenticity Policy",
            "الزام تأیید سه‌گانه وجود فیزیکی ملک، بررسی سند رسمی و اخذ رضایت مالک پیش از انتشار عمومی.",
            "<h3>الزام سه‌مرحله‌ای پیش از انتشار</h3><p>هیچ آگهی ملکی تا پیش از ثبت تأییدیه وجود فیزیکی، بررسی سند مالکیت و رضایت مالک مجوز نمایش در پورتال عمومی را دریافت نمی‌کند. صدور استثنا صرفاً برای مدیران مجاز و با ثبت دلیل مستند در لاگ ممیزی امکان‌پذیر است.</p>",
            False,
            4,
        ),
        (
            "agency-membership-rules",
            "AGENCY",
            "آیین‌نامه عضویت و تعهدات آژانس‌های املاک",
            "Agency Membership Rules",
            "شرایط احراز پروانه کسب، مدیریت شعب، انضباط حرفه‌ای مشاوران و سهمیه‌های پلن اشتراک.",
            "<p>آژانس‌های عضو موظف‌اند اطلاعات ثبتی و پروانه کسب معتبر خود را به‌روز نگه دارند و دسترسی پرسنل و شعب خود را صرفاً بر اساس نیاز شغلی و با رعایت ماتریس دسترسی تنظیم کنند.</p>",
            False,
            5,
        ),
        (
            "anti-fraud-policy",
            "COMPLIANCE",
            "سیاست مقابله با آگهی جعلی، تکراری و قیمت غیرواقعی",
            "Anti-Fraud & Anomaly Policy",
            "سازوکارهای پایش هوشمند قیمت هر متر مربع، تطبیق کدپستی و تعلیق آگهی‌های متخلف.",
            "<p>سامانه به‌صورت مستمر قیمت‌های غیرمتعارف و مشخصات جغرافیایی/پستی تکراری را شناسایی کرده و گزارش‌های مردمی را به صف بازرسی مدیران پلتفرم ارجاع می‌دهد.</p>",
            False,
            6,
        ),
        (
            "commission-transparency",
            "FINANCE",
            "منشور شفافیت کمیسیون، مالیات و تقسیم کارمزد",
            "Commission Transparency",
            "ضوابط محاسبه دقیق اعشاری حق‌الزحمه معاملات، سهم مشاور اول/همکار و ثبت سند حسابداری.",
            "<p>تمامی محاسبات کارمزد و مالیات بر ارزش افزوده بر مبنای سیاست نسخه‌دار آژانس و با دقت اعشاری استاندارد (Decimal) انجام شده و نرخ ارز لحظه‌ای در سند معامله قفل می‌گردد.</p>",
            False,
            7,
        ),
        (
            "data-retention-policy",
            "PRIVACY",
            "سیاست نگهداری، آرشیو و حذف امن داده‌ها",
            "Data Retention Policy",
            "مدت زمان نگهداری اسناد قرارداد، لاگ‌های ممیزی مالی، گزارش‌های پیامکی و تاریخچه نشست‌ها.",
            "<p>سوابق معاملاتی و لاگ‌های ممیزی جهت پاسخگویی حقوقی و انطباق مالی به‌صورت تغییرناپذیر نگهداری می‌شوند و تاریخچه نشست‌ها طبق سیاست امنیتی پلتفرم پاک‌سازی دوره‌ای می‌گردد.</p>",
            False,
            8,
        ),
        (
            "cookie-notice",
            "PRIVACY",
            "اعلامیه کوکی‌ها و ذخیره‌سازی محلی مرورگر",
            "Cookie & Storage Notice",
            "شفاف‌سازی درباره کوکی‌ها و توکن‌های نشست جهت امنیت احراز هویت و حفظ تنظیمات تم و تقویم.",
            "<p>بنیان ملک صرفاً برای احراز هویت امن، تنظیمات تم روشن/تیره، زبان و تقویم انتخابی کاربر از ذخیره‌سازی استاندارد مرورگر استفاده می‌کند.</p>",
            False,
            9,
        ),
        (
            "complaint-resolution-policy",
            "GOVERNANCE",
            "دستورالعمل رسیدگی به شکایات و گزارش‌های تخلف",
            "Complaint Resolution Policy",
            "فرایند ثبت شکایت، پیگیری با کد رهگیری، بازرسی بی‌طرفانه و زمان‌بندی پاسخ‌گویی (SLA).",
            "<p>کاربران می‌توانند شکایات و گزارش‌های تخلف آگهی را همراه با کد رهگیری ثبت کنند. تیم نظارت پلتفرم حداکثر ظرف ۲۴ ساعت وضعیت پرونده را بررسی و در صورت احراز تخلف، آگهی را تعلیق می‌کند.</p>",
            False,
            10,
        ),
        (
            "api-usage-terms",
            "TECHNICAL",
            "مقررات استفاده از وب‌سرویس‌ها و اتصالات بیرونی",
            "API & Integration Terms",
            "ضوابط نرخ درخواست (Rate Limit)، حفاظت از کلیدهای دسترسی و اتصال درگاه‌های پرداخت، نقشه و پیامک.",
            "<p>تمامی درخواست‌های API مشمول سیاست محدودیت نرخ (Rate Limiting) مبتنی بر تنظیمات امنیتی پلتفرم هستند و افشا یا سوءاستفاده از توکن‌ها منجر به ابطال فوری نشست می‌شود.</p>",
            False,
            11,
        ),
        (
            "about-platform",
            "ABOUT",
            "معرفی رسمی و منشور مأموریت بنیان ملک",
            "About Bonyan Melk",
            "معرفی ساختار فناوری، اهداف حرفه‌ای و استانداردهای کیفیت در اکوسیستم بنیان ملک.",
            "<h3>مأموریت ما</h3><p>ایجاد پلتفرمی استاندارد، یکپارچه و قابل اتکا برای تحول دیجیتال در صنعت املاک، از جستجوی دقیق خریدار تا ترازنامه دقیق حسابداری آژانس‌ها.</p>",
            False,
            12,
        ),
    ]

    first_legal_doc = None
    for slug, dtype, tfa, ten, summary, body_html, req_acc, sord in legal_docs_seed:
        ldoc, lnew = LegalDocument.objects.get_or_create(
            slug=slug,
            defaults={
                "doc_type": dtype,
                "title_fa": tfa,
                "title_en": ten,
                "summary": summary,
                "body_html": body_html,
                "status": LegalDocument.Status.PUBLISHED,
                "version_number": 1,
                "requires_acceptance": req_acc,
                "effective_at": now - timedelta(days=30),
                "published_at": now - timedelta(days=30),
                "meta_title": f"{tfa} | بنیان ملک",
                "meta_description": summary[:300],
                "sort_order": sord,
                "is_system_doc": True,
                "created_by": super_admin,
            },
        )
        if first_legal_doc is None:
            first_legal_doc = ldoc
        if lnew or not ldoc.versions.exists():
            LegalDocumentVersion.objects.get_or_create(
                document=ldoc,
                version_number=ldoc.version_number,
                defaults={
                    "title_fa": ldoc.title_fa,
                    "summary": ldoc.summary,
                    "body_html": ldoc.body_html,
                    "change_note": "انتشار نسخه اولیه رسمی",
                    "edited_by": super_admin,
                    "created_by": super_admin,
                },
            )

    if first_legal_doc and not LegalAcceptanceRecord.objects.exists():
        LegalAcceptanceRecord.objects.get_or_create(
            document=first_legal_doc,
            version_number=first_legal_doc.version_number,
            user=customer_user,
            defaults={"ip_address": "127.0.0.1", "user_agent": "Mozilla/5.0 BonyanMelk-Client"},
        )

    counts = collect_domain_model_counts()
    empty_models = [name for name, cnt in counts.items() if cnt == 0]
    _log(f"Seeded {len(counts)} domain models ({len(counts) - len(empty_models)} populated, {len(empty_models)} empty).")
    if verify_all and empty_models:
        raise RuntimeError(f"Empty domain models detected after seed_all: {empty_models}")
    return {"counts": counts, "empty_models": empty_models}


@transaction.atomic
def clear_demo_platform_data(*, log_fn: Optional[Callable[[str], None]] = None) -> dict[str, int]:
    """Safely removes seeded demo records only, leaving real user/agency data intact."""
    assert_non_production_environment()

    def _log(msg: str) -> None:
        if log_fn:
            log_fn(msg)

    removed: dict[str, int] = {}
    demo_agencies = list(Agency.objects.filter(slug__in=DEMO_AGENCY_SLUGS))
    demo_agency_ids = [a.id for a in demo_agencies]
    demo_users = list(User.objects.filter(phone_number__in=DEMO_PHONES))

    if demo_agency_ids:
        for model in (
            ImportJob,
            DashboardLayout,
            OnboardingProgress,
            SavedView,
            AiInteractionLog,
            AuditLog,
            NotificationMessage,
            AgencyCooperation,
            PaymentGatewayTransaction,
            DocumentDownloadLog,
            Document,
            Negotiation,
            Lead,
            Payslip,
            PayrollCycle,
            CompensationPlan,
            EmployeeProfile,
            DealFinancialLedger,
            ChequeInstrument,
            JournalEntryLine,
            JournalEntry,
            BankAccount,
            CashBox,
            CostCenter,
            ChartOfAccount,
            FiscalPeriod,
            FiscalYear,
            Deal,
            ContractStatusHistory,
            ContractParty,
            Contract,
            ContractTemplate,
            ViewingAppointment,
            FollowUpTask,
            CustomerInteractionLog,
            CustomerPipelineItem,
            PipelineStage,
            CustomerRequirement,
            CustomerShare,
            Customer,
            PropertyPriceHistory,
            PropertyStatusHistory,
            PropertyVerificationHistory,
            PropertyVerification,
            PropertyViolationReport,
            PropertyAmenityValue,
            PropertyMedia,
            PropertyAgentAssignment,
            PropertyOwner,
            PropertyLocation,
            Property,
            AgencySubscription,
            Branch,
        ):
            mgr = model.objects
            qs = mgr.all_tenants() if hasattr(mgr, "all_tenants") else mgr.all()
            if hasattr(model, "agency_id"):
                cnt, _ = qs.filter(agency_id__in=demo_agency_ids).delete()
                if cnt:
                    removed[model.__name__] = removed.get(model.__name__, 0) + cnt
            elif hasattr(model, "requester_agency_id"):
                cnt, _ = qs.filter(requester_agency_id__in=demo_agency_ids).delete()
                if cnt:
                    removed[model.__name__] = cnt

        cnt_tkt, _ = Ticket.objects.filter(agency_id__in=demo_agency_ids).delete()
        if cnt_tkt:
            removed["Ticket"] = cnt_tkt
        cnt_cmp, _ = Complaint.objects.filter(agency_id__in=demo_agency_ids).delete()
        if cnt_cmp:
            removed["Complaint"] = cnt_cmp
        cnt_srv, _ = Survey.objects.filter(agency_id__in=demo_agency_ids).delete()
        if cnt_srv:
            removed["Survey"] = cnt_srv

        cnt_ag, _ = Agency.objects.filter(id__in=demo_agency_ids).delete()
        removed["Agency"] = cnt_ag

    cnt_art, _ = Article.objects.filter(
        slug__in=[
            "tehran-luxury-market-report-1405",
            "real-estate-contract-checklist",
            "double-entry-accounting-for-agencies",
        ]
    ).delete()
    if cnt_art:
        removed["Article"] = cnt_art

    cnt_req, _ = ContactInquiry.objects.filter(tracking_code="REQ-1405-1001").delete()
    if cnt_req:
        removed["ContactInquiry"] = cnt_req
    cnt_coop, _ = AgencyCooperationRequest.objects.filter(tracking_code="COOP-1405-1001").delete()
    if cnt_coop:
        removed["AgencyCooperationRequest"] = cnt_coop

    if demo_users:
        cnt_usr, _ = User.objects.filter(id__in=[u.id for u in demo_users]).delete()
        removed["User"] = cnt_usr

    _log(f"Cleared demo records across {len(removed)} entity groups.")
    return removed

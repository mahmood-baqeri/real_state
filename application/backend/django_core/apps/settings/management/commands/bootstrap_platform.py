from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import AgencyMembership, Permission, Role, RolePermission, User
from apps.accounting.models import ChartOfAccount, FiscalPeriod, FiscalYear, JournalEntry
from apps.accounting.services import create_and_post_journal_entry
from apps.agencies.models import Agency, AgencyAccessPolicy
from apps.appointments.models import ViewingAppointment
from apps.branches.models import Branch
from apps.commissions.models import CommissionPolicy, CommissionPolicyVersion
from apps.commissions.services import calculate_deal_commission
from apps.contracts.models import Contract, ContractTemplate
from apps.crm.models import CustomerPipelineItem, FollowUpTask, PipelineStage
from apps.customers.models import Customer, CustomerRequirement
from apps.employees.models import CompensationPlan, EmployeeProfile
from apps.properties.models import (
    Amenity,
    DealType,
    Property,
    PropertyAgentAssignment,
    PropertyLocation,
    PropertyOwner,
    PropertyType,
)
from apps.property_media.models import PropertyMedia
from apps.settings.models import Country, Currency, ProviderConfiguration
from apps.subscriptions.models import AgencySubscription, SubscriptionPlan
from apps.transactions.models import Deal


class Command(BaseCommand):
    help = "Seeds initial localization, RBAC, multi-tenant agencies, properties, CRM, deals, and accounting data."

    @transaction.atomic
    def handle(self, *args, **options):
        now = timezone.now()

        # 1. Countries & Currencies
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

        Currency.objects.get_or_create(
            code="IRT",
            defaults={
                "name_fa": "تومان",
                "name_en": "Iranian Toman",
                "symbol": "تومان",
                "decimal_places": 0,
                "base_unit_factor": Decimal("10.000000"),
            },
        )
        Currency.objects.get_or_create(
            code="IRR",
            defaults={
                "name_fa": "ریال",
                "name_en": "Iranian Rial",
                "symbol": "ریال",
                "decimal_places": 0,
                "base_unit_factor": Decimal("1.000000"),
            },
        )
        Currency.objects.get_or_create(
            code="USD",
            defaults={
                "name_fa": "دلار آمریکا",
                "name_en": "US Dollar",
                "symbol": "$",
                "decimal_places": 2,
                "base_unit_factor": Decimal("1.000000"),
            },
        )

        # 2. Catalog Types
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

        # 3. Permissions & System Roles
        perm_codes = [
            ("agency.manage_policy", "agencies", "مدیریت سیاست‌های دسترسی آژانس"),
            ("agency.manage_branches", "agencies", "مدیریت شعب آژانس"),
            ("property.view_all_agency", "properties", "مشاهده تمام املاک آژانس"),
            ("property.publish", "properties", "تأیید و انتشار عمومی ملک"),
            ("customer.view_all_agency", "customers", "مشاهده تمام مشتریان آژانس"),
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
            code__in=["accounting.view", "accounting.post", "commission.view_all_agency", "deal.view_all_agency"]
        ):
            RolePermission.objects.get_or_create(role=acct_role, permission=p)

        # 4. Demo Users (One per role)
        super_admin, created = User.objects.get_or_create(
            phone_number="09120000001",
            defaults={
                "first_name": "سهراب",
                "last_name": "مدیری (مدیر کل)",
                "email": "admin@realestate-erp.ir",
                "platform_role": User.PlatformRole.SUPER_ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "is_phone_verified": True,
            },
        )
        if created:
            super_admin.set_password("Admin@12345")
            super_admin.save()

        mgr_a, created = User.objects.get_or_create(
            phone_number="09121111111",
            defaults={
                "first_name": "امیرحسین",
                "last_name": "کیانی",
                "email": "manager@parsnegin.ir",
                "platform_role": User.PlatformRole.AGENCY_USER,
                "is_phone_verified": True,
            },
        )
        if created:
            mgr_a.set_password("Manager@12345")
            mgr_a.save()

        agent_a1, created = User.objects.get_or_create(
            phone_number="09122222222",
            defaults={
                "first_name": "نیما",
                "last_name": "فرهادی",
                "email": "nima@parsnegin.ir",
                "platform_role": User.PlatformRole.AGENCY_USER,
                "is_phone_verified": True,
            },
        )
        if created:
            agent_a1.set_password("Agent@12345")
            agent_a1.save()

        mgr_b, created = User.objects.get_or_create(
            phone_number="09123333333",
            defaults={
                "first_name": "مریم",
                "last_name": "شریفی",
                "email": "manager@aryahome.ir",
                "platform_role": User.PlatformRole.AGENCY_USER,
                "is_phone_verified": True,
            },
        )
        if created:
            mgr_b.set_password("Manager@12345")
            mgr_b.save()

        customer_user, created = User.objects.get_or_create(
            phone_number="09124444444",
            defaults={
                "first_name": "آرش",
                "last_name": "صادقی",
                "email": "arash@customer.ir",
                "platform_role": User.PlatformRole.CUSTOMER,
                "is_phone_verified": True,
            },
        )
        if created:
            customer_user.set_password("Customer@12345")
            customer_user.save()

        # 5. Subscription Plans & Providers
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

        # 6. Agencies, Branches & Memberships
        agency_a, _ = Agency.objects.get_or_create(
            slug="pars-negin",
            defaults={
                "name": "گروه مشاورین املاک پارس نگین",
                "registration_number": "IR-TEH-88412",
                "phone": "02122334455",
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
                "is_main": True,
            },
        )
        mem_mgr_a, _ = AgencyMembership.objects.get_or_create(
            user=mgr_a, agency=agency_a, defaults={"role": mgr_role, "branch": branch_a}
        )
        mem_agent_a1, _ = AgencyMembership.objects.get_or_create(
            user=agent_a1, agency=agency_a, defaults={"role": agent_role, "branch": branch_a}
        )

        agency_b, _ = Agency.objects.get_or_create(
            slug="arya-home",
            defaults={
                "name": "آژانس املاک آریا",
                "registration_number": "IR-TEH-99105",
                "phone": "02188776655",
                "owner_user": mgr_b,
                "status": Agency.Status.ACTIVE,
            },
        )
        AgencyAccessPolicy.objects.get_or_create(agency=agency_b)
        AgencyMembership.objects.get_or_create(
            user=mgr_b, agency=agency_b, defaults={"role": mgr_role}
        )

        # 7. Customers & 12-Stage Pipeline
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
                defaults={"name": name, "sort_order": order, "is_terminal_won": won, "is_terminal_lost": lost},
            )
            stages[code] = st

        CustomerPipelineItem.objects.all_tenants().get_or_create(
            agency=agency_a,
            customer=buyer_cust,
            defaults={"stage": stages["VIEWING_SCHEDULED"], "assigned_membership": mem_agent_a1},
        )
        FollowUpTask.objects.all_tenants().get_or_create(
            agency=agency_a,
            customer=buyer_cust,
            assigned_membership=mem_agent_a1,
            title="پیگیری نتیجه بازدید واحد زعفرانیه",
            defaults={"due_at": now + timedelta(hours=18)},
        )

        # 8. Properties (Published + Pending)
        sample_props = [
            {
                "code": "PN-1001",
                "title": "پنت‌هاوس ۱۸۵ متری نوساز در زعفرانیه",
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
                "img": "/images/prop-zafaranieh.jpg",
            },
            {
                "code": "PN-1002",
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
                "img": "/images/prop-office.jpg",
            },
            {
                "code": "PN-1004",
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
                    "branch": branch_a,
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
                prop.amenities.set([amenities["PARKING"], amenities["ELEVATOR"], amenities["STORAGE"]])
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
                    property=prop, membership=mem_agent_a1, role=PropertyAgentAssignment.Role.PRIMARY
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

        # 9. Viewing, Contract, Deal, Commission & Double-Entry Accounting
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

        # Accounting COA + Initial Double-Entry Journal
        fy, _ = FiscalYear.objects.all_tenants().get_or_create(
            agency=agency_a,
            title="سال مالی ۱۴۰۵",
            defaults={"start_date": now - timedelta(days=200), "end_date": now + timedelta(days=165)},
        )
        fp, _ = FiscalPeriod.objects.all_tenants().get_or_create(
            agency=agency_a,
            fiscal_year=fy,
            name="آبان ۱۴۰۵",
            defaults={"start_date": now - timedelta(days=15), "end_date": now + timedelta(days=15)},
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
        if not JournalEntry.objects.all_tenants().filter(agency=agency_a, entry_number="JE-1405-001").exists():
            create_and_post_journal_entry(
                agency=agency_a,
                fiscal_period=fp,
                entry_number="JE-1405-001",
                description="شناسایی کمیسیون معامله DEAL-1405-001",
                lines=[
                    {"account": ar_acc, "debit": Decimal("294000000"), "credit": Decimal("0"), "description": "طلب کمیسیون از طرفین معامله"},
                    {"account": rev_acc, "debit": Decimal("0"), "credit": Decimal("147000000"), "description": "سهم درآمد آژانس (۵۰٪)"},
                    {"account": comm_pay_acc, "debit": Decimal("0"), "credit": Decimal("147000000"), "description": "سهم پورسانت مشاور (۵۰٪)"},
                ],
                source_type="DEAL_COMMISSION",
                source_id=str(deal.id),
                actor=mgr_a,
            )

        # Employee & Compensation Plan
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

        # 10. Additional Currencies & Subscription Plans
        Currency.objects.get_or_create(
            code="EUR",
            defaults={"name_fa": "یورو", "name_en": "Euro", "symbol": "€", "decimal_places": 2, "base_unit_factor": Decimal("1.000000")},
        )
        Currency.objects.get_or_create(
            code="AED",
            defaults={"name_fa": "درهم امارات", "name_en": "UAE Dirham", "symbol": "AED", "decimal_places": 2, "base_unit_factor": Decimal("1.000000")},
        )
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
            },
        )

        # 11. Leads, Negotiations, Treasury, Payroll, Documents, Notifications & Audit
        from apps.accounting.models import BankAccount, CashBox, ChequeInstrument, DealFinancialLedger
        from apps.agencies.models import AgencyCooperation
        from apps.audit.models import AuditLog
        from apps.documents.models import Document, DocumentVersion
        from apps.leads.models import Lead
        from apps.negotiations.models import Negotiation, NegotiationOfferVersion
        from apps.notifications.models import NotificationMessage
        from apps.payments.models import PaymentGatewayTransaction
        from apps.payroll.models import PayrollCycle, Payslip, PayslipLineItem

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

        bank_coa, _ = ChartOfAccount.objects.all_tenants().get_or_create(
            agency=agency_a,
            code="1102",
            defaults={"name": "موجودی بانک‌ها", "account_type": "ASSET"},
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
            defaults={"default_split_percent": Decimal("50.00"), "status": AgencyCooperation.Status.ACTIVE},
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

        self.stdout.write(self.style.SUCCESS("Bootstrap completed successfully."))

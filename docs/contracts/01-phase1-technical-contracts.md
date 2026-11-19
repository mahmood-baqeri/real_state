# قراردادهای فنی جامع ماژول‌های سیستم (Technical Contracts)

این سند قرارداد نهایی مدل‌های دیتابیس، روابط، APIها، مجوزها، قوانین تجاری، ماشین وضعیت و معیارهای پذیرش برای فازهای پیاده‌سازی است.

---

## بخش اول: لایه مشترک و هسته زیرساخت (`common` & `settings`)

### ۱. مدل‌های پایه و بومی‌سازی
- **`BaseModel` (Abstract):** `id (UUIDField, PK)`, `created_at (DateTimeField, UTC)`, `updated_at (DateTimeField, UTC)`, `created_by (FK User, null=True)`, `updated_by (FK User, null=True)`.
- **`TenantScopedModel(BaseModel)` (Abstract):** + `agency (FK Agency, on_delete=PROTECT, db_index=True)`.
- **`SoftDeleteModel` (Mixin):** `is_deleted (bool, default=False)`, `deleted_at (DateTimeField, null=True)`, `deleted_by (FK User, null=True)`.
- **`Country`:** `code (ISO-3166-1 alpha-2, PK)`, `name_fa`, `name_en`, `default_currency_code`, `default_calendar (jalali|gregorian)`, `default_timezone`, `phone_prefix`, `is_active`.
- **`Currency`:** `code (CharField(10), PK: IRT, IRR, USD, EUR, AED)`, `name_fa`, `name_en`, `symbol`, `decimal_places (int)`, `base_unit_factor (Decimal: برای IRT=10 نسبت به IRR)`.
- **`ProviderConfiguration`:** `id`, `agency (nullable=پلتفرم)`, `category (PAYMENT|SMS|MAP)`, `provider_key`, `display_name`, `is_active`, `is_sandbox`, `encrypted_credentials (TextField)`, `config_json (JSONB)`.

### ۲. قوانین تجاری پایه
- تمامی عملیات مالی منحصراً از `Decimal` و `ROUND_HALF_UP` استفاده می‌کنند.
- تبدیل ارز/واحد فقط از طریق `CurrencyConversionService.convert(amount, from_currency, to_currency)` انجام می‌شود.

---

## بخش دوم: احراز هویت، کاربران و RBAC (`accounts`)

### ۱. مدل‌ها و روابط
- **`User`:** `id (UUID)`, `email (unique, nullable)`, `phone_number (unique)`, `first_name`, `last_name`, `national_id_encrypted`, `avatar_url`, `preferred_language (fa|en)`, `preferred_calendar (jalali|gregorian)`, `preferred_currency`, `is_phone_verified`, `is_email_verified`, `is_mfa_enabled`, `mfa_secret_encrypted`, `status (PENDING|ACTIVE|SUSPENDED|BANNED|DELETED)`, `is_staff`, `is_superuser`.
- **`UserSession`:** `id`, `user (FK)`, `jti (UUID, unique)`, `refresh_token_hash`, `device_name`, `ip_address`, `user_agent`, `last_active_at`, `expires_at`, `revoked_at`.
- **`LoginAttemptLog`:** `id`, `identifier`, `user (FK, null=True)`, `ip_address`, `user_agent`, `succeeded`, `failure_reason`, `created_at`.
- **`Role`:** `id`, `code`, `name`, `scope (PLATFORM|AGENCY)`, `agency (FK, null=True)`, `is_system_role`.
- **`Permission`:** `code (unique: e.g. property.view_all_agency)`, `module`, `description`.
- **`RolePermission`:** `role (FK)`, `permission (FK)` (`UNIQUE(role, permission)`).
- **`AgencyMembership`:** `id`, `user (FK)`, `agency (FK)`, `branch (FK, null=True)`, `role (FK Role)`, `status (INVITED|ACTIVE|SUSPENDED|LEFT)`, `joined_at`.
- **`MembershipPermissionOverride`:** `membership (FK)`, `permission (FK)`, `effect (ALLOW|DENY)` (`UNIQUE(membership, permission)`).

### ۲. APIها
- `POST /api/v1/accounts/register/` (ثبت‌نام مشتری یا مدیر آژانس)
- `POST /api/v1/accounts/login/` (ورود با صدور Access + HttpOnly Refresh Cookie)
- `POST /api/v1/accounts/token/refresh/` (چرخش Refresh Token و ابطال توکن قبلی)
- `POST /api/v1/accounts/logout/` (ابطال نشست جاری)
- `GET/DELETE /api/v1/accounts/sessions/` (مشاهده و قطع نشست‌های فعال)
- `POST /api/v1/accounts/otp/request/` و `POST /api/v1/accounts/otp/verify/`
- `POST /api/v1/accounts/mfa/enable/` و `POST /api/v1/accounts/mfa/verify/`
- `GET/PATCH /api/v1/accounts/me/`

### ۳. معیارهای پذیرش
- کاربر مسدود یا تعلیق‌شده بلافاصله امکان Refresh یا دسترسی ندارد.
- پس از ۵ تلاش ناموفق پیاپی در ۱ دقیقه، حساب/IP به‌صورت موقت Rate-Limit می‌شود.

---

## بخش سوم: آژانس‌ها، شعب و سیاست‌های دسترسی (`agencies`, `branches`)

### ۱. مدل‌ها و روابط
- **`Agency`:** `id`, `name`, `slug (unique)`, `registration_number`, `tax_id`, `country (FK)`, `default_currency (FK)`, `default_calendar`, `timezone`, `area_unit (SQM|SQFT)`, `logo_url`, `description`, `status (PENDING_REVIEW|APPROVED|ACTIVE|SUSPENDED|ARCHIVED)`, `owner_user (FK User)`.
- **`Branch`:** `id`, `agency (FK)`, `name`, `code`, `country (FK)`, `province`, `city`, `address`, `latitude`, `longitude`, `phone`, `manager_membership (FK AgencyMembership, null=True)`, `working_hours (JSONB)`, `is_main`, `is_active`.
- **`AgencyAccessPolicy` (1:1 با `Agency`):** تنظیمات مستقل ۱۰گانه سطح آژانس:
  - `property_view_scope` (`OWN_AND_SHARED|PUBLIC_AGENCY|ALL_AGENCY`)
  - `property_edit_scope` (`ASSIGNED_ONLY|BRANCH|ALL_WITH_PERMISSION`)
  - `customer_view_scope` (`ASSIGNED_AND_SHARED|BRANCH|ALL_WITH_PERMISSION`)
  - `customer_edit_scope` (`ASSIGNED_ONLY|SHARED_EDITORS|ALL_WITH_PERMISSION`)
  - `owner_pii_visibility` (`ASSIGNED_AND_MANAGER|MANAGERS_ONLY|PERMISSION_BASED`)
  - `negotiation_visibility` (`ASSIGNED_ONLY|BRANCH|ALL_WITH_PERMISSION`)
  - `contract_visibility` (`ASSIGNED_ONLY|FINANCE_AND_MANAGER|ALL_WITH_PERMISSION`)
  - `financial_visibility` (`MANAGERS_AND_ACCOUNTANT|PERMISSION_BASED`)
  - `commission_visibility` (`OWN_ONLY|TEAM_LEAD|ALL_WITH_PERMISSION`)
  - `agent_performance_visibility` (`OWN_ONLY|RANKING_ONLY|FULL_TEAM`)
- **`AgencyCooperation`:** همکاری بین دو آژانس برای اشتراک فایل (`requester_agency`, `provider_agency`, `status`, `default_split_ratio`).

### ۲. APIها
- `GET/POST /api/v1/agencies/`
- `POST /api/v1/agencies/{id}/approve/` و `/suspend/` (فقط Super Admin)
- `GET/PUT/PATCH /api/v1/agencies/{id}/access-policy/` (فقط Agency Manager)
- `GET/POST /api/v1/agencies/{id}/branches/` و `PATCH /api/v1/branches/{id}/`
- `GET/POST /api/v1/agencies/{id}/memberships/` و `PATCH /api/v1/memberships/{id}/permissions/`

---

## بخش چهارم: املاک و رسانه (`properties`, `property_media`)

### ۱. مدل‌ها و روابط
- **`PropertyType` / `DealType` / `Amenity`:** جداول کاتالوگ قابل تعریف توسط Super Admin و قابل توسعه در آژانس (`slug`, `name_fa`, `name_en`, `schema_json`).
- **`Property` (TenantScopedModel + SoftDelete):**
  - `property_code (UNIQUE(agency, property_code))`
  - `title`, `description`, `property_type (FK)`, `deal_type (FK)`, `usage_type`
  - `branch (FK Branch, null=True)`
  - `status` (`DRAFT|PENDING_APPROVAL|APPROVED|PUBLISHED|RESERVED|UNDER_NEGOTIATION|SOLD|RENTED|EXPIRED|INACTIVE|REJECTED|ARCHIVED`)
  - `visibility` (`PRIVATE_AGENCY|PUBLIC_PORTAL|MLS_SHARED`)
  - مشخصات فیزیکی: `land_area_sqm (Decimal)`, `built_area_sqm (Decimal)`, `bedrooms`, `bathrooms`, `floor_number`, `total_floors`, `units_per_floor`, `building_age`, `construction_year`, `deed_type`, `deed_status`, `orientation`, `facade_type`, `renovation_status`, `evacuation_status`
  - مالی ملک: `currency (FK)`, `total_price (Decimal)`, `price_per_sqm (Decimal)`, `deposit_amount (Decimal)`, `rent_amount (Decimal)`, `is_negotiable (bool)`, `min_acceptable_price (Decimal - محرمانه)`, `price_valid_until`
  - انحصار و آمار: `is_exclusive`, `exclusive_until`, `view_count`, `inquiry_count`
- **`PropertyLocation` (1:1):** `country`, `province`, `city`, `district`, `neighborhood`, `street`, `full_address (محرمانه)`, `postal_code`, `geo_point (Point/lat,lng)`, `hide_exact_address (bool, default=True)`.
- **`PropertyOwner` (M:N با Customer/Person):** `property`, `owner_customer (FK Customer)`, `ownership_share_percent (Decimal)`, `is_primary_contact`.
- **`PropertyAgentAssignment`:** `property`, `membership (FK AgencyMembership)`, `role (PRIMARY|CO_AGENT)`, `assigned_by`.
- **`PropertyMedia`:** `property`, `media_type (IMAGE|VIDEO|FLOORPLAN|VIRTUAL_TOUR|DOC)`, `file_key`, `url`, `is_cover`, `sort_order`, `is_public`.
- **`PropertyPriceHistory` / `PropertyStatusHistory`:** ثبت خودکار تمام تغییرات قیمت و وضعیت با `changed_by` و `reason`.

### ۲. قوانین تجاری و امنیتی
- در خروجی عمومی (`PublicPropertySerializer`) فیلدهای `full_address`, `postal_code`, `min_acceptable_price` و `owners` مطلقاً ارسال نمی‌شوند و مختصات جغرافیایی با گرد/جابه‎جایی ۵۰۰ متری در صورت `hide_exact_address=True` برگردانده می‌شود.
- دسترسی به جزئیات کامل ملک در آژانس بر اساس `AgencyAccessPolicy.property_view_scope` و `owner_pii_visibility` چک شده و مشاهده اطلاعات مالک در `AuditLog` ثبت می‌شود.
- حذف ملکی که در جدول `ViewingAppointment`، `Negotiation` یا `Deal` رکورد دارد به `ARCHIVED` تبدیل می‌شود.

---

## بخش پنجم: مشتریان، سرنخ‌ها، جستجو، بازدید و مذاکره (`customers`, `crm`, `appointments`, `negotiations`)

### ۱. مشتریان و CRM
- **`Customer` (TenantScopedModel):** `customer_type` (خریدار، فروشنده، مستأجر، موجر، سرمایه‌گذار، مالک، متقاضی مشارکت، بالقوه), `full_name`, `primary_phone` (`UNIQUE(agency, primary_phone)`), `secondary_phone`, `email`, `national_id_encrypted`, `source`, `assigned_membership (FK)`, `lead_score`, `readiness_level`, `is_active`.
- **`CustomerShare`:** اشتراک‌گذاری کنترل‌شده مشتری با مشاور دیگر (`customer`, `membership`, `access_level (VIEW|EDIT)`, `granted_by`, `expires_at`).
- **`CustomerRequirement`:** `customer`, `deal_type`, `property_types (M2M)`, `target_cities/districts`, `min_area`, `max_area`, `min_budget`, `max_budget`, `currency`, `min_bedrooms`, `required_amenities`, `priority`.
- **`PipelineStage` & `CustomerPipelineItem`:** ۱۲ مرحله استاندارد + مراحل قابل افزودن توسط مدیر آژانس؛ انتقال مرحله در `CustomerPipelineHistory` ثبت می‌شود.
- **`CustomerInteractionLog` & `FollowUpTask`:** یادداشت‌های خصوصی، ثبت تماس، وظایف پیگیری با سررسید و وضعیت.

### ۲. بازدیدها (`appointments`)
- **`ViewingAppointment`:** `agency`, `property`, `customer`, `agent_membership`, `scheduled_start`, `scheduled_end`, `status (REQUESTED|CONFIRMED|RESCHEDULED|CANCELLED|REJECTED|COMPLETED|NO_SHOW)`, `customer_feedback`, `agent_report`.
- **قانون تعارض:** پیش از ثبت/تأیید/تغییر زمان، با قفل تراکنشی بررسی می‌شود که هیچ بازدید `CONFIRMED` یا `RESCHEDULED` برای همان `agent_membership` یا `property` با بازه `[scheduled_start, scheduled_end)` تداخل نداشته باشد (در غیر این صورت `409 Conflict`).

### ۳. مذاکرات (`negotiations`)
- **`Negotiation`:** `agency`, `property`, `customer`, `agent_membership`, `deal_type`, `status (OPEN|COUNTER_OFFERED|ACCEPTED|REJECTED|WITHDRAWN|EXPIRED)`.
- **`NegotiationOfferVersion`:** `negotiation`, `version_number`, `offered_by (BUYER|SELLER|AGENT)`, `proposed_price`, `proposed_deposit`, `proposed_rent`, `currency`, `payment_terms (JSONB)`, `discount_amount`, `valid_until`, `status`.
- **قانون تبدیل به معامله:** پذیرش یک نسخه (`accept`) سایر نسخه‌های باز را بسته و امکان فراخوانی `POST /api/v1/negotiations/{id}/convert-to-deal/` را فعال می‌کند.

---

## بخش ششم: قراردادها، معاملات، کمیسیون، حسابداری دوطرفه و حقوق (`contracts`, `transactions`, `commissions`, `accounting`, `payroll`)

### ۱. قراردادها و معاملات
- **`ContractTemplate`:** `agency (nullable)`, `country`, `deal_type`, `contract_type`, `title`, `body_template`, `legal_disclaimer`, `is_manager_verified` (شرط اجباری پیش از استفاده قطعی).
- **`Contract`:** `agency`, `contract_number (UNIQUE(agency, contract_number))`, `internal_tracking_code`, `contract_type`, `property`, `deal_type`, `template`, `amount`, `deposit_amount`, `rent_amount`, `advance_payment`, `remaining_amount`, `currency`, `start_date`, `end_date`, `terms_snapshot`, `status (DRAFT|PENDING_REVIEW|PENDING_PARTIES_APPROVAL|SIGNED|ACTIVE|COMPLETED|TERMINATED|EXPIRED|ARCHIVED)`.
- **`Deal`:** پرونده یکپارچه معامله متصل ۱:۱ به `Contract` فعال (`agency`, `contract`, `property`, `primary_agent`, `co_agents`, `deal_value`, `currency`, `status (INITIATED|ACTIVE|SETTLING|CLOSED_WON|VOIDED)`).

### ۲. موتور کمیسیون (`commissions`)
- **`CommissionPolicy` & `CommissionPolicyVersion`:** قوانین نسخه‌بندی‌شده (`version`, `effective_from`, `deal_type`, `formula_type (PERCENT|FIXED|TIERED)`, `rules_json`).
- **`DealCommission` (1:1 با `Deal`, یکتا):** `deal`, `policy_version`, `base_amount`, `gross_commission`, `discount_amount`, `tax_amount`, `net_distributable_commission`, `currency`, `status (CALCULATED|MANAGER_APPROVED|FINANCE_APPROVED|SETTLED|REVERSED)`.
- **`CommissionShare`:** `deal_commission`, `beneficiary_type (PLATFORM|AGENCY|CO_AGENCY|REFERRER|MANAGER|AGENT)`, `beneficiary_membership (nullable)`, `share_percent`, `calculated_amount`, `payable_amount`, `is_included_in_payroll`.

### ۳. حسابداری دوطرفه (`accounting`)
- **`FiscalYear` & `FiscalPeriod`:** دوره‌های مالی آژانس (`OPEN|CLOSED`).
- **`ChartOfAccount`:** درخت کل/معین/تفصیلی (`code`, `name`, `account_type (ASSET|LIABILITY|EQUITY|REVENUE|EXPENSE)`, `normal_balance (DEBIT|CREDIT)`, `parent`).
- **`JournalEntry` & `JournalEntryLine`:**
  - `entry_number (UNIQUE(agency, fiscal_year, entry_number))`, `entry_date`, `status (DRAFT|POSTED|REVERSED)`, `source_type`, `source_id`, `reversed_entry`.
  - قانون غیرقابل نقض: مجموع `debit == credit` در آرتیکل‌ها؛ سند `POSTED` غیرقابل ویرایش/حذف.
- **`BankAccount`, `CashBox`, `ChequeInstrument`, `DealFinancialLedger`:** مدیریت نقدینگی، چک‌های دریافتی/پرداختنی و پرونده مالی هر معامله.

### ۴. حقوق و دستمزد (`employees`, `payroll`)
- **`EmployeeProfile` & `CompensationPlan`:** ۷ مدل همکاری (`FIXED`, `FIXED_PLUS_COMMISSION`, `PURE_COMMISSION`, `TIERED_COMMISSION`, `TARGET_BASED`, `TEAM_OVERRIDE`, `CUSTOM`).
- **`PayrollCycle` & `Payslip` & `PayslipLineItem`:** تجمیع حقوق پایه، پورسانت‌های `FINANCE_APPROVED` مصرف‌نشده، پاداش، اضافه‌کاری، مساعده/وام، بیمه و مالیات با تولید سند حسابداری پس از تأیید نهایی.

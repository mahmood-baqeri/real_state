# سند معماری اصلی و تصمیمات نهایی پلتفرم سازمانی املاک

**نسخه:** 1.1 (نهایی‌شده پس از تصویب تصمیمات معماری)  
**وضعیت:** مصوب — مبنای پیاده‌سازی تمام فازها

---

## ۱. تصمیمات معماری تصویب‌شده

### ۱.۱. بازار هدف، بومی‌سازی، ارز و تقویم (Localization-Agnostic Core)
- **تنظیمات پیش‌فرض نسخه اول:** کشور `IR` (ایران)، زبان `fa` (فارسی با جهت `RTL`)، تقویم نمایشی `jalali` (شمسی)، واحد پول نمایشی `IRT` (تومان) با پشتیبانی کامل از `IRR` (ریال) و سایر ارزها، واحد مساحت `SQM` (مترمربع).
- **الزام عدم وابستگی ساختاری به ایران:**
  - تمامی تاریخ‌ها و زمان‌ها در PostgreSQL به‌صورت استاندارد **UTC (`TIMESTAMPTZ`)** ذخیره می‌شوند.
  - منطق محاسباتی دوره‌ها (گزارش‌ها و حقوق) از طریق لایه `CalendarAdapter` (`JalaliCalendarAdapter` / `GregorianCalendarAdapter`) در Backend محاسبه می‌گردد.
  - مبالغ مالی منحصراً با نوع `Decimal` (`NUMERIC(20, 2)`) همراه با `currency_code` (ISO-4217 یا کد تعریف‌شده در `Currency` مثل `IRT`) ذخیره می‌شوند.
  - تبدیل بین ریال و تومان از طریق `CurrencyConversionService` و ضریب صریح `1 IRT = 10 IRR` بدون هیچ تبدیل ضمنی انجام می‌شود.
  - ساختار `Country`, `Currency`, `LocaleSetting`, `MeasurementUnit`, `TaxJurisdiction` و `LegalJurisdiction` در دیتابیس به‌صورت پویا تعریف می‌شوند.

### ۱.۲. ساختار Workspace و Monorepo (غیرقابل تغییر)
پروژه به‌صورت **Monorepo** استاندارد با فناوری‌های قطعی زیر سازمان‌دهی می‌شود:
- `backend/django_core/`: **Python + Django** (هسته منطق تجاری، مالک دیتابیس و Migrationها، RBAC، Multi-Tenancy و سرویس‌های دامنه؛ بدون Django REST Framework)
- `backend/fastapi_core/`: **Python + FastAPI** (لایه API برای Frontend، با استفاده از Django ORM و سرویس‌های دامنه)
- `frontend/`: **Next.js (App Router) + React + TypeScript + Tailwind CSS** (جایگزین کامل قالب اولیه Vite/React؛ شامل بخش عمومی سئو-محور، پنل مشتری، پنل مشاور، پنل مدیر آژانس و پنل مدیر کل)
- `infra/` و `docker-compose.yml`: **PostgreSQL (+ PostGIS)** به‌عنوان دیتابیس اصلی، **Redis** برای کش/صف/قفل توزیع‌شده، Celery Worker/Beat، و Nginx Reverse Proxy.

### ۱.۳. ارائه‌دهندگان سرویس‌های جانبی (Adapter & Strategy Pattern)
- سه زیرساخت مستقل برای **درگاه پرداخت (`PaymentProviderBase`)**، **سرویس پیامک (`SMSProviderBase`)** و **سرویس نقشه (`MapProviderBase`)** طراحی می‌شود.
- هر آژانس یا پلتفرم می‌تواند چندین پیکربندی ارائه‌دهنده (`ProviderConfiguration`) ثبت و یکی را به‌عنوان ارائه‌دهنده فعال انتخاب کند.
- اسرار و کلیدهای API هر ارائه‌دهنده با رمزنگاری متقارن (Fernet/AES) در دیتابیس یا متغیرهای محیطی امن نگهداری شده و در پاسخ APIهای مدیریتی Mask می‌شوند.
- در محیط توسعه (`development` / `test`) آداپتورهای `SandboxPaymentAdapter`، `ConsoleSMSAdapter` و `OpenStreetMapAdapter` به‌صورت پیش‌فرض فعال هستند.

### ۱.۴. سیاست دسترسی مشاوران و محرمانگی در سطح آژانس
در سطح هر آژانس (`AgencyAccessPolicy` + `AgencyMembership` + `MembershipCustomPermission`) سیاست‌های زیر به‌صورت مستقل و قابل تنظیم در Backend اعمال می‌شوند:
- **املاک:**
  - مشاهده املاک ثبت‌شده توسط خود مشاور و املاک عمومی آژانس (بر اساس سیاست آژانس)
  - مشاهده املاک سایر مشاوران منوط به مجوز `property.view_all_agency`
  - ویرایش فقط برای مشاور مسئول (`PropertyAgentAssignment`) یا افراد دارای مجوز `property.edit_all_agency`
  - تخصیص و انتقال مالکیت پرونده ملک فقط توسط مدیر آژانس یا دارای مجوز `property.assign`
- **مشتریان:**
  - به‌صورت پیش‌فرض مشتری فقط برای مشاور مسئول و مدیر آژانس قابل مشاهده است.
  - مشاوران دیگر بدون مجوز صریح (`customer.view_all_agency` یا اشتراک در `CustomerShare`) به اطلاعات تماس، هویتی، مذاکرات و یادداشت‌های خصوصی دسترسی ندارند.
  - اشتراک‌گذاری کنترل‌شده مشتری با چند مشاور (`CustomerShare`) و انتقال مشتری (`customer.transfer`) توسط مدیر مجاز است.
- **اطلاعات مالک:**
  - اطلاعات هویتی و تماس مالک (`PropertyOwner` / `Customer`) در لایه Serializer/Selector ماسک یا حذف می‌شود، مگر اینکه کاربر مشاور مسئول ملک، مدیر آژانس یا دارای مجوز `owner.view_pii` باشد.
- **تنظیمات دسترسی مستقل آژانس برای ۱۰ حوزه:**
  1. مشاهده املاک
  2. ویرایش املاک
  3. مشاهده مشتریان
  4. ویرایش مشتریان
  5. مشاهده اطلاعات مالک
  6. مشاهده مذاکرات
  7. مشاهده قراردادها
  8. مشاهده اطلاعات مالی
  9. مشاهده کمیسیون‌ها
  10. مشاهده عملکرد سایر مشاوران
- تمام دسترسی‌های حساس (مشاهده اطلاعات مالک، دانلود اسناد محرمانه، مشاهده/ویرایش مالی، تغییر دسترسی و انتقال مشتری/ملک) در `AuditLog` ثبت می‌شوند.

---

## ۲. لایه‌های دفاعی Multi-Tenant و امنیت
1. **Middleware Context:** استخراج `agency_id` از JWT یا هدر `X-Agency-ID` پس از احراز عضویت فعال کاربر در آن آژانس.
2. **ORM Custom Manager (`TenantScopedManager`):** فیلتر خودکار `agency_id` در سطح QuerySetها.
3. **PostgreSQL Row-Level Security (RLS):** اعمال Policy در دیتابیس برای جداول مالی، قراردادی و CRM.
4. **Object-Level Permission + Policy Evaluator:** ارزیابی هم‌زمان نقش، سیاست آژانس (`AgencyAccessPolicy`) و تخصیص/اشتراک‌گذاری رکورد.
5. **Audit Trail:** ثبت غیرقابل تغییر تمام رخدادهای حساس با `actor_id`, `agency_id`, `ip_address`, `action`, `before_state`, `after_state`.

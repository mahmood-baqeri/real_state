# PROJECT CONTEXT

> این فایل به‌صورت خودکار از سورس پروژه تولید شده است. اطلاعات استخراج‌شده از کد از فرضیات جدا شده‌اند.
> نسخه تحلیلگر: 2.0.0 | زمان تولید (UTC): 2026-11-18T06:33:38.385214+00:00
> حالت تحلیل: static source analysis; project code was not executed

## 1. خلاصه پروژه
- نام ریشه پروژه: `application`
- تعداد فایل‌های تحلیل‌شده: 260
- حجم فایل‌های خوانده‌شده: 4,639,010 bytes
- فایل Python: 162 | فایل Frontend: 80
- کلاس Python: 412 | تابع: 534
- مدل‌های شناسایی‌شده: 20 | Routeهای شناسایی‌شده: 180
- خطاها/فایل‌های تحلیل‌نشده: 0

## 2. فناوری‌های شناسایی‌شده
- Django (detected by markers)
- FastAPI (detected by markers)
- JavaScript/React candidate
- Next.js (config detected)
- Node.js ecosystem
- Python
- TypeScript

## 3. ساختار فایل‌ها و پوشه‌ها

```text
├── .env
├── .env.example
├── backend
│   ├── django_core
│   │   ├── apps
│   │   │   ├── accounting
│   │   │   │   ├── apps.py
│   │   │   │   ├── models.py
│   │   │   │   └── services.py
│   │   │   ├── accounts
│   │   │   │   ├── apps.py
│   │   │   │   ├── models.py
│   │   │   │   └── services.py
│   │   │   ├── agencies
│   │   │   │   ├── apps.py
│   │   │   │   ├── models.py
│   │   │   │   └── services.py
│   │   │   ├── ai_assistant
│   │   │   │   ├── __init__.py
│   │   │   │   ├── apps.py
│   │   │   │   ├── models.py
│   │   │   │   └── services.py
│   │   │   ├── appointments
│   │   │   │   ├── apps.py
│   │   │   │   ├── models.py
│   │   │   │   └── services.py
│   │   │   ├── audit
│   │   │   │   ├── apps.py
│   │   │   │   ├── models.py
│   │   │   │   └── services.py
│   │   │   ├── branches
│   │   │   │   ├── apps.py
│   │   │   │   └── models.py
│   │   │   ├── cms
│   │   │   │   ├── __init__.py
│   │   │   │   ├── apps.py
│   │   │   │   ├── models.py
│   │   │   │   └── services.py
│   │   │   ├── commissions
│   │   │   │   ├── apps.py
│   │   │   │   ├── models.py
│   │   │   │   └── services.py
│   │   │   ├── complaints
│   │   │   │   ├── __init__.py
│   │   │   │   ├── apps.py
│   │   │   │   ├── models.py
│   │   │   │   └── services.py
│   │   │   ├── contracts
│   │   │   │   ├── apps.py
│   │   │   │   ├── models.py
│   │   │   │   └── services.py
│   │   │   ├── crm
│   │   │   │   ├── apps.py
│   │   │   │   ├── models.py
│   │   │   │   └── services.py
│   │   │   ├── customers
│   │   │   │   ├── apps.py
│   │   │   │   ├── models.py
│   │   │   │   └── services.py
│   │   │   ├── documents
│   │   │   │   ├── apps.py
│   │   │   │   ├── models.py
│   │   │   │   └── services.py
│   │   │   ├── employees
│   │   │   │   ├── apps.py
│   │   │   │   └── models.py
│   │   │   ├── leads
│   │   │   │   ├── apps.py
│   │   │   │   └── models.py
│   │   │   ├── negotiations
│   │   │   │   ├── apps.py
│   │   │   │   ├── models.py
│   │   │   │   └── services.py
│   │   │   ├── notifications
│   │   │   │   ├── apps.py
│   │   │   │   ├── models.py
│   │   │   │   ├── services.py
│   │   │   │   └── tasks.py
│   │   │   ├── payments
│   │   │   │   ├── apps.py
│   │   │   │   └── models.py
│   │   │   ├── payroll
│   │   │   │   ├── apps.py
│   │   │   │   ├── models.py
│   │   │   │   └── services.py
│   │   │   ├── properties
│   │   │   │   ├── apps.py
│   │   │   │   ├── models.py
│   │   │   │   └── services.py
│   │   │   ├── property_media
│   │   │   │   ├── apps.py
│   │   │   │   └── models.py
│   │   │   ├── reports
│   │   │   │   ├── apps.py
│   │   │   │   └── services.py
│   │   │   ├── search
│   │   │   │   ├── apps.py
│   │   │   │   └── models.py
│   │   │   ├── settings
│   │   │   │   ├── apps.py
│   │   │   │   ├── management
│   │   │   │   │   └── commands
│   │   │   │   │       └── bootstrap_platform.py
│   │   │   │   ├── models.py
│   │   │   │   └── services.py
│   │   │   ├── subscriptions
│   │   │   │   ├── apps.py
│   │   │   │   ├── models.py
│   │   │   │   └── services.py
│   │   │   ├── support
│   │   │   │   ├── __init__.py
│   │   │   │   ├── apps.py
│   │   │   │   ├── models.py
│   │   │   │   └── services.py
│   │   │   ├── surveys
│   │   │   │   ├── __init__.py
│   │   │   │   ├── apps.py
│   │   │   │   ├── models.py
│   │   │   │   └── services.py
│   │   │   └── transactions
│   │   │       ├── apps.py
│   │   │       └── models.py
│   │   ├── common
│   │   │   ├── encryption.py
│   │   │   ├── exceptions.py
│   │   │   ├── idempotency.py
│   │   │   ├── localization
│   │   │   │   ├── calendar.py
│   │   │   │   ├── currency.py
│   │   │   │   └── units.py
│   │   │   ├── models.py
│   │   │   ├── pagination.py
│   │   │   ├── permissions.py
│   │   │   ├── responses.py
│   │   │   └── tenant
│   │   │       ├── context.py
│   │   │       ├── managers.py
│   │   │       ├── middleware.py
│   │   │       └── rls.py
│   │   ├── config
│   │   │   ├── __init__.py
│   │   │   ├── asgi.py
│   │   │   ├── celery.py
│   │   │   ├── settings
│   │   │   │   ├── base.py
│   │   │   │   ├── development.py
│   │   │   │   ├── production.py
│   │   │   │   └── test.py
│   │   │   ├── urls.py
│   │   │   └── wsgi.py
│   │   ├── core
│   │   │   └── __init__.py
│   │   ├── integrations
│   │   │   ├── maps.py
│   │   │   ├── payment.py
│   │   │   ├── registry.py
│   │   │   └── sms.py
│   │   ├── manage.py
│   │   ├── pyproject.toml
│   │   ├── requirements.txt
│   │   ├── services
│   │   │   └── __init__.py
│   │   └── tests
│   │       └── test_enterprise_invariants.py
│   ├── fastapi_core
│   │   ├── api
│   │   │   └── __init__.py
│   │   ├── app
│   │   │   ├── api
│   │   │   │   └── v1
│   │   │   │       ├── accounting.py
│   │   │   │       ├── admin.py
│   │   │   │       ├── agencies.py
│   │   │   │       ├── ai.py
│   │   │   │       ├── appointments.py
│   │   │   │       ├── auth.py
│   │   │   │       ├── cms.py
│   │   │   │       ├── commissions.py
│   │   │   │       ├── complaints.py
│   │   │   │       ├── contracts_deals.py
│   │   │   │       ├── crm.py
│   │   │   │       ├── customers.py
│   │   │   │       ├── documents.py
│   │   │   │       ├── matching.py
│   │   │   │       ├── negotiations.py
│   │   │   │       ├── notifications.py
│   │   │   │       ├── payroll.py
│   │   │   │       ├── properties.py
│   │   │   │       ├── push.py
│   │   │   │       ├── reports_audit.py
│   │   │   │       ├── search.py
│   │   │   │       ├── settings.py
│   │   │   │       ├── subscriptions.py
│   │   │   │       ├── support.py
│   │   │   │       ├── surveys.py
│   │   │   │       └── team.py
│   │   │   ├── core
│   │   │   │   ├── config.py
│   │   │   │   ├── django_bridge.py
│   │   │   │   └── security.py
│   │   │   ├── dependencies
│   │   │   │   └── auth.py
│   │   │   ├── main.py
│   │   │   ├── middleware
│   │   │   │   ├── __init__.py
│   │   │   │   └── request_context.py
│   │   │   ├── schemas
│   │   │   │   └── common.py
│   │   │   └── services
│   │   │       └── matching_service.py
│   │   ├── dependencies
│   │   │   └── __init__.py
│   │   ├── main.py
│   │   ├── middleware
│   │   │   └── __init__.py
│   │   ├── pyproject.toml
│   │   ├── requirements.txt
│   │   ├── schemas
│   │   │   └── __init__.py
│   │   ├── services
│   │   │   └── __init__.py
│   │   └── tests
│   │       └── test_fastapi_engine.py
│   └── run.py
├── frontend
│   ├── README.md
│   ├── metadata.json
│   ├── next-env.d.ts
│   ├── next.config.ts
│   ├── package-lock.json
│   ├── package.json
│   ├── postcss.config.mjs
│   ├── public
│   │   └── images
│   │       ├── prop-fereshteh.jpg
│   │       ├── prop-office.jpg
│   │       ├── prop-villa.jpg
│   │       └── prop-zafaranieh.jpg
│   ├── src
│   │   ├── app
│   │   │   ├── api
│   │   │   │   └── v1
│   │   │   │       └── [...path]
│   │   │   │           └── route.ts
│   │   │   ├── dashboard
│   │   │   │   ├── accounting
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── admin
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── agencies
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── agents
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── appointments
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── audit
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── commissions
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── contracts
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── crm
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── customers
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── deals
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── documents
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── employees
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── layout.tsx
│   │   │   │   ├── leads
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── negotiations
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── notifications
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── page.tsx
│   │   │   │   ├── payroll
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── profile
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── properties
│   │   │   │   │   ├── [id]
│   │   │   │   │   │   └── edit
│   │   │   │   │   │       └── …
│   │   │   │   │   ├── new
│   │   │   │   │   │   └── page.tsx
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── reports
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── roles
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── settings
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── subscriptions
│   │   │   │   │   └── page.tsx
│   │   │   │   └── team
│   │   │   │       └── page.tsx
│   │   │   ├── forgot-password
│   │   │   │   └── page.tsx
│   │   │   ├── layout.tsx
│   │   │   ├── login
│   │   │   │   └── page.tsx
│   │   │   ├── page.tsx
│   │   │   ├── properties
│   │   │   │   └── [id]
│   │   │   │       └── page.tsx
│   │   │   └── register
│   │   │       └── page.tsx
│   │   ├── components
│   │   │   ├── Providers.tsx
│   │   │   ├── layout
│   │   │   │   ├── CommandPalette.tsx
│   │   │   │   ├── DashboardShell.tsx
│   │   │   │   ├── NotificationsDropdown.tsx
│   │   │   │   ├── PublicHeader.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── ThemeToggle.tsx
│   │   │   │   └── TopBar.tsx
│   │   │   ├── properties
│   │   │   │   ├── PropertyCard.tsx
│   │   │   │   └── PropertyForm.tsx
│   │   │   └── ui
│   │   │       ├── AnalyticsCharts.tsx
│   │   │       ├── Avatar.tsx
│   │   │       ├── Badge.tsx
│   │   │       ├── Button.tsx
│   │   │       ├── Card.tsx
│   │   │       ├── DataTable.tsx
│   │   │       ├── DateDisplay.tsx
│   │   │       ├── Dialog.tsx
│   │   │       ├── Drawer.tsx
│   │   │       ├── Input.tsx
│   │   │       ├── Kbd.tsx
│   │   │       ├── KpiCard.tsx
│   │   │       ├── ModalDrawer.tsx
│   │   │       ├── MoneyDisplay.tsx
│   │   │       ├── PageHeader.tsx
│   │   │       ├── Select.tsx
│   │   │       ├── Separator.tsx
│   │   │       ├── Skeleton.tsx
│   │   │       ├── StateNotice.tsx
│   │   │       ├── StatusText.tsx
│   │   │       ├── Toast.tsx
│   │   │       └── Tooltip.tsx
│   │   ├── lib
│   │   │   ├── api-client.ts
│   │   │   ├── auth-context.tsx
│   │   │   ├── formatters.test.ts
│   │   │   ├── formatters.ts
│   │   │   ├── role-navigation.test.ts
│   │   │   ├── role-navigation.ts
│   │   │   ├── theme-provider.tsx
│   │   │   ├── types.ts
│   │   │   ├── use-media-query.ts
│   │   │   └── utils.ts
│   │   └── styles
│   │       ├── globals.css
│   │       ├── theme.css
│   │       └── tokens.css
│   └── tsconfig.json
├── project_analyzer.py
└── project_analyzer_v3.py
```

## 4. تنظیمات و وابستگی‌های پروژه
- `.env`
- `.env.example`
- `backend/django_core/manage.py`
- `backend/django_core/pyproject.toml`
- `backend/django_core/requirements.txt`
- `backend/fastapi_core/pyproject.toml`
- `backend/fastapi_core/requirements.txt`
- `frontend/next.config.ts`
- `frontend/package-lock.json`
- `frontend/package.json`
- `frontend/tsconfig.json`

### متغیرهای محیطی شناسایی‌شده
> مقدارهای حساس حذف شده‌اند.
- `.env`: `DJANGO_SETTINGS_MODULE="config.settings.development"`
- `.env`: `DJANGO_SECRET_KEY=<REDACTED>`
- `.env`: `DJANGO_DEBUG="True"`
- `.env`: `DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,0.0.0.0"`
- `.env`: `DJANGO_FIELD_ENCRYPTION_KEY="dWYDilqzBKu1BAhL4n8KvC2A37bG2OkeYXXL2ZVo2Bc="`
- `.env`: `POSTGRES_DB="realestate_db"`
- `.env`: `POSTGRES_USER="realestate_user"`
- `.env`: `POSTGRES_PASSWORD=<REDACTED>`
- `.env`: `DATABASE_URL="postgresql://realestate_user:realestate_pass@127.0.0.1:5432/realestate_db"`
- `.env`: `USE_LOCAL_SANDBOX_DB="0"`
- `.env`: `REDIS_URL="redis://127.0.0.1:6379/0"`
- `.env`: `CELERY_EAGER="1"`
- `.env`: `JWT_SIGNING_KEY="change-me-shared-jwt-signing-secret"`
- `.env`: `JWT_ACCESS_LIFETIME_MINUTES="15"`
- `.env`: `JWT_REFRESH_LIFETIME_DAYS="7"`
- `.env`: `DEFAULT_COUNTRY="IR"`
- `.env`: `DEFAULT_LANGUAGE="fa"`
- `.env`: `DEFAULT_CALENDAR="jalali"`
- `.env`: `DEFAULT_CURRENCY="IRT"`
- `.env`: `DEFAULT_TIMEZONE="UTC"`
- `.env`: `ACTIVE_PAYMENT_PROVIDER="sandbox"`
- `.env`: `ACTIVE_SMS_PROVIDER="console"`
- `.env`: `ACTIVE_MAP_PROVIDER="osm"`
- `.env`: `CORS_ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"`
- `.env`: `DJANGO_URL="http://127.0.0.1:8010"`
- `.env`: `FASTAPI_URL="http://127.0.0.1:8020"`
- `.env`: `NEXT_PUBLIC_APP_NAME="سامانه سازمانی املاک"`
- `.env`: `NEXT_PUBLIC_DEFAULT_LOCALE="fa"`
- `.env`: `NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:8020"`
- `.env`: `INTERNAL_DJANGO_URL="http://127.0.0.1:8010"`
- `.env`: `INTERNAL_FASTAPI_URL="http://127.0.0.1:8020"`
- `.env`: `GEMINI_API_KEY=<REDACTED>`
- `.env`: `APP_URL="MY_APP_URL"`
- `.env`: `EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend"`
- `.env`: `EMAIL_HOST="smtp.example.com"`
- `.env`: `EMAIL_PORT="587"`
- `.env`: `EMAIL_USE_TLS="True"`
- `.env`: `EMAIL_HOST_USER=""`
- `.env`: `EMAIL_HOST_PASSWORD=<REDACTED>`
- `.env`: `DEFAULT_FROM_EMAIL="noreply@example.com"`
- `.env.example`: `DJANGO_SETTINGS_MODULE="config.settings.local"`
- `.env.example`: `DJANGO_SECRET_KEY=<REDACTED>`
- `.env.example`: `DJANGO_DEBUG="True"`
- `.env.example`: `DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,0.0.0.0"`
- `.env.example`: `DJANGO_FIELD_ENCRYPTION_KEY=""`
- `.env.example`: `POSTGRES_DB="realestate_db"`
- `.env.example`: `POSTGRES_USER="realestate_user"`
- `.env.example`: `POSTGRES_PASSWORD=<REDACTED>`
- `.env.example`: `DATABASE_URL="postgresql://realestate_user:realestate_pass@127.0.0.1:5432/realestate_db"`
- `.env.example`: `USE_LOCAL_SANDBOX_DB="0"`
- `.env.example`: `REDIS_URL="redis://127.0.0.1:6379/0"`
- `.env.example`: `CELERY_EAGER="1"`
- `.env.example`: `JWT_SIGNING_KEY="change-me-shared-jwt-signing-secret"`
- `.env.example`: `JWT_ACCESS_LIFETIME_MINUTES="15"`
- `.env.example`: `JWT_REFRESH_LIFETIME_DAYS="7"`
- `.env.example`: `DEFAULT_COUNTRY="IR"`
- `.env.example`: `DEFAULT_LANGUAGE="fa"`
- `.env.example`: `DEFAULT_CALENDAR="jalali"`
- `.env.example`: `DEFAULT_CURRENCY="IRT"`
- `.env.example`: `DEFAULT_TIMEZONE="UTC"`
- `.env.example`: `ACTIVE_PAYMENT_PROVIDER="sandbox"`
- `.env.example`: `ACTIVE_SMS_PROVIDER="console"`
- `.env.example`: `ACTIVE_MAP_PROVIDER="osm"`
- `.env.example`: `CORS_ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"`
- `.env.example`: `DJANGO_URL="http://127.0.0.1:8010"`
- `.env.example`: `FASTAPI_URL="http://127.0.0.1:8020"`
- `.env.example`: `NEXT_PUBLIC_APP_NAME="سامانه سازمانی املاک"`
- `.env.example`: `NEXT_PUBLIC_DEFAULT_LOCALE="fa"`
- `.env.example`: `NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:8020"`
- `.env.example`: `INTERNAL_DJANGO_URL="http://127.0.0.1:8010"`
- `.env.example`: `INTERNAL_FASTAPI_URL="http://127.0.0.1:8020"`
- `.env.example`: `GEMINI_API_KEY=<REDACTED>`
- `.env.example`: `APP_URL="MY_APP_URL"`
- `.env.example`: `EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend"`
- `.env.example`: `EMAIL_HOST="smtp.example.com"`
- `.env.example`: `EMAIL_PORT="587"`
- `.env.example`: `EMAIL_USE_TLS="True"`
- `.env.example`: `EMAIL_HOST_USER=""`
- `.env.example`: `EMAIL_HOST_PASSWORD=<REDACTED>`
- `.env.example`: `DEFAULT_FROM_EMAIL="noreply@example.com"`

## 5. مدل‌های دیتابیس شناسایی‌شده
### `UserSession` — `backend/django_core/apps/accounts/models.py:95`
- ارث‌بری: models.Model
- `id`: `UUIDField` () primary_key=True, default=uuid.uuid4, editable=False [line 96]
- `jti`: `UUIDField` () unique=True, default=uuid.uuid4 [line 98]
- `device_name`: `CharField` () max_length=128, blank=True, default='Web Browser' [line 99]
- `ip_address`: `GenericIPAddressField` () null=True, blank=True [line 100]
- `user_agent`: `CharField` () max_length=255, blank=True, default='' [line 101]
- `created_at`: `DateTimeField` () default=dj_timezone.now [line 102]
- `last_active_at`: `DateTimeField` () default=dj_timezone.now [line 103]
- `revoked_at`: `DateTimeField` () null=True, blank=True [line 104]
### `LoginAttemptLog` — `backend/django_core/apps/accounts/models.py:110`
- ارث‌بری: models.Model
- `id`: `UUIDField` () primary_key=True, default=uuid.uuid4, editable=False [line 111]
- `identifier`: `CharField` () max_length=128, db_index=True [line 112]
- `ip_address`: `GenericIPAddressField` () null=True, blank=True [line 114]
- `succeeded`: `BooleanField` () default=False [line 115]
- `failure_reason`: `CharField` () max_length=120, blank=True, default='' [line 116]
- `created_at`: `DateTimeField` () default=dj_timezone.now, db_index=True [line 117]
### `Permission` — `backend/django_core/apps/accounts/models.py:123`
- ارث‌بری: models.Model
- `code`: `CharField` () max_length=100, primary_key=True [line 124]
- `module`: `CharField` () max_length=48, db_index=True [line 125]
- `description`: `CharField` () max_length=255 [line 126]
### `Role` — `backend/django_core/apps/accounts/models.py:132`
- ارث‌بری: models.Model
- `id`: `UUIDField` () primary_key=True, default=uuid.uuid4, editable=False [line 137]
- `code`: `CharField` () max_length=64, db_index=True [line 138]
- `name`: `CharField` () max_length=100 [line 139]
- `scope`: `CharField` () max_length=16, choices=Scope.choices, default=Scope.AGENCY [line 140]
- `is_system_role`: `BooleanField` () default=False [line 148]
- `permissions`: `ManyToManyField` (Permission) through='RolePermission', blank=True [line 149]
### `RolePermission` — `backend/django_core/apps/accounts/models.py:158`
- ارث‌بری: models.Model
### `AgencyMembership` — `backend/django_core/apps/accounts/models.py:167`
- ارث‌بری: models.Model
- `id`: `UUIDField` () primary_key=True, default=uuid.uuid4, editable=False [line 174]
- `status`: `CharField` () max_length=16, choices=Status.choices, default=Status.ACTIVE [line 187]
- `joined_at`: `DateTimeField` () default=dj_timezone.now [line 188]
### `MembershipPermissionOverride` — `backend/django_core/apps/accounts/models.py:195`
- ارث‌بری: models.Model
- `effect`: `CharField` () max_length=8, choices=Effect.choices [line 204]
### `AuditLog` — `backend/django_core/apps/audit/models.py:7`
- ارث‌بری: models.Model
- `id`: `UUIDField` () primary_key=True, default=uuid.uuid4, editable=False [line 10]
- `agency_id`: `UUIDField` () null=True, blank=True, db_index=True [line 11]
- `action`: `CharField` () max_length=120, db_index=True [line 19]
- `resource_type`: `CharField` () max_length=80, db_index=True [line 20]
- `resource_id`: `CharField` () max_length=64, blank=True, default='', db_index=True [line 21]
- `ip_address`: `GenericIPAddressField` () null=True, blank=True [line 22]
- `user_agent`: `CharField` () max_length=255, blank=True, default='' [line 23]
- `before_state`: `JSONField` () null=True, blank=True [line 24]
- `after_state`: `JSONField` () null=True, blank=True [line 25]
- `metadata`: `JSONField` () default=dict, blank=True [line 26]
- `created_at`: `DateTimeField` () default=timezone.now, editable=False, db_index=True [line 27]
- توضیح: Append-only immutable audit trail for sensitive operations and access checks.
### `ContractStatusHistory` — `backend/django_core/apps/contracts/models.py:111`
- ارث‌بری: models.Model
- `from_status`: `CharField` () max_length=32 [line 113]
- `to_status`: `CharField` () max_length=32 [line 114]
- `reason`: `CharField` () max_length=255, blank=True, default='' [line 115]
- `changed_at`: `DateTimeField` () auto_now_add=True [line 117]
### `PropertyType` — `backend/django_core/apps/properties/models.py:7`
- ارث‌بری: models.Model
- `code`: `CharField` () max_length=48, primary_key=True [line 8]
- `name_fa`: `CharField` () max_length=80 [line 9]
- `name_en`: `CharField` () max_length=80 [line 10]
- `category`: `CharField` () max_length=32, default='RESIDENTIAL', choices=[('RESIDENTIAL', 'Residential'), ('COMMERCIAL', 'Commercial'), ('LAND', 'Land'), ('INDUSTRIAL', 'Industrial'), ('AGRICULTURAL', 'Agricultural'), ('PROJECT', 'Construction Project')] [line 11]
- `is_active`: `BooleanField` () default=True [line 23]
### `DealType` — `backend/django_core/apps/properties/models.py:29`
- ارث‌بری: models.Model
- `code`: `CharField` () max_length=48, primary_key=True [line 30]
- `name_fa`: `CharField` () max_length=80 [line 31]
- `name_en`: `CharField` () max_length=80 [line 32]
- `is_rental`: `BooleanField` () default=False [line 33]
- `is_active`: `BooleanField` () default=True [line 34]
### `Amenity` — `backend/django_core/apps/properties/models.py:40`
- ارث‌بری: models.Model
- `code`: `CharField` () max_length=48, primary_key=True [line 41]
- `name_fa`: `CharField` () max_length=80 [line 42]
- `name_en`: `CharField` () max_length=80 [line 43]
- `icon_name`: `CharField` () max_length=48, blank=True, default='' [line 44]
### `PropertyLocation` — `backend/django_core/apps/properties/models.py:143`
- ارث‌بری: models.Model
- `property`: `OneToOneField` (Property) on_delete=models.CASCADE, related_name='location' [line 144]
- `province`: `CharField` () max_length=80, db_index=True [line 146]
- `city`: `CharField` () max_length=80, db_index=True [line 147]
- `district`: `CharField` () max_length=80, blank=True, default='', db_index=True [line 148]
- `neighborhood`: `CharField` () max_length=80, blank=True, default='' [line 149]
- `street`: `CharField` () max_length=120, blank=True, default='' [line 150]
- `full_address`: `CharField` () max_length=255, blank=True, default='' [line 151]
- `postal_code`: `CharField` () max_length=20, blank=True, default='' [line 152]
- `latitude`: `DecimalField` () max_digits=9, decimal_places=6, null=True, blank=True [line 153]
- `longitude`: `DecimalField` () max_digits=9, decimal_places=6, null=True, blank=True [line 154]
- `hide_exact_address`: `BooleanField` () default=True [line 155]
### `PropertyPriceHistory` — `backend/django_core/apps/properties/models.py:194`
- ارث‌بری: models.Model
- `previous_price`: `DecimalField` () max_digits=20, decimal_places=2 [line 196]
- `new_price`: `DecimalField` () max_digits=20, decimal_places=2 [line 197]
- `currency_code`: `CharField` () max_length=10, default='IRT' [line 198]
- `changed_at`: `DateTimeField` () auto_now_add=True [line 202]
### `PropertyStatusHistory` — `backend/django_core/apps/properties/models.py:208`
- ارث‌بری: models.Model
- `from_status`: `CharField` () max_length=24 [line 210]
- `to_status`: `CharField` () max_length=24 [line 211]
- `reason`: `CharField` () max_length=255, blank=True, default='' [line 212]
- `changed_at`: `DateTimeField` () auto_now_add=True [line 216]
### `Country` — `backend/django_core/apps/settings/models.py:7`
- ارث‌بری: models.Model
- `code`: `CharField` () max_length=2, primary_key=True [line 8]
- `name_fa`: `CharField` () max_length=100 [line 9]
- `name_en`: `CharField` () max_length=100 [line 10]
- `default_currency_code`: `CharField` () max_length=10, default='IRT' [line 11]
- `default_calendar`: `CharField` () max_length=16, choices=[('jalali', 'Jalali'), ('gregorian', 'Gregorian')], default='jalali' [line 12]
- `default_timezone`: `CharField` () max_length=64, default='Asia/Tehran' [line 17]
- `phone_prefix`: `CharField` () max_length=8, default='+98' [line 18]
- `is_active`: `BooleanField` () default=True [line 19]
### `Currency` — `backend/django_core/apps/settings/models.py:28`
- ارث‌بری: models.Model
- `code`: `CharField` () max_length=10, primary_key=True [line 29]
- `name_fa`: `CharField` () max_length=64 [line 30]
- `name_en`: `CharField` () max_length=64 [line 31]
- `symbol`: `CharField` () max_length=16 [line 32]
- `decimal_places`: `PositiveSmallIntegerField` () default=0 [line 33]
- `base_unit_factor`: `DecimalField` () max_digits=18, decimal_places=6, default=Decimal('1.000000') [line 34]
- `is_active`: `BooleanField` () default=True [line 37]
### `PlatformSetting` — `backend/django_core/apps/settings/models.py:78`
- ارث‌بری: models.Model
- `key`: `CharField` () max_length=128, primary_key=True [line 79]
- `value_json`: `JSONField` () default=dict [line 80]
- `description`: `TextField` () blank=True, default='' [line 81]
- `updated_at`: `DateTimeField` () auto_now=True [line 82]
### `BaseModel` — `backend/django_core/common/models.py:8`
- ارث‌بری: models.Model
- `id`: `UUIDField` () primary_key=True, default=uuid.uuid4, editable=False [line 9]
- `created_at`: `DateTimeField` () default=timezone.now, editable=False, db_index=True [line 10]
- `updated_at`: `DateTimeField` () auto_now=True [line 11]
### `SoftDeleteMixin` — `backend/django_core/common/models.py:31`
- ارث‌بری: models.Model
- `is_deleted`: `BooleanField` () default=False, db_index=True [line 32]
- `deleted_at`: `DateTimeField` () null=True, blank=True [line 33]

## 6. کلاس‌ها و توابع Python
### `project_analyzer.py`
- **class `PythonFileAnalyzer`** (line 134) extends `ast.NodeVisitor`
  - `__init__(self, source, path)` — line 135
  - `analyze(self)` — line 145
  - `visit_Import(self, node)` — line 154
  - `visit_ImportFrom(self, node)` — line 158
  - `visit_ClassDef(self, node)` — line 164
  - `_function(self, node)` — line 190
  - `visit_FunctionDef(self, node)` — line 226
  - `visit_AsyncFunctionDef(self, node)` — line 228
  - `visit_Call(self, node)` — line 231
  - `visit_Assign(self, node)` — line 248
  - `visit_AnnAssign(self, node)` — line 264
- `def rel(path, root)` — line 68
- `def safe_read(path, max_bytes)` — line 71
- `def compact(value, limit)` — line 80
- `def node_text(node)` — line 84
- `def get_call_name(node)` — line 92
- `def literal(node)` — line 102
- `def args_info(args)` — line 110
- `def classify_file(path, root)` — line 278
- `def parse_frontend(source, path)` — line 307
- `def redact_env_line(line)` — line 339
- `def detect_stack(files, config_texts)` — line 348
- `def build_tree(paths, max_depth)` — line 364
- `def analyze_project(root, args)` — line 383
- `def md_escape(value)` — line 524
- `def generate_markdown(data, max_items)` — line 527
- `def main()` — line 636
### `project_analyzer_v3.py`
- `def slug(s)` — line 21
- `def module_for(path)` — line 25
- `def short_tree(paths, max_lines)` — line 35
- `def write_module_docs(root, data, out_dir)` — line 48
- `def make_master(data, module_index, detail_dir_name)` — line 105
- `def main()` — line 152
### `backend/run.py`
- `def main()` — line 11
### `backend/django_core/manage.py`
- `def main()` — line 7
### `backend/django_core/apps/accounting/apps.py`
- **class `AccountingConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/accounting/models.py`
- **class `FiscalYear`** (line 7) extends `TenantScopedModel`
- **class `Meta`** (line 13) extends ``
- **class `FiscalPeriod`** (line 18) extends `TenantScopedModel`
- **class `Meta`** (line 27) extends ``
- **class `ChartOfAccount`** (line 32) extends `TenantScopedModel`
- **class `AccountType`** (line 33) extends `models.TextChoices`
- **class `Level`** (line 40) extends `models.TextChoices`
- **class `Meta`** (line 55) extends ``
- **class `CostCenter`** (line 61) extends `TenantScopedModel`
- **class `Meta`** (line 66) extends ``
- **class `JournalEntry`** (line 71) extends `TenantScopedModel`
  - `save(self, *args, **kwargs)` — line 94
  - `delete(self, *args, **kwargs)` — line 101
- **class `Status`** (line 72) extends `models.TextChoices`
- **class `Meta`** (line 89) extends ``
- **class `JournalEntryLine`** (line 105) extends `BaseModel`
- **class `Meta`** (line 117) extends ``
- **class `BankAccount`** (line 127) extends `TenantScopedModel`
- **class `Meta`** (line 136) extends ``
- **class `CashBox`** (line 140) extends `TenantScopedModel`
- **class `Meta`** (line 147) extends ``
- **class `ChequeInstrument`** (line 151) extends `TenantScopedModel`
- **class `Direction`** (line 152) extends `models.TextChoices`
- **class `Status`** (line 156) extends `models.TextChoices`
- **class `Meta`** (line 173) extends ``
- **class `DealFinancialLedger`** (line 177) extends `TenantScopedModel`
- **class `SettlementStatus`** (line 178) extends `models.TextChoices`
- **class `Meta`** (line 200) extends ``
### `backend/django_core/apps/accounting/services.py`
- `def assert_accounting_view(user, agency_id)` — line 30
- `def assert_accounting_post(user, agency_id)` — line 35
- `def create_and_post_journal_entry(agency, fiscal_period, entry_number, description, lines, currency_id, source_type, source_id, actor)` — line 41
- `def reverse_journal_entry(original_entry, reversal_number, actor)` — line 118
- `def list_coa(user, agency_id)` — line 154
- `def create_coa_account(user, agency_id, data)` — line 164
- `def list_journal_entries(user, agency_id)` — line 179
- `def post_journal_entry_service(user, agency_id, data)` — line 190
- `def reverse_journal_entry_service(user, agency_id, entry_id)` — line 222
- `def list_treasury_and_cheques(user, agency_id)` — line 243
- `def create_cheque(user, agency_id, data)` — line 267
- `def update_cheque_status(user, agency_id, cheque_id, status_value)` — line 283
- `def get_trial_balance(user, agency_id, fiscal_period_id)` — line 300
- `def get_financial_statements(user, agency_id)` — line 365
- `def get_general_ledger(user, agency_id, account_id)` — line 429
- `def list_fiscal_periods(user, agency_id)` — line 485
- `def close_fiscal_period(user, agency_id, period_id)` — line 496
### `backend/django_core/apps/accounts/apps.py`
- **class `AccountsConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/accounts/models.py`
- **class `UserManager`** (line 9) extends `BaseUserManager`
  - `create_user(self, phone_number, password, **extra_fields)` — line 10
  - `create_superuser(self, phone_number, password, **extra_fields)` — line 24
- **class `User`** (line 32) extends `AbstractBaseUser, PermissionsMixin`
  - `full_name(self)` — line 82
  - `set_national_id(self, raw_id)` — line 85
  - `get_national_id(self)` — line 88
  - `can_authenticate(self)` — line 91
- **class `Status`** (line 33) extends `models.TextChoices`
- **class `PlatformRole`** (line 40) extends `models.TextChoices`
- **class `Meta`** (line 78) extends ``
- **class `UserSession`** (line 95) extends `models.Model`
- **class `Meta`** (line 106) extends ``
- **class `LoginAttemptLog`** (line 110) extends `models.Model`
- **class `Meta`** (line 119) extends ``
- **class `Permission`** (line 123) extends `models.Model`
- **class `Meta`** (line 128) extends ``
- **class `Role`** (line 132) extends `models.Model`
- **class `Scope`** (line 133) extends `models.TextChoices`
- **class `Meta`** (line 151) extends ``
- **class `RolePermission`** (line 158) extends `models.Model`
- **class `Meta`** (line 162) extends ``
- **class `AgencyMembership`** (line 167) extends `models.Model`
- **class `Status`** (line 168) extends `models.TextChoices`
- **class `Meta`** (line 190) extends ``
- **class `MembershipPermissionOverride`** (line 195) extends `models.Model`
- **class `Effect`** (line 196) extends `models.TextChoices`
- **class `Meta`** (line 206) extends ``
### `backend/django_core/apps/accounts/services.py`
- `def register_user(phone_number, password, first_name, last_name, email, preferred_language, preferred_calendar, preferred_currency)` — line 31
- `def authenticate_user_credentials(phone_number, password, ip_address, user_agent, device_name)` — line 72
- `def validate_active_session_for_refresh(user_id, jti)` — line 126
- `def rotate_user_session(old_session, new_jti)` — line 136
- `def request_password_reset_otp(phone_number)` — line 143
- `def confirm_password_reset_otp(phone_number, otp_code, new_password)` — line 171
- `def list_user_sessions(user)` — line 197
- `def revoke_user_session(user, session_id)` — line 203
- `def update_user_profile(user, **fields)` — line 210
- `def list_all_users_for_admin(actor)` — line 234
- `def update_user_status_by_admin(actor, target_user_id, status_value)` — line 240
- `def list_roles_and_permissions(agency_id)` — line 263
- `def create_custom_role(actor, agency_id, code, name, permission_codes)` — line 274
- `def add_agency_member(actor, agency_id, phone_number, first_name, last_name, role_code, branch_id, password, email)` — line 309
- `def update_member_role_or_status(actor, agency_id, membership_id, role_code, status_value, branch_id)` — line 368
- `def set_membership_overrides(actor, agency_id, membership_id, overrides)` — line 401
### `backend/django_core/apps/agencies/apps.py`
- **class `AgenciesConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/agencies/models.py`
- **class `Agency`** (line 7) extends `BaseModel, SoftDeleteMixin`
  - `__str__(self)` — line 49
- **class `Status`** (line 8) extends `models.TextChoices`
- **class `Meta`** (line 45) extends ``
- **class `AgencyAccessPolicy`** (line 53) extends `BaseModel`
- **class `PropertyViewScope`** (line 59) extends `models.TextChoices`
- **class `PropertyEditScope`** (line 64) extends `models.TextChoices`
- **class `CustomerViewScope`** (line 69) extends `models.TextChoices`
- **class `CustomerEditScope`** (line 74) extends `models.TextChoices`
- **class `OwnerPIIVisibility`** (line 79) extends `models.TextChoices`
- **class `StandardVisibility`** (line 84) extends `models.TextChoices`
- **class `CommissionVisibility`** (line 89) extends `models.TextChoices`
- **class `PerformanceVisibility`** (line 94) extends `models.TextChoices`
- **class `Meta`** (line 146) extends ``
- **class `AgencyCooperation`** (line 150) extends `BaseModel`
- **class `Status`** (line 151) extends `models.TextChoices`
- **class `Meta`** (line 167) extends ``
### `backend/django_core/apps/agencies/services.py`
- `def list_agencies_for_user(user)` — line 13
- `def get_agency_for_user(user, agency_id)` — line 23
- `def create_agency(owner, name, slug, registration_number, tax_id, phone, email, description, country_id, default_currency_id, default_calendar, timezone_str, area_unit)` — line 31
- `def update_agency_status(actor, agency_id, new_status)` — line 100
- `def get_access_policy(actor, agency_id)` — line 122
- `def update_access_policy(actor, agency_id, updates)` — line 130
- `def list_branches(actor, agency_id)` — line 165
- `def create_branch(actor, agency_id, data)` — line 170
- `def list_agency_members(actor, agency_id)` — line 190
- `def list_cooperations(actor, agency_id)` — line 200
- `def request_cooperation(actor, requester_agency_id, provider_agency_id, split_percent)` — line 211
- `def respond_cooperation(actor, agency_id, coop_id, status_value)` — line 231
### `backend/django_core/apps/ai_assistant/apps.py`
- **class `AiAssistantConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/ai_assistant/models.py`
- **class `AiInteractionLog`** (line 6) extends `BaseModel`
- **class `ToolType`** (line 7) extends `models.TextChoices`
- **class `Meta`** (line 26) extends ``
### `backend/django_core/apps/ai_assistant/services.py`
- `def _assert_ai_access(user, agency_id)` — line 15
- `def draft_property_listing(user, agency_id, property_id, tone)` — line 22
- `def summarize_customer_crm(user, agency_id, customer_id)` — line 73
- `def draft_seo_metadata(user, agency_id, title, body_excerpt, target_city)` — line 121
- `def get_portfolio_insights(user, agency_id)` — line 149
- `def list_ai_logs(user, agency_id)` — line 171
### `backend/django_core/apps/appointments/apps.py`
- **class `AppointmentsConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/appointments/models.py`
- **class `ViewingAppointment`** (line 6) extends `TenantScopedModel`
  - `check_conflict(cls, agent_membership_id, property_id, start_at, end_at, exclude_id)` — line 39
  - `schedule_safely(cls, **kwargs)` — line 64
- **class `Status`** (line 7) extends `models.TextChoices`
- **class `Meta`** (line 31) extends ``
### `backend/django_core/apps/appointments/services.py`
- `def list_appointments(user, agency_id)` — line 16
- `def request_public_viewing(user, property_id, scheduled_start, scheduled_end, notes)` — line 38
- `def create_agency_appointment(user, agency_id, property_id, customer_id, scheduled_start, scheduled_end, agent_membership_id, status_value)` — line 90
- `def transition_appointment_status(user, agency_id, appt_id, new_status, agent_report)` — line 136
### `backend/django_core/apps/audit/apps.py`
- **class `AuditConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/audit/models.py`
- **class `AuditLog`** (line 7) extends `models.Model`
  - `save(self, *args, **kwargs)` — line 37
  - `delete(self, *args, **kwargs)` — line 42
- **class `Meta`** (line 29) extends ``
### `backend/django_core/apps/audit/services.py`
- `def record_audit_event(action, resource_type, resource_id, actor, agency_id, ip_address, user_agent, before_state, after_state, metadata)` — line 9
- `def list_audit_logs(user, agency_id, resource_type, action)` — line 36
### `backend/django_core/apps/branches/apps.py`
- **class `BranchesConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/branches/models.py`
- **class `Branch`** (line 5) extends `TenantScopedModel`
  - `__str__(self)` — line 23
- **class `Meta`** (line 19) extends ``
### `backend/django_core/apps/cms/apps.py`
- **class `CmsConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/cms/models.py`
- **class `ContentCategory`** (line 6) extends `BaseModel`
- **class `Meta`** (line 12) extends ``
- **class `Tag`** (line 17) extends `BaseModel`
- **class `Meta`** (line 21) extends ``
- **class `AuthorProfile`** (line 26) extends `BaseModel`
- **class `Meta`** (line 34) extends ``
- **class `Article`** (line 38) extends `BaseModel`
- **class `ArticleType`** (line 39) extends `models.TextChoices`
- **class `Status`** (line 43) extends `models.TextChoices`
- **class `Meta`** (line 69) extends ``
- **class `ContentVersion`** (line 74) extends `BaseModel`
- **class `Meta`** (line 82) extends ``
- **class `RedirectRule`** (line 88) extends `BaseModel`
- **class `Meta`** (line 94) extends ``
- **class `ContactInquiry`** (line 99) extends `BaseModel`
- **class `InquiryType`** (line 100) extends `models.TextChoices`
- **class `Status`** (line 106) extends `models.TextChoices`
- **class `Meta`** (line 122) extends ``
- **class `AgencyCooperationRequest`** (line 127) extends `BaseModel`
- **class `Status`** (line 128) extends `models.TextChoices`
- **class `Meta`** (line 146) extends ``
- **class `JobOpening`** (line 151) extends `BaseModel`
- **class `Meta`** (line 159) extends ``
- **class `FaqItem`** (line 164) extends `BaseModel`
- **class `Meta`** (line 171) extends ``
### `backend/django_core/apps/cms/services.py`
- `def _assert_cms_editor(user)` — line 40
- `def _assert_cms_approver(user)` — line 50
- `def list_categories()` — line 55
- `def create_category(user, name, slug, description, sort_order)` — line 60
- `def list_public_articles(category_slug, article_type, q)` — line 74
- `def get_public_article(slug)` — line 93
- `def list_cms_articles(user, status_filter)` — line 101
- `def create_article(user, data)` — line 112
- `def update_article(user, article_id, data)` — line 164
- `def transition_article_status(user, article_id, to_status, scheduled_for)` — line 194
- `def list_redirects(active_only)` — line 230
- `def create_redirect(user, from_path, to_path, status_code)` — line 238
- `def submit_contact_inquiry(data)` — line 252
- `def track_contact_inquiry(tracking_code, phone_number)` — line 267
- `def list_contact_inquiries(user)` — line 276
- `def update_contact_inquiry(user, inquiry_id, status_value, staff_response)` — line 282
- `def submit_cooperation_request(data)` — line 296
- `def list_cooperation_requests(user)` — line 313
- `def review_cooperation_request(user, request_id, decision)` — line 319
- `def list_public_jobs()` — line 367
- `def list_public_faqs()` — line 371
### `backend/django_core/apps/commissions/apps.py`
- **class `CommissionsConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/commissions/models.py`
- **class `CommissionPolicy`** (line 7) extends `TenantScopedModel`
- **class `Meta`** (line 12) extends ``
- **class `CommissionPolicyVersion`** (line 17) extends `BaseModel`
- **class `FormulaType`** (line 18) extends `models.TextChoices`
- **class `Meta`** (line 53) extends ``
- **class `DealCommission`** (line 59) extends `TenantScopedModel`
- **class `Status`** (line 60) extends `models.TextChoices`
- **class `Meta`** (line 81) extends ``
- **class `CommissionShare`** (line 85) extends `TenantScopedModel`
- **class `BeneficiaryType`** (line 86) extends `models.TextChoices`
- **class `Meta`** (line 109) extends ``
### `backend/django_core/apps/commissions/services.py`
- `def calculate_deal_commission(deal, policy_version, discount_amount, actor)` — line 17
- `def list_commissions(user, agency_id)` — line 160
- `def list_commission_policies(agency_id)` — line 178
- `def create_commission_policy(user, agency_id, data)` — line 188
- `def calculate_commission_for_deal_service(user, agency_id, deal_id, policy_version_id, discount_amount)` — line 218
- `def update_commission_status(user, agency_id, commission_id, status_value)` — line 244
### `backend/django_core/apps/complaints/apps.py`
- **class `ComplaintsConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/complaints/models.py`
- **class `Complaint`** (line 6) extends `BaseModel`
- **class `TargetType`** (line 7) extends `models.TextChoices`
- **class `Status`** (line 14) extends `models.TextChoices`
- **class `Meta`** (line 50) extends ``
- **class `ComplaintNote`** (line 55) extends `BaseModel`
- **class `Meta`** (line 63) extends ``
### `backend/django_core/apps/complaints/services.py`
- `def _normalize_phone(phone)` — line 12
- `def _can_manage_complaint(user, complaint)` — line 19
- `def list_complaints(user, agency_id, status_filter)` — line 31
- `def create_complaint(user, agency_id, data)` — line 57
- `def track_public_complaint(tracking_code, phone_number)` — line 89
- `def add_complaint_note(user, complaint_id, note, is_confidential)` — line 106
- `def update_complaint_status(user, complaint_id, to_status, resolution_summary, assigned_to_user_id)` — line 122
### `backend/django_core/apps/contracts/apps.py`
- **class `ContractsConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/contracts/models.py`
- **class `ContractTemplate`** (line 8) extends `BaseModel`
- **class `Meta`** (line 26) extends ``
- **class `Contract`** (line 30) extends `TenantScopedModel`
  - `delete(self, *args, **kwargs)` — line 88
- **class `ContractType`** (line 31) extends `models.TextChoices`
- **class `Status`** (line 41) extends `models.TextChoices`
- **class `Meta`** (line 79) extends ``
- **class `ContractParty`** (line 92) extends `BaseModel`
- **class `Role`** (line 93) extends `models.TextChoices`
- **class `Meta`** (line 107) extends ``
- **class `ContractStatusHistory`** (line 111) extends `models.Model`
- **class `Meta`** (line 119) extends ``
### `backend/django_core/apps/contracts/services.py`
- `def list_contract_templates(agency_id)` — line 18
- `def create_contract_template(user, agency_id, data)` — line 28
- `def list_contracts(user, agency_id)` — line 43
- `def create_contract(user, agency_id, data)` — line 65
- `def transition_contract_status(user, agency_id, contract_id, to_status, reason)` — line 112
- `def list_deals(user, agency_id)` — line 139
- `def create_deal(user, agency_id, data)` — line 154
- `def close_deal_won(user, agency_id, deal_id, auto_calculate_commission)` — line 201
- `def get_contract(user, agency_id, contract_id)` — line 224
- `def get_deal(user, agency_id, deal_id)` — line 236
### `backend/django_core/apps/crm/apps.py`
- **class `CrmConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/crm/models.py`
- **class `PipelineStage`** (line 5) extends `TenantScopedModel`
- **class `Meta`** (line 13) extends ``
- **class `CustomerPipelineItem`** (line 19) extends `TenantScopedModel`
- **class `Meta`** (line 32) extends ``
- **class `CustomerInteractionLog`** (line 36) extends `TenantScopedModel`
- **class `Channel`** (line 37) extends `models.TextChoices`
- **class `Meta`** (line 53) extends ``
- **class `FollowUpTask`** (line 58) extends `TenantScopedModel`
- **class `Status`** (line 59) extends `models.TextChoices`
- **class `Meta`** (line 75) extends ``
### `backend/django_core/apps/crm/services.py`
- `def list_pipeline_stages(agency_id)` — line 12
- `def list_pipeline_items(user, agency_id)` — line 16
- `def upsert_pipeline_item(user, agency_id, customer_id, stage_id, property_id, notes)` — line 31
- `def move_pipeline_item_stage(user, agency_id, item_id, stage_id, notes)` — line 60
- `def list_follow_up_tasks(user, agency_id)` — line 75
- `def create_follow_up_task(user, agency_id, customer_id, title, due_at, assigned_membership_id)` — line 90
- `def update_follow_up_task_status(user, agency_id, task_id, status_value)` — line 108
- `def list_interactions(user, agency_id, customer_id)` — line 120
- `def add_interaction_log(user, agency_id, customer_id, channel, summary, is_private)` — line 132
### `backend/django_core/apps/customers/apps.py`
- **class `CustomersConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/customers/models.py`
- **class `Customer`** (line 8) extends `TenantScopedModel, SoftDeleteMixin`
  - `set_national_id(self, raw)` — line 60
  - `get_national_id(self)` — line 63
- **class `CustomerType`** (line 9) extends `models.TextChoices`
- **class `Meta`** (line 51) extends ``
- **class `CustomerShare`** (line 67) extends `BaseModel`
- **class `AccessLevel`** (line 68) extends `models.TextChoices`
- **class `Meta`** (line 81) extends ``
- **class `CustomerRequirement`** (line 86) extends `TenantScopedModel`
- **class `Meta`** (line 102) extends ``
### `backend/django_core/apps/customers/services.py`
- `def list_customers(user, agency_id, q, customer_type)` — line 19
- `def create_customer(user, agency_id, data)` — line 48
- `def update_customer(user, agency_id, customer_id, data)` — line 82
- `def share_customer(user, agency_id, customer_id, target_membership_id, access_level)` — line 100
- `def add_customer_requirement(user, agency_id, customer_id, data)` — line 126
- `def list_leads(user, agency_id, status_filter, q)` — line 148
- `def create_lead(user, agency_id, data)` — line 167
- `def update_lead_status(user, agency_id, lead_id, status_value, notes)` — line 184
- `def convert_lead_to_customer(user, agency_id, lead_id)` — line 197
### `backend/django_core/apps/documents/apps.py`
- **class `DocumentsConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/documents/models.py`
- **class `Document`** (line 6) extends `TenantScopedModel`
- **class `AccessLevel`** (line 7) extends `models.TextChoices`
- **class `Meta`** (line 28) extends ``
- **class `DocumentVersion`** (line 32) extends `BaseModel`
- **class `Meta`** (line 39) extends ``
- **class `DocumentDownloadLog`** (line 44) extends `BaseModel`
- **class `Meta`** (line 49) extends ``
### `backend/django_core/apps/documents/services.py`
- `def list_documents(user, agency_id, category)` — line 11
- `def create_document(user, agency_id, data)` — line 32
- `def log_document_download(user, agency_id, document_id, ip_address)` — line 65
### `backend/django_core/apps/employees/apps.py`
- **class `EmployeesConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/employees/models.py`
- **class `EmployeeProfile`** (line 6) extends `TenantScopedModel`
- **class `EmploymentType`** (line 7) extends `models.TextChoices`
- **class `Meta`** (line 26) extends ``
- **class `CompensationPlan`** (line 31) extends `TenantScopedModel`
- **class `ModelType`** (line 32) extends `models.TextChoices`
- **class `Meta`** (line 56) extends ``
### `backend/django_core/apps/leads/apps.py`
- **class `LeadsConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/leads/models.py`
- **class `Lead`** (line 5) extends `TenantScopedModel`
- **class `Status`** (line 6) extends `models.TextChoices`
- **class `Meta`** (line 29) extends ``
### `backend/django_core/apps/negotiations/apps.py`
- **class `NegotiationsConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/negotiations/models.py`
- **class `Negotiation`** (line 6) extends `TenantScopedModel`
- **class `Status`** (line 7) extends `models.TextChoices`
- **class `Meta`** (line 28) extends ``
- **class `NegotiationOfferVersion`** (line 33) extends `BaseModel`
- **class `OfferedBy`** (line 34) extends `models.TextChoices`
- **class `Status`** (line 39) extends `models.TextChoices`
- **class `Meta`** (line 59) extends ``
### `backend/django_core/apps/negotiations/services.py`
- `def list_negotiations(user, agency_id)` — line 13
- `def create_negotiation(user, agency_id, data)` — line 33
- `def add_offer_version(user, agency_id, negotiation_id, data)` — line 69
- `def respond_to_negotiation(user, agency_id, negotiation_id, status_value)` — line 97
### `backend/django_core/apps/notifications/apps.py`
- **class `NotificationsConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/notifications/models.py`
- **class `NotificationMessage`** (line 6) extends `BaseModel`
- **class `Channel`** (line 7) extends `models.TextChoices`
- **class `DeliveryStatus`** (line 13) extends `models.TextChoices`
- **class `Meta`** (line 35) extends ``
- **class `PushSubscription`** (line 40) extends `BaseModel`
- **class `Meta`** (line 54) extends ``
- **class `NotificationPreference`** (line 59) extends `BaseModel`
- **class `Meta`** (line 70) extends ``
### `backend/django_core/apps/notifications/services.py`
- `def get_vapid_public_key()` — line 15
- `def list_notifications_for_user(user, unread_only)` — line 25
- `def send_notification(recipient_user_id, title, body, channel, agency_id, actor)` — line 33
- `def mark_notification_read(user, notification_id)` — line 79
- `def mark_all_notifications_read(user)` — line 89
- `def register_push_subscription(user, agency_id, endpoint, p256dh, auth, device_label)` — line 96
- `def unregister_push_subscription(user, endpoint)` — line 113
- `def list_user_push_subscriptions(user)` — line 117
- `def get_or_create_preferences(user)` — line 121
- `def update_preferences(user, updates)` — line 127
### `backend/django_core/apps/notifications/tasks.py`
- `def dispatch_web_push_task(subscription_id, title, body, url)` — line 6
### `backend/django_core/apps/payments/apps.py`
- **class `PaymentsConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/payments/models.py`
- **class `PaymentGatewayTransaction`** (line 5) extends `BaseModel`
- **class `Status`** (line 6) extends `models.TextChoices`
- **class `Meta`** (line 26) extends ``
### `backend/django_core/apps/payroll/apps.py`
- **class `PayrollConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/payroll/models.py`
- **class `PayrollCycle`** (line 6) extends `TenantScopedModel`
- **class `Status`** (line 7) extends `models.TextChoices`
- **class `Meta`** (line 18) extends ``
- **class `Payslip`** (line 23) extends `TenantScopedModel`
- **class `Status`** (line 24) extends `models.TextChoices`
- **class `Meta`** (line 48) extends ``
- **class `PayslipLineItem`** (line 53) extends `BaseModel`
- **class `ItemType`** (line 54) extends `models.TextChoices`
- **class `Meta`** (line 75) extends ``
### `backend/django_core/apps/payroll/services.py`
- `def list_employees(user, agency_id)` — line 16
- `def create_employee_profile(user, agency_id, data)` — line 29
- `def create_compensation_plan(user, agency_id, employee_id, data)` — line 61
- `def list_payroll_cycles(user, agency_id)` — line 84
- `def create_and_calculate_payroll_cycle(user, agency_id, title, period_start, period_end)` — line 104
- `def update_payroll_cycle_status(user, agency_id, cycle_id, status_value)` — line 197
### `backend/django_core/apps/properties/apps.py`
- **class `PropertiesConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/properties/models.py`
- **class `PropertyType`** (line 7) extends `models.Model`
- **class `Meta`** (line 25) extends ``
- **class `DealType`** (line 29) extends `models.Model`
- **class `Meta`** (line 36) extends ``
- **class `Amenity`** (line 40) extends `models.Model`
- **class `Meta`** (line 46) extends ``
- **class `Property`** (line 50) extends `TenantScopedModel, SoftDeleteMixin`
  - `recalculate_price_per_sqm(self)` — line 137
- **class `Status`** (line 51) extends `models.TextChoices`
- **class `Visibility`** (line 65) extends `models.TextChoices`
- **class `Meta`** (line 124) extends ``
- **class `PropertyLocation`** (line 143) extends `models.Model`
- **class `Meta`** (line 157) extends ``
- **class `PropertyOwner`** (line 161) extends `BaseModel`
- **class `Meta`** (line 171) extends ``
- **class `PropertyAgentAssignment`** (line 176) extends `BaseModel`
- **class `Role`** (line 177) extends `models.TextChoices`
- **class `Meta`** (line 189) extends ``
- **class `PropertyPriceHistory`** (line 194) extends `models.Model`
- **class `Meta`** (line 204) extends ``
- **class `PropertyStatusHistory`** (line 208) extends `models.Model`
- **class `Meta`** (line 218) extends ``
### `backend/django_core/apps/properties/services.py`
- `def get_property_catalog()` — line 32
- `def list_public_properties(city, district, deal_type, property_type, min_price, max_price, min_area, min_bedrooms, q, featured_only)` — line 40
- `def list_agency_properties(user, agency_id, status_filter, deal_type, property_type, q)` — line 92
- `def get_property_for_context(user, agency_id, property_id)` — line 149
- `def serialize_property_owners(user, prop)` — line 161
- `def create_property(user, agency_id, data)` — line 180
- `def update_property(user, agency_id, property_id, data)` — line 271
- `def soft_delete_property(user, agency_id, property_id)` — line 323
- `def transition_property_status(user, agency_id, property_id, to_status, reason)` — line 340
- `def add_property_media(user, agency_id, property_id, media_type, url, title, is_cover, is_public)` — line 379
- `def delete_property_media(user, agency_id, property_id, media_id)` — line 402
### `backend/django_core/apps/property_media/apps.py`
- **class `PropertyMediaConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/property_media/models.py`
- **class `PropertyMedia`** (line 5) extends `BaseModel`
- **class `MediaType`** (line 6) extends `models.TextChoices`
- **class `Meta`** (line 24) extends ``
### `backend/django_core/apps/reports/apps.py`
- **class `ReportsConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/reports/services.py`
- `def get_dashboard_summary(user, agency_id, period_days)` — line 30
- `def get_agency_analytics(user, agency_id, period_days)` — line 360
### `backend/django_core/apps/search/apps.py`
- **class `SearchConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/search/models.py`
- **class `SavedSearch`** (line 6) extends `BaseModel`
- **class `Meta`** (line 14) extends ``
### `backend/django_core/apps/settings/apps.py`
- **class `SettingsConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/settings/models.py`
- **class `Country`** (line 7) extends `models.Model`
  - `__str__(self)` — line 24
- **class `Meta`** (line 21) extends ``
- **class `Currency`** (line 28) extends `models.Model`
  - `__str__(self)` — line 42
- **class `Meta`** (line 39) extends ``
- **class `ProviderConfiguration`** (line 46) extends `BaseModel`
  - `set_credentials(self, raw_json)` — line 71
  - `get_credentials(self)` — line 74
- **class `Category`** (line 47) extends `models.TextChoices`
- **class `Meta`** (line 67) extends ``
- **class `PlatformSetting`** (line 78) extends `models.Model`
- **class `Meta`** (line 84) extends ``
### `backend/django_core/apps/settings/services.py`
- `def get_localization_metadata()` — line 13
- `def list_provider_configs(user, agency_id)` — line 26
- `def upsert_provider_config(user, agency_id, data)` — line 37
### `backend/django_core/apps/settings/management/commands/bootstrap_platform.py`
- **class `Command`** (line 33) extends `BaseCommand`
  - `handle(self, *args, **options)` — line 37
### `backend/django_core/apps/subscriptions/apps.py`
- **class `SubscriptionsConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/subscriptions/models.py`
- **class `SubscriptionPlan`** (line 6) extends `BaseModel`
- **class `Meta`** (line 19) extends ``
- **class `AgencySubscription`** (line 23) extends `BaseModel`
- **class `Status`** (line 24) extends `models.TextChoices`
- **class `Meta`** (line 42) extends ``
### `backend/django_core/apps/subscriptions/services.py`
- `def list_subscription_plans()` — line 16
- `def list_agency_subscriptions(user, agency_id)` — line 20
- `def list_payment_transactions(user, agency_id)` — line 29
- `def initiate_subscription_payment(user, agency_id, plan_code, billing_cycle, provider_key)` — line 39
- `def verify_subscription_payment(user, agency_id, authority)` — line 91
### `backend/django_core/apps/support/apps.py`
- **class `SupportConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/support/models.py`
- **class `Ticket`** (line 6) extends `BaseModel`
- **class `Scope`** (line 7) extends `models.TextChoices`
- **class `Category`** (line 11) extends `models.TextChoices`
- **class `Priority`** (line 18) extends `models.TextChoices`
- **class `Status`** (line 24) extends `models.TextChoices`
- **class `Meta`** (line 55) extends ``
- **class `TicketMessage`** (line 60) extends `BaseModel`
- **class `Meta`** (line 68) extends ``
- **class `TicketAttachment`** (line 73) extends `BaseModel`
- **class `Meta`** (line 80) extends ``
- **class `TicketStatusHistory`** (line 84) extends `BaseModel`
- **class `Meta`** (line 93) extends ``
- **class `CannedReply`** (line 98) extends `BaseModel`
- **class `Meta`** (line 107) extends ``
### `backend/django_core/apps/support/services.py`
- `def _is_support_staff(user, ticket)` — line 27
- `def list_tickets(user, agency_id, scope, status_filter)` — line 37
- `def get_ticket(user, agency_id, ticket_id)` — line 60
- `def create_ticket(user, agency_id, data)` — line 80
- `def add_ticket_message(user, agency_id, ticket_id, data)` — line 134
- `def update_ticket_status(user, agency_id, ticket_id, to_status, note)` — line 173
- `def assign_ticket(user, agency_id, ticket_id, assignee_user_id)` — line 193
- `def submit_ticket_rating(user, agency_id, ticket_id, rating, comment)` — line 208
- `def list_canned_replies(user, agency_id)` — line 222
- `def create_canned_reply(user, agency_id, data)` — line 232
- `def get_ticket_report(user, agency_id)` — line 246
### `backend/django_core/apps/surveys/apps.py`
- **class `SurveysConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/surveys/models.py`
- **class `Survey`** (line 6) extends `BaseModel`
- **class `TargetAudience`** (line 7) extends `models.TextChoices`
- **class `CrmTriggerEvent`** (line 13) extends `models.TextChoices`
- **class `Meta`** (line 36) extends ``
- **class `SurveyQuestion`** (line 41) extends `BaseModel`
- **class `QuestionType`** (line 42) extends `models.TextChoices`
- **class `Meta`** (line 59) extends ``
- **class `SurveyResponse`** (line 64) extends `BaseModel`
- **class `Meta`** (line 73) extends ``
- **class `SurveyAnswer`** (line 79) extends `BaseModel`
- **class `Meta`** (line 86) extends ``
### `backend/django_core/apps/surveys/services.py`
- `def _assert_survey_admin(user, agency_id)` — line 18
- `def list_surveys(user, agency_id, public_only)` — line 28
- `def get_survey_by_slug(slug)` — line 42
- `def get_survey_by_id(user, agency_id, survey_id)` — line 49
- `def create_survey(user, agency_id, data)` — line 60
- `def submit_survey_response(slug, user, respondent_identifier, respondent_name, answers)` — line 102
- `def get_survey_analytics(user, agency_id, survey_id)` — line 174
- `def compare_surveys(user, agency_id)` — line 234
### `backend/django_core/apps/transactions/apps.py`
- **class `TransactionsConfig`** (line 4) extends `AppConfig`
### `backend/django_core/apps/transactions/models.py`
- **class `Deal`** (line 7) extends `TenantScopedModel`
  - `delete(self, *args, **kwargs)` — line 53
- **class `Status`** (line 8) extends `models.TextChoices`
- **class `Meta`** (line 44) extends ``
### `backend/django_core/common/encryption.py`
- `def _get_fernet()` — line 7
- `def encrypt_sensitive_value(plaintext)` — line 19
- `def decrypt_sensitive_value(ciphertext)` — line 25
### `backend/django_core/common/exceptions.py`
- **class `DomainError`** (line 1) extends `Exception`
  - `__init__(self, message, code, status_code, extra)` — line 7
- **class `ValidationDomainError`** (line 17) extends `DomainError`
- **class `AuthenticationDomainError`** (line 22) extends `DomainError`
- **class `PermissionDeniedDomainError`** (line 27) extends `DomainError`
- **class `NotFoundDomainError`** (line 32) extends `DomainError`
- **class `ConflictDomainError`** (line 37) extends `DomainError`
### `backend/django_core/common/idempotency.py`
- `def check_and_store_idempotency_key(scope, key, ttl_seconds)` — line 4
### `backend/django_core/common/models.py`
- **class `BaseModel`** (line 8) extends `models.Model`
- **class `Meta`** (line 27) extends ``
- **class `SoftDeleteMixin`** (line 31) extends `models.Model`
  - `soft_delete(self, user)` — line 45
- **class `Meta`** (line 42) extends ``
- **class `TenantScopedModel`** (line 52) extends `BaseModel`
- **class `Meta`** (line 62) extends ``
### `backend/django_core/common/pagination.py`
- `def paginate_queryset(qs, page, page_size, serializer_fn)` — line 6
- `def paginate_list(items, page, page_size)` — line 31
### `backend/django_core/common/permissions.py`
- `def is_super_admin(user)` — line 6
- `def get_active_membership(user, agency_id)` — line 14
- `def get_effective_permissions(user, agency_id)` — line 25
- `def has_agency_permission(user, agency_id, permission_code)` — line 44
- `def get_agency_policy(agency_id)` — line 62
- `def can_view_owner_pii(user, agency_id, is_assigned_agent)` — line 69
- `def can_edit_property(user, prop)` — line 85
- `def can_edit_customer(user, customer)` — line 104
### `backend/django_core/common/responses.py`
- `def build_api_envelope(data, success, meta, errors)` — line 4
### `backend/django_core/common/localization/calendar.py`
- **class `CalendarAdapter`** (line 6) extends ``
  - `format_date(dt, calendar_type)` — line 13
  - `jalali_month_bounds_utc(jy, jm)` — line 21
  - `gregorian_month_bounds_utc(gy, gm)` — line 32
### `backend/django_core/common/localization/currency.py`
- **class `CurrencyConversionService`** (line 24) extends ``
  - `convert_rial_toman(amount, from_currency, to_currency)` — line 28
  - `convert_with_rate(amount, rate, to_currency)` — line 40
- `def quantize_amount(amount, currency_code)` — line 18
### `backend/django_core/common/localization/units.py`
- **class `AreaUnitConverter`** (line 10) extends ``
  - `to_sqm(value, from_unit)` — line 12
  - `from_sqm(sqm_value, to_unit)` — line 19
### `backend/django_core/common/tenant/context.py`
- `def set_current_agency_id(agency_id)` — line 10
- `def get_current_agency_id()` — line 14
- `def is_tenant_bypassed()` — line 18
- `def tenant_bypass()` — line 23
- `def scoped_agency(agency_id)` — line 33
### `backend/django_core/common/tenant/managers.py`
- **class `TenantScopedQuerySet`** (line 5) extends `models.QuerySet`
  - `active_only(self)` — line 6
- **class `TenantScopedManager`** (line 12) extends `models.Manager`
  - `get_queryset(self)` — line 15
  - `all_tenants(self)` — line 25
### `backend/django_core/common/tenant/middleware.py`
- **class `TenantContextMiddleware`** (line 7) extends ``
  - `__init__(self, get_response)` — line 13
  - `__call__(self, request)` — line 16
### `backend/django_core/common/tenant/rls.py`
- `def generate_rls_policy_sql(table_name, agency_column)` — line 4
### `backend/django_core/config/settings/base.py`
- `def parse_database_url(url)` — line 89
### `backend/django_core/integrations/maps.py`
- **class `GeoCoordinate`** (line 9) extends ``
- **class `MapClientConfig`** (line 15) extends ``
- **class `MapProviderBase`** (line 21) extends `ABC`
  - `geocode(self, address, country_code)` — line 25
  - `get_client_tile_config(self)` — line 29
  - `haversine_meters(a, b)` — line 33
- **class `OpenStreetMapAdapter`** (line 46) extends `MapProviderBase`
  - `geocode(self, address, country_code)` — line 49
  - `get_client_tile_config(self)` — line 53
### `backend/django_core/integrations/payment.py`
- **class `PaymentInitResult`** (line 8) extends ``
- **class `PaymentVerifyResult`** (line 15) extends ``
- **class `PaymentProviderBase`** (line 23) extends `ABC`
  - `create_payment_intent(self, amount, currency, callback_url, metadata)` — line 27
  - `verify_payment(self, authority, expected_amount, currency)` — line 37
- **class `SandboxPaymentAdapter`** (line 46) extends `PaymentProviderBase`
  - `create_payment_intent(self, amount, currency, callback_url, metadata)` — line 49
  - `verify_payment(self, authority, expected_amount, currency)` — line 63
### `backend/django_core/integrations/registry.py`
- `def get_payment_provider(provider_key)` — line 19
- `def get_sms_provider(provider_key)` — line 27
- `def get_map_provider(provider_key)` — line 35
### `backend/django_core/integrations/sms.py`
- **class `SMSDeliveryResult`** (line 10) extends ``
- **class `SMSProviderBase`** (line 16) extends `ABC`
  - `send_sms(self, phone_number, message, sender_line)` — line 20
  - `send_otp(self, phone_number, template_key, tokens)` — line 26
- **class `ConsoleSMSAdapter`** (line 32) extends `SMSProviderBase`
  - `send_sms(self, phone_number, message, sender_line)` — line 35
  - `send_otp(self, phone_number, template_key, tokens)` — line 45
### `backend/django_core/tests/test_enterprise_invariants.py`
- `def seed_base(db)` — line 28
- `def test_1_multi_tenant_isolation_agent_a_cannot_access_agency_b(seed_base)` — line 72
- `def test_2_customer_cannot_access_accounting_service(seed_base)` — line 89
- `def test_3_public_portal_only_exposes_published_public_properties(seed_base)` — line 94
- `def test_4_double_entry_balance_and_reversal(seed_base)` — line 128
- `def test_5_commission_precision_and_agent_cannot_approve(seed_base)` — line 172
- `def test_6_viewing_conflict_lead_conversion_and_otp_reset(seed_base)` — line 228
- `def test_localization_currency_and_jalali_adapter()` — line 279
- `def test_7_accounting_statements_general_ledger_and_period_close(seed_base)` — line 286
- `def test_8_dashboard_summary_role_and_period_filter(seed_base)` — line 372
- `def test_9_tickets_complaints_surveys_and_ai_isolation(seed_base)` — line 392
- `def test_10_cms_workflow_redirects_and_agency_cooperation_approval(seed_base)` — line 546
### `backend/fastapi_core/app/main.py`
- `async def lifespan(_app)` — line 43
- `async def domain_error_handler(_request, exc)` — line 67
- `async def django_validation_handler(_request, exc)` — line 81
- `async def health()` — line 126
### `backend/fastapi_core/app/api/v1/accounting.py`
- **class `CoaCreateBody`** (line 14) extends `BaseModel`
- **class `JournalLineBody`** (line 22) extends `BaseModel`
- **class `JournalEntryCreateBody`** (line 29) extends `BaseModel`
- **class `ChequeCreateBody`** (line 37) extends `BaseModel`
- **class `ChequeStatusBody`** (line 47) extends `BaseModel`
- `def _ser_journal_entry(je)` — line 51
- `async def list_coa_endpoint(ctx)` — line 76
- `async def create_coa_endpoint(body, ctx)` — line 96
- `async def list_journal_entries_endpoint(page, page_size, ctx)` — line 109
- `async def post_journal_entry_endpoint(body, ctx)` — line 128
- `async def reverse_journal_entry_endpoint(entry_id, ctx)` — line 143
- `async def list_treasury_endpoint(ctx)` — line 158
- `async def create_cheque_endpoint(body, ctx)` — line 221
- `async def patch_cheque_endpoint(cheque_id, body, ctx)` — line 234
- `async def trial_balance_endpoint(fiscal_period_id, ctx)` — line 249
- `async def financial_statements_endpoint(ctx)` — line 264
- `async def general_ledger_endpoint(account_id, ctx)` — line 274
- `async def list_fiscal_periods_endpoint(ctx)` — line 286
- `async def close_fiscal_period_endpoint(period_id, ctx)` — line 306
### `backend/fastapi_core/app/api/v1/admin.py`
- **class `UserStatusBody`** (line 11) extends `BaseModel`
- `async def admin_list_users(page, page_size, ctx)` — line 16
- `async def admin_update_user_status(user_id, body, ctx)` — line 47
- `async def admin_list_subscriptions(ctx)` — line 62
### `backend/fastapi_core/app/api/v1/agencies.py`
- **class `AgencyCreateBody`** (line 13) extends `BaseModel`
- **class `AgencyStatusBody`** (line 28) extends `BaseModel`
- **class `AccessPolicyPatchBody`** (line 32) extends `BaseModel`
- **class `BranchCreateBody`** (line 45) extends `BaseModel`
- **class `CooperationCreateBody`** (line 56) extends `BaseModel`
- **class `CooperationRespondBody`** (line 61) extends `BaseModel`
- `def _ser_agency(a)` — line 65
- `def _ser_policy(p)` — line 86
- `async def list_agencies(page, page_size, ctx)` — line 104
- `async def create_agency_endpoint(body, ctx)` — line 121
- `async def get_agency(agency_id, ctx)` — line 134
- `async def update_agency_status_endpoint(agency_id, body, ctx)` — line 144
- `async def get_policy(agency_id, ctx)` — line 156
- `async def patch_policy(agency_id, body, ctx)` — line 166
- `async def list_branches_endpoint(agency_id, ctx)` — line 180
- `async def create_branch_endpoint(agency_id, body, ctx)` — line 203
- `async def list_members_endpoint(agency_id, ctx)` — line 223
- `async def list_cooperations_endpoint(agency_id, ctx)` — line 247
- `async def create_cooperation_endpoint(agency_id, body, ctx)` — line 268
- `async def respond_cooperation_endpoint(agency_id, coop_id, body, ctx)` — line 286
### `backend/fastapi_core/app/api/v1/ai.py`
- **class `PropertyCopyBody`** (line 11) extends `BaseModel`
- **class `CrmSummaryBody`** (line 16) extends `BaseModel`
- **class `SeoDraftBody`** (line 20) extends `BaseModel`
- `async def property_copy_endpoint(body, ctx)` — line 27
- `async def crm_summary_endpoint(body, ctx)` — line 39
- `async def seo_draft_endpoint(body, ctx)` — line 49
- `async def portfolio_insights_endpoint(ctx)` — line 65
- `async def ai_logs_endpoint(ctx)` — line 75
### `backend/fastapi_core/app/api/v1/appointments.py`
- **class `PublicAppointmentBody`** (line 13) extends `BaseModel`
- **class `AgencyAppointmentBody`** (line 20) extends `BaseModel`
- **class `AppointmentStatusBody`** (line 29) extends `BaseModel`
- `def _ser_appt(a)` — line 34
- `async def get_appointments(page, page_size, ctx)` — line 54
- `async def request_public(body, ctx)` — line 71
- `async def create_appointment(body, ctx)` — line 82
- `async def confirm_appointment(appt_id, ctx)` — line 97
- `async def update_appointment_status(appt_id, body, ctx)` — line 114
### `backend/fastapi_core/app/api/v1/auth.py`
- **class `RegisterBody`** (line 14) extends `BaseModel`
- **class `LoginBody`** (line 25) extends `BaseModel`
- **class `RefreshBody`** (line 31) extends `BaseModel`
- **class `PasswordResetRequestBody`** (line 35) extends `BaseModel`
- **class `PasswordResetConfirmBody`** (line 39) extends `BaseModel`
- **class `ProfilePatchBody`** (line 45) extends `BaseModel`
- `def _serialize_user(user)` — line 55
- `async def register(body)` — line 96
- `async def login(body, request)` — line 107
- `async def refresh_token(body)` — line 128
- `async def logout(ctx)` — line 157
- `async def password_reset_request(body)` — line 172
- `async def password_reset_confirm(body)` — line 182
- `async def get_me(ctx)` — line 197
- `async def patch_me(body, ctx)` — line 202
- `async def list_sessions(ctx)` — line 213
- `async def delete_session(session_id, ctx)` — line 233
### `backend/fastapi_core/app/api/v1/cms.py`
- **class `CategoryCreateBody`** (line 13) extends `BaseModel`
- **class `ArticleCreateBody`** (line 20) extends `BaseModel`
- **class `ArticlePatchBody`** (line 34) extends `BaseModel`
- **class `ArticleStatusBody`** (line 47) extends `BaseModel`
- **class `RedirectCreateBody`** (line 52) extends `BaseModel`
- **class `ContactInquiryCreateBody`** (line 58) extends `BaseModel`
- **class `ContactInquiryPatchBody`** (line 67) extends `BaseModel`
- **class `CooperationSubmitBody`** (line 72) extends `BaseModel`
- **class `CooperationReviewBody`** (line 83) extends `BaseModel`
- `def _ser_article(a, include_versions)` — line 87
- `async def get_public_categories()` — line 124
- `async def get_public_articles_endpoint(category, article_type, q, page, page_size)` — line 137
- `async def get_public_article_detail(slug)` — line 156
- `async def get_public_faqs_endpoint()` — line 166
- `async def get_public_jobs_endpoint()` — line 179
- `async def list_cms_articles_endpoint(status, ctx)` — line 199
- `async def create_cms_category_endpoint(body, ctx)` — line 212
- `async def create_cms_article_endpoint(body, ctx)` — line 223
- `async def patch_cms_article_endpoint(article_id, body, ctx)` — line 233
- `async def transition_cms_article_endpoint(article_id, body, ctx)` — line 248
- `async def list_seo_redirects_endpoint()` — line 265
- `async def create_seo_redirect_endpoint(body, ctx)` — line 284
- `async def submit_contact_inquiry_endpoint(body)` — line 295
- `async def track_contact_inquiry_endpoint(tracking_code, phone_number)` — line 311
- `async def list_contact_inquiries_endpoint(ctx)` — line 329
- `async def patch_contact_inquiry_endpoint(inquiry_id, body, ctx)` — line 353
- `async def submit_cooperation_request_endpoint(body)` — line 368
- `async def list_cooperation_requests_endpoint(ctx)` — line 383
- `async def review_cooperation_request_endpoint(request_id, body, ctx)` — line 408
### `backend/fastapi_core/app/api/v1/commissions.py`
- **class `CommissionPolicyCreateBody`** (line 13) extends `BaseModel`
- **class `CommissionCalculateBody`** (line 26) extends `BaseModel`
- **class `CommissionStatusBody`** (line 32) extends `BaseModel`
- `def _ser_commission(dc)` — line 36
- `async def list_commissions_endpoint(page, page_size, ctx)` — line 67
- `async def list_policies_endpoint(ctx)` — line 84
- `async def create_policy_endpoint(body, ctx)` — line 117
- `async def calculate_commission_endpoint(body, ctx)` — line 130
- `async def commission_status_endpoint(commission_id, body, ctx)` — line 149
### `backend/fastapi_core/app/api/v1/complaints.py`
- **class `ComplaintCreateBody`** (line 12) extends `BaseModel`
- **class `ComplaintNoteBody`** (line 23) extends `BaseModel`
- **class `ComplaintStatusBody`** (line 28) extends `BaseModel`
- `def _ser_complaint(c, include_notes)` — line 34
- `async def create_public_complaint_endpoint(body, ctx)` — line 70
- `async def track_public_complaint_endpoint(tracking_code, phone_number)` — line 88
- `async def list_complaints_endpoint(status, page, page_size, ctx)` — line 98
- `async def create_complaint_endpoint(body, ctx)` — line 121
- `async def add_complaint_note_endpoint(complaint_id, body, ctx)` — line 134
- `async def update_complaint_status_endpoint(complaint_id, body, ctx)` — line 158
### `backend/fastapi_core/app/api/v1/contracts_deals.py`
- **class `ContractTemplateCreateBody`** (line 14) extends `BaseModel`
- **class `ContractPartyBody`** (line 23) extends `BaseModel`
- **class `ContractCreateBody`** (line 29) extends `BaseModel`
- **class `ContractStatusBody`** (line 50) extends `BaseModel`
- **class `DealCreateBody`** (line 55) extends `BaseModel`
- **class `DealCloseBody`** (line 66) extends `BaseModel`
- `def _ser_contract(c)` — line 70
- `def _ser_deal(d)` — line 104
- `async def list_templates_endpoint(ctx)` — line 124
- `async def create_template_endpoint(body, ctx)` — line 144
- `async def list_contracts_endpoint(page, page_size, ctx)` — line 157
- `async def create_contract_endpoint(body, ctx)` — line 174
- `async def contract_status_endpoint(contract_id, body, ctx)` — line 187
- `async def list_deals_endpoint(page, page_size, ctx)` — line 208
- `async def create_deal_endpoint(body, ctx)` — line 225
- `async def get_contract_endpoint(contract_id, ctx)` — line 236
- `async def get_deal_endpoint(deal_id, ctx)` — line 262
- `async def close_deal_endpoint(deal_id, body, ctx)` — line 296
### `backend/fastapi_core/app/api/v1/crm.py`
- **class `PipelineUpsertBody`** (line 13) extends `BaseModel`
- **class `PipelineStageMoveBody`** (line 20) extends `BaseModel`
- **class `TaskCreateBody`** (line 25) extends `BaseModel`
- **class `TaskPatchBody`** (line 32) extends `BaseModel`
- **class `InteractionCreateBody`** (line 36) extends `BaseModel`
- `def _ser_pipeline_item(it)` — line 43
- `async def get_stages(ctx)` — line 60
- `async def get_pipeline(ctx)` — line 80
- `async def upsert_pipeline(body, ctx)` — line 90
- `async def move_pipeline_stage(item_id, body, ctx)` — line 101
- `async def get_tasks(ctx)` — line 116
- `async def post_task(body, ctx)` — line 138
- `async def patch_task(task_id, body, ctx)` — line 149
- `async def get_interactions(customer_id, ctx)` — line 162
- `async def post_interaction(body, ctx)` — line 186
### `backend/fastapi_core/app/api/v1/customers.py`
- **class `CustomerCreateBody`** (line 13) extends `BaseModel`
- **class `CustomerPatchBody`** (line 26) extends `BaseModel`
- **class `CustomerShareBody`** (line 36) extends `BaseModel`
- **class `CustomerRequirementBody`** (line 41) extends `BaseModel`
- **class `LeadCreateBody`** (line 55) extends `BaseModel`
- **class `LeadPatchBody`** (line 64) extends `BaseModel`
- `def _ser_customer(c)` — line 69
- `def _ser_lead(l)` — line 113
- `async def get_customers(q, customer_type, page, page_size, ctx)` — line 131
- `async def post_customer(body, ctx)` — line 150
- `async def patch_customer(customer_id, body, ctx)` — line 161
- `async def post_customer_share(customer_id, body, ctx)` — line 176
- `async def post_customer_req(customer_id, body, ctx)` — line 195
- `async def get_leads(status, q, page, page_size, ctx)` — line 210
- `async def post_lead(body, ctx)` — line 229
- `async def patch_lead(lead_id, body, ctx)` — line 239
- `async def convert_lead(lead_id, ctx)` — line 253
### `backend/fastapi_core/app/api/v1/documents.py`
- **class `DocumentCreateBody`** (line 12) extends `BaseModel`
- `def _ser_doc(d)` — line 24
- `async def list_documents_endpoint(category, page, page_size, ctx)` — line 49
- `async def create_document_endpoint(body, ctx)` — line 67
- `async def download_document_endpoint(document_id, request, ctx)` — line 81
### `backend/fastapi_core/app/api/v1/matching.py`
- `async def match_properties_for_customer(deal_type_id, property_type_id, target_city, districts, min_area_sqm, max_area_sqm, min_budget, max_budget, min_bedrooms, ctx)` — line 12
- `async def district_price_trends(city)` — line 74
### `backend/fastapi_core/app/api/v1/negotiations.py`
- **class `NegotiationCreateBody`** (line 13) extends `BaseModel`
- **class `OfferVersionCreateBody`** (line 27) extends `BaseModel`
- **class `NegotiationRespondBody`** (line 37) extends `BaseModel`
- `def _ser_neg(n)` — line 41
- `async def list_negotiations_endpoint(page, page_size, ctx)` — line 74
- `async def create_negotiation_endpoint(body, ctx)` — line 91
- `async def add_offer_endpoint(negotiation_id, body, ctx)` — line 104
- `async def respond_negotiation_endpoint(negotiation_id, body, ctx)` — line 124
### `backend/fastapi_core/app/api/v1/notifications.py`
- **class `NotificationCreateBody`** (line 11) extends `BaseModel`
- `def _ser_notif(n)` — line 18
- `async def list_notifications_endpoint(unread_only, page, page_size, ctx)` — line 34
- `async def send_notification_endpoint(body, ctx)` — line 52
- `async def read_notification_endpoint(notification_id, ctx)` — line 72
- `async def read_all_notifications_endpoint(ctx)` — line 85
### `backend/fastapi_core/app/api/v1/payroll.py`
- **class `PayrollCycleCreateBody`** (line 12) extends `BaseModel`
- **class `PayrollCycleStatusBody`** (line 18) extends `BaseModel`
- `def _ser_cycle(c)` — line 22
- `async def list_payroll_cycles_endpoint(ctx)` — line 55
- `async def create_payroll_cycle_endpoint(body, ctx)` — line 65
- `async def payroll_cycle_status_endpoint(cycle_id, body, ctx)` — line 84
### `backend/fastapi_core/app/api/v1/properties.py`
- **class `PropertyLocationBody`** (line 13) extends `BaseModel`
- **class `PropertyCreateBody`** (line 27) extends `BaseModel`
- **class `PropertyPatchBody`** (line 63) extends `BaseModel`
- **class `PropertyStatusBody`** (line 90) extends `BaseModel`
- **class `PropertyMediaBody`** (line 95) extends `BaseModel`
- `def _ser_public_property(p)` — line 103
- `def _ser_agency_property(p, user)` — line 178
- `async def catalog()` — line 221
- `async def list_public(city, district, deal_type, property_type, min_price, max_price, min_area, min_bedrooms, q, featured, page, page_size)` — line 245
- `async def list_properties(status, deal_type, property_type, q, page, page_size, ctx)` — line 282
- `async def create_property_endpoint(body, ctx)` — line 316
- `async def get_property(property_id, ctx)` — line 330
- `async def patch_property(property_id, body, ctx)` — line 345
- `async def delete_property(property_id, ctx)` — line 363
- `async def submit_property(property_id, ctx)` — line 374
- `async def publish_property(property_id, ctx)` — line 391
- `async def set_property_status(property_id, body, ctx)` — line 408
- `async def add_media(property_id, body, ctx)` — line 427
- `async def remove_media(property_id, media_id, ctx)` — line 445
### `backend/fastapi_core/app/api/v1/push.py`
- **class `PushSubscribeBody`** (line 11) extends `BaseModel`
- **class `PushUnsubscribeBody`** (line 18) extends `BaseModel`
- **class `NotificationPreferencePatchBody`** (line 22) extends `BaseModel`
- `async def vapid_public_key_endpoint()` — line 32
- `async def list_subscriptions_endpoint(ctx)` — line 42
- `async def subscribe_push_endpoint(body, ctx)` — line 62
- `async def unsubscribe_push_endpoint(body, ctx)` — line 80
- `async def get_preferences_endpoint(ctx)` — line 91
- `async def patch_preferences_endpoint(body, ctx)` — line 109
- `async def test_push_endpoint(ctx)` — line 129
### `backend/fastapi_core/app/api/v1/reports_audit.py`
- `async def dashboard_summary_endpoint(period_days, ctx)` — line 11
- `async def analytics_endpoint(period_days, ctx)` — line 26
- `async def audit_logs_endpoint(resource_type, action, page, page_size, ctx)` — line 41
### `backend/fastapi_core/app/api/v1/search.py`
- `async def search_properties(city, district, deal_type, property_type, min_price, max_price, min_area, min_bedrooms, q, page, page_size, ctx)` — line 12
### `backend/fastapi_core/app/api/v1/settings.py`
- **class `ProviderUpsertBody`** (line 11) extends `BaseModel`
- `async def localization_endpoint()` — line 22
- `async def list_providers_endpoint(ctx)` — line 73
- `async def upsert_provider_endpoint(body, ctx)` — line 96
### `backend/fastapi_core/app/api/v1/subscriptions.py`
- **class `CheckoutBody`** (line 10) extends `BaseModel`
- **class `VerifyBody`** (line 16) extends `BaseModel`
- `async def list_plans_endpoint()` — line 21
- `async def list_current_subscriptions_endpoint(ctx)` — line 47
- `async def checkout_subscription_endpoint(body, ctx)` — line 70
- `async def verify_subscription_endpoint(body, ctx)` — line 88
- `async def list_transactions_endpoint(ctx)` — line 110
### `backend/fastapi_core/app/api/v1/support.py`
- **class `TicketAttachmentBody`** (line 12) extends `BaseModel`
- **class `TicketCreateBody`** (line 19) extends `BaseModel`
- **class `TicketMessageBody`** (line 28) extends `BaseModel`
- **class `TicketStatusBody`** (line 34) extends `BaseModel`
- **class `TicketAssignBody`** (line 39) extends `BaseModel`
- **class `TicketRatingBody`** (line 43) extends `BaseModel`
- **class `CannedReplyBody`** (line 48) extends `BaseModel`
- `def _ser_ticket(t, include_internal)` — line 54
- `async def list_tickets_endpoint(scope, status, page, page_size, ctx)` — line 110
- `async def create_ticket_endpoint(body, ctx)` — line 134
- `async def list_canned_replies_endpoint(ctx)` — line 145
- `async def create_canned_reply_endpoint(body, ctx)` — line 158
- `async def ticket_report_endpoint(ctx)` — line 169
- `async def get_ticket_endpoint(ticket_id, ctx)` — line 179
- `async def add_ticket_message_endpoint(ticket_id, body, ctx)` — line 192
- `async def update_ticket_status_endpoint(ticket_id, body, ctx)` — line 211
- `async def assign_ticket_endpoint(ticket_id, body, ctx)` — line 230
- `async def rate_ticket_endpoint(ticket_id, body, ctx)` — line 248
### `backend/fastapi_core/app/api/v1/surveys.py`
- **class `SurveyQuestionBody`** (line 12) extends `BaseModel`
- **class `SurveyCreateBody`** (line 20) extends `BaseModel`
- **class `SurveyAnswerSubmitBody`** (line 31) extends `BaseModel`
- **class `SurveySubmitBody`** (line 38) extends `BaseModel`
- `def _ser_survey(s)` — line 44
- `async def get_public_survey_endpoint(slug)` — line 73
- `async def submit_public_survey_endpoint(slug, body, ctx)` — line 83
- `async def list_surveys_endpoint(public_only, page, page_size, ctx)` — line 102
- `async def create_survey_endpoint(body, ctx)` — line 120
- `async def compare_surveys_endpoint(ctx)` — line 131
- `async def get_survey_detail_endpoint(survey_id, ctx)` — line 141
- `async def survey_analytics_endpoint(survey_id, ctx)` — line 151
### `backend/fastapi_core/app/api/v1/team.py`
- **class `MemberCreateBody`** (line 14) extends `BaseModel`
- **class `MemberPatchBody`** (line 24) extends `BaseModel`
- **class `OverrideItem`** (line 30) extends `BaseModel`
- **class `OverridesPutBody`** (line 35) extends `BaseModel`
- **class `RoleCreateBody`** (line 39) extends `BaseModel`
- **class `EmployeeCreateBody`** (line 45) extends `BaseModel`
- **class `CompensationPlanBody`** (line 57) extends `BaseModel`
- `async def list_team_members(ctx)` — line 66
- `async def create_team_member(body, ctx)` — line 95
- `async def patch_team_member(membership_id, body, ctx)` — line 106
- `async def put_member_overrides(membership_id, body, ctx)` — line 126
- `async def get_roles_permissions(ctx)` — line 144
- `async def create_role_endpoint(body, ctx)` — line 170
- `async def list_employees_endpoint(ctx)` — line 181
- `async def create_employee_endpoint(body, ctx)` — line 218
- `async def create_compensation_plan_endpoint(employee_id, body, ctx)` — line 229
### `backend/fastapi_core/app/core/config.py`
- **class `Settings`** (line 9) extends `BaseSettings`
### `backend/fastapi_core/app/core/django_bridge.py`
- `def init_django()` — line 14
- `async def run_django(fn, *args, agency_id, **kwargs)` — line 32
### `backend/fastapi_core/app/core/security.py`
- `def build_token_pair(user, session, membership)` — line 8
- `def decode_jwt_token(token, expected_type)` — line 43
- `def new_jti()` — line 50
### `backend/fastapi_core/app/dependencies/auth.py`
- **class `RequestContext`** (line 11) extends ``
- `def _resolve_auth_sync(token, header_agency_id)` — line 19
- `async def get_optional_context(authorization, x_agency_id)` — line 91
- `async def get_current_context(ctx)` — line 101
- `async def require_agency_context(ctx)` — line 112
### `backend/fastapi_core/app/middleware/request_context.py`
- **class `RequestContextMiddleware`** (line 11) extends `BaseHTTPMiddleware`
  - `dispatch(self, request, call_next)` — line 17
### `backend/fastapi_core/app/schemas/common.py`
- **class `ApiEnvelope`** (line 5) extends `BaseModel`
- `def ok(data, meta)` — line 12
### `backend/fastapi_core/app/services/matching_service.py`
- `def score_property_for_requirement(prop, req)` — line 5
### `backend/fastapi_core/tests/test_fastapi_engine.py`
- `def bootstrap_db()` — line 21
- `def _login(client, phone, password)` — line 28
- `def test_matching_scorer_deterministic()` — line 34
- `def test_fastapi_health()` — line 62
- `def test_auth_login_refresh_and_profile()` — line 69
- `def test_tenant_isolation_and_rbac_enforcement()` — line 85
- `def test_subscriptions_and_payroll_endpoints()` — line 130
- `def test_public_search_address_masking_and_matching()` — line 161
- `def test_double_entry_accounting_and_lead_conversion()` — line 188
- `def test_phase5_tickets_complaints_surveys_push_and_ai_isolation()` — line 253
- `def test_phase6_cms_seo_public_requests_and_cooperation()` — line 317

## 7. API و Routeهای شناسایی‌شده
- **GET /health** → `health` در `backend/fastapi_core/app/main.py:126` (FastAPI/Starlette-style)
- **GET /coa** → `list_coa_endpoint` در `backend/fastapi_core/app/api/v1/accounting.py:76` (FastAPI/Starlette-style)
- **POST /coa** → `create_coa_endpoint` در `backend/fastapi_core/app/api/v1/accounting.py:96` (FastAPI/Starlette-style)
- **GET /journal-entries** → `list_journal_entries_endpoint` در `backend/fastapi_core/app/api/v1/accounting.py:109` (FastAPI/Starlette-style)
- **POST /journal-entries** → `post_journal_entry_endpoint` در `backend/fastapi_core/app/api/v1/accounting.py:128` (FastAPI/Starlette-style)
- **POST /journal-entries/{entry_id}/reverse** → `reverse_journal_entry_endpoint` در `backend/fastapi_core/app/api/v1/accounting.py:143` (FastAPI/Starlette-style)
- **GET /treasury** → `list_treasury_endpoint` در `backend/fastapi_core/app/api/v1/accounting.py:158` (FastAPI/Starlette-style)
- **POST /cheques** → `create_cheque_endpoint` در `backend/fastapi_core/app/api/v1/accounting.py:221` (FastAPI/Starlette-style)
- **PATCH /cheques/{cheque_id}** → `patch_cheque_endpoint` در `backend/fastapi_core/app/api/v1/accounting.py:234` (FastAPI/Starlette-style)
- **GET /reports/trial-balance** → `trial_balance_endpoint` در `backend/fastapi_core/app/api/v1/accounting.py:249` (FastAPI/Starlette-style)
- **GET /reports/financial-statements** → `financial_statements_endpoint` در `backend/fastapi_core/app/api/v1/accounting.py:264` (FastAPI/Starlette-style)
- **GET /reports/general-ledger/{account_id}** → `general_ledger_endpoint` در `backend/fastapi_core/app/api/v1/accounting.py:274` (FastAPI/Starlette-style)
- **GET /fiscal-periods** → `list_fiscal_periods_endpoint` در `backend/fastapi_core/app/api/v1/accounting.py:286` (FastAPI/Starlette-style)
- **POST /fiscal-periods/{period_id}/close** → `close_fiscal_period_endpoint` در `backend/fastapi_core/app/api/v1/accounting.py:306` (FastAPI/Starlette-style)
- **GET /users** → `admin_list_users` در `backend/fastapi_core/app/api/v1/admin.py:16` (FastAPI/Starlette-style)
- **PATCH /users/{user_id}/status** → `admin_update_user_status` در `backend/fastapi_core/app/api/v1/admin.py:47` (FastAPI/Starlette-style)
- **GET /subscriptions** → `admin_list_subscriptions` در `backend/fastapi_core/app/api/v1/admin.py:62` (FastAPI/Starlette-style)
- **GET [dynamic path]** → `list_agencies` در `backend/fastapi_core/app/api/v1/agencies.py:104` (FastAPI/Starlette-style)
- **POST [dynamic path]** → `create_agency_endpoint` در `backend/fastapi_core/app/api/v1/agencies.py:121` (FastAPI/Starlette-style)
- **GET /{agency_id}** → `get_agency` در `backend/fastapi_core/app/api/v1/agencies.py:134` (FastAPI/Starlette-style)
- **POST /{agency_id}/status** → `update_agency_status_endpoint` در `backend/fastapi_core/app/api/v1/agencies.py:144` (FastAPI/Starlette-style)
- **GET /{agency_id}/access-policy** → `get_policy` در `backend/fastapi_core/app/api/v1/agencies.py:156` (FastAPI/Starlette-style)
- **PATCH /{agency_id}/access-policy** → `patch_policy` در `backend/fastapi_core/app/api/v1/agencies.py:166` (FastAPI/Starlette-style)
- **GET /{agency_id}/branches** → `list_branches_endpoint` در `backend/fastapi_core/app/api/v1/agencies.py:180` (FastAPI/Starlette-style)
- **POST /{agency_id}/branches** → `create_branch_endpoint` در `backend/fastapi_core/app/api/v1/agencies.py:203` (FastAPI/Starlette-style)
- **GET /{agency_id}/members** → `list_members_endpoint` در `backend/fastapi_core/app/api/v1/agencies.py:223` (FastAPI/Starlette-style)
- **GET /{agency_id}/cooperations** → `list_cooperations_endpoint` در `backend/fastapi_core/app/api/v1/agencies.py:247` (FastAPI/Starlette-style)
- **POST /{agency_id}/cooperations** → `create_cooperation_endpoint` در `backend/fastapi_core/app/api/v1/agencies.py:268` (FastAPI/Starlette-style)
- **POST /{agency_id}/cooperations/{coop_id}/respond** → `respond_cooperation_endpoint` در `backend/fastapi_core/app/api/v1/agencies.py:286` (FastAPI/Starlette-style)
- **POST /property-copy** → `property_copy_endpoint` در `backend/fastapi_core/app/api/v1/ai.py:27` (FastAPI/Starlette-style)
- **POST /crm-summary** → `crm_summary_endpoint` در `backend/fastapi_core/app/api/v1/ai.py:39` (FastAPI/Starlette-style)
- **POST /seo-draft** → `seo_draft_endpoint` در `backend/fastapi_core/app/api/v1/ai.py:49` (FastAPI/Starlette-style)
- **GET /portfolio-insights** → `portfolio_insights_endpoint` در `backend/fastapi_core/app/api/v1/ai.py:65` (FastAPI/Starlette-style)
- **GET /logs** → `ai_logs_endpoint` در `backend/fastapi_core/app/api/v1/ai.py:75` (FastAPI/Starlette-style)
- **GET [dynamic path]** → `get_appointments` در `backend/fastapi_core/app/api/v1/appointments.py:54` (FastAPI/Starlette-style)
- **POST /request-public** → `request_public` در `backend/fastapi_core/app/api/v1/appointments.py:71` (FastAPI/Starlette-style)
- **POST [dynamic path]** → `create_appointment` در `backend/fastapi_core/app/api/v1/appointments.py:82` (FastAPI/Starlette-style)
- **POST /{appt_id}/confirm** → `confirm_appointment` در `backend/fastapi_core/app/api/v1/appointments.py:97` (FastAPI/Starlette-style)
- **PATCH /{appt_id}/status** → `update_appointment_status` در `backend/fastapi_core/app/api/v1/appointments.py:114` (FastAPI/Starlette-style)
- **POST /register** → `register` در `backend/fastapi_core/app/api/v1/auth.py:96` (FastAPI/Starlette-style)
- **POST /login** → `login` در `backend/fastapi_core/app/api/v1/auth.py:107` (FastAPI/Starlette-style)
- **POST /refresh** → `refresh_token` در `backend/fastapi_core/app/api/v1/auth.py:128` (FastAPI/Starlette-style)
- **POST /logout** → `logout` در `backend/fastapi_core/app/api/v1/auth.py:157` (FastAPI/Starlette-style)
- **POST /password-reset/request** → `password_reset_request` در `backend/fastapi_core/app/api/v1/auth.py:172` (FastAPI/Starlette-style)
- **POST /password-reset/confirm** → `password_reset_confirm` در `backend/fastapi_core/app/api/v1/auth.py:182` (FastAPI/Starlette-style)
- **GET /me** → `get_me` در `backend/fastapi_core/app/api/v1/auth.py:197` (FastAPI/Starlette-style)
- **PATCH /me** → `patch_me` در `backend/fastapi_core/app/api/v1/auth.py:202` (FastAPI/Starlette-style)
- **GET /sessions** → `list_sessions` در `backend/fastapi_core/app/api/v1/auth.py:213` (FastAPI/Starlette-style)
- **DELETE /sessions/{session_id}** → `delete_session` در `backend/fastapi_core/app/api/v1/auth.py:233` (FastAPI/Starlette-style)
- **GET /cms/public/categories** → `get_public_categories` در `backend/fastapi_core/app/api/v1/cms.py:124` (FastAPI/Starlette-style)
- **GET /cms/public/articles** → `get_public_articles_endpoint` در `backend/fastapi_core/app/api/v1/cms.py:137` (FastAPI/Starlette-style)
- **GET /cms/public/articles/{slug}** → `get_public_article_detail` در `backend/fastapi_core/app/api/v1/cms.py:156` (FastAPI/Starlette-style)
- **GET /cms/public/faqs** → `get_public_faqs_endpoint` در `backend/fastapi_core/app/api/v1/cms.py:166` (FastAPI/Starlette-style)
- **GET /cms/public/jobs** → `get_public_jobs_endpoint` در `backend/fastapi_core/app/api/v1/cms.py:179` (FastAPI/Starlette-style)
- **GET /cms/articles** → `list_cms_articles_endpoint` در `backend/fastapi_core/app/api/v1/cms.py:199` (FastAPI/Starlette-style)
- **POST /cms/categories** → `create_cms_category_endpoint` در `backend/fastapi_core/app/api/v1/cms.py:212` (FastAPI/Starlette-style)
- **POST /cms/articles** → `create_cms_article_endpoint` در `backend/fastapi_core/app/api/v1/cms.py:223` (FastAPI/Starlette-style)
- **PATCH /cms/articles/{article_id}** → `patch_cms_article_endpoint` در `backend/fastapi_core/app/api/v1/cms.py:233` (FastAPI/Starlette-style)
- **POST /cms/articles/{article_id}/status** → `transition_cms_article_endpoint` در `backend/fastapi_core/app/api/v1/cms.py:248` (FastAPI/Starlette-style)
- **GET /seo/redirects** → `list_seo_redirects_endpoint` در `backend/fastapi_core/app/api/v1/cms.py:265` (FastAPI/Starlette-style)
- **POST /seo/redirects** → `create_seo_redirect_endpoint` در `backend/fastapi_core/app/api/v1/cms.py:284` (FastAPI/Starlette-style)
- **POST /public-requests/contact** → `submit_contact_inquiry_endpoint` در `backend/fastapi_core/app/api/v1/cms.py:295` (FastAPI/Starlette-style)
- **GET /public-requests/track** → `track_contact_inquiry_endpoint` در `backend/fastapi_core/app/api/v1/cms.py:311` (FastAPI/Starlette-style)
- **GET /cms/contact-inquiries** → `list_contact_inquiries_endpoint` در `backend/fastapi_core/app/api/v1/cms.py:329` (FastAPI/Starlette-style)
- **PATCH /cms/contact-inquiries/{inquiry_id}** → `patch_contact_inquiry_endpoint` در `backend/fastapi_core/app/api/v1/cms.py:353` (FastAPI/Starlette-style)
- **POST /public-requests/cooperation** → `submit_cooperation_request_endpoint` در `backend/fastapi_core/app/api/v1/cms.py:368` (FastAPI/Starlette-style)
- **GET /cms/cooperation-requests** → `list_cooperation_requests_endpoint` در `backend/fastapi_core/app/api/v1/cms.py:383` (FastAPI/Starlette-style)
- **POST /cms/cooperation-requests/{request_id}/review** → `review_cooperation_request_endpoint` در `backend/fastapi_core/app/api/v1/cms.py:408` (FastAPI/Starlette-style)
- **GET [dynamic path]** → `list_commissions_endpoint` در `backend/fastapi_core/app/api/v1/commissions.py:67` (FastAPI/Starlette-style)
- **GET /policies** → `list_policies_endpoint` در `backend/fastapi_core/app/api/v1/commissions.py:84` (FastAPI/Starlette-style)
- **POST /policies** → `create_policy_endpoint` در `backend/fastapi_core/app/api/v1/commissions.py:117` (FastAPI/Starlette-style)
- **POST /calculate** → `calculate_commission_endpoint` در `backend/fastapi_core/app/api/v1/commissions.py:130` (FastAPI/Starlette-style)
- **POST /{commission_id}/status** → `commission_status_endpoint` در `backend/fastapi_core/app/api/v1/commissions.py:149` (FastAPI/Starlette-style)
- **POST /public** → `create_public_complaint_endpoint` در `backend/fastapi_core/app/api/v1/complaints.py:70` (FastAPI/Starlette-style)
- **GET /public/track** → `track_public_complaint_endpoint` در `backend/fastapi_core/app/api/v1/complaints.py:88` (FastAPI/Starlette-style)
- **GET [dynamic path]** → `list_complaints_endpoint` در `backend/fastapi_core/app/api/v1/complaints.py:98` (FastAPI/Starlette-style)
- **POST [dynamic path]** → `create_complaint_endpoint` در `backend/fastapi_core/app/api/v1/complaints.py:121` (FastAPI/Starlette-style)
- **POST /{complaint_id}/notes** → `add_complaint_note_endpoint` در `backend/fastapi_core/app/api/v1/complaints.py:134` (FastAPI/Starlette-style)
- **POST /{complaint_id}/status** → `update_complaint_status_endpoint` در `backend/fastapi_core/app/api/v1/complaints.py:158` (FastAPI/Starlette-style)
- **GET /contracts/templates** → `list_templates_endpoint` در `backend/fastapi_core/app/api/v1/contracts_deals.py:124` (FastAPI/Starlette-style)
- **POST /contracts/templates** → `create_template_endpoint` در `backend/fastapi_core/app/api/v1/contracts_deals.py:144` (FastAPI/Starlette-style)
- **GET /contracts** → `list_contracts_endpoint` در `backend/fastapi_core/app/api/v1/contracts_deals.py:157` (FastAPI/Starlette-style)
- **POST /contracts** → `create_contract_endpoint` در `backend/fastapi_core/app/api/v1/contracts_deals.py:174` (FastAPI/Starlette-style)
- **POST /contracts/{contract_id}/status** → `contract_status_endpoint` در `backend/fastapi_core/app/api/v1/contracts_deals.py:187` (FastAPI/Starlette-style)
- **GET /deals** → `list_deals_endpoint` در `backend/fastapi_core/app/api/v1/contracts_deals.py:208` (FastAPI/Starlette-style)
- **POST /deals** → `create_deal_endpoint` در `backend/fastapi_core/app/api/v1/contracts_deals.py:225` (FastAPI/Starlette-style)
- **GET /contracts/{contract_id}** → `get_contract_endpoint` در `backend/fastapi_core/app/api/v1/contracts_deals.py:236` (FastAPI/Starlette-style)
- **GET /deals/{deal_id}** → `get_deal_endpoint` در `backend/fastapi_core/app/api/v1/contracts_deals.py:262` (FastAPI/Starlette-style)
- **POST /deals/{deal_id}/close** → `close_deal_endpoint` در `backend/fastapi_core/app/api/v1/contracts_deals.py:296` (FastAPI/Starlette-style)
- **GET /stages** → `get_stages` در `backend/fastapi_core/app/api/v1/crm.py:60` (FastAPI/Starlette-style)
- **GET /pipeline** → `get_pipeline` در `backend/fastapi_core/app/api/v1/crm.py:80` (FastAPI/Starlette-style)
- **POST /pipeline** → `upsert_pipeline` در `backend/fastapi_core/app/api/v1/crm.py:90` (FastAPI/Starlette-style)
- **PATCH /pipeline/{item_id}** → `move_pipeline_stage` در `backend/fastapi_core/app/api/v1/crm.py:101` (FastAPI/Starlette-style)
- **GET /tasks** → `get_tasks` در `backend/fastapi_core/app/api/v1/crm.py:116` (FastAPI/Starlette-style)
- **POST /tasks** → `post_task` در `backend/fastapi_core/app/api/v1/crm.py:138` (FastAPI/Starlette-style)
- **PATCH /tasks/{task_id}** → `patch_task` در `backend/fastapi_core/app/api/v1/crm.py:149` (FastAPI/Starlette-style)
- **GET /interactions** → `get_interactions` در `backend/fastapi_core/app/api/v1/crm.py:162` (FastAPI/Starlette-style)
- **POST /interactions** → `post_interaction` در `backend/fastapi_core/app/api/v1/crm.py:186` (FastAPI/Starlette-style)
- **GET /customers** → `get_customers` در `backend/fastapi_core/app/api/v1/customers.py:131` (FastAPI/Starlette-style)
- **POST /customers** → `post_customer` در `backend/fastapi_core/app/api/v1/customers.py:150` (FastAPI/Starlette-style)
- **PATCH /customers/{customer_id}** → `patch_customer` در `backend/fastapi_core/app/api/v1/customers.py:161` (FastAPI/Starlette-style)
- **POST /customers/{customer_id}/share** → `post_customer_share` در `backend/fastapi_core/app/api/v1/customers.py:176` (FastAPI/Starlette-style)
- **POST /customers/{customer_id}/requirements** → `post_customer_req` در `backend/fastapi_core/app/api/v1/customers.py:195` (FastAPI/Starlette-style)
- **GET /leads** → `get_leads` در `backend/fastapi_core/app/api/v1/customers.py:210` (FastAPI/Starlette-style)
- **POST /leads** → `post_lead` در `backend/fastapi_core/app/api/v1/customers.py:229` (FastAPI/Starlette-style)
- **PATCH /leads/{lead_id}** → `patch_lead` در `backend/fastapi_core/app/api/v1/customers.py:239` (FastAPI/Starlette-style)
- **POST /leads/{lead_id}/convert** → `convert_lead` در `backend/fastapi_core/app/api/v1/customers.py:253` (FastAPI/Starlette-style)
- **GET [dynamic path]** → `list_documents_endpoint` در `backend/fastapi_core/app/api/v1/documents.py:49` (FastAPI/Starlette-style)
- **POST [dynamic path]** → `create_document_endpoint` در `backend/fastapi_core/app/api/v1/documents.py:67` (FastAPI/Starlette-style)
- **POST /{document_id}/download** → `download_document_endpoint` در `backend/fastapi_core/app/api/v1/documents.py:81` (FastAPI/Starlette-style)
- **GET /customer-to-properties** → `match_properties_for_customer` در `backend/fastapi_core/app/api/v1/matching.py:12` (FastAPI/Starlette-style)
- **GET /analytics/price-trends** → `district_price_trends` در `backend/fastapi_core/app/api/v1/matching.py:74` (FastAPI/Starlette-style)
- **GET [dynamic path]** → `list_negotiations_endpoint` در `backend/fastapi_core/app/api/v1/negotiations.py:74` (FastAPI/Starlette-style)
- **POST [dynamic path]** → `create_negotiation_endpoint` در `backend/fastapi_core/app/api/v1/negotiations.py:91` (FastAPI/Starlette-style)
- **POST /{negotiation_id}/offers** → `add_offer_endpoint` در `backend/fastapi_core/app/api/v1/negotiations.py:104` (FastAPI/Starlette-style)
- **POST /{negotiation_id}/respond** → `respond_negotiation_endpoint` در `backend/fastapi_core/app/api/v1/negotiations.py:124` (FastAPI/Starlette-style)
- **GET [dynamic path]** → `list_notifications_endpoint` در `backend/fastapi_core/app/api/v1/notifications.py:34` (FastAPI/Starlette-style)
- **POST [dynamic path]** → `send_notification_endpoint` در `backend/fastapi_core/app/api/v1/notifications.py:52` (FastAPI/Starlette-style)
- **POST /{notification_id}/read** → `read_notification_endpoint` در `backend/fastapi_core/app/api/v1/notifications.py:72` (FastAPI/Starlette-style)
- **POST /read-all** → `read_all_notifications_endpoint` در `backend/fastapi_core/app/api/v1/notifications.py:85` (FastAPI/Starlette-style)
- **GET /cycles** → `list_payroll_cycles_endpoint` در `backend/fastapi_core/app/api/v1/payroll.py:55` (FastAPI/Starlette-style)
- **POST /cycles** → `create_payroll_cycle_endpoint` در `backend/fastapi_core/app/api/v1/payroll.py:65` (FastAPI/Starlette-style)
- **POST /cycles/{cycle_id}/status** → `payroll_cycle_status_endpoint` در `backend/fastapi_core/app/api/v1/payroll.py:84` (FastAPI/Starlette-style)
- **GET /catalog** → `catalog` در `backend/fastapi_core/app/api/v1/properties.py:221` (FastAPI/Starlette-style)
- **GET /public** → `list_public` در `backend/fastapi_core/app/api/v1/properties.py:245` (FastAPI/Starlette-style)
- **GET [dynamic path]** → `list_properties` در `backend/fastapi_core/app/api/v1/properties.py:282` (FastAPI/Starlette-style)
- **POST [dynamic path]** → `create_property_endpoint` در `backend/fastapi_core/app/api/v1/properties.py:316` (FastAPI/Starlette-style)
- **GET /{property_id}** → `get_property` در `backend/fastapi_core/app/api/v1/properties.py:330` (FastAPI/Starlette-style)
- **PATCH /{property_id}** → `patch_property` در `backend/fastapi_core/app/api/v1/properties.py:345` (FastAPI/Starlette-style)
- **DELETE /{property_id}** → `delete_property` در `backend/fastapi_core/app/api/v1/properties.py:363` (FastAPI/Starlette-style)
- **POST /{property_id}/submit** → `submit_property` در `backend/fastapi_core/app/api/v1/properties.py:374` (FastAPI/Starlette-style)
- **POST /{property_id}/publish** → `publish_property` در `backend/fastapi_core/app/api/v1/properties.py:391` (FastAPI/Starlette-style)
- **POST /{property_id}/status** → `set_property_status` در `backend/fastapi_core/app/api/v1/properties.py:408` (FastAPI/Starlette-style)
- **POST /{property_id}/media** → `add_media` در `backend/fastapi_core/app/api/v1/properties.py:427` (FastAPI/Starlette-style)
- **DELETE /{property_id}/media/{media_id}** → `remove_media` در `backend/fastapi_core/app/api/v1/properties.py:445` (FastAPI/Starlette-style)
- **GET /vapid-public-key** → `vapid_public_key_endpoint` در `backend/fastapi_core/app/api/v1/push.py:32` (FastAPI/Starlette-style)
- **GET /subscriptions** → `list_subscriptions_endpoint` در `backend/fastapi_core/app/api/v1/push.py:42` (FastAPI/Starlette-style)
- **POST /subscribe** → `subscribe_push_endpoint` در `backend/fastapi_core/app/api/v1/push.py:62` (FastAPI/Starlette-style)
- **POST /unsubscribe** → `unsubscribe_push_endpoint` در `backend/fastapi_core/app/api/v1/push.py:80` (FastAPI/Starlette-style)
- **GET /preferences** → `get_preferences_endpoint` در `backend/fastapi_core/app/api/v1/push.py:91` (FastAPI/Starlette-style)
- **PATCH /preferences** → `patch_preferences_endpoint` در `backend/fastapi_core/app/api/v1/push.py:109` (FastAPI/Starlette-style)
- **POST /test** → `test_push_endpoint` در `backend/fastapi_core/app/api/v1/push.py:129` (FastAPI/Starlette-style)
- **GET /reports/dashboard** → `dashboard_summary_endpoint` در `backend/fastapi_core/app/api/v1/reports_audit.py:11` (FastAPI/Starlette-style)
- **GET /reports/analytics** → `analytics_endpoint` در `backend/fastapi_core/app/api/v1/reports_audit.py:26` (FastAPI/Starlette-style)
- **GET /audit/logs** → `audit_logs_endpoint` در `backend/fastapi_core/app/api/v1/reports_audit.py:41` (FastAPI/Starlette-style)
- **GET /properties** → `search_properties` در `backend/fastapi_core/app/api/v1/search.py:12` (FastAPI/Starlette-style)
- **GET /localization** → `localization_endpoint` در `backend/fastapi_core/app/api/v1/settings.py:22` (FastAPI/Starlette-style)
- **GET /providers** → `list_providers_endpoint` در `backend/fastapi_core/app/api/v1/settings.py:73` (FastAPI/Starlette-style)
- **POST /providers** → `upsert_provider_endpoint` در `backend/fastapi_core/app/api/v1/settings.py:96` (FastAPI/Starlette-style)
- **GET /subscriptions/plans** → `list_plans_endpoint` در `backend/fastapi_core/app/api/v1/subscriptions.py:21` (FastAPI/Starlette-style)
- **GET /subscriptions/current** → `list_current_subscriptions_endpoint` در `backend/fastapi_core/app/api/v1/subscriptions.py:47` (FastAPI/Starlette-style)
- **POST /subscriptions/checkout** → `checkout_subscription_endpoint` در `backend/fastapi_core/app/api/v1/subscriptions.py:70` (FastAPI/Starlette-style)
- **POST /subscriptions/verify** → `verify_subscription_endpoint` در `backend/fastapi_core/app/api/v1/subscriptions.py:88` (FastAPI/Starlette-style)
- **GET /payments/transactions** → `list_transactions_endpoint` در `backend/fastapi_core/app/api/v1/subscriptions.py:110` (FastAPI/Starlette-style)
- **GET [dynamic path]** → `list_tickets_endpoint` در `backend/fastapi_core/app/api/v1/support.py:110` (FastAPI/Starlette-style)
- **POST [dynamic path]** → `create_ticket_endpoint` در `backend/fastapi_core/app/api/v1/support.py:134` (FastAPI/Starlette-style)
- **GET /canned-replies** → `list_canned_replies_endpoint` در `backend/fastapi_core/app/api/v1/support.py:145` (FastAPI/Starlette-style)
- **POST /canned-replies** → `create_canned_reply_endpoint` در `backend/fastapi_core/app/api/v1/support.py:158` (FastAPI/Starlette-style)
- **GET /reports/summary** → `ticket_report_endpoint` در `backend/fastapi_core/app/api/v1/support.py:169` (FastAPI/Starlette-style)
- **GET /{ticket_id}** → `get_ticket_endpoint` در `backend/fastapi_core/app/api/v1/support.py:179` (FastAPI/Starlette-style)
- **POST /{ticket_id}/messages** → `add_ticket_message_endpoint` در `backend/fastapi_core/app/api/v1/support.py:192` (FastAPI/Starlette-style)
- **POST /{ticket_id}/status** → `update_ticket_status_endpoint` در `backend/fastapi_core/app/api/v1/support.py:211` (FastAPI/Starlette-style)
- **POST /{ticket_id}/assign** → `assign_ticket_endpoint` در `backend/fastapi_core/app/api/v1/support.py:230` (FastAPI/Starlette-style)
- **POST /{ticket_id}/rating** → `rate_ticket_endpoint` در `backend/fastapi_core/app/api/v1/support.py:248` (FastAPI/Starlette-style)
- **GET /public/{slug}** → `get_public_survey_endpoint` در `backend/fastapi_core/app/api/v1/surveys.py:73` (FastAPI/Starlette-style)
- **POST /public/{slug}/submit** → `submit_public_survey_endpoint` در `backend/fastapi_core/app/api/v1/surveys.py:83` (FastAPI/Starlette-style)
- **GET [dynamic path]** → `list_surveys_endpoint` در `backend/fastapi_core/app/api/v1/surveys.py:102` (FastAPI/Starlette-style)
- **POST [dynamic path]** → `create_survey_endpoint` در `backend/fastapi_core/app/api/v1/surveys.py:120` (FastAPI/Starlette-style)
- **GET /analytics/compare** → `compare_surveys_endpoint` در `backend/fastapi_core/app/api/v1/surveys.py:131` (FastAPI/Starlette-style)
- **GET /{survey_id}** → `get_survey_detail_endpoint` در `backend/fastapi_core/app/api/v1/surveys.py:141` (FastAPI/Starlette-style)
- **GET /{survey_id}/analytics** → `survey_analytics_endpoint` در `backend/fastapi_core/app/api/v1/surveys.py:151` (FastAPI/Starlette-style)
- **GET /team/members** → `list_team_members` در `backend/fastapi_core/app/api/v1/team.py:66` (FastAPI/Starlette-style)
- **POST /team/members** → `create_team_member` در `backend/fastapi_core/app/api/v1/team.py:95` (FastAPI/Starlette-style)
- **PATCH /team/members/{membership_id}** → `patch_team_member` در `backend/fastapi_core/app/api/v1/team.py:106` (FastAPI/Starlette-style)
- **PUT /team/members/{membership_id}/overrides** → `put_member_overrides` در `backend/fastapi_core/app/api/v1/team.py:126` (FastAPI/Starlette-style)
- **GET /team/roles** → `get_roles_permissions` در `backend/fastapi_core/app/api/v1/team.py:144` (FastAPI/Starlette-style)
- **POST /team/roles** → `create_role_endpoint` در `backend/fastapi_core/app/api/v1/team.py:170` (FastAPI/Starlette-style)
- **GET /employees** → `list_employees_endpoint` در `backend/fastapi_core/app/api/v1/team.py:181` (FastAPI/Starlette-style)
- **POST /employees** → `create_employee_endpoint` در `backend/fastapi_core/app/api/v1/team.py:218` (FastAPI/Starlette-style)
- **POST /employees/{employee_id}/compensation-plans** → `create_compensation_plan_endpoint` در `backend/fastapi_core/app/api/v1/team.py:229` (FastAPI/Starlette-style)

### نشانه‌های URLConf جنگو
- `backend/django_core/config/urls.py:7` → `path`

## 8. Frontend: صفحات، کامپوننت‌ها و ارتباط‌ها
### `frontend/src/app/layout.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `RootLayout`, `metadata`
- Importها: `@/components/Providers`, `@/lib/theme-provider`, `next`, `next/font/google`
### `frontend/src/app/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `HomePage`
- Interfaceها: `PriceTrendRow`
- مسیرهای ارجاع‌شده:
  - `/login` (line 101)
- Importها: `@/components/layout/PublicHeader`, `@/components/properties/PropertyCard`, `@/components/ui/AnalyticsCharts`, `@/components/ui/StateNotice`, `@/lib/api-client`, `@/lib/types`, `@tanstack/react-query`, `lucide-react`, `next/link`, `react`
### `frontend/src/app/api/v1/[...path]/route.ts`
- خروجی‌ها/کامپوننت‌های احتمالی: `DELETE`, `GET`, `PATCH`, `POST`, `PUT`
- Importها: `next/server`
### `frontend/src/app/dashboard/layout.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `DashboardLayout`
- Importها: `@/components/layout/DashboardShell`, `react`
### `frontend/src/app/dashboard/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `DashboardOverviewPage`
- Interfaceها: `AnalyticsData`, `DashboardSummary`
- مسیرهای ارجاع‌شده:
  - `/dashboard/properties/new` (line 111)
  - `/dashboard/crm` (line 118)
  - `/` (line 183)
  - `/dashboard/appointments` (line 189)
- Importها: `@/components/ui/AnalyticsCharts`, `@/components/ui/KpiCard`, `@/components/ui/MoneyDisplay`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/formatters`, `@tanstack/react-query`, `lucide-react`, `next/link`, `react`
### `frontend/src/app/dashboard/accounting/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `AccountingPage`
- Interfaceها: `JournalDraftLine`, `TreasuryResponse`
- Importها: `@/components/ui/DataTable`, `@/components/ui/DateDisplay`, `@/components/ui/KpiCard`, `@/components/ui/ModalDrawer`, `@/components/ui/MoneyDisplay`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/components/ui/StatusText`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/types`, `@tanstack/react-query`, `lucide-react`, `react`
### `frontend/src/app/dashboard/admin/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `AdminPlatformPage`
- Interfaceها: `AdminSubRow`, `AdminUserRow`
- Importها: `@/components/ui/DataTable`, `@/components/ui/DateDisplay`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/components/ui/StatusText`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/types`, `@tanstack/react-query`, `react`
### `frontend/src/app/dashboard/agencies/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `AgenciesBranchesPage`
- Importها: `@/components/ui/DataTable`, `@/components/ui/ModalDrawer`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/components/ui/StatusText`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/types`, `@tanstack/react-query`, `lucide-react`, `react`
### `frontend/src/app/dashboard/agents/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `AgentsDirectoryPage`
- Interfaceها: `AnalyticsResp`
- مسیرهای ارجاع‌شده:
  - `/dashboard/team` (line 60)
- Importها: `@/components/ui/AnalyticsCharts`, `@/components/ui/DataTable`, `@/components/ui/PageHeader`, `@/components/ui/StatusText`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/formatters`, `@/lib/types`, `@tanstack/react-query`, `lucide-react`, `next/link`, `react`
### `frontend/src/app/dashboard/appointments/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `AppointmentsPage`
- Importها: `@/components/ui/DataTable`, `@/components/ui/DateDisplay`, `@/components/ui/ModalDrawer`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/components/ui/StatusText`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/types`, `@tanstack/react-query`, `lucide-react`, `react`
### `frontend/src/app/dashboard/audit/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `AuditLogsPage`
- Importها: `@/components/ui/DataTable`, `@/components/ui/DateDisplay`, `@/components/ui/ModalDrawer`, `@/components/ui/PageHeader`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/types`, `@tanstack/react-query`, `lucide-react`, `react`
### `frontend/src/app/dashboard/commissions/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `CommissionsPage`
- Interfaceها: `PolicyItem`
- Importها: `@/components/ui/DataTable`, `@/components/ui/ModalDrawer`, `@/components/ui/MoneyDisplay`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/components/ui/StatusText`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/types`, `@tanstack/react-query`, `lucide-react`, `react`
### `frontend/src/app/dashboard/contracts/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `ContractsPage`
- Interfaceها: `TemplateItem`
- Importها: `@/components/ui/DataTable`, `@/components/ui/ModalDrawer`, `@/components/ui/MoneyDisplay`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/components/ui/StatusText`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/types`, `@tanstack/react-query`, `lucide-react`, `react`
### `frontend/src/app/dashboard/crm/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `CrmPipelinePage`
- Interfaceها: `MatchResult`
- Importها: `@/components/ui/DateDisplay`, `@/components/ui/ModalDrawer`, `@/components/ui/MoneyDisplay`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/components/ui/StatusText`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/types`, `@tanstack/react-query`, `lucide-react`, `react`
### `frontend/src/app/dashboard/customers/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `CustomersPage`
- Importها: `@/components/ui/DataTable`, `@/components/ui/ModalDrawer`, `@/components/ui/MoneyDisplay`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/types`, `@tanstack/react-query`, `lucide-react`, `react`
### `frontend/src/app/dashboard/deals/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `DealsPage`
- Importها: `@/components/ui/DataTable`, `@/components/ui/DateDisplay`, `@/components/ui/ModalDrawer`, `@/components/ui/MoneyDisplay`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/components/ui/StatusText`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/types`, `@tanstack/react-query`, `lucide-react`, `react`
### `frontend/src/app/dashboard/documents/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `DocumentsVaultPage`
- Importها: `@/components/ui/DataTable`, `@/components/ui/DateDisplay`, `@/components/ui/ModalDrawer`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/types`, `@tanstack/react-query`, `lucide-react`, `react`
### `frontend/src/app/dashboard/employees/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `EmployeesHrPage`
- Importها: `@/components/ui/DataTable`, `@/components/ui/DateDisplay`, `@/components/ui/ModalDrawer`, `@/components/ui/MoneyDisplay`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/types`, `@tanstack/react-query`, `lucide-react`, `react`
### `frontend/src/app/dashboard/leads/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `LeadsPage`
- Importها: `@/components/ui/DataTable`, `@/components/ui/DateDisplay`, `@/components/ui/ModalDrawer`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/components/ui/StatusText`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/types`, `@tanstack/react-query`, `lucide-react`, `react`
### `frontend/src/app/dashboard/negotiations/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `NegotiationsPage`
- Importها: `@/components/ui/DataTable`, `@/components/ui/DateDisplay`, `@/components/ui/ModalDrawer`, `@/components/ui/MoneyDisplay`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/components/ui/StatusText`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/types`, `@tanstack/react-query`, `lucide-react`, `react`
### `frontend/src/app/dashboard/notifications/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `NotificationsPage`
- Importها: `@/components/ui/DateDisplay`, `@/components/ui/ModalDrawer`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/components/ui/StatusText`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/types`, `@tanstack/react-query`, `lucide-react`, `react`
### `frontend/src/app/dashboard/payroll/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `PayrollPage`
- Importها: `@/components/ui/DataTable`, `@/components/ui/DateDisplay`, `@/components/ui/ModalDrawer`, `@/components/ui/MoneyDisplay`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/components/ui/StatusText`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/formatters`, `@/lib/types`, `@tanstack/react-query`, `lucide-react`, `react`
### `frontend/src/app/dashboard/profile/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `ProfilePage`
- Interfaceها: `SessionItem`
- Importها: `@/components/ui/DateDisplay`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/types`, `@tanstack/react-query`, `lucide-react`, `react`
### `frontend/src/app/dashboard/properties/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `DashboardPropertiesPage`
- مسیرهای ارجاع‌شده:
  - `/dashboard/properties/new` (line 70)
  - `/dashboard/properties/new` (line 102)
- Importها: `@/components/ui/DataTable`, `@/components/ui/MoneyDisplay`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/components/ui/StatusText`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/formatters`, `@/lib/types`, `@tanstack/react-query`, `lucide-react`, `next/link`, `react`
### `frontend/src/app/dashboard/properties/[id]/edit/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `EditPropertyPage`
- Importها: `@/components/properties/PropertyForm`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/types`, `@tanstack/react-query`, `next/navigation`, `react`
### `frontend/src/app/dashboard/properties/new/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `NewPropertyPage`
- Importها: `@/components/properties/PropertyForm`, `@/components/ui/PageHeader`, `react`
### `frontend/src/app/dashboard/reports/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `ReportsPage`
- Interfaceها: `AnalyticsResponse`, `PriceTrendItem`
- Importها: `@/components/ui/AnalyticsCharts`, `@/components/ui/KpiCard`, `@/components/ui/MoneyDisplay`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/formatters`, `@tanstack/react-query`, `lucide-react`, `react`
### `frontend/src/app/dashboard/roles/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `RolesAndPolicyPage`
- Interfaceها: `PolicyFieldMeta`
- Importها: `@/components/ui/ModalDrawer`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/types`, `@tanstack/react-query`, `lucide-react`, `react`
### `frontend/src/app/dashboard/settings/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `SettingsPage`
- Interfaceها: `LocalizationResponse`, `ProviderConfigItem`
- Importها: `@/components/ui/ModalDrawer`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/components/ui/StatusText`, `@/lib/api-client`, `@/lib/auth-context`, `@tanstack/react-query`, `lucide-react`, `react`
### `frontend/src/app/dashboard/subscriptions/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `SubscriptionsPage`
- Interfaceها: `CheckoutResult`, `CurrentSubItem`, `PlanItem`, `TransactionItem`
- Importها: `@/components/ui/DataTable`, `@/components/ui/DateDisplay`, `@/components/ui/MoneyDisplay`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/components/ui/StatusText`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/formatters`, `@/lib/types`, `@tanstack/react-query`, `lucide-react`, `react`
### `frontend/src/app/dashboard/team/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `TeamMembersPage`
- Importها: `@/components/ui/DataTable`, `@/components/ui/ModalDrawer`, `@/components/ui/PageHeader`, `@/components/ui/StateNotice`, `@/components/ui/StatusText`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/types`, `@tanstack/react-query`, `lucide-react`, `react`
### `frontend/src/app/forgot-password/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `ForgotPasswordPage`
- مسیرهای ارجاع‌شده:
  - `/login` (line 86)
  - `/login` (line 158)
- Importها: `@/components/layout/PublicHeader`, `@/components/ui/StateNotice`, `@/lib/api-client`, `lucide-react`, `next/link`, `react`
### `frontend/src/app/login/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `LoginPage`
- Typeها: `Values`
- مسیرهای ارجاع‌شده:
  - `/forgot-password` (line 99)
  - `/register` (line 129)
- Importها: `@/components/ui/Button`, `@/components/ui/Card`, `@/components/ui/Input`, `@/components/ui/Toast`, `@/lib/auth-context`, `@hookform/resolvers/zod`, `lucide-react`, `next/link`, `next/navigation`, `react`, `react-hook-form`, `zod`
### `frontend/src/app/properties/[id]/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `PropertyDetailPage`
- Importها: `@/components/layout/PublicHeader`, `@/components/ui/StateNotice`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/formatters`, `@/lib/types`, `@tanstack/react-query`, `lucide-react`, `next/navigation`, `react`
### `frontend/src/app/register/page.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `RegisterPage`
- Typeها: `Values`
- مسیرهای ارجاع‌شده:
  - `/login` (line 133)
- Importها: `@/components/ui/Button`, `@/components/ui/Card`, `@/components/ui/Input`, `@/components/ui/Toast`, `@/lib/api-client`, `@/lib/auth-context`, `@hookform/resolvers/zod`, `lucide-react`, `next/link`, `next/navigation`, `react`, `react-hook-form`, `zod`
### `frontend/src/components/Providers.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `Providers`
- Importها: `@/components/ui/Toast`, `@/lib/auth-context`, `@/lib/theme-provider`, `@tanstack/react-query`, `react`
### `frontend/src/components/layout/CommandPalette.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `CommandPalette`
- Importها: `@/components/ui/Kbd`, `@/lib/auth-context`, `@/lib/role-navigation`, `@/lib/utils`, `lucide-react`, `next/navigation`, `react`
### `frontend/src/components/layout/DashboardShell.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `DashboardShell`
- Importها: `./CommandPalette`, `./Sidebar`, `./TopBar`, `@/components/ui/StateNotice`, `@/lib/auth-context`, `next/navigation`, `react`
### `frontend/src/components/layout/NotificationsDropdown.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `NotificationsDropdown`
- مسیرهای ارجاع‌شده:
  - `/dashboard/notifications` (line 134)
- Importها: `@/components/ui/DateDisplay`, `@/components/ui/Tooltip`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/types`, `@/lib/utils`, `@tanstack/react-query`, `lucide-react`, `next/link`, `react`
### `frontend/src/components/layout/PublicHeader.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `PublicHeader`
- مسیرهای ارجاع‌شده:
  - `/` (line 14)
  - `/#listings` (line 27)
  - `/#market-trends` (line 30)
  - `/#capabilities` (line 33)
  - `/register` (line 36)
  - `/dashboard` (line 44)
  - `/login` (line 52)
- Importها: `@/lib/auth-context`, `lucide-react`, `next/link`, `react`
### `frontend/src/components/layout/Sidebar.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `Sidebar`
- Interfaceها: `SidebarProps`
- مسیرهای ارجاع‌شده:
  - `/dashboard` (line 114)
  - `/dashboard` (line 125)
- Importها: `@/components/ui/Tooltip`, `@/lib/auth-context`, `@/lib/role-navigation`, `@/lib/utils`, `lucide-react`, `next/link`, `next/navigation`, `react`
### `frontend/src/components/layout/ThemeToggle.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `ThemeToggle`
- Importها: `@/components/ui/Tooltip`, `@/lib/theme-provider`, `@/lib/utils`, `lucide-react`, `react`
### `frontend/src/components/layout/TopBar.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `TopBar`
- Importها: `./NotificationsDropdown`, `./ThemeToggle`, `@/components/ui/Avatar`, `@/components/ui/Kbd`, `@/lib/auth-context`, `lucide-react`, `next/navigation`, `react`
### `frontend/src/components/properties/PropertyCard.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `PropertyCard`
- Importها: `@/lib/auth-context`, `@/lib/formatters`, `@/lib/types`, `lucide-react`, `next/link`, `react`
### `frontend/src/components/properties/PropertyForm.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `PropertyForm`
- Typeها: `PropertyFormValues`
- Importها: `@/components/ui/StateNotice`, `@/lib/api-client`, `@/lib/auth-context`, `@/lib/types`, `@hookform/resolvers/zod`, `@tanstack/react-query`, `lucide-react`, `next/navigation`, `react`, `react-hook-form`, `zod`
### `frontend/src/components/ui/AnalyticsCharts.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `DonutBreakdownChart`, `HorizontalBarChart`
- Interfaceها: `ChartDatum`
- Importها: `@/lib/formatters`, `react`
### `frontend/src/components/ui/Avatar.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `Avatar`
- Importها: `@/lib/utils`, `react`
### `frontend/src/components/ui/Badge.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `Badge`
- Typeها: `Tone`
- Importها: `@/lib/utils`, `react`
### `frontend/src/components/ui/Button.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `Button`
- Interfaceها: `ButtonProps`
- Typeها: `Size`, `Variant`
- Importها: `@/lib/utils`, `react`
### `frontend/src/components/ui/Card.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `Card`, `CardContent`, `CardDescription`, `CardFooter`, `CardHeader`, `CardTitle`
- Importها: `@/lib/utils`, `react`
### `frontend/src/components/ui/DataTable.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `DataTable`
- Interfaceها: `ColumnDef`, `DataTableProps`, `FilterTab`
- Importها: `./StateNotice`, `lucide-react`, `react`
### `frontend/src/components/ui/DateDisplay.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `DateDisplay`
- Interfaceها: `DateDisplayProps`
- Importها: `@/lib/auth-context`, `@/lib/formatters`, `react`
### `frontend/src/components/ui/Dialog.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `Dialog`
- Interfaceها: `DialogProps`
- Importها: `@/lib/utils`, `lucide-react`, `react`
### `frontend/src/components/ui/Drawer.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `Drawer`
- Interfaceها: `DrawerProps`
- Importها: `@/lib/utils`, `lucide-react`, `react`
### `frontend/src/components/ui/Input.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `FieldError`, `Input`, `Label`, `Textarea`
- Interfaceها: `InputProps`
- Importها: `@/lib/utils`, `react`
### `frontend/src/components/ui/Kbd.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `Kbd`
- Importها: `@/lib/utils`, `react`
### `frontend/src/components/ui/KpiCard.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `KpiCard`
- Interfaceها: `KpiCardProps`
- Importها: `react`
### `frontend/src/components/ui/ModalDrawer.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `ModalDrawer`
- Interfaceها: `ModalDrawerProps`
- Importها: `lucide-react`, `react`
### `frontend/src/components/ui/MoneyDisplay.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `MoneyDisplay`
- Interfaceها: `MoneyDisplayProps`
- Importها: `@/lib/auth-context`, `@/lib/formatters`, `@/lib/types`, `react`
### `frontend/src/components/ui/PageHeader.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `PageHeader`
- Interfaceها: `BreadcrumbItem`, `PageHeaderProps`
- Importها: `lucide-react`, `next/link`, `react`
### `frontend/src/components/ui/Select.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `Select`
- Interfaceها: `SelectProps`
- Importها: `@/lib/utils`, `lucide-react`, `react`
### `frontend/src/components/ui/Separator.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `Separator`
- Importها: `@/lib/utils`, `react`
### `frontend/src/components/ui/Skeleton.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `Skeleton`
- Importها: `@/lib/utils`, `react`
### `frontend/src/components/ui/StateNotice.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `EmptyState`, `ErrorState`, `LoadingState`, `SuccessBanner`
- Importها: `lucide-react`, `react`
### `frontend/src/components/ui/StatusText.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `StatusText`
- Interfaceها: `StatusTextProps`
- Importها: `@/lib/formatters`, `react`
### `frontend/src/components/ui/Toast.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `ToastProvider`, `useToast`
- Interfaceها: `Toast`, `ToastContextValue`
- Typeها: `ToastTone`
- Hookها: `useToast`
- Importها: `@/lib/utils`, `lucide-react`, `react`
### `frontend/src/components/ui/Tooltip.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `Tooltip`
- Importها: `@/lib/utils`, `react`
### `frontend/src/lib/api-client.ts`
- خروجی‌ها/کامپوننت‌های احتمالی: `ApiRequestError`, `apiFetch`
- Interfaceها: `ApiEnvelope`, `ApiErrorItem`
- فراخوانی‌های API:
  - `/api/v1/auth/refresh` (line 55)
### `frontend/src/lib/auth-context.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `AuthProvider`, `useAuth`
- Interfaceها: `AuthContextValue`, `StoredAuth`
- Hookها: `useAuth`
- Importها: `./api-client`, `./role-navigation`, `./types`, `react`
### `frontend/src/lib/formatters.ts`
- خروجی‌ها/کامپوننت‌های احتمالی: `ROLE_LABELS_FA`, `STATUS_LABELS_FA`, `convertTomanRial`, `formatArea`, `formatLocalizedDate`, `formatLocalizedDateTime`, `formatMoney`, `formatNumberFa`, `translateStatus`
- Importها: `./types`
### `frontend/src/lib/role-navigation.ts`
- خروجی‌ها/کامپوننت‌های احتمالی: `ALL_NAV_ITEMS`, `NAV_GROUP_LABELS`, `getNavigationForUser`, `getRoleNavigationKeys`, `resolveEffectiveRole`
- Interfaceها: `NavItemConfig`
- Importها: `./types`
### `frontend/src/lib/theme-provider.tsx`
- خروجی‌ها/کامپوننت‌های احتمالی: `THEME_INIT_SCRIPT`, `ThemeProvider`, `useTheme`
- Interfaceها: `ThemeContextValue`
- Typeها: `ThemeMode`
- Hookها: `useTheme`
- Importها: `react`
### `frontend/src/lib/types.ts`
- Interfaceها: `AgencyAccessPolicy`, `AgencyItem`, `AgencyMembershipBrief`, `AppointmentItem`, `AuditLogItem`, `BranchItem`, `CoaAccount`, `CommissionItem`, `ContractItem`, `CooperationItem`, `CustomerItem`, `DealItem`, `DocumentItem`, `EmployeeItem`, `FollowUpTask`, `InteractionItem`, `JournalEntryItem`, `LeadItem`, `NegotiationItem`, `NotificationItem`, `PaginationMeta`, `PayrollCycleItem`, `PermissionItem`, `PipelineItem`, `PipelineStage`, `PropertyCatalog`, `PropertyItem`, `PropertyLocation`, `PropertyMediaItem`, `PublicSearchProperty`, `RoleItem`, `TeamMemberItem`, `UserProfile`
- Typeها: `AreaUnit`, `CalendarMode`, `CurrencyCode`, `EffectiveRole`, `PlatformRole`
### `frontend/src/lib/use-media-query.ts`
- خروجی‌ها/کامپوننت‌های احتمالی: `useMediaQuery`
- Hookها: `useMediaQuery`
- Importها: `react`
### `frontend/src/lib/utils.ts`
- خروجی‌ها/کامپوننت‌های احتمالی: `cn`
- Typeها: `ClassValue`

## 9. گراف وابستگی‌های محلی
> این ارتباط‌ها از importهای قابل resolve استخراج شده‌اند؛ وابستگی زمان اجرا ممکن است بیشتر باشد.
- `project_analyzer_v3.py` → `project_analyzer.py` (python-import)
- `frontend/src/components/layout/DashboardShell.tsx` → `frontend/src/components/layout/CommandPalette.tsx` (frontend-import)
- `frontend/src/components/layout/DashboardShell.tsx` → `frontend/src/components/layout/Sidebar.tsx` (frontend-import)
- `frontend/src/components/layout/DashboardShell.tsx` → `frontend/src/components/layout/TopBar.tsx` (frontend-import)
- `frontend/src/components/layout/TopBar.tsx` → `frontend/src/components/layout/NotificationsDropdown.tsx` (frontend-import)
- `frontend/src/components/layout/TopBar.tsx` → `frontend/src/components/layout/ThemeToggle.tsx` (frontend-import)
- `frontend/src/components/ui/DataTable.tsx` → `frontend/src/components/ui/StateNotice.tsx` (frontend-import)
- `frontend/src/lib/auth-context.tsx` → `frontend/src/lib/api-client.ts` (frontend-import)
- `frontend/src/lib/auth-context.tsx` → `frontend/src/lib/role-navigation.ts` (frontend-import)
- `frontend/src/lib/auth-context.tsx` → `frontend/src/lib/types.ts` (frontend-import)
- `frontend/src/lib/formatters.test.ts` → `frontend/src/lib/formatters.ts` (frontend-import)
- `frontend/src/lib/formatters.ts` → `frontend/src/lib/types.ts` (frontend-import)
- `frontend/src/lib/role-navigation.test.ts` → `frontend/src/lib/role-navigation.ts` (frontend-import)
- `frontend/src/lib/role-navigation.ts` → `frontend/src/lib/types.ts` (frontend-import)

## 10. فایل‌های مستندات و Schema
- مستندات: `frontend/README.md` — Run and deploy your AI Studio app

## 11. آمار ساختار
- `.css`: 3
- `.example`: 1
- `.jpg`: 4
- `.json`: 4
- `.md`: 1
- `.mjs`: 1
- `.py`: 162
- `.toml`: 2
- `.ts`: 11
- `.tsx`: 68
- `.txt`: 2
- `[no extension]`: 1

### کلاس‌های پرتکرار Tailwind
- `items-center`: 46
- `text-xs`: 45
- `flex`: 42
- `border`: 40
- `font-semibold`: 39
- `rounded-lg`: 38
- `h-4`: 36
- `text-sm`: 36
- `w-4`: 36
- `bg-white`: 34
- `w-full`: 34
- `font-bold`: 32
- `inline-flex`: 32
- `text-white`: 31
- `space-y-6`: 30
- `text-slate-900`: 30
- `border-slate-200`: 29
- `border-slate-300`: 29
- `gap-2`: 28
- `gap-3`: 28
- `font-mono`: 28
- `bg-teal-700`: 27
- `justify-between`: 27
- `h-10`: 26
- `px-3`: 26
- `gap-1.5`: 26
- `text-slate-500`: 25
- `h-9`: 24
- `font-medium`: 24
- `grid`: 23
- `rounded-xl`: 23
- `text-slate-700`: 23
- `hover:bg-teal-800`: 22
- `border-b`: 21
- `px-3.5`: 21
- `h-3.5`: 21
- `w-3.5`: 21
- `space-y-3`: 20
- `tabular-nums`: 19
- `text-slate-600`: 19

## 12. خطاها و محدودیت‌های تحلیل
- خطای خواندن یا Parse ثبت نشد.

## 13. راهنمای استفاده برای AI
- این سند نقشه استاتیک سورس‌کد است، نه تضمین رفتار واقعی برنامه.
- برای تغییر یک قابلیت، ابتدا مسیر فایل‌ها، نمادها و وابستگی‌های مرتبط را بررسی کن.
- قبل از تغییر مدل یا API، تمام ارجاع‌های آن را در سورس جست‌وجو کن.
- هرجا اطلاعات این سند کافی نیست، فایل‌های مرجع را مستقیماً بخوان؛ از حدس‌زدن خودداری کن.
- اطلاعات دارای عبارت «احتمالی» یا «استاتیک» قطعی نیستند.

## 14. مواردی که این نسخه تضمین نمی‌کند
- اجرای برنامه، تحلیل رفتار واقعی، کشف کامل جریان Business Logic یا اثبات نبود باگ.
- استخراج کامل URLهای Django، routerهای پویا، مسیرهای ساخته‌شده در زمان اجرا و APIهای غیرمستقیم.
- حل کامل aliasهای TypeScript، importهای barrel، dynamic import و تمام syntaxهای JSX با Regex.
- تولید ERD قطعی از migrationهای پیچیده، دیتابیس زنده یا مدل‌های سفارشی.
- تشخیص قطعی کد مرده، امنیت یا پوشش تست بدون ابزار تخصصی و اجرای کنترل‌شده.

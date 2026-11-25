# راهنمای توسعهٔ بنیان ملک

## از کجا شروع کنیم

1. برای تغییر API ابتدا مسیر متناظر را در `backend/fastapi_core/app/api/v1/` و محل ثبت آن را در `app/main.py` ببینید.
2. قواعد کسب‌وکار و تراکنش را در `backend/django_core/apps/<domain>/services.py` و مدل همان دامنه دنبال کنید. برای تغییر دیتابیس، migration همان برنامه را بررسی کنید.
3. در فرانت‌اند از `frontend/src/app/` و کامپوننت مربوط در `frontend/src/components/` شروع کنید. کلاینت HTTP و احراز هویت در `frontend/src/lib/api-client.ts` و `auth-context.tsx` هستند. مسیر `app/api/v1/[...path]/route.ts` واسط هم‌مبدأ است.
4. برای هر تغییر، مصرف‌کننده، سرویس، سیاست دسترسی و تست مرتبط را دنبال کنید. برای تغییرهای سراسری مثل نقش‌ها و مستأجر، تمام مسیرهای مصرف‌کنندهٔ همان قرارداد را بررسی کنید.
5. شواهد فعلی قابلیت‌ها و محدودیت‌های بررسی در `PRODUCT_AUDIT.md` آمده است.

## مسیرهای متداول

| حوزه | مسیرهای شروع |
|---|---|
| هویت و دسترسی | `api/v1/auth.py`، `app/dependencies/auth.py`، `apps/accounts/`، `common/permissions.py` |
| چندآژانسی | `app/core/django_bridge.py`، `common/tenant/`، migrationهای RLS در `apps/settings/` |
| مشتری و فروش | `api/v1/{customers,crm,matching}.py`، `apps/{customers,crm,search}/`، داشبورد `work-hub` |
| ملک و تور | `api/v1/properties.py`، بستهٔ `api/v1/virtual_tours/` و `apps/virtual_tours/` |
| قرارداد و مالی | `api/v1/{contracts_deals,payments,accounting}.py` و سرویس‌های همان دامنه |
| فایل و محتوا | `integrations/storage.py`، `apps/documents/services.py`، `common/sanitizer.py`، `api/v1/{documents,cms,settings}.py` |

## قواعد تغییر

- مجوز سمت سرور، آژانس و مالکیت شیء را هنگام خواندن و نوشتن کنترل کنید. شناسهٔ آژانس و شناسهٔ روابط از ورودی درخواست نیاز به تأیید دارند.
- برای مسیرهای عمومی، فقط دادهٔ منتشرشده و فیلدهای مجاز را سریال کنید. فایل خصوصی از مسیر سرویس ذخیره‌سازی و سیاست دسترسی دامنه عبور کند.
- در عملیات مالی و تغییر وضعیت‌ها، رفتار درخواست تکراری، شکست نیمه‌راه، هم‌زمانی و داده‌های نسخه‌های پیشین را بررسی کنید.
- اگر متن HTML ساخته یا نمایش داده می‌شود، عنوان و داده‌های متنی را escape و HTML محتوایی را با پاک‌کنندهٔ مشترک پردازش کنید.
- برای فایل، کلاس و تابعی که اضافه یا تغییر می‌دهید، توضیح فارسی کوتاه دربارهٔ مسئولیت و شرط‌های مهم بنویسید.
- تنظیمات محلی را از `.env.example` بسازید. کلید و دادهٔ محیط عملیاتی را در گزارش یا مخزن قرار ندهید.

## اجرای بررسی‌ها

- بک‌اند از `backend/` با `python -m pip install -r requirements.txt` آماده می‌شود. برای Django، از `backend/django_core/`، دستور `python manage.py check` و `python -m pytest` را اجرا کنید.
- برای FastAPI، از `backend/fastapi_core/` دستور `python -m pytest` را اجرا کنید. برای اجرای pytest-django، مسیر مطلق `backend/django_core/` را به `PYTHONPATH` بدهید و `DJANGO_SETTINGS_MODULE` را روی `config.settings.test` قرار دهید. هر دو URL پایگاه داده را برای محیط آزمایشی تنظیم کنید. آزمون RLS به PostgreSQL و نقش‌های واقعی نیاز دارد.
- فرانت‌اند از `frontend/` با `npm ci` نصب می‌شود. بررسی نوع با `npm run lint`، تست واحد با `npm test` و ساخت تولیدی با `npm run build` انجام می‌شود.

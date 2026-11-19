# معیارهای پذیرش و نقشه اجرای مرحله‌ای (فاز ۰ و هسته اولیه)

## ۱. معیارهای پذیرش فاز ۰ (زیرساخت Monorepo)
1. وجود ساختار سه‌سرویسی کامل: `backend/django_core/` (Django بدون DRF)، `backend/fastapi_core/` (FastAPI)، `frontend/` (Next.js + TS + Tailwind)، به همراه `docker-compose.yml`، `infra/` و `.env.example`.
2. پیکربندی PostgreSQL و Redis در `config/settings/base.py` و `production.py` همراه با Migrationهای اولیه تمامی Appهای ثبت‌شده.
3. برقراری ارتباط احراز هویت‌شده با JWT بین Next.js، Django و FastAPI (تست Healthcheck و Token Verification).
4. پاس شدن تست‌های اولیه زیرساخت:
   - تست تبدیل تاریخ UTC ↔ شمسی (`CalendarAdapter`)
   - تست تبدیل صریح ارز `IRT ↔ IRR` با `Decimal`
   - تست ایزوله‌سازی Multi-Tenant در لایه ORM و دسترسی‌های ۱۰گانه آژانس
   - تست آداپتورهای Payment/SMS/Map (Sandbox/Console/OSM)

## ۲. معیارهای پذیرش گام‌های اول هسته (`accounts`, `agencies`, `branches`, `properties`, `customers`)
1. ثبت‌نام/ورود کاربر با صدور JWT، مشاهده و ابطال نشست‌ها، پروفایل کاربری.
2. ایجاد آژانس و شعبه، تأیید آژانس توسط Super Admin، تنظیم سیاست‌های دسترسی ۱۰گانه آژانس (`AgencyAccessPolicy`).
3. ثبت ملک توسط مشاور ← بررسی و انتشار توسط مدیر آژانس ← نمایش عمومی در Next.js با پنهان‌سازی آدرس دقیق و اطلاعات مالک.
4. ثبت مشتری و تقاضا ← اعمال سیاست محرمانگی مشتری و مالک ← تطبیق هوشمند در FastAPI (`/engine/v1/matching/...`).
5. ثبت رویدادهای حساس در `AuditLog` غیرقابل تغییر.

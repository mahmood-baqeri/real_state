# راهنمای عیب‌یابی دیتابیس بنیان ملک

این راهنما برای تشخیص اختلاف بین مدل‌های Django، Migrationها و دیتابیس واقعی است.

## ۱) ابتدا از دیتابیس بکاپ بگیرید

قبل از هر Migration، از دیتابیس PostgreSQL نسخه پشتیبان تهیه کنید.

## ۲) اجرای بررسی فقط‌خواندنی

در PowerShell و از پوشه اصلی پروژه اجرا کنید:

```powershell
.\check_project.ps1
```

یا برای بررسی دقیق جدول اسناد:

```powershell
cd .\backend\django_core
python manage.py showmigrations documents
python manage.py diagnose_schema --app documents
```

دستور `diagnose_schema` فقط اتصال، وضعیت Migration و ستون‌های واقعی را می‌خواند و هیچ تغییری در دیتابیس نمی‌دهد.

## ۳) تفسیر خطای documents_document.is_deleted

در سورس فعلی، مدل `Document` از `SoftDeleteMixin` ارث‌بری می‌کند و Migration شماره `0002_document_deleted_at_document_deleted_by_and_more` هر سه فیلد `is_deleted`، `deleted_at` و `deleted_by_id` را اضافه می‌کند.

- اگر Migration شماره 0002 با `[ ]` نمایش داده شد، هنوز روی دیتابیسی که Django به آن وصل است اجرا نشده است.
- اگر با `[X]` نمایش داده شد ولی ستون‌ها وجود نداشتند، احتمالاً به دیتابیس دیگری وصل شده‌اید یا سابقه Migration با ساختار واقعی دیتابیس ناسازگار است.
- اگر ستون‌ها در بررسی Django وجود داشتند اما درخواست FastAPI همچنان همین خطا را می‌دهد، تنظیمات اتصال و متغیر `DATABASE_URL` فرایند FastAPI را با فرایند Django مقایسه کنید.

فقط در حالت اول، پس از اطمینان از بکاپ و مقصد اتصال، Migrationهای pending را اجرا کنید:

```powershell
python manage.py migrate
```

در حالت دوم از `--fake`، حذف رکوردهای `django_migrations` یا اجرای `ALTER TABLE` حدسی خودداری کنید. ابتدا باید دیتابیس مقصد و تاریخچه Migration بررسی شود.

## ۴) نکته درباره فایل محیطی

در نسخه فعلی، تنظیمات Django فایل `.env` را از ریشه پروژه بارگذاری می‌کند. مطمئن شوید فایل `.env` در همان مسیر مورد انتظار قرار دارد و مقدار `DATABASE_URL` به دیتابیس مورد استفاده برنامه اشاره می‌کند. رمز عبور یا مقدار کامل `DATABASE_URL` را در گزارش عمومی ارسال نکنید.

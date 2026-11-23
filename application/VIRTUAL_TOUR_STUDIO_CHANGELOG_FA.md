# گزارش تغییرات Virtual Tour Studio

## اصلاحات انجام‌شده در این نسخه

1. **رفع عنوان خالی نوع فضاها:** قرارداد نوع اتاق در فرانت‌اند با پاسخ واقعی API هماهنگ شد. API کاتالوگ را با کلید `label` می‌فرستد؛ رابط کاربری اکنون `label` و `label_fa` قدیمی را می‌پذیرد.
2. **کاتالوگ پشتیبان واحد در فرانت‌اند:** در صورت نبود تنظیمات API، ۱۵ نوع فضای موجود در مدل Django با عنوان فارسی نمایش داده می‌شوند. مقدارهای داخلی مانند `living_room` و `dining_room` تغییر نکرده‌اند.
3. **یکسان‌سازی نمایش در فرم‌ها:** فرم ایجاد صحنه و ابزار تعریف اتاق روی پلان از تابع مشترک عنوان فارسی استفاده می‌کنند.
4. **ناوبری مستقیم فضاها:** در نمایشگر پانوراما انتخاب مستقیم تمام فضاهای تور، دکمه فضای قبلی/بعدی و شماره موقعیت اضافه شد. انتخاب از فهرست می‌تواند بین طبقات جابه‌جا شود و پانورامای همان صحنه را باز کند.
5. **شفاف‌سازی منشأ Dollhouse فعلی:** برای مدل‌هایی که `geometry_source=floorplan_2d_extrusion` دارند، هشدار روشن نمایش داده می‌شود که این هندسه از پلان دوبعدی و دیوارهای ترسیم‌شده ساخته شده و بازسازی فوتوگرامتری از تصاویر موبایل نیست.

## محدودیت مهم بازسازی سه‌بعدی واقعی

در سورس فعلی، تابع `build_parametric_dollhouse_glb` در `backend/django_core/apps/virtual_tours/services/geometry_service.py` هندسه GLB را از چندضلعی اتاق‌ها و دیوارهای پلان می‌سازد و مقدار منشأ را `floorplan_2d_extrusion` ثبت می‌کند. این یک مدل هندسی پارامتریک مبتنی بر پلان است، نه خروجی Structure-from-Motion / Multi-View Stereo.

در محیط بررسی این بسته، باینری COLMAP و ابزارهای OpenMVS و ماژول‌های Python مانند `pycolmap` و `open3d` نصب نبودند. بنابراین اتصال فوتوگرامتری واقعی، تخمین pose دوربین از تصاویر، dense point cloud، mesh reconstruction و texture mapping در این نسخه پیاده‌سازی یا ادعا نشده است. پانوراماهای ۳۶۰ به‌تنهایی نیز برای استخراج هندسه متریک واقعی کافی نیستند.

برای تکمیل آن بخش باید تصاویر خام هم‌پوشانِ چند زاویه از فضاها، مشخصات دوربین/فاصله کانونی در صورت دسترس، و ابزار پردازش SfM/MVS روی worker پردازشی فراهم شود. تا پیش از آن، مدل پلان‌محور فعلی باید با همین منشأ و دقت تقریبی شناخته شود.

## فایل‌های تغییرکرده

- `frontend/src/lib/types.ts`
- `frontend/src/lib/virtual-tour-room-types.ts` (جدید)
- `frontend/src/app/dashboard/properties/[id]/virtual-tour/page.tsx`
- `frontend/src/app/dashboard/properties/%5Bid%5D/virtual-tour/page.tsx` (نسخه مسیر کدگذاری‌شده موجود در بسته)
- `frontend/src/components/virtual-tour/FloorPlanEditor.tsx`
- `frontend/src/components/virtual-tour/PanoramaViewer.tsx`
- `frontend/src/components/virtual-tour/DollhouseViewer.tsx`

## وضعیت آزمون

این محیط فاقد `frontend/node_modules` بود؛ بنابراین build و type-check کامل Next.js در این نوبت اجرا نشد. فایل‌ها از نظر تغییرات متنی بررسی شدند. پیش از استقرار، اجرای `npm ci` و سپس `npm run lint` و `npm run build` در محیط پروژه ضروری است.

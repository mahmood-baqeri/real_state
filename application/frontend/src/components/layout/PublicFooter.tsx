import React from "react";
import Link from "next/link";
import { Building2 } from "lucide-react";

export function PublicFooter() {
  return (
    <footer className="border-t border-slate-200 bg-white text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-slate-900 dark:text-slate-100">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-700 text-white dark:bg-teal-600">
                <Building2 className="h-4 w-4" />
              </div>
              <span className="text-base font-bold">بنیان ملک</span>
            </div>
            <p className="text-xs leading-relaxed">
              پلتفرم سازمانی چندآژانسی مدیریت املاک، پایپ‌لاین فروش CRM، محاسبه دقیق کمیسیون و
              حسابداری دوطرفه برای شبکه حرفه‌ای مشاوران املاک.
            </p>
          </div>

          <div>
            <h3 className="mb-3 text-xs font-bold text-slate-900 dark:text-slate-100">
              جستجو و پورتال ملک
            </h3>
            <ul className="space-y-2 text-xs">
              <li>
                <Link href="/properties" className="hover:text-teal-700 dark:hover:text-teal-400">
                  فهرست کامل فایل‌های تأییدشده
                </Link>
              </li>
              <li>
                <Link href="/search" className="hover:text-teal-700 dark:hover:text-teal-400">
                  جستجوی پیشرفته و فیلتر مناطق
                </Link>
              </li>
              <li>
                <Link
                  href="/explore/tehran"
                  className="hover:text-teal-700 dark:hover:text-teal-400"
                >
                  املاک تهران و مناطق منتخب
                </Link>
              </li>
              <li>
                <Link href="/blog" className="hover:text-teal-700 dark:hover:text-teal-400">
                  مجله تخصصی و تحلیل بازار
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="mb-3 text-xs font-bold text-slate-900 dark:text-slate-100">
              آژانس‌ها و خدمات سازمانی
            </h3>
            <ul className="space-y-2 text-xs">
              <li>
                <Link href="/features" className="hover:text-teal-700 dark:hover:text-teal-400">
                  امکانات و زیرساخت فناوری
                </Link>
              </li>
              <li>
                <Link href="/pricing" className="hover:text-teal-700 dark:hover:text-teal-400">
                  تعرفه‌ها و پلن‌های اشتراک
                </Link>
              </li>
              <li>
                <Link
                  href="/agency-application"
                  className="hover:text-teal-700 dark:hover:text-teal-400"
                >
                  درخواست همکاری آژانس املاک
                </Link>
              </li>
              <li>
                <Link href="/services" className="hover:text-teal-700 dark:hover:text-teal-400">
                  خدمات و مشاوره استقرار
                </Link>
              </li>
              <li>
                <Link href="/guide" className="hover:text-teal-700 dark:hover:text-teal-400">
                  راهنمای استفاده از سامانه
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="mb-3 text-xs font-bold text-slate-900 dark:text-slate-100">
              پشتیبانی، پیگیری و قوانین
            </h3>
            <ul className="space-y-2 text-xs">
              <li>
                <Link href="/requests/new" className="hover:text-teal-700 dark:hover:text-teal-400">
                  ثبت درخواست و پیگیری
                </Link>
              </li>
              <li>
                <Link
                  href="/complaints/new"
                  className="hover:text-teal-700 dark:hover:text-teal-400"
                >
                  ثبت و پیگیری شکایت
                </Link>
              </li>
              <li>
                <Link href="/faq" className="hover:text-teal-700 dark:hover:text-teal-400">
                  سؤالات متداول
                </Link>
              </li>
              <li>
                <Link href="/about" className="hover:text-teal-700 dark:hover:text-teal-400">
                  درباره ما و فرصت‌های شغلی
                </Link>
              </li>
              <li>
                <Link href="/terms" className="hover:text-teal-700 dark:hover:text-teal-400">
                  قوانین، حریم خصوصی و شرایط استفاده
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-10 flex flex-col items-center justify-between gap-3 border-t border-slate-200 pt-6 text-[11px] dark:border-slate-800 sm:flex-row">
          <span>© ۱۴۰۵ پلتفرم سازمانی بنیان ملک — تمامی حقوق محفوظ است.</span>
          <div className="flex items-center gap-4">
            <Link href="/privacy" className="hover:text-teal-700 dark:hover:text-teal-400">
              حریم خصوصی
            </Link>
            <Link href="/terms-of-use" className="hover:text-teal-700 dark:hover:text-teal-400">
              شرایط استفاده
            </Link>
            <Link href="/careers" className="hover:text-teal-700 dark:hover:text-teal-400">
              فرصت‌های شغلی
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}

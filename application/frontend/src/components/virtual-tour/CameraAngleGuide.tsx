"use client";

import React from "react";
import { Camera, CheckCircle2, Compass, Info, MoveDown, MoveUp } from "lucide-react";

const horizontalAngles = Array.from({ length: 12 }, (_, index) => index * 30);
const ringAngles = [0, 60, 120, 180, 240, 300];
const capAngles = [0, 120, 240];

function AnglePills({ angles }: { angles: number[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {angles.map((angle) => (
        <span key={angle} className="inline-flex min-w-11 items-center justify-center rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] font-bold tabular-nums text-slate-700 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200">
          {angle}°
        </span>
      ))}
    </div>
  );
}

export function CameraAngleGuide() {
  return (
    <details className="group overflow-hidden rounded-xl border border-sky-200 bg-white dark:border-sky-900 dark:bg-slate-900" open>
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 bg-sky-50 px-4 py-3 dark:bg-sky-950/30 [&::-webkit-details-marker]:hidden">
        <span className="flex items-center gap-2 text-xs font-bold text-sky-950 dark:text-sky-100">
          <Camera className="h-4 w-4" />
          راهنمای کامل زاویه‌های دوربین (Yaw و Pitch)
        </span>
        <span className="text-[10px] font-semibold text-sky-700 group-open:hidden dark:text-sky-300">نمایش راهنما</span>
        <span className="hidden text-[10px] font-semibold text-sky-700 group-open:inline dark:text-sky-300">بستن راهنما</span>
      </summary>

      <div className="space-y-4 p-4 text-[11px] leading-6 text-slate-700 dark:text-slate-300">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
            <div className="mb-1 flex items-center gap-2 font-bold text-slate-900 dark:text-slate-100"><Compass className="h-4 w-4 text-teal-600" /> زاویه افقی — Yaw</div>
            <p>جهت چرخش گوشی به چپ یا راست، حول محور عمودی است. صفر درجه فقط جهت شروع شماست؛ سپس گوشی را در همان ارتفاع، دور خود بچرخانید.</p>
            <div className="mt-2 rounded-md bg-slate-50 p-2 dark:bg-slate-950">
              <div className="mb-1 text-[10px] font-semibold text-slate-500">۱۲ جهت افقی با فاصله ۳۰ درجه</div>
              <AnglePills angles={horizontalAngles} />
            </div>
            <p className="mt-2 text-[10px] text-slate-500">۰°، ۳۰°، ۶۰° ... تا ۳۳۰°؛ پس از ۳۳۰° یک دور کامل ۳۶۰ درجه می‌شود. نقطه ۳۶۰° همان ۰° است و عکس تکراری نگیرید.</p>
          </div>

          <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
            <div className="mb-1 flex items-center gap-2 font-bold text-slate-900 dark:text-slate-100"><MoveUp className="h-4 w-4 text-amber-600" /> زاویه عمودی — Pitch</div>
            <p>میزان بالا یا پایین گرفتن لنز نسبت به حالت مستقیم است. در این راهنما، عدد مثبت یعنی دوربین رو به بالا و عدد منفی یعنی دوربین رو به پایین.</p>
            <div className="mt-3 flex items-center justify-center gap-5 rounded-md bg-slate-50 p-3 dark:bg-slate-950">
              <div className="text-center"><MoveUp className="mx-auto h-6 w-6 text-amber-600" /><div className="font-bold">+۴۰° / +۸۰°</div><div className="text-[10px] text-slate-500">رو به بالا</div></div>
              <div className="h-12 w-px bg-slate-300 dark:bg-slate-700" />
              <div className="text-center"><Camera className="mx-auto h-6 w-6 text-teal-600" /><div className="font-bold">۰°</div><div className="text-[10px] text-slate-500">مستقیم</div></div>
              <div className="h-12 w-px bg-slate-300 dark:bg-slate-700" />
              <div className="text-center"><MoveDown className="mx-auto h-6 w-6 text-sky-600" /><div className="font-bold">−۴۰° / −۸۰°</div><div className="text-[10px] text-slate-500">رو به پایین</div></div>
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <h4 className="font-bold text-slate-900 dark:text-slate-100">ترتیب دقیق عکاسی در الگوی پیش‌فرض سیستم</h4>
          <div className="grid gap-2 sm:grid-cols-2">
            <div className="rounded-lg border border-teal-200 bg-teal-50/60 p-3 dark:border-teal-900 dark:bg-teal-950/20">
              <div className="mb-1 flex items-center justify-between gap-2"><strong className="text-teal-900 dark:text-teal-200">۱. حلقه افقی — ۱۲ عکس</strong><span className="rounded bg-teal-100 px-2 py-0.5 text-[10px] font-bold text-teal-800 dark:bg-teal-900 dark:text-teal-200">Pitch = ۰°</span></div>
              <p>گوشی را در ارتفاع چشم و کاملاً روبه‌رو نگه دارید. از جهت شروع، هر بار ۳۰ درجه بچرخید و عکس بگیرید.</p>
              <AnglePills angles={horizontalAngles} />
            </div>
            <div className="rounded-lg border border-amber-200 bg-amber-50/60 p-3 dark:border-amber-900 dark:bg-amber-950/20">
              <div className="mb-1 flex items-center justify-between gap-2"><strong className="text-amber-900 dark:text-amber-200">۲. حلقه رو به بالا — ۶ عکس</strong><span className="rounded bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-800 dark:bg-amber-900 dark:text-amber-200">Pitch = +۴۰°</span></div>
              <p>دوربین را حدود ۴۰ درجه بالا بگیرید؛ در هر جهت بخشی از دیوار و سقف در تصویر باشد. هر ۶۰ درجه یک عکس.</p>
              <AnglePills angles={ringAngles} />
            </div>
            <div className="rounded-lg border border-sky-200 bg-sky-50/60 p-3 dark:border-sky-900 dark:bg-sky-950/20">
              <div className="mb-1 flex items-center justify-between gap-2"><strong className="text-sky-900 dark:text-sky-200">۳. حلقه رو به پایین — ۶ عکس</strong><span className="rounded bg-sky-100 px-2 py-0.5 text-[10px] font-bold text-sky-800 dark:bg-sky-900 dark:text-sky-200">Pitch = −۴۰°</span></div>
              <p>دوربین را حدود ۴۰ درجه پایین بگیرید؛ در هر جهت بخشی از دیوار و کف در تصویر باشد. هر ۶۰ درجه یک عکس.</p>
              <AnglePills angles={ringAngles} />
            </div>
            <div className="rounded-lg border border-violet-200 bg-violet-50/60 p-3 dark:border-violet-900 dark:bg-violet-950/20">
              <div className="mb-1 flex items-center justify-between gap-2"><strong className="text-violet-900 dark:text-violet-200">۴. پوشش سقف — ۳ عکس</strong><span className="rounded bg-violet-100 px-2 py-0.5 text-[10px] font-bold text-violet-800 dark:bg-violet-900 dark:text-violet-200">Pitch = +۸۰°</span></div>
              <p>لنز را نزدیک ۸۰ درجه به سمت بالا بگیرید تا سقف و ناحیه بالای تصویر پوشش داده شود.</p>
              <AnglePills angles={capAngles} />
            </div>
            <div className="rounded-lg border border-indigo-200 bg-indigo-50/60 p-3 dark:border-indigo-900 dark:bg-indigo-950/20 sm:col-span-2">
              <div className="mb-1 flex items-center justify-between gap-2"><strong className="text-indigo-900 dark:text-indigo-200">۵. پوشش کف — ۳ عکس</strong><span className="rounded bg-indigo-100 px-2 py-0.5 text-[10px] font-bold text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200">Pitch = −۸۰°</span></div>
              <p>لنز را نزدیک ۸۰ درجه به سمت پایین بگیرید تا کف و ناحیه پایین تصویر پوشش داده شود.</p>
              <AnglePills angles={capAngles} />
            </div>
          </div>
          <div className="flex items-start gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-950">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-teal-600" />
            <div><strong className="text-slate-900 dark:text-slate-100">جمع کل الگوی پیش‌فرض: ۳۰ عکس</strong><p>۱۲ افقی + ۶ بالا + ۶ پایین + ۳ سقف + ۳ کف. تنظیمات مدیر سیستم ممکن است تعداد یا الزام عکس‌های سقف و کف را تغییر دهد؛ مراحل واقعی و ترتیب نهایی را همیشه از فهرست عکاسی هدایت‌شده دنبال کنید.</p></div>
          </div>
        </div>

        <div className="grid gap-2 sm:grid-cols-2">
          <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800"><strong className="flex items-center gap-1.5 text-slate-900 dark:text-slate-100"><CheckCircle2 className="h-3.5 w-3.5 text-teal-600" /> روش صحیح ثبت هر عکس</strong><ul className="mt-1 list-inside list-disc space-y-1"><li>در محل تقریبی مرکز اتاق بایستید.</li><li>گوشی را تا حد ممکن نزدیک همان نقطه نگه دارید.</li><li>پس از چرخش، چند لحظه صبر کنید تا تصویر ثابت شود.</li><li>از حرکت‌دادن بدن و جابه‌جایی مکان بین عکس‌ها خودداری کنید.</li></ul></div>
          <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800"><strong className="flex items-center gap-1.5 text-slate-900 dark:text-slate-100"><Info className="h-3.5 w-3.5 text-sky-600" /> هم‌پوشانی و کیفیت</strong><ul className="mt-1 list-inside list-disc space-y-1"><li>هر عکس باید بخشی از عکس قبلی را تکرار کند؛ دیوارها و گوشه‌ها نقاط مرجع خوبی هستند.</li><li>از تغییر شدید نور، زوم و حالت لنز در میانه کار پرهیز کنید.</li><li>افراد و اشیای متحرک را از محدوده ثبت دور نگه دارید.</li><li>در صورت اعلام نیاز به ثبت مجدد، همان زاویه را دوباره بگیرید.</li></ul></div>
        </div>
        <p className="text-[10px] text-slate-500">نکته: Yaw و Pitch زاویه هدف هر فریم هستند. قطب‌نمای گوشی و حسگر چرخش ممکن است با توجه به کالیبراسیون دستگاه کمی اختلاف داشته باشند؛ راهنمای مرحله جاری در ابزار عکاسی، مرجع عملی ثبت است.</p>
      </div>
    </details>
  );
}

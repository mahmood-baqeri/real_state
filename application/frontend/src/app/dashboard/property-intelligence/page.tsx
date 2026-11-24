"use client";
import React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ArrowLeft, Search, SearchCheck, TrendingDown, Clock3 } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { PageHeader } from "@/components/ui/PageHeader";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";

type QualityRow = { property_id: string; property_code: string; title: string; status: string; quality_score: number; missing_checks: string[]; verification_status: string; possible_duplicate_ids: string[]; price_valid_until: string | null };
type QualityData = { total: number; average_score: number; low_quality: number; items: QualityRow[] };
type SearchResult = { id: string; property_code: string; title: string; city: string; district: string; status: string };
type MarketData = { city: string; currency: string; minimum_sample_count: number; threshold_percent: number; count: number; items: { property_id: string; property_code: string; title: string; district: string; deal_type: string; property_type: string; currency: string; price_per_sqm: string; district_average: string; discount_percent: number; sample_count: number }[] };
type PriceData = { window_days: number; expiring_or_expired: { property_id: string; property_code: string; title: string; price_valid_until: string; expired: boolean }[]; recent_changes: { property_id: string; property_code: string; title: string; previous_price: string; new_price: string; price_type: "SALE" | "RENT"; currency: string; changed_at: string }[]; expired_count: number };
const checkLabels: Record<string,string> = { title:"عنوان", description:"توضیحات", location:"موقعیت", area:"متراژ", price:"قیمت", bedrooms:"اتاق", media:"تصاویر", verification:"احراز اصالت", duplicate_free:"عدم تکرار" };
function dateFa(value: string) { try { return new Date(value).toLocaleDateString("fa-IR"); } catch { return value; } }
export default function PropertyIntelligencePage() {
  const { accessToken, activeAgencyId } = useAuth();
  const [searchText, setSearchText] = useState("");
  const [submittedSearch, setSubmittedSearch] = useState("");
  const [marketCity, setMarketCity] = useState("تهران");
  const [submittedMarketCity, setSubmittedMarketCity] = useState("تهران");
  const quality = useQuery({ queryKey:["property-quality",activeAgencyId], enabled:!!accessToken&&!!activeAgencyId, queryFn:async()=> (await apiFetch<QualityData>("/api/v1/matching/property-quality",{token:accessToken,agencyId:activeAgencyId})).data });
  const prices = useQuery({ queryKey:["property-price-alerts",activeAgencyId], enabled:!!accessToken&&!!activeAgencyId, queryFn:async()=> (await apiFetch<PriceData>("/api/v1/matching/price-alerts?days=30",{token:accessToken,agencyId:activeAgencyId})).data });
  const searchQ = useQuery({ queryKey:["property-intelligent-search",activeAgencyId,submittedSearch], enabled:!!accessToken&&submittedSearch.length>0, queryFn:async()=> (await apiFetch<{query:string;normalized_query:string;results:SearchResult[];count:number}>(`/api/v1/matching/search?q=${encodeURIComponent(submittedSearch)}&limit=20`,{token:accessToken,agencyId:activeAgencyId})).data });
  const marketQ = useQuery({ queryKey:["property-market-radar",submittedMarketCity], enabled:!!accessToken&&submittedMarketCity.length>0, queryFn:async()=> (await apiFetch<MarketData>(`/api/v1/matching/market-opportunities?city=${encodeURIComponent(submittedMarketCity)}&currency_code=IRT`,{token:accessToken,agencyId:activeAgencyId})).data });
  return <div className="space-y-6">
    <PageHeader title="هوشمندی فایل‌های املاک" subtitle="امتیاز کیفیت فایل، موارد ناقص، احتمال تکرار و هشدار اعتبار قیمت" breadcrumbs={[{label:"میز کار",href:"/dashboard"},{label:"املاک",href:"/dashboard/properties"},{label:"هوشمندی فایل"}]} actions={<Link href="/dashboard/properties" className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm"><ArrowLeft className="h-4 w-4"/> بازگشت به فایل‌ها</Link>} />
    {!activeAgencyId && <ErrorState message="برای گزارش کیفیت و هشدارها، آژانس فعال را از منوی بالای داشبورد انتخاب کنید."/>}
    {(quality.isLoading||prices.isLoading)&&activeAgencyId&&<LoadingState/>}
    {quality.error instanceof Error&&<ErrorState message={quality.error.message}/>}
    {prices.error instanceof Error&&<ErrorState message={prices.error.message}/>}
    {quality.data&&<div className="grid gap-3 sm:grid-cols-3">
      <div className="rounded-xl border bg-card p-4"><div className="text-sm text-muted-foreground">فایل‌های بررسی‌شده</div><div className="mt-1 text-2xl font-bold">{quality.data.total}</div></div>
      <div className="rounded-xl border bg-card p-4"><div className="text-sm text-muted-foreground">میانگین کیفیت</div><div className="mt-1 text-2xl font-bold">{quality.data.average_score}٪</div></div>
      <div className="rounded-xl border bg-card p-4"><div className="text-sm text-muted-foreground">کیفیت زیر ۶۰٪</div><div className="mt-1 text-2xl font-bold text-amber-600">{quality.data.low_quality}</div></div>
    </div>}
    <section className="space-y-3 rounded-xl border bg-card p-4">
      <h2 className="flex items-center gap-2 font-semibold"><Search className="h-5 w-5"/> جستجوی فارسی هوشمند فایل</h2>
      <form onSubmit={(e)=>{e.preventDefault();setSubmittedSearch(searchText.trim());}} className="flex gap-2">
        <input value={searchText} onChange={(e)=>setSearchText(e.target.value)} placeholder="مثلاً آپارتمان، ویلا، رهن یا منطقه..." className="h-10 min-w-0 flex-1 rounded-lg border bg-background px-3 text-sm" />
        <button type="submit" disabled={!searchText.trim()} className="rounded-lg bg-teal-700 px-4 text-sm font-semibold text-white disabled:opacity-50">جستجو</button>
      </form>
      {searchQ.isLoading&&<LoadingState message="در حال جستجو..."/>}
      {searchQ.error instanceof Error&&<ErrorState message={searchQ.error.message}/>}
      {searchQ.data&&<div className="space-y-2">{searchQ.data.results.length===0?<p className="text-sm text-muted-foreground">نتیجه‌ای یافت نشد.</p>:searchQ.data.results.map(r=><div key={r.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3"><div><Link className="font-medium hover:underline" href={`/dashboard/properties/${r.id}`}>{r.title}</Link><div className="text-xs text-muted-foreground">{r.property_code} · {r.city} · {r.district}</div></div><Link className="text-xs font-medium text-teal-700 dark:text-teal-300" href={`/dashboard/properties/${r.id}`}>مشاهده فایل</Link></div>)}</div>}
    </section>
    {quality.data&&<section className="space-y-3 rounded-xl border bg-card p-4">
      <h2 className="flex items-center gap-2 font-semibold"><SearchCheck className="h-5 w-5"/> کیفیت و تکمیل اطلاعات</h2>
      {quality.data.items.length===0?<div className="text-sm text-muted-foreground">فایلی برای بررسی در محدوده دسترسی شما وجود ندارد.</div>:<div className="overflow-x-auto"><table className="w-full min-w-[720px] text-sm"><thead><tr className="border-b text-right text-muted-foreground"><th className="p-2">ملک</th><th className="p-2">کیفیت</th><th className="p-2">موارد ناقص</th><th className="p-2">تکراری</th><th className="p-2">اصالت</th></tr></thead><tbody>{quality.data.items.map(r=><tr key={r.property_id} className="border-b last:border-0"><td className="p-2"><Link className="font-medium hover:underline" href={`/dashboard/properties/${r.property_id}`}>{r.title}</Link><div className="text-xs text-muted-foreground">{r.property_code}</div></td><td className="p-2"><span className={`font-semibold ${r.quality_score<60?"text-amber-600":"text-emerald-600"}`}>{r.quality_score}٪</span></td><td className="p-2 text-xs">{r.missing_checks.length? r.missing_checks.map(k=>checkLabels[k]||k).join("، "):"تکمیل"}</td><td className="p-2">{r.possible_duplicate_ids.length?<span className="text-amber-600">احتمال تکراری ({r.possible_duplicate_ids.length})</span>:"—"}</td><td className="p-2 text-xs">{r.verification_status==="VERIFIED"||r.verification_status==="EXCEPTION_APPROVED"?<span className="text-emerald-600">تأیید</span>:<span className="text-amber-600">تأیید نشده</span>}</td></tr>)}</tbody></table></div>}
    </section>}
    {prices.data&&<div className="grid gap-4 lg:grid-cols-2">
      <section className="rounded-xl border bg-card p-4 space-y-3"><h2 className="flex items-center gap-2 font-semibold"><Clock3 className="h-5 w-5"/> قیمت‌های منقضی/رو به انقضا (۳۰ روز)</h2>{prices.data.expiring_or_expired.length===0?<p className="text-sm text-muted-foreground">موردی یافت نشد.</p>:prices.data.expiring_or_expired.map(p=><div key={p.property_id} className="flex items-center justify-between gap-3 border-b py-2 last:border-0"><div><Link href={`/dashboard/properties/${p.property_id}`} className="font-medium hover:underline">{p.title}</Link><div className="text-xs text-muted-foreground">{p.property_code} · {dateFa(p.price_valid_until)}</div></div><span className={`text-xs font-medium ${p.expired?"text-rose-600":"text-amber-600"}`}>{p.expired?"منقضی":"رو به انقضا"}</span></div>)}</section>
      <section className="rounded-xl border bg-card p-4 space-y-3"><h2 className="flex items-center gap-2 font-semibold"><TrendingDown className="h-5 w-5"/> تغییرات قیمت اخیر</h2>{prices.data.recent_changes.length===0?<p className="text-sm text-muted-foreground">تغییر قیمتی در این بازه ثبت نشده است.</p>:prices.data.recent_changes.map(h=><div key={`${h.property_id}-${h.changed_at}`} className="border-b py-2 last:border-0"><Link href={`/dashboard/properties/${h.property_id}`} className="font-medium hover:underline">{h.title}</Link><div className="mt-1 text-xs text-muted-foreground">{h.previous_price} ← {h.new_price} {h.price_type==="RENT"?`اجاره · ${h.currency}`:h.currency} · {dateFa(h.changed_at)}</div></div>)}</section>
    </div>}
    <section className="space-y-3 rounded-xl border bg-card p-4">
      <h2 className="flex items-center gap-2 font-semibold"><TrendingDown className="h-5 w-5"/> رادار فرصت بازار</h2>
      <form onSubmit={(e)=>{e.preventDefault();setSubmittedMarketCity(marketCity.trim());}} className="flex gap-2">
        <input value={marketCity} onChange={(e)=>setMarketCity(e.target.value)} placeholder="شهر" className="h-10 min-w-0 flex-1 rounded-lg border bg-background px-3 text-sm" />
        <button type="submit" disabled={!marketCity.trim()} className="rounded-lg bg-teal-700 px-4 text-sm font-semibold text-white disabled:opacity-50">تحلیل بازار</button>
      </form>
      <p className="text-xs text-muted-foreground">فقط فایل‌های منتشرشده و عمومی بررسی می‌شوند؛ فرصت یعنی قیمت هر متر حداقل ۱۵٪ پایین‌تر از میانگین گروه مشابه با حداقل ۵ نمونه است، نه تضمین ارزش یا معامله.</p>
      {marketQ.isLoading&&<LoadingState message="در حال تحلیل فایل‌های عمومی بازار..."/>}
      {marketQ.error instanceof Error&&<ErrorState message={marketQ.error.message}/>}
      {marketQ.data&&<div className="space-y-2">{marketQ.data.items.length===0?<p className="text-sm text-muted-foreground">با حداقل ۵ نمونه مشابه و اختلاف ۱۵٪، فرصتی در این شهر پیدا نشد.</p>:marketQ.data.items.map(o=><div key={o.property_id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3"><div><Link href={`/dashboard/properties/${o.property_id}`} className="font-medium hover:underline">{o.title}</Link><div className="text-xs text-muted-foreground">{o.property_code} · {o.district} · {o.property_type} / {o.deal_type}</div><div className="text-xs text-muted-foreground">قیمت هر متر: {o.price_per_sqm} · میانگین منطقه: {o.district_average} · نمونه: {o.sample_count}</div></div><span className="rounded-md bg-emerald-50 px-2.5 py-1.5 text-sm font-bold text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300">{o.discount_percent}% پایین‌تر</span></div>)}</div>}
    </section>
  </div>;
}

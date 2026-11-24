"use client";
import React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, CalendarClock, Flame, Home, Lightbulb, RefreshCw, Users } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { PageHeader } from "@/components/ui/PageHeader";
import { LoadingState, ErrorState } from "@/components/ui/StateNotice";
type Task={id:string;title:string;due_at:string;customer_id:string;customer_name:string;assigned_name:string;is_overdue:boolean;href:string};
type Customer={id:string;name:string;readiness:string;score:number;assigned:string;href:string};
type Property={id:string;title:string;created_at:string;status:string;city:string;href:string};
type Viewing={id:string;start_at:string;property_title:string;customer_name:string;agent_name:string;href:string};
type Action={type:string;priority:string;title:string;detail:string;href:string};
type Hub={date:string;tasks:Task[];hot_customers:Customer[];new_properties:Property[];today_viewings:Viewing[];next_actions:Action[]};
const faDate=(s:string)=>new Intl.DateTimeFormat("fa-IR",{dateStyle:"medium",timeStyle:"short"}).format(new Date(s));
function Section({title,Icon,count,href,children}:{title:string;Icon:any;count:number;href?:string;children:React.ReactNode}){return <section className="rounded-2xl border-[var(--border-hairline)] bg-[var(--bg-surface)] p-4 shadow-sm"><header className="mb-3 flex items-center justify-between gap-2"><div className="flex items-center gap-2"><Icon className="h-5 w-5 text-[var(--accent-primary)]"/><h2 className="font-semibold">{title}</h2><span className="rounded-full bg-[var(--bg-subtle)] px-2 text-xs">{count}</span></div>{href&&<Link href={href} className="text-sm text-[var(--accent-primary)] hover:underline">مشاهده همه</Link>}</header>{children}</section>}
function Empty({text}:{text:string}){return <p className="rounded-xl bg-[var(--bg-subtle)] p-3 text-sm text-[var(--text-muted)]">{text}</p>}
function Item({title,subtitle,meta,href,alert}:{title:string;subtitle?:string;meta?:string;href:string;alert?:boolean}){return <Link href={href} className="flex items-start justify-between gap-3 rounded-xl p-3 hover:bg-[var(--bg-subtle)]/70"><div className="min-w-0"><div className="flex items-center gap-2 font-medium">{alert&&<AlertCircle className="h-4 w-4 text-destructive"/>}<span className="truncate">{title}</span></div>{subtitle&&<p className="mt-1 text-sm text-[var(--text-muted)]">{subtitle}</p>}</div>{meta&&<span className="shrink-0 text-xs text-[var(--text-muted)]">{meta}</span>}</Link>}
export default function DailyWorkHubPage(){
 const {accessToken,activeAgencyId}=useAuth();
 const q=useQuery({queryKey:["daily-work-hub",activeAgencyId],enabled:!!accessToken&&!!activeAgencyId,queryFn:async()=> (await apiFetch<Hub>("/api/v1/reports/daily-work",{token:accessToken,agencyId:activeAgencyId})).data});
 return <div className="space-y-6"><PageHeader title="مرکز کار روزانه" subtitle="اولویت‌های امروز، پیگیری‌ها و فعالیت‌های مهم تیم"/>
 <div className="flex items-center justify-between rounded-xl bg-[var(--bg-subtle)] p-3"><span className="text-sm text-[var(--text-muted)]">{q.data?.date?new Date(q.data.date+"T12:00:00").toLocaleDateString("fa-IR",{dateStyle:"full"}):"نمای روزانه"}</span><button onClick={()=>q.refetch()} className="inline-flex items-center gap-2 rounded-lg border bg-background px-3 py-2 text-sm"><RefreshCw className="h-4 w-4"/>به‌روزرسانی</button></div>
 {q.isLoading&&<LoadingState/>}{q.isError&&<ErrorState message="بارگذاری مرکز کار روزانه ناموفق بود. اتصال را بررسی کنید و دوباره تلاش کنید." onRetry={()=>q.refetch()}/>}
 {q.data&&<><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{[{Icon:CalendarClock,label:"پیگیری امروز و عقب‌افتاده",n:q.data.tasks.length},{Icon:Flame,label:"مشتریان داغ",n:q.data.hot_customers.length},{Icon:Home,label:"فایل جدید (۷ روز)",n:q.data.new_properties.length},{Icon:Users,label:"بازدید امروز",n:q.data.today_viewings.length}].map((k,i)=><div key={i} className="rounded-2xl border-[var(--border-hairline)] bg-[var(--bg-surface)] p-4"><div className="flex items-center gap-2 text-sm text-[var(--text-muted)]"><k.Icon className="h-4 w-4"/>{k.label}</div><div className="mt-3 text-3xl font-bold">{k.n.toLocaleString("fa-IR")}</div></div>)}</div>
 <div className="grid gap-4 xl:grid-cols-2">
 <Section title="کارهای امروز و عقب‌افتاده" Icon={CalendarClock} count={q.data.tasks.length} href="/dashboard/crm">{!q.data.tasks.length?<Empty text="کار پیگیری باز برای امروز یا موعد گذشته ندارید."/>:<div className="divide-y">{q.data.tasks.slice(0,40).map(t=><Item key={t.id} title={t.title} subtitle={`مشتری: ${t.customer_name}${t.assigned_name?` · مسئول: ${t.assigned_name}`:""}`} meta={faDate(t.due_at)} href={t.href} alert={t.is_overdue}/>)}</div>}</Section>
 <Section title="مشتریان داغ" Icon={Flame} count={q.data.hot_customers.length} href="/dashboard/customers">{!q.data.hot_customers.length?<Empty text="مشتری با اولویت بالا پیدا نشد."/>:<div className="divide-y">{q.data.hot_customers.slice(0,30).map(c=><Item key={c.id} title={c.name} subtitle={`سطح: ${c.readiness} · مسئول: ${c.assigned||"تعیین نشده"}`} meta={`امتیاز ${c.score}`} href={c.href}/>)}</div>}</Section>
 <Section title="فایل‌های جدید" Icon={Home} count={q.data.new_properties.length} href="/dashboard/properties">{!q.data.new_properties.length?<Empty text="فایل جدیدی در ۷ روز اخیر ثبت نشده است."/>:<div className="divide-y">{q.data.new_properties.slice(0,30).map(p=><Item key={p.id} title={p.title} subtitle={`${p.city||"موقعیت ثبت نشده"} · ${p.status}`} meta={faDate(p.created_at)} href={p.href}/>)}</div>}</Section>
 <Section title="بازدیدهای امروز" Icon={Users} count={q.data.today_viewings.length} href="/dashboard/appointments">{!q.data.today_viewings.length?<Empty text="برای امروز بازدیدی ثبت نشده است."/>:<div className="divide-y">{q.data.today_viewings.map(a=><Item key={a.id} title={a.property_title} subtitle={`مشتری: ${a.customer_name} · مشاور: ${a.agent_name}`} meta={faDate(a.start_at)} href={a.href}/>)}</div>}</Section></div>
 <Section title="پیشنهاد اقدام بعدی" Icon={Lightbulb} count={q.data.next_actions.length}>{!q.data.next_actions.length?<Empty text="اقدام پیشنهادی فوری ندارید. کارهای جاری را ادامه دهید."/>:<div className="divide-y">{q.data.next_actions.map((a,i)=><Item key={`${a.type}-${i}`} title={a.title} subtitle={a.detail} meta={a.priority==="HIGH"?"اولویت بالا":"پیشنهادی"} href={a.href} alert={a.priority==="HIGH"}/>)}</div>}</Section></>}
 </div>;
}

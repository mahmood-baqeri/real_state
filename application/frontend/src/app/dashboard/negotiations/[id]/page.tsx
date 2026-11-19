"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  FileSignature,
  History,
  MessageSquarePlus,
  Plus,
  Sparkles,
} from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { AiChatMessageResult, NegotiationItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusText } from "@/components/ui/StatusText";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ErrorState, LoadingState, SuccessBanner } from "@/components/ui/StateNotice";
import { formatNumberFa, translateStatus } from "@/lib/formatters";

const WORKFLOW_STAGES = [
  "CREATED",
  "AWAITING_BUYER_OFFER",
  "BUYER_OFFERED",
  "AWAITING_OWNER_RESPONSE",
  "OWNER_COUNTERED",
  "BARGAINING",
  "PRE_AGREEMENT",
  "AWAITING_FINAL_APPROVAL",
  "ACCEPTED",
  "PAUSED",
  "REJECTED",
  "CANCELLED",
];

export default function NegotiationDetailWorkspacePage() {
  const params = useParams<{ id: string }>();
  const qc = useQueryClient();
  const { accessToken, activeAgencyId } = useAuth();

  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);
  const [aiAdvice, setAiAdvice] = useState<AiChatMessageResult | null>(null);

  const [offerForm, setOfferForm] = useState({
    offered_by: "BUYER",
    proposed_price: "",
    proposed_deposit: "0",
    proposed_rent: "0",
    discount_amount: "0",
    notes: "",
  });

  const [stageForm, setStageForm] = useState({
    status: "BARGAINING",
    agreed_price: "",
    reason: "",
    next_action: "",
    next_followup_at: "",
  });

  const [activityForm, setActivityForm] = useState({
    activity_type: "CALL",
    title: "",
    description: "",
    outcome: "",
    next_action: "",
    next_action_due_at: "",
  });

  const negQ = useQuery({
    queryKey: ["negotiation-detail", params.id, activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (
        await apiFetch<NegotiationItem>(`/api/v1/negotiations/${params.id}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const addOfferMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/negotiations/${params.id}/offers`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify(offerForm),
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("نسخه جدید پیشنهاد ثبت و در جدول تاریخچه مقایسه قرار گرفت.");
      setOfferForm((p) => ({ ...p, proposed_price: "", notes: "" }));
      qc.invalidateQueries({ queryKey: ["negotiation-detail", params.id] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const stageMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/negotiations/${params.id}/respond`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          status: stageForm.status,
          reason: stageForm.reason,
          agreed_price: stageForm.agreed_price ? Number(stageForm.agreed_price) : null,
          next_action: stageForm.next_action || null,
          next_followup_at: stageForm.next_followup_at
            ? new Date(stageForm.next_followup_at).toISOString()
            : null,
        }),
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("مرحله مذاکره و زمان‌بندی پیگیری با موفقیت به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["negotiation-detail", params.id] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const activityMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/negotiations/${params.id}/activities`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          ...activityForm,
          next_action_due_at: activityForm.next_action_due_at
            ? new Date(activityForm.next_action_due_at).toISOString()
            : null,
        }),
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("فعالیت و تماس جدید در خط زمانی مذاکره ثبت شد.");
      setActivityForm({
        activity_type: "CALL",
        title: "",
        description: "",
        outcome: "",
        next_action: "",
        next_action_due_at: "",
      });
      qc.invalidateQueries({ queryKey: ["negotiation-detail", params.id] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const convertMut = useMutation({
    mutationFn: async () =>
      apiFetch<{ contract_id: string; contract_number: string }>(
        `/api/v1/negotiations/${params.id}/convert-to-contract`,
        {
          method: "POST",
          token: accessToken,
          agencyId: activeAgencyId,
          body: JSON.stringify({}),
        }
      ),
    onSuccess: (env) => {
      setErrMsg(null);
      setNotice(`قرارداد ${env.data.contract_number} به‌صورت خودکار ایجاد و به این پرونده متصل شد.`);
      qc.invalidateQueries({ queryKey: ["negotiation-detail", params.id] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const aiSummaryMut = useMutation({
    mutationFn: async () =>
      (
        await apiFetch<AiChatMessageResult>("/api/v1/ai/negotiation-summary", {
          method: "POST",
          token: accessToken,
          agencyId: activeAgencyId,
          body: JSON.stringify({ negotiation_id: params.id }),
        })
      ).data,
    onSuccess: (res) => {
      setAiAdvice(res);
      setNotice("تحلیل استراتژیک مذاکره توسط دستیار هوشمند تولید شد.");
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const neg = negQ.data;
  const canConvert =
    neg &&
    !neg.converted_contract_id &&
    ["PRE_AGREEMENT", "AWAITING_FINAL_APPROVAL", "ACCEPTED"].includes(neg.status);

  return (
    <div className="space-y-6">
      <PageHeader
        title={neg ? `پرونده مذاکره: ${neg.property_title}` : "میز کار مذاکره"}
        subtitle={
          neg
            ? `کد ملک ${neg.property_code} · خریدار: ${neg.customer_name}${
                neg.owner_name ? ` · مالک: ${neg.owner_name}` : ""
              } · مشاور: ${neg.agent_name}`
            : undefined
        }
        breadcrumbs={[
          { label: "میز کار", href: "/dashboard" },
          { label: "مذاکرات", href: "/dashboard/negotiations" },
          { label: neg?.property_code || "پرونده" },
        ]}
        actions={
          neg ? (
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={aiSummaryMut.isPending}
                onClick={() => aiSummaryMut.mutate()}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-indigo-300 bg-indigo-50 px-3 text-xs font-semibold text-indigo-800 hover:bg-indigo-100 dark:border-indigo-800 dark:bg-indigo-950/50 dark:text-indigo-300"
              >
                <Sparkles className="h-3.5 w-3.5" />
                {aiSummaryMut.isPending ? "در حال تحلیل..." : "تحلیل هوشمند GapGPT"}
              </button>

              {canConvert && (
                <button
                  type="button"
                  disabled={convertMut.isPending}
                  onClick={() => convertMut.mutate()}
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-emerald-700 px-3.5 text-xs font-semibold text-white hover:bg-emerald-800"
                >
                  <FileSignature className="h-4 w-4" />
                  تبدیل یک‌کلیکی به قرارداد
                </button>
              )}

              {neg.converted_contract_number && (
                <Link
                  href="/dashboard/contracts"
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  مشاهده قرارداد {neg.converted_contract_number}
                </Link>
              )}
            </div>
          ) : null
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      {negQ.isLoading ? (
        <LoadingState />
      ) : negQ.error instanceof Error ? (
        <ErrorState message={negQ.error.message} onRetry={() => negQ.refetch()} />
      ) : neg ? (
        <>
          {/* Overdue Warning + Price Telemetry Strip */}
          {neg.is_followup_overdue && (
            <div className="flex items-center gap-2.5 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-xs font-semibold text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
              <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />
              <span>
                مهلت پیگیری بعدی این مذاکره گذشته است! اقدام برنامه‌ریزی‌شده: {neg.next_action || "تماس پیگیری"}
              </span>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
            <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
              <div className="text-[11px] text-slate-500">مرحله فعلی</div>
              <div className="mt-1.5">
                <StatusText status={neg.status} />
              </div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
              <div className="text-[11px] text-slate-500">قیمت پایه ملک</div>
              <div className="mt-1.5 text-sm font-bold tabular-nums">
                <MoneyDisplay amount={neg.asking_price || "0"} sourceCurrency="IRT" />
              </div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
              <div className="text-[11px] text-slate-500">آخرین پیشنهاد</div>
              <div className="mt-1.5 text-sm font-bold text-teal-700 tabular-nums dark:text-teal-300">
                <MoneyDisplay amount={neg.latest_proposed_price || "0"} sourceCurrency="IRT" />
              </div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
              <div className="text-[11px] text-slate-500">اختلاف از قیمت پایه</div>
              <div className="mt-1.5 font-mono text-sm font-bold tabular-nums text-amber-700 dark:text-amber-400">
                {neg.price_delta_percent ? `${neg.price_delta_percent > 0 ? "+" : ""}${neg.price_delta_percent}٪` : "۰٪"}
              </div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
              <div className="text-[11px] text-slate-500">توافق نهایی</div>
              <div className="mt-1.5 text-sm font-bold text-emerald-700 tabular-nums dark:text-emerald-400">
                {neg.agreed_price ? (
                  <MoneyDisplay amount={neg.agreed_price} sourceCurrency="IRT" />
                ) : (
                  "در جریان"
                )}
              </div>
            </div>
          </div>

          {aiAdvice && (
            <div className="rounded-xl border border-indigo-200 bg-indigo-50/70 p-5 text-xs space-y-2 dark:border-indigo-900/60 dark:bg-indigo-950/30">
              <div className="flex items-center justify-between font-bold text-indigo-900 dark:text-indigo-200">
                <span className="flex items-center gap-1.5">
                  <Bot className="h-4 w-4" />
                  تحلیل هوشمند مذاکره ({aiAdvice.provider} · {aiAdvice.model})
                </span>
                <span className="font-mono text-[11px] font-normal">
                  {formatNumberFa(aiAdvice.latency_ms)} ms
                </span>
              </div>
              <p className="whitespace-pre-line leading-relaxed text-slate-800 dark:text-slate-200">
                {aiAdvice.reply}
              </p>
            </div>
          )}

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
            {/* Left Column: Offer Versions + Activity Logger */}
            <div className="space-y-6 lg:col-span-7">
              <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-4">
                <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                  <History className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                  تاریخچه و مقایسه نسخه‌های پیشنهاد ({formatNumberFa(neg.offers.length)} نسخه)
                </h2>

                {neg.offers.length === 0 ? (
                  <p className="text-xs text-slate-500">هنوز پیشنهادی ثبت نشده است.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-right text-xs">
                      <thead className="border-b border-slate-200 text-slate-500 dark:border-slate-800">
                        <tr>
                          <th className="py-2">نسخه</th>
                          <th className="py-2">ارائه‌دهنده</th>
                          <th className="py-2">مبلغ پیشنهادی</th>
                          <th className="py-2">توضیح</th>
                          <th className="py-2">وضعیت</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {neg.offers.map((o) => (
                          <tr key={o.id}>
                            <td className="py-2.5 font-mono font-bold">v{o.version_number}</td>
                            <td className="py-2.5">
                              {o.offered_by === "BUYER"
                                ? "خریدار"
                                : o.offered_by === "SELLER"
                                ? "مالک / فروشنده"
                                : "مشاور"}
                            </td>
                            <td className="py-2.5 font-bold tabular-nums">
                              <MoneyDisplay amount={o.proposed_price} sourceCurrency={o.currency} />
                            </td>
                            <td className="py-2.5 text-slate-500">{o.notes || "—"}</td>
                            <td className="py-2.5">
                              <StatusText status={o.status} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    addOfferMut.mutate();
                  }}
                  className="grid grid-cols-1 gap-3 border-t border-slate-100 pt-4 dark:border-slate-800 sm:grid-cols-4"
                >
                  <select
                    value={offerForm.offered_by}
                    onChange={(e) => setOfferForm({ ...offerForm, offered_by: e.target.value })}
                    className="h-9 rounded-lg border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                  >
                    <option value="BUYER">پیشنهاد خریدار</option>
                    <option value="SELLER">پیشنهاد متقابل مالک</option>
                    <option value="AGENT">جمع‌بندی مشاور</option>
                  </select>
                  <input
                    required
                    type="number"
                    placeholder="مبلغ جدید (تومان)"
                    value={offerForm.proposed_price}
                    onChange={(e) => setOfferForm({ ...offerForm, proposed_price: e.target.value })}
                    className="h-9 rounded-lg border border-slate-300 px-2.5 text-xs tabular-nums dark:border-slate-700 dark:bg-slate-950"
                  />
                  <input
                    placeholder="شرایط پرداخت / یادداشت"
                    value={offerForm.notes}
                    onChange={(e) => setOfferForm({ ...offerForm, notes: e.target.value })}
                    className="h-9 rounded-lg border border-slate-300 px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                  />
                  <button
                    type="submit"
                    disabled={addOfferMut.isPending}
                    className="inline-flex h-9 items-center justify-center gap-1 rounded-lg bg-teal-700 px-3 text-xs font-semibold text-white hover:bg-teal-800"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    ثبت پیشنهاد متقابل
                  </button>
                </form>
              </div>

              {/* Log New Activity */}
              <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-4">
                <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                  <MessageSquarePlus className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                  ثبت تماس، جلسه، پیام یا پیگیری جدید
                </h2>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    activityMut.mutate();
                  }}
                  className="grid grid-cols-1 gap-3 sm:grid-cols-2"
                >
                  <select
                    value={activityForm.activity_type}
                    onChange={(e) =>
                      setActivityForm({ ...activityForm, activity_type: e.target.value })
                    }
                    className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs dark:border-slate-700 dark:bg-slate-950"
                  >
                    <option value="CALL">تماس تلفنی</option>
                    <option value="MEETING">جلسه حضوری مذاکره</option>
                    <option value="MESSAGE">پیام / واتساپ</option>
                    <option value="FOLLOW_UP">پیگیری زمان‌بندی‌شده</option>
                    <option value="NOTE">یادداشت داخلی مشاور</option>
                  </select>
                  <input
                    required
                    placeholder="عنوان فعالیت (مثلاً تماس با مالک بابت شرایط نقدی)"
                    value={activityForm.title}
                    onChange={(e) => setActivityForm({ ...activityForm, title: e.target.value })}
                    className="h-9 rounded-lg border border-slate-300 px-3 text-xs dark:border-slate-700 dark:bg-slate-950"
                  />
                  <input
                    placeholder="نتیجه تماس یا جلسه"
                    value={activityForm.outcome}
                    onChange={(e) => setActivityForm({ ...activityForm, outcome: e.target.value })}
                    className="h-9 rounded-lg border border-slate-300 px-3 text-xs dark:border-slate-700 dark:bg-slate-950"
                  />
                  <input
                    placeholder="گام و اقدام بعدی"
                    value={activityForm.next_action}
                    onChange={(e) =>
                      setActivityForm({ ...activityForm, next_action: e.target.value })
                    }
                    className="h-9 rounded-lg border border-slate-300 px-3 text-xs dark:border-slate-700 dark:bg-slate-950"
                  />
                  <textarea
                    rows={2}
                    placeholder="شرح مذاکرات انجام‌شده..."
                    value={activityForm.description}
                    onChange={(e) =>
                      setActivityForm({ ...activityForm, description: e.target.value })
                    }
                    className="sm:col-span-2 rounded-lg border border-slate-300 p-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                  />
                  <div className="sm:col-span-2 flex flex-wrap items-center justify-between gap-2">
                    <input
                      type="datetime-local"
                      value={activityForm.next_action_due_at}
                      onChange={(e) =>
                        setActivityForm({ ...activityForm, next_action_due_at: e.target.value })
                      }
                      className="h-9 rounded-lg border border-slate-300 px-3 text-xs dark:border-slate-700 dark:bg-slate-950"
                    />
                    <button
                      type="submit"
                      disabled={activityMut.isPending}
                      className="h-9 rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white hover:bg-teal-800"
                    >
                      ثبت در خط زمانی مذاکره
                    </button>
                  </div>
                </form>
              </div>
            </div>

            {/* Right Column: Stage Transition + Chronological Timeline */}
            <div className="space-y-6 lg:col-span-5">
              <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-3">
                <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  تغییر مرحله مذاکره و ثبت توافق / نتیجه
                </h2>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    stageMut.mutate();
                  }}
                  className="space-y-3 text-xs"
                >
                  <select
                    value={stageForm.status}
                    onChange={(e) => setStageForm({ ...stageForm, status: e.target.value })}
                    className="h-9 w-full rounded-lg border border-slate-300 bg-white px-3 dark:border-slate-700 dark:bg-slate-950"
                  >
                    {WORKFLOW_STAGES.map((st) => (
                      <option key={st} value={st}>
                        {translateStatus(st)} ({st})
                      </option>
                    ))}
                  </select>
                  <input
                    type="number"
                    placeholder="مبلغ توافق‌شده (اختیاری)"
                    value={stageForm.agreed_price}
                    onChange={(e) => setStageForm({ ...stageForm, agreed_price: e.target.value })}
                    className="h-9 w-full rounded-lg border border-slate-300 px-3 tabular-nums dark:border-slate-700 dark:bg-slate-950"
                  />
                  <input
                    placeholder="دلیل تغییر وضعیت یا علت موفقیت/عدم توافق"
                    value={stageForm.reason}
                    onChange={(e) => setStageForm({ ...stageForm, reason: e.target.value })}
                    className="h-9 w-full rounded-lg border border-slate-300 px-3 dark:border-slate-700 dark:bg-slate-950"
                  />
                  <button
                    type="submit"
                    disabled={stageMut.isPending}
                    className="h-9 w-full rounded-lg bg-slate-900 text-xs font-semibold text-white hover:bg-slate-800 dark:bg-teal-600"
                  >
                    به‌روزرسانی مرحله مذاکره
                  </button>
                </form>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 space-y-4">
                <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  خط زمانی کامل رویدادها و پیگیری‌ها
                </h2>
                <div className="space-y-3 border-r-2 border-slate-200 pr-4 dark:border-slate-800">
                  {(neg.activities || []).map((act) => (
                    <div key={act.id} className="space-y-1 text-xs">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-bold text-slate-900 dark:text-slate-100">
                          {act.title}
                        </span>
                        <DateDisplay
                          value={act.created_at}
                          withTime
                          className="text-[11px] text-slate-400"
                        />
                      </div>
                      {act.description && (
                        <p className="text-slate-600 dark:text-slate-300">{act.description}</p>
                      )}
                      {act.outcome && (
                        <div className="text-[11px] font-semibold text-teal-700 dark:text-teal-400">
                          نتیجه: {act.outcome}
                        </div>
                      )}
                      {act.actor_name && (
                        <div className="text-[10px] text-slate-400">ثبت‌کننده: {act.actor_name}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}

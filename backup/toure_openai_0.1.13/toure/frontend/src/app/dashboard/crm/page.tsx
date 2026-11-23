"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, MessageSquare, Plus, Sparkles } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type {
  CustomerItem,
  FollowUpTask,
  InteractionItem,
  PipelineItem,
  PipelineStage,
} from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { StatusText } from "@/components/ui/StatusText";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, LoadingState, SuccessBanner } from "@/components/ui/StateNotice";

interface MatchResult {
  id: string;
  property_code: string;
  title: string;
  district: string;
  built_area_sqm: string;
  total_price: string;
  match_score: number;
  reasons: string[];
}

export default function CrmPipelinePage() {
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();
  const [tab, setTab] = useState<"pipeline" | "tasks" | "matching">("pipeline");
  const [pipeModal, setPipeModal] = useState(false);
  const [taskModal, setTaskModal] = useState(false);
  const [intModal, setIntModal] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const [pipeForm, setPipeForm] = useState({ customer_id: "", stage_id: "", notes: "" });
  const [taskForm, setTaskForm] = useState({ customer_id: "", title: "", due_at: "2026-12-05T11:00" });
  const [intForm, setIntForm] = useState({ customer_id: "", channel: "CALL", summary: "" });
  const [matchForm, setMatchForm] = useState({
    target_city: "تهران",
    districts: "زعفرانیه,فرشته",
    min_budget: "15000000000",
    max_budget: "45000000000",
  });

  const stagesQ = useQuery({
    queryKey: ["crm-stages", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<PipelineStage[]>("/api/v1/crm/stages", { token: accessToken, agencyId: activeAgencyId })).data,
  });

  const pipelineQ = useQuery({
    queryKey: ["crm-pipeline", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<PipelineItem[]>("/api/v1/crm/pipeline", { token: accessToken, agencyId: activeAgencyId })).data,
  });

  const tasksQ = useQuery({
    queryKey: ["crm-tasks", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<FollowUpTask[]>("/api/v1/crm/tasks", { token: accessToken, agencyId: activeAgencyId })).data,
  });

  const interactionsQ = useQuery({
    queryKey: ["crm-interactions", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<InteractionItem[]>("/api/v1/crm/interactions", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const customersQ = useQuery({
    queryKey: ["crm-customers", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<CustomerItem[]>("/api/v1/customers", { token: accessToken, agencyId: activeAgencyId })).data,
  });

  const matchingQ = useQuery({
    queryKey: ["crm-matching", activeAgencyId, matchForm],
    enabled: !!accessToken && tab === "matching",
    queryFn: async () => {
      const qs = new URLSearchParams(matchForm).toString();
      return (
        await apiFetch<MatchResult[]>(`/api/v1/matching/customer-to-properties?${qs}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data;
    },
  });

  const moveStageMut = useMutation({
    mutationFn: async ({ itemId, stageId }: { itemId: string; stageId: string }) =>
      apiFetch(`/api/v1/crm/pipeline/${itemId}`, {
        method: "PATCH",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ stage_id: stageId }),
      }),
    onSuccess: () => {
      setNotice("مرحله مشتری در پایپ‌لاین به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["crm-pipeline"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const upsertPipeMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/crm/pipeline", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify(pipeForm),
      }),
    onSuccess: () => {
      setPipeModal(false);
      setNotice("مشتری به پایپ‌لاین CRM اضافه شد.");
      qc.invalidateQueries({ queryKey: ["crm-pipeline"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const createTaskMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/crm/tasks", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          customer_id: taskForm.customer_id,
          title: taskForm.title,
          due_at: new Date(taskForm.due_at).toISOString(),
        }),
      }),
    onSuccess: () => {
      setTaskModal(false);
      setNotice("وظیفه پیگیری جدید ثبت شد.");
      qc.invalidateQueries({ queryKey: ["crm-tasks"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const doneTaskMut = useMutation({
    mutationFn: async (taskId: string) =>
      apiFetch(`/api/v1/crm/tasks/${taskId}`, {
        method: "PATCH",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ status: "DONE" }),
      }),
    onSuccess: () => {
      setNotice("وظیفه پیگیری انجام شد.");
      qc.invalidateQueries({ queryKey: ["crm-tasks"] });
    },
  });

  const addIntMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/crm/interactions", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ ...intForm, is_private: true }),
      }),
    onSuccess: () => {
      setIntModal(false);
      setNotice("تعامل مشتری ثبت شد.");
      qc.invalidateQueries({ queryKey: ["crm-interactions"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="پایپ‌لاین ۱۲مرحله‌ای CRM و تطبیق هوشمند"
        subtitle="مدیریت قیف فروش، پیگیری وظایف روزانه، تاریخچه تعاملات و موتور تطبیق ملک"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "CRM و تطبیق" }]}
        actions={
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setPipeModal(true)}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white"
            >
              <Plus className="h-4 w-4" />
              افزودن به پایپ‌لاین
            </button>
            <button
              type="button"
              onClick={() => setTaskModal(true)}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3.5 text-xs font-semibold text-slate-800 dark:text-slate-200"
            >
              وظیفه جدید
            </button>
            <button
              type="button"
              onClick={() => setIntModal(true)}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3.5 text-xs font-semibold text-slate-800 dark:text-slate-200"
            >
              <MessageSquare className="h-4 w-4" />
              ثبت تماس/یادداشت
            </button>
          </div>
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      <div className="flex flex-wrap gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
        {[
          { key: "pipeline", label: "پایپ‌لاین مشتریان" },
          { key: "tasks", label: "وظایف پیگیری و تعاملات" },
          { key: "matching", label: "موتور تطبیق هوشمند ملک" },
        ].map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key as typeof tab)}
            className={`h-9 rounded-lg border px-4 text-xs font-semibold transition-colors ${
              tab === t.key
                ? "border-teal-700 bg-teal-700 text-white"
                : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "pipeline" && (
        pipelineQ.isLoading || stagesQ.isLoading ? (
          <LoadingState />
        ) : (
          <div className="overflow-x-auto pb-4">
            <div className="flex gap-4 min-w-max">
              {(stagesQ.data || []).map((st) => {
                const cards = (pipelineQ.data || []).filter((it) => it.stage === st.id);
                return (
                  <div
                    key={st.id}
                    className="w-72 shrink-0 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-3.5"
                  >
                    <div className="mb-3 flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-2">
                      <span className="text-xs font-bold text-slate-900 dark:text-slate-100">{st.name}</span>
                      <span className="tabular-nums rounded bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                        {cards.length}
                      </span>
                    </div>
                    <div className="space-y-2.5">
                      {cards.length === 0 ? (
                        <p className="py-4 text-center text-[11px] text-slate-400">خالی</p>
                      ) : (
                        cards.map((card) => (
                          <div key={card.id} className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 p-3 space-y-2">
                            <div className="text-xs font-bold text-slate-900 dark:text-slate-100">{card.customer_name}</div>
                            {card.property_title && (
                              <div className="text-[11px] text-teal-800 dark:text-teal-300">{card.property_title}</div>
                            )}
                            {card.notes && <div className="text-[11px] text-slate-600 dark:text-slate-400">{card.notes}</div>}
                            <select
                              value={card.stage}
                              onChange={(e) => moveStageMut.mutate({ itemId: card.id, stageId: e.target.value })}
                              className="h-8 w-full rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 text-[11px]"
                            >
                              {(stagesQ.data || []).map((opt) => (
                                <option key={opt.id} value={opt.id}>
                                  انتقال به: {opt.name}
                                </option>
                              ))}
                            </select>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )
      )}

      {tab === "tasks" && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
            <h3 className="mb-4 text-sm font-bold text-slate-900 dark:text-slate-100">وظایف پیگیری مشتریان</h3>
            <div className="divide-y divide-slate-100 dark:divide-slate-800">
              {(tasksQ.data || []).map((tk) => (
                <div key={tk.id} className="flex items-center justify-between gap-3 py-3">
                  <div>
                    <div className="text-xs font-bold text-slate-900 dark:text-slate-100">{tk.title}</div>
                    <div className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                      مشتری: {tk.customer_name} — سررسید: <DateDisplay value={tk.due_at} />
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusText status={tk.status} />
                    {tk.status !== "DONE" && (
                      <button
                        type="button"
                        onClick={() => doneTaskMut.mutate(tk.id)}
                        className="inline-flex h-7 items-center gap-1 rounded bg-emerald-700 px-2 text-[11px] font-semibold text-white"
                      >
                        <Check className="h-3 w-3" />
                        تکمیل
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
            <h3 className="mb-4 text-sm font-bold text-slate-900 dark:text-slate-100">تاریخچه تماس‌ها و یادداشت‌ها</h3>
            <div className="divide-y divide-slate-100 dark:divide-slate-800">
              {(interactionsQ.data || []).map((it) => (
                <div key={it.id} className="py-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-slate-900 dark:text-slate-100">{it.customer_name}</span>
                    <span className="text-[11px] text-slate-400">
                      <DateDisplay value={it.created_at} withTime />
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">{it.summary}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === "matching" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 sm:grid-cols-4">
            <input
              value={matchForm.target_city}
              onChange={(e) => setMatchForm({ ...matchForm, target_city: e.target.value })}
              placeholder="شهر"
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm"
            />
            <input
              value={matchForm.districts}
              onChange={(e) => setMatchForm({ ...matchForm, districts: e.target.value })}
              placeholder="مناطق (با کاما)"
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm"
            />
            <input
              type="number"
              value={matchForm.min_budget}
              onChange={(e) => setMatchForm({ ...matchForm, min_budget: e.target.value })}
              placeholder="حداقل بودجه"
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm tabular-nums"
            />
            <input
              type="number"
              value={matchForm.max_budget}
              onChange={(e) => setMatchForm({ ...matchForm, max_budget: e.target.value })}
              placeholder="حداکثر بودجه"
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm tabular-nums"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {(matchingQ.data || []).map((m) => (
              <div key={m.id} className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-slate-500 dark:text-slate-400">{m.property_code}</span>
                  <span className="inline-flex items-center gap-1 rounded-md bg-teal-50 dark:bg-teal-950/40 px-2.5 py-1 text-xs font-bold text-teal-800 dark:text-teal-300 border border-teal-200 dark:border-teal-800/70 tabular-nums">
                    <Sparkles className="h-3.5 w-3.5" />
                    امتیاز تطبیق: {m.match_score}٪
                  </span>
                </div>
                <h4 className="mt-2 text-sm font-bold text-slate-900 dark:text-slate-100">{m.title}</h4>
                <div className="mt-2 flex items-center justify-between text-xs text-slate-600 dark:text-slate-400">
                  <span>{m.district}</span>
                  <MoneyDisplay amount={m.total_price} className="font-bold text-slate-900 dark:text-slate-100" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <ModalDrawer open={pipeModal} onClose={() => setPipeModal(false)} title="افزودن مشتری به پایپ‌لاین CRM">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            upsertPipeMut.mutate();
          }}
          className="space-y-3"
        >
          <select
            required
            value={pipeForm.customer_id}
            onChange={(e) => setPipeForm({ ...pipeForm, customer_id: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
          >
            <option value="">انتخاب مشتری...</option>
            {(customersQ.data || []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.full_name}
              </option>
            ))}
          </select>
          <select
            required
            value={pipeForm.stage_id}
            onChange={(e) => setPipeForm({ ...pipeForm, stage_id: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
          >
            <option value="">انتخاب مرحله...</option>
            {(stagesQ.data || []).map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
          <textarea
            rows={2}
            placeholder="یادداشت"
            value={pipeForm.notes}
            onChange={(e) => setPipeForm({ ...pipeForm, notes: e.target.value })}
            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 p-2.5 text-sm"
          />
          <button type="submit" className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white">
            ثبت در پایپ‌لاین
          </button>
        </form>
      </ModalDrawer>

      <ModalDrawer open={taskModal} onClose={() => setTaskModal(false)} title="ثبت وظیفه پیگیری">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createTaskMut.mutate();
          }}
          className="space-y-3"
        >
          <select
            required
            value={taskForm.customer_id}
            onChange={(e) => setTaskForm({ ...taskForm, customer_id: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
          >
            <option value="">انتخاب مشتری...</option>
            {(customersQ.data || []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.full_name}
              </option>
            ))}
          </select>
          <input
            required
            placeholder="عنوان پیگیری"
            value={taskForm.title}
            onChange={(e) => setTaskForm({ ...taskForm, title: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm"
          />
          <input
            type="datetime-local"
            value={taskForm.due_at}
            onChange={(e) => setTaskForm({ ...taskForm, due_at: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm"
          />
          <button type="submit" className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white">
            ذخیره وظیفه
          </button>
        </form>
      </ModalDrawer>

      <ModalDrawer open={intModal} onClose={() => setIntModal(false)} title="ثبت تماس / یادداشت تعامل">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            addIntMut.mutate();
          }}
          className="space-y-3"
        >
          <select
            required
            value={intForm.customer_id}
            onChange={(e) => setIntForm({ ...intForm, customer_id: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
          >
            <option value="">انتخاب مشتری...</option>
            {(customersQ.data || []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.full_name}
              </option>
            ))}
          </select>
          <textarea
            required
            rows={3}
            placeholder="خلاصه تماس یا جلسه..."
            value={intForm.summary}
            onChange={(e) => setIntForm({ ...intForm, summary: e.target.value })}
            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 p-2.5 text-sm"
          />
          <button type="submit" className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white">
            ثبت تعامل
          </button>
        </form>
      </ModalDrawer>
    </div>
  );
}

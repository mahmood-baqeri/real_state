"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Share2, Target } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { CustomerItem, TeamMemberItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";

export default function CustomersPage() {
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [shareTarget, setShareTarget] = useState<CustomerItem | null>(null);
  const [reqTarget, setReqTarget] = useState<CustomerItem | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const [form, setForm] = useState({
    full_name: "",
    primary_phone: "",
    customer_type: "BUYER",
    email: "",
    source: "PORTAL",
    readiness_level: "HIGH",
  });
  const [shareForm, setShareForm] = useState({ membership_id: "", access_level: "VIEW" });
  const [reqForm, setReqForm] = useState({
    deal_type_id: "SALE",
    property_type_id: "APARTMENT",
    target_city: "تهران",
    districts_csv: "زعفرانیه,فرشته",
    min_area_sqm: "120",
    max_area_sqm: "250",
    min_budget: "15000000000",
    max_budget: "40000000000",
    min_bedrooms: "2",
  });

  const custQ = useQuery({
    queryKey: ["customers", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<CustomerItem[]>("/api/v1/customers", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const membersQ = useQuery({
    queryKey: ["team-members-for-share", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<TeamMemberItem[]>("/api/v1/team/members", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const createMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/customers", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify(form),
      }),
    onSuccess: () => {
      setCreateOpen(false);
      setForm({
        full_name: "",
        primary_phone: "",
        customer_type: "BUYER",
        email: "",
        source: "PORTAL",
        readiness_level: "HIGH",
      });
      setNotice("مشتری جدید ثبت شد.");
      qc.invalidateQueries({ queryKey: ["customers"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const shareMut = useMutation({
    mutationFn: async () => {
      if (!shareTarget) return;
      return apiFetch(`/api/v1/customers/${shareTarget.id}/share`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify(shareForm),
      });
    },
    onSuccess: () => {
      setShareTarget(null);
      setNotice("مشتری با مشاور همکار به اشتراک گذاشته شد.");
      qc.invalidateQueries({ queryKey: ["customers"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const reqMut = useMutation({
    mutationFn: async () => {
      if (!reqTarget) return;
      return apiFetch(`/api/v1/customers/${reqTarget.id}/requirements`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          deal_type_id: reqForm.deal_type_id,
          property_type_id: reqForm.property_type_id,
          target_city: reqForm.target_city,
          target_districts: reqForm.districts_csv
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
          min_area_sqm: reqForm.min_area_sqm,
          max_area_sqm: reqForm.max_area_sqm,
          min_budget: reqForm.min_budget,
          max_budget: reqForm.max_budget,
          min_bedrooms: Number(reqForm.min_bedrooms),
        }),
      });
    },
    onSuccess: () => {
      setReqTarget(null);
      setNotice("نیاز ملکی مشتری ثبت شد.");
      qc.invalidateQueries({ queryKey: ["customers"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="مشتریان و اشتراک‌گذاری خصوصی"
        subtitle="مدیریت خریداران، مستأجران، مالکین، نیازهای ملکی و اشتراک‌گذاری با سایر مشاوران"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "مشتریان" }]}
        actions={
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
          >
            <Plus className="h-4 w-4" />
            ثبت مشتری جدید
          </button>
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      <DataTable
        rows={custQ.data || []}
        rowKey={(c) => c.id}
        isLoading={custQ.isLoading}
        error={custQ.error instanceof Error ? custQ.error.message : null}
        exportFileName="bonyan-customers"
        searchPlaceholder="جستجو در نام یا موبایل مشتری..."
        columns={[
          {
            key: "name",
            header: "نام مشتری",
            exportValue: (c) => c.full_name,
            render: (c) => (
              <div>
                <Link
                  href={`/dashboard/customers/${c.id}`}
                  className="font-semibold text-slate-900 hover:text-teal-700 dark:text-slate-100 dark:hover:text-teal-400"
                >
                  {c.full_name}
                </Link>
                <div className="font-mono text-xs text-slate-500 dark:text-slate-400">
                  {c.primary_phone}
                </div>
              </div>
            ),
          },
          { key: "type", header: "نوع", render: (c) => c.customer_type },
          { key: "agent", header: "مشاور مسئول", render: (c) => c.assigned_agent_name || "—" },
          {
            key: "reqs",
            header: "نیازهای ثبت‌شده",
            render: (c) =>
              c.requirements.length > 0 ? (
                <div className="text-xs">
                  <span>{c.requirements[0].target_city}</span>{" "}
                  <span className="text-slate-500 dark:text-slate-400">
                    (تا <MoneyDisplay amount={c.requirements[0].max_budget} />)
                  </span>
                </div>
              ) : (
                "—"
              ),
          },
          {
            key: "shares",
            header: "اشتراک‌گذاری",
            render: (c) =>
              c.shares.length > 0
                ? c.shares.map((s) => s.agent_name).join("، ")
                : "خصوصی",
          },
          {
            key: "act",
            header: "عملیات",
            render: (c) => (
              <div className="flex flex-wrap gap-1.5">
                <button
                  type="button"
                  onClick={() => setReqTarget(c)}
                  className="inline-flex h-7 items-center gap-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  <Target className="h-3.5 w-3.5 text-teal-700 dark:text-teal-400" />
                  ثبت نیاز ملکی
                </button>
                <button
                  type="button"
                  onClick={() => setShareTarget(c)}
                  className="inline-flex h-7 items-center gap-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  <Share2 className="h-3.5 w-3.5 text-amber-700" />
                  اشتراک با همکار
                </button>
              </div>
            ),
          },
        ]}
      />

      <ModalDrawer open={createOpen} onClose={() => setCreateOpen(false)} title="ثبت مشتری جدید">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMut.mutate();
          }}
          className="space-y-3"
        >
          <input
            required
            placeholder="نام و نام خانوادگی"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm"
          />
          <input
            required
            dir="ltr"
            placeholder="0912..."
            value={form.primary_phone}
            onChange={(e) => setForm({ ...form, primary_phone: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-left font-mono text-sm"
          />
          <select
            value={form.customer_type}
            onChange={(e) => setForm({ ...form, customer_type: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
          >
            <option value="BUYER">خریدار</option>
            <option value="TENANT">مستأجر</option>
            <option value="SELLER">فروشنده</option>
            <option value="LANDLORD">موجر</option>
            <option value="INVESTOR">سرمایه‌گذار</option>
          </select>
          <button
            type="submit"
            disabled={createMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white"
          >
            ثبت مشتری
          </button>
        </form>
      </ModalDrawer>

      <ModalDrawer
        open={!!shareTarget}
        onClose={() => setShareTarget(null)}
        title={`اشتراک‌گذاری خصوصی مشتری — ${shareTarget?.full_name || ""}`}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            shareMut.mutate();
          }}
          className="space-y-3"
        >
          <select
            required
            value={shareForm.membership_id}
            onChange={(e) => setShareForm({ ...shareForm, membership_id: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
          >
            <option value="">انتخاب مشاور همکار...</option>
            {(membersQ.data || []).map((m) => (
              <option key={m.id} value={m.id}>
                {m.full_name} ({m.role_name})
              </option>
            ))}
          </select>
          <select
            value={shareForm.access_level}
            onChange={(e) => setShareForm({ ...shareForm, access_level: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
          >
            <option value="VIEW">فقط مشاهده (VIEW)</option>
            <option value="COLLABORATE">همکاری و ویرایش (COLLABORATE)</option>
          </select>
          <button
            type="submit"
            disabled={shareMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white"
          >
            اعطای دسترسی اشتراکی
          </button>
        </form>
      </ModalDrawer>

      <ModalDrawer
        open={!!reqTarget}
        onClose={() => setReqTarget(null)}
        title={`ثبت تقاضای ملکی — ${reqTarget?.full_name || ""}`}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            reqMut.mutate();
          }}
          className="space-y-3"
        >
          <div className="grid grid-cols-2 gap-3">
            <select
              value={reqForm.deal_type_id}
              onChange={(e) => setReqForm({ ...reqForm, deal_type_id: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
            >
              <option value="SALE">خرید</option>
              <option value="MORTGAGE_RENT">رهن و اجاره</option>
            </select>
            <select
              value={reqForm.property_type_id}
              onChange={(e) => setReqForm({ ...reqForm, property_type_id: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
            >
              <option value="APARTMENT">آپارتمان</option>
              <option value="VILLA">ویلا</option>
              <option value="OFFICE">اداری</option>
            </select>
          </div>
          <input
            placeholder="شهر هدف"
            value={reqForm.target_city}
            onChange={(e) => setReqForm({ ...reqForm, target_city: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm"
          />
          <input
            placeholder="مناطق (با کاما جدا کنید)"
            value={reqForm.districts_csv}
            onChange={(e) => setReqForm({ ...reqForm, districts_csv: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm"
          />
          <div className="grid grid-cols-2 gap-3">
            <input
              type="number"
              placeholder="حداقل بودجه"
              value={reqForm.min_budget}
              onChange={(e) => setReqForm({ ...reqForm, min_budget: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm tabular-nums"
            />
            <input
              type="number"
              placeholder="حداکثر بودجه"
              value={reqForm.max_budget}
              onChange={(e) => setReqForm({ ...reqForm, max_budget: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm tabular-nums"
            />
          </div>
          <button
            type="submit"
            disabled={reqMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white"
          >
            ذخیره نیاز ملکی
          </button>
        </form>
      </ModalDrawer>
    </div>
  );
}

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Edit3, Eye, Plus, Share2, Target, Trash2 } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { CustomerItem, TeamMemberItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";

const CUSTOMER_TYPE_LABELS: Record<string, string> = {
  BUYER: "خریدار",
  TENANT: "مستأجر",
  SELLER: "فروشنده",
  LANDLORD: "موجر",
  INVESTOR: "سرمایه‌گذار",
};

export default function CustomersPage() {
  const { accessToken, activeAgencyId, effectiveRole } = useAuth();
  const qc = useQueryClient();
  const [typeFilter, setTypeFilter] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<CustomerItem | null>(null);
  const [shareTarget, setShareTarget] = useState<CustomerItem | null>(null);
  const [reqTarget, setReqTarget] = useState<CustomerItem | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const [form, setForm] = useState({
    full_name: "",
    primary_phone: "",
    secondary_phone: "",
    customer_type: "BUYER",
    email: "",
    source: "PORTAL",
    readiness_level: "HIGH",
  });
  const [editForm, setEditForm] = useState({
    full_name: "",
    primary_phone: "",
    secondary_phone: "",
    customer_type: "BUYER",
    email: "",
    source: "PORTAL",
    readiness_level: "MEDIUM",
    assigned_membership_id: "",
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
    queryKey: ["customers", activeAgencyId, typeFilter],
    enabled: !!accessToken,
    queryFn: async () => {
      const q = typeFilter ? `?customer_type=${typeFilter}&page_size=100` : "?page_size=100";
      return (
        await apiFetch<CustomerItem[]>(`/api/v1/customers${q}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data;
    },
  });

  const targetAgencyForMembers = activeAgencyId || shareTarget?.agency || editTarget?.agency || null;

  const membersQ = useQuery({
    queryKey: ["team-members-for-share", targetAgencyForMembers],
    enabled: !!accessToken && !!targetAgencyForMembers,
    queryFn: async () =>
      (
        await apiFetch<TeamMemberItem[]>("/api/v1/team/members", {
          token: accessToken,
          agencyId: targetAgencyForMembers,
        })
      ).data,
  });

  const createMut = useMutation({
    mutationFn: async () => {
      if (!activeAgencyId) {
        throw new Error("برای ثبت مشتری جدید، ابتدا آژانس مقصد را از منوی بالای صفحه انتخاب کنید.");
      }
      return apiFetch("/api/v1/customers", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify(form),
      });
    },
    onSuccess: () => {
      setCreateOpen(false);
      setForm({
        full_name: "",
        primary_phone: "",
        secondary_phone: "",
        customer_type: "BUYER",
        email: "",
        source: "PORTAL",
        readiness_level: "HIGH",
      });
      setErrMsg(null);
      setNotice("مشتری جدید ثبت شد.");
      qc.invalidateQueries({ queryKey: ["customers"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const editMut = useMutation({
    mutationFn: async () => {
      if (!editTarget) return;
      return apiFetch(`/api/v1/customers/${editTarget.id}`, {
        method: "PATCH",
        token: accessToken,
        agencyId: activeAgencyId || editTarget.agency,
        body: JSON.stringify({
          full_name: editForm.full_name.trim(),
          primary_phone: editForm.primary_phone.trim(),
          secondary_phone: editForm.secondary_phone.trim(),
          customer_type: editForm.customer_type,
          email: editForm.email.trim(),
          source: editForm.source,
          readiness_level: editForm.readiness_level,
          ...(editForm.assigned_membership_id
            ? { assigned_membership_id: editForm.assigned_membership_id }
            : {}),
        }),
      });
    },
    onSuccess: () => {
      const id = editTarget?.id;
      setEditTarget(null);
      setErrMsg(null);
      setNotice("اطلاعات مشتری با موفقیت به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["customers"] });
      if (id) qc.invalidateQueries({ queryKey: ["customer-detail", id] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const deleteMut = useMutation({
    mutationFn: async (c: CustomerItem) =>
      apiFetch(`/api/v1/customers/${c.id}`, {
        method: "DELETE",
        token: accessToken,
        agencyId: activeAgencyId || c.agency,
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("پرونده مشتری با موفقیت بایگانی (حذف) شد.");
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
        agencyId: activeAgencyId || shareTarget.agency,
        body: JSON.stringify(shareForm),
      });
    },
    onSuccess: () => {
      setShareTarget(null);
      setErrMsg(null);
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
        agencyId: activeAgencyId || reqTarget.agency,
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
      setErrMsg(null);
      setNotice("نیاز ملکی مشتری ثبت شد.");
      qc.invalidateQueries({ queryKey: ["customers"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="مشتریان و اشتراک‌گذاری خصوصی"
        subtitle="مدیریت خریداران، مستأجران، مالکین، نیازهای ملکی، ویرایش و اشتراک‌گذاری با سایر مشاوران"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "مشتریان" }]}
        actions={
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800 whitespace-nowrap"
          >
            <Plus className="h-4 w-4" />
            ثبت مشتری جدید
          </button>
        }
      />

      {effectiveRole === "SUPER_ADMIN" && !activeAgencyId && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
          شما در نمای سراسری همه آژانس‌ها هستید. برای ثبت مشتری جدید، ابتدا آژانس مقصد را از منوی بالای صفحه انتخاب کنید.
        </div>
      )}

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      <DataTable
        rows={custQ.data || []}
        rowKey={(c) => c.id}
        isLoading={custQ.isLoading}
        error={custQ.error instanceof Error ? custQ.error.message : null}
        onRetry={() => custQ.refetch()}
        exportFileName="bonyan-customers"
        searchPlaceholder="جستجو در نام یا موبایل مشتری..."
        activeFilter={typeFilter}
        onFilterChange={setTypeFilter}
        filterTabs={[
          { value: "", label: "همه مشتریان" },
          { value: "BUYER", label: "خریدار" },
          { value: "TENANT", label: "مستأجر" },
          { value: "SELLER", label: "فروشنده" },
          { value: "LANDLORD", label: "موجر" },
          { value: "INVESTOR", label: "سرمایه‌گذار" },
        ]}
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
                  {!activeAgencyId && c.agency_name ? ` · ${c.agency_name}` : ""}
                </div>
              </div>
            ),
          },
          {
            key: "type",
            header: "نوع",
            render: (c) => <span className="text-xs">{CUSTOMER_TYPE_LABELS[c.customer_type] || c.customer_type}</span>,
          },
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
                <Link
                  href={`/dashboard/customers/${c.id}`}
                  className="inline-flex h-7 items-center gap-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 whitespace-nowrap"
                >
                  <Eye className="h-3.5 w-3.5" />
                  پرونده
                </Link>
                <button
                  type="button"
                  onClick={() => {
                    setEditTarget(c);
                    setEditForm({
                      full_name: c.full_name,
                      primary_phone: c.primary_phone,
                      secondary_phone: c.secondary_phone || "",
                      customer_type: c.customer_type,
                      email: c.email || "",
                      source: c.source || "PORTAL",
                      readiness_level: c.readiness_level || "MEDIUM",
                      assigned_membership_id: c.assigned_membership || "",
                    });
                  }}
                  className="inline-flex h-7 items-center gap-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 whitespace-nowrap"
                >
                  <Edit3 className="h-3.5 w-3.5" />
                  ویرایش
                </button>
                <button
                  type="button"
                  onClick={() => setReqTarget(c)}
                  className="inline-flex h-7 items-center gap-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 whitespace-nowrap"
                >
                  <Target className="h-3.5 w-3.5 text-teal-700 dark:text-teal-400" />
                  تقاضا
                </button>
                <button
                  type="button"
                  onClick={() => setShareTarget(c)}
                  className="inline-flex h-7 items-center gap-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 whitespace-nowrap"
                >
                  <Share2 className="h-3.5 w-3.5 text-amber-700" />
                  اشتراک
                </button>
                <button
                  type="button"
                  disabled={deleteMut.isPending}
                  onClick={() => {
                    if (window.confirm(`آیا از حذف (بایگانی) مشتری «${c.full_name}» مطمئن هستید؟`)) {
                      deleteMut.mutate(c);
                    }
                  }}
                  className="inline-flex h-7 items-center justify-center rounded border border-rose-200 bg-rose-50 px-2 text-rose-700 hover:bg-rose-100 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-300"
                  title="حذف مشتری"
                >
                  <Trash2 className="h-3.5 w-3.5" />
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
          {!activeAgencyId && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-200">
              برای ثبت مشتری جدید، ابتدا از منوی بالای صفحه آژانس مقصد را انتخاب کنید.
            </div>
          )}
          <input
            required
            placeholder="نام و نام خانوادگی *"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
          />
          <input
            required
            dir="ltr"
            placeholder="0912..."
            value={form.primary_phone}
            onChange={(e) => setForm({ ...form, primary_phone: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-left font-mono text-sm"
          />
          <input
            type="email"
            dir="ltr"
            placeholder="ایمیل (اختیاری)"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-left font-mono text-sm"
          />
          <div className="grid grid-cols-2 gap-3">
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
            <select
              value={form.readiness_level}
              onChange={(e) => setForm({ ...form, readiness_level: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
            >
              <option value="HIGH">آمادگی بالا</option>
              <option value="MEDIUM">آمادگی متوسط</option>
              <option value="LOW">در حال بررسی</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={createMut.isPending || !activeAgencyId}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white disabled:opacity-60"
          >
            {createMut.isPending ? "در حال ثبت..." : "ثبت مشتری"}
          </button>
        </form>
      </ModalDrawer>

      <ModalDrawer
        open={Boolean(editTarget)}
        onClose={() => setEditTarget(null)}
        title={`ویرایش اطلاعات مشتری — ${editTarget?.full_name || ""}`}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            editMut.mutate();
          }}
          className="space-y-3"
        >
          <input
            required
            placeholder="نام و نام خانوادگی *"
            value={editForm.full_name}
            onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
          />
          <div className="grid grid-cols-2 gap-3">
            <input
              required
              dir="ltr"
              placeholder="شماره اصلی"
              value={editForm.primary_phone}
              onChange={(e) => setEditForm({ ...editForm, primary_phone: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-left font-mono text-sm"
            />
            <input
              dir="ltr"
              placeholder="شماره دوم"
              value={editForm.secondary_phone}
              onChange={(e) => setEditForm({ ...editForm, secondary_phone: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-left font-mono text-sm"
            />
          </div>
          <input
            type="email"
            dir="ltr"
            placeholder="ایمیل"
            value={editForm.email}
            onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-left font-mono text-sm"
          />
          <div className="grid grid-cols-2 gap-3">
            <select
              value={editForm.customer_type}
              onChange={(e) => setEditForm({ ...editForm, customer_type: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
            >
              <option value="BUYER">خریدار</option>
              <option value="TENANT">مستأجر</option>
              <option value="SELLER">فروشنده</option>
              <option value="LANDLORD">موجر</option>
              <option value="INVESTOR">سرمایه‌گذار</option>
            </select>
            <select
              value={editForm.readiness_level}
              onChange={(e) => setEditForm({ ...editForm, readiness_level: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
            >
              <option value="HIGH">آمادگی بالا</option>
              <option value="MEDIUM">آمادگی متوسط</option>
              <option value="LOW">در حال بررسی</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-600 dark:text-slate-300">مشاور مسئول</label>
            <select
              value={editForm.assigned_membership_id}
              onChange={(e) => setEditForm({ ...editForm, assigned_membership_id: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
            >
              <option value="">بدون تغییر / تخصیص‌نیافته</option>
              {(membersQ.data || []).map((m) => (
                <option key={m.id} value={m.id}>
                  {m.full_name} ({m.role_name})
                </option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            disabled={editMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
          >
            {editMut.isPending ? "در حال ذخیره..." : "ذخیره تغییرات مشتری"}
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
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
          />
          <input
            placeholder="مناطق (با کاما جدا کنید)"
            value={reqForm.districts_csv}
            onChange={(e) => setReqForm({ ...reqForm, districts_csv: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
          />
          <div className="grid grid-cols-2 gap-3">
            <input
              type="number"
              placeholder="حداقل بودجه"
              value={reqForm.min_budget}
              onChange={(e) => setReqForm({ ...reqForm, min_budget: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm tabular-nums"
            />
            <input
              type="number"
              placeholder="حداکثر بودجه"
              value={reqForm.max_budget}
              onChange={(e) => setReqForm({ ...reqForm, max_budget: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm tabular-nums"
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

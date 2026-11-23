"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Edit3, GitMerge, Plus, Power, Trash2 } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { AgencyItem, BranchItem, CooperationItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { StatusText } from "@/components/ui/StatusText";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";

export default function AgenciesBranchesPage() {
  const { accessToken, activeAgencyId, effectiveRole } = useAuth();
  const qc = useQueryClient();
  const isSuper = effectiveRole === "SUPER_ADMIN";

  const [branchModal, setBranchModal] = useState(false);
  const [editingBranchId, setEditingBranchId] = useState<string | null>(null);
  const [includeInactiveBranches, setIncludeInactiveBranches] = useState(true);

  const [agencyModal, setAgencyModal] = useState(false);
  const [editingAgencyId, setEditingAgencyId] = useState<string | null>(null);

  const [coopModal, setCoopModal] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const emptyBranchForm = { name: "", code: "", province: "", city: "تهران", address: "", phone: "", is_main: false };
  const [branchForm, setBranchForm] = useState(emptyBranchForm);

  const emptyAgencyForm = {
    name: "",
    slug: "",
    phone: "",
    email: "",
    registration_number: "",
    tax_id: "",
    description: "",
  };
  const [agencyForm, setAgencyForm] = useState(emptyAgencyForm);
  const [coopForm, setCoopForm] = useState({ provider_agency_id: "", default_split_percent: "50.00" });

  const agenciesQ = useQuery({
    queryKey: ["agencies-list"],
    enabled: !!accessToken,
    queryFn: async () => (await apiFetch<AgencyItem[]>("/api/v1/agencies?page_size=100", { token: accessToken })).data,
  });

  const branchesQ = useQuery({
    queryKey: ["branches-list", activeAgencyId, includeInactiveBranches],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (
        await apiFetch<BranchItem[]>(
          `/api/v1/agencies/${activeAgencyId}/branches?include_inactive=${includeInactiveBranches}`,
          { token: accessToken }
        )
      ).data,
  });

  const coopsQ = useQuery({
    queryKey: ["coops-list", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<CooperationItem[]>(`/api/v1/agencies/${activeAgencyId}/cooperations`, { token: accessToken })).data,
  });

  const saveAgencyMut = useMutation({
    mutationFn: async () => {
      if (editingAgencyId) {
        return apiFetch(`/api/v1/agencies/${editingAgencyId}`, {
          method: "PATCH",
          token: accessToken,
          body: JSON.stringify({
            name: agencyForm.name,
            phone: agencyForm.phone,
            email: agencyForm.email,
            registration_number: agencyForm.registration_number,
            tax_id: agencyForm.tax_id,
            description: agencyForm.description,
          }),
        });
      }
      return apiFetch("/api/v1/agencies", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify(agencyForm),
      });
    },
    onSuccess: () => {
      setAgencyModal(false);
      setEditingAgencyId(null);
      setAgencyForm(emptyAgencyForm);
      setNotice(editingAgencyId ? "اطلاعات آژانس به‌روزرسانی شد." : "آژانس جدید ثبت شد.");
      qc.invalidateQueries({ queryKey: ["agencies-list"] });
      qc.invalidateQueries({ queryKey: ["header-agencies"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const agencyStatusMut = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) =>
      apiFetch(`/api/v1/agencies/${id}/status`, {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      setNotice("وضعیت آژانس تغییر یافت.");
      qc.invalidateQueries({ queryKey: ["agencies-list"] });
      qc.invalidateQueries({ queryKey: ["header-agencies"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const deleteAgencyMut = useMutation({
    mutationFn: async (id: string) =>
      apiFetch(`/api/v1/agencies/${id}`, {
        method: "DELETE",
        token: accessToken,
      }),
    onSuccess: () => {
      setNotice("آژانس با موفقیت بایگانی (حذف نرم) شد.");
      qc.invalidateQueries({ queryKey: ["agencies-list"] });
      qc.invalidateQueries({ queryKey: ["header-agencies"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const saveBranchMut = useMutation({
    mutationFn: async () => {
      if (editingBranchId) {
        return apiFetch(`/api/v1/agencies/${activeAgencyId}/branches/${editingBranchId}`, {
          method: "PATCH",
          token: accessToken,
          body: JSON.stringify(branchForm),
        });
      }
      return apiFetch(`/api/v1/agencies/${activeAgencyId}/branches`, {
        method: "POST",
        token: accessToken,
        body: JSON.stringify(branchForm),
      });
    },
    onSuccess: () => {
      setBranchModal(false);
      setEditingBranchId(null);
      setBranchForm(emptyBranchForm);
      setNotice(editingBranchId ? "اطلاعات شعبه ویرایش شد." : "شعبه جدید با موفقیت ثبت شد.");
      qc.invalidateQueries({ queryKey: ["branches-list", activeAgencyId] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const toggleBranchMut = useMutation({
    mutationFn: async ({ branchId, isActive }: { branchId: string; isActive: boolean }) =>
      isActive
        ? apiFetch(`/api/v1/agencies/${activeAgencyId}/branches/${branchId}`, {
            method: "PATCH",
            token: accessToken,
            body: JSON.stringify({ is_active: true }),
          })
        : apiFetch(`/api/v1/agencies/${activeAgencyId}/branches/${branchId}`, {
            method: "DELETE",
            token: accessToken,
          }),
    onSuccess: () => {
      setNotice("وضعیت فعال‌سازی شعبه تغییر یافت.");
      qc.invalidateQueries({ queryKey: ["branches-list", activeAgencyId] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const createCoopMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/agencies/${activeAgencyId}/cooperations`, {
        method: "POST",
        token: accessToken,
        body: JSON.stringify(coopForm),
      }),
    onSuccess: () => {
      setCoopModal(false);
      setNotice("درخواست همکاری بین‌آژانسی ارسال شد.");
      qc.invalidateQueries({ queryKey: ["coops-list", activeAgencyId] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const respondCoopMut = useMutation({
    mutationFn: async ({ coopId, status }: { coopId: string; status: string }) =>
      apiFetch(`/api/v1/agencies/${activeAgencyId}/cooperations/${coopId}/respond`, {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      setNotice("وضعیت قرارداد همکاری به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["coops-list", activeAgencyId] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="آژانس‌ها، شعب و شبکه همکاری"
        subtitle="مدیریت کامل آژانس‌ها، شعب فعال/غیرفعال و تفاهم‌نامه‌های فایل مشترک"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "آژانس‌ها و شعب" }]}
        actions={
          <div className="flex flex-wrap gap-2">
            {activeAgencyId && (
              <>
                <button
                  type="button"
                  onClick={() => {
                    setEditingBranchId(null);
                    setBranchForm(emptyBranchForm);
                    setBranchModal(true);
                  }}
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
                >
                  <Plus className="h-4 w-4" />
                  شعبه جدید
                </button>
                <button
                  type="button"
                  onClick={() => setCoopModal(true)}
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3.5 text-xs font-semibold text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  <GitMerge className="h-4 w-4" />
                  همکاری بین‌آژانسی
                </button>
              </>
            )}
            <button
              type="button"
              onClick={() => {
                setEditingAgencyId(null);
                setAgencyForm(emptyAgencyForm);
                setAgencyModal(true);
              }}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3.5 text-xs font-semibold text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
            >
              <Building2 className="h-4 w-4" />
              ثبت آژانس جدید
            </button>
          </div>
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      {activeAgencyId && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">شعب آژانس فعال</h2>
            <label className="inline-flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
              <input
                type="checkbox"
                checked={includeInactiveBranches}
                onChange={(e) => setIncludeInactiveBranches(e.target.checked)}
                className="accent-teal-700"
              />
              نمایش شعب غیرفعال / بایگانی
            </label>
          </div>
          <DataTable
            rows={branchesQ.data || []}
            rowKey={(b) => b.id}
            isLoading={branchesQ.isLoading}
            searchPlaceholder="جستجو در شعب..."
            columns={[
              { key: "code", header: "کد شعبه", render: (b) => <span className="font-mono text-xs">{b.code}</span> },
              { key: "name", header: "نام شعبه", render: (b) => <span className="font-semibold">{b.name}</span> },
              { key: "city", header: "شهر", render: (b) => b.city || "—" },
              { key: "address", header: "نشانی", render: (b) => b.address || "—" },
              { key: "main", header: "نوع", render: (b) => (b.is_main ? "شعبه مرکزی" : "فرعی") },
              { key: "status", header: "وضعیت", render: (b) => <StatusText status={b.is_active ? "ACTIVE" : "SUSPENDED"} /> },
              {
                key: "act",
                header: "عملیات",
                render: (b) => (
                  <div className="flex flex-wrap items-center gap-1.5">
                    <button
                      type="button"
                      onClick={() => {
                        setEditingBranchId(b.id);
                        setBranchForm({
                          name: b.name,
                          code: b.code,
                          province: b.province || "",
                          city: b.city || "",
                          address: b.address || "",
                          phone: b.phone || "",
                          is_main: b.is_main,
                        });
                        setBranchModal(true);
                      }}
                      className="inline-flex items-center gap-1 rounded-md border border-slate-300 dark:border-slate-700 px-2 py-1 text-xs font-semibold"
                    >
                      <Edit3 className="h-3 w-3" />
                      ویرایش
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleBranchMut.mutate({ branchId: b.id, isActive: !b.is_active })}
                      className={`inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-semibold ${
                        b.is_active
                          ? "border border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100"
                          : "bg-emerald-700 text-white hover:bg-emerald-800"
                      }`}
                    >
                      <Power className="h-3 w-3" />
                      {b.is_active ? "غیرفعال‌سازی" : "فعال‌سازی"}
                    </button>
                  </div>
                ),
              },
            ]}
          />
        </div>
      )}

      {activeAgencyId && (
        <div className="space-y-3">
          <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">همکاری‌های بین‌آژانسی (Co-op)</h2>
          <DataTable
            rows={coopsQ.data || []}
            rowKey={(c) => c.id}
            isLoading={coopsQ.isLoading}
            searchPlaceholder="جستجو در آژانس همکار..."
            columns={[
              { key: "req", header: "آژانس درخواست‌دهنده", render: (c) => c.requester_agency_name },
              { key: "prov", header: "آژانس طرف مقابل", render: (c) => c.provider_agency_name },
              { key: "split", header: "درصد تقسیم پیش‌فرض", render: (c) => `${c.default_split_percent}%` },
              { key: "status", header: "وضعیت", render: (c) => <StatusText status={c.status} /> },
              {
                key: "act",
                header: "عملیات",
                render: (c) =>
                  c.status === "PENDING" ? (
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => respondCoopMut.mutate({ coopId: c.id, status: "ACTIVE" })}
                        className="rounded-md bg-emerald-700 px-2.5 py-1 text-xs font-semibold text-white"
                      >
                        تأیید همکاری
                      </button>
                      <button
                        type="button"
                        onClick={() => respondCoopMut.mutate({ coopId: c.id, status: "REJECTED" })}
                        className="rounded-md border border-rose-200 bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-700"
                      >
                        رد
                      </button>
                    </div>
                  ) : (
                    "—"
                  ),
              },
            ]}
          />
        </div>
      )}

      <div className="space-y-3">
        <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">فهرست آژانس‌های قابل مشاهده</h2>
        <DataTable
          rows={agenciesQ.data || []}
          rowKey={(a) => a.id}
          isLoading={agenciesQ.isLoading}
          searchPlaceholder="جستجو در نام آژانس..."
          exportFileName="agencies"
          columns={[
            {
              key: "name",
              header: "نام آژانس",
              render: (a) => (
                <Link href={`/dashboard/agencies/${a.id}`} className="font-semibold text-teal-700 dark:text-teal-400 hover:underline">
                  {a.name}
                </Link>
              ),
            },
            { key: "slug", header: "شناسه یکتا", render: (a) => <span className="font-mono text-xs">{a.slug}</span> },
            { key: "owner", header: "مدیر مسئول", render: (a) => a.owner_name },
            { key: "phone", header: "تلفن", render: (a) => <span className="font-mono text-xs">{a.phone || "—"}</span> },
            { key: "status", header: "وضعیت", render: (a) => <StatusText status={a.status} /> },
            {
              key: "actions",
              header: "عملیات",
              render: (a) => (
                <div className="flex flex-wrap items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => {
                      setEditingAgencyId(a.id);
                      setAgencyForm({
                        name: a.name,
                        slug: a.slug,
                        phone: a.phone || "",
                        email: a.email || "",
                        registration_number: a.registration_number || "",
                        tax_id: a.tax_id || "",
                        description: a.description || "",
                      });
                      setAgencyModal(true);
                    }}
                    className="inline-flex items-center gap-1 rounded-md border border-slate-300 dark:border-slate-700 px-2 py-1 text-xs font-semibold"
                  >
                    <Edit3 className="h-3 w-3" />
                    ویرایش
                  </button>
                  {isSuper && a.status !== "ACTIVE" && (
                    <button
                      type="button"
                      onClick={() => agencyStatusMut.mutate({ id: a.id, status: "ACTIVE" })}
                      className="rounded-md bg-emerald-700 px-2 py-1 text-xs font-semibold text-white"
                    >
                      فعال‌سازی
                    </button>
                  )}
                  {isSuper && a.status === "ACTIVE" && (
                    <button
                      type="button"
                      onClick={() => agencyStatusMut.mutate({ id: a.id, status: "SUSPENDED" })}
                      className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-800"
                    >
                      تعلیق
                    </button>
                  )}
                  {isSuper && a.status !== "ARCHIVED" && (
                    <button
                      type="button"
                      onClick={() => deleteAgencyMut.mutate(a.id)}
                      className="inline-flex items-center gap-1 rounded-md border border-rose-200 bg-rose-50 px-2 py-1 text-xs font-semibold text-rose-700"
                      title="بایگانی آژانس"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  )}
                </div>
              ),
            },
          ]}
        />
      </div>

      <ModalDrawer
        open={branchModal}
        onClose={() => {
          setBranchModal(false);
          setEditingBranchId(null);
        }}
        title={editingBranchId ? "ویرایش شعبه" : "ثبت شعبه جدید"}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            saveBranchMut.mutate();
          }}
          className="space-y-3"
        >
          <input
            required
            placeholder="نام شعبه"
            value={branchForm.name}
            onChange={(e) => setBranchForm({ ...branchForm, name: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
          />
          <input
            required
            placeholder="کد شعبه (مثال: TEH-W2)"
            value={branchForm.code}
            onChange={(e) => setBranchForm({ ...branchForm, code: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-sm"
          />
          <div className="grid grid-cols-2 gap-2">
            <input
              placeholder="استان"
              value={branchForm.province}
              onChange={(e) => setBranchForm({ ...branchForm, province: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
            />
            <input
              placeholder="شهر"
              value={branchForm.city}
              onChange={(e) => setBranchForm({ ...branchForm, city: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
            />
          </div>
          <input
            placeholder="تلفن شعبه"
            value={branchForm.phone}
            onChange={(e) => setBranchForm({ ...branchForm, phone: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-sm"
          />
          <input
            placeholder="نشانی"
            value={branchForm.address}
            onChange={(e) => setBranchForm({ ...branchForm, address: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
          />
          <label className="inline-flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              checked={branchForm.is_main}
              onChange={(e) => setBranchForm({ ...branchForm, is_main: e.target.checked })}
              className="accent-teal-700"
            />
            شعبه مرکزی آژانس
          </label>
          <button
            type="submit"
            disabled={saveBranchMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white"
          >
            {editingBranchId ? "ذخیره تغییرات شعبه" : "ثبت شعبه"}
          </button>
        </form>
      </ModalDrawer>

      <ModalDrawer
        open={agencyModal}
        onClose={() => {
          setAgencyModal(false);
          setEditingAgencyId(null);
        }}
        title={editingAgencyId ? "ویرایش مشخصات آژانس" : "ایجاد آژانس جدید"}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            saveAgencyMut.mutate();
          }}
          className="space-y-3"
        >
          <input
            required
            placeholder="نام رسمی آژانس"
            value={agencyForm.name}
            onChange={(e) => setAgencyForm({ ...agencyForm, name: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
          />
          <input
            required
            disabled={!!editingAgencyId}
            placeholder="نامک انگلیسی (slug)"
            value={agencyForm.slug}
            onChange={(e) => setAgencyForm({ ...agencyForm, slug: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-sm disabled:opacity-60"
          />
          <div className="grid grid-cols-2 gap-2">
            <input
              placeholder="شماره تماس"
              value={agencyForm.phone}
              onChange={(e) => setAgencyForm({ ...agencyForm, phone: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
            />
            <input
              dir="ltr"
              placeholder="ایمیل"
              value={agencyForm.email}
              onChange={(e) => setAgencyForm({ ...agencyForm, email: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <input
              placeholder="شماره پروانه / ثبت"
              value={agencyForm.registration_number}
              onChange={(e) => setAgencyForm({ ...agencyForm, registration_number: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
            />
            <input
              placeholder="شناسه مالیاتی"
              value={agencyForm.tax_id}
              onChange={(e) => setAgencyForm({ ...agencyForm, tax_id: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
            />
          </div>
          <textarea
            rows={2}
            placeholder="توضیحات آژانس"
            value={agencyForm.description}
            onChange={(e) => setAgencyForm({ ...agencyForm, description: e.target.value })}
            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 p-2.5 text-sm"
          />
          <button
            type="submit"
            disabled={saveAgencyMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white"
          >
            {editingAgencyId ? "ذخیره تغییرات آژانس" : "ثبت آژانس"}
          </button>
        </form>
      </ModalDrawer>

      <ModalDrawer open={coopModal} onClose={() => setCoopModal(false)} title="درخواست همکاری بین‌آژانسی">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createCoopMut.mutate();
          }}
          className="space-y-3"
        >
          <select
            required
            value={coopForm.provider_agency_id}
            onChange={(e) => setCoopForm({ ...coopForm, provider_agency_id: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
          >
            <option value="">انتخاب آژانس مقصد...</option>
            {(agenciesQ.data || [])
              .filter((a) => a.id !== activeAgencyId)
              .map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
          </select>
          <input
            type="number"
            step="0.5"
            value={coopForm.default_split_percent}
            onChange={(e) => setCoopForm({ ...coopForm, default_split_percent: e.target.value })}
            placeholder="درصد تقسیم پورسانت (مثال 50)"
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm"
          />
          <button
            type="submit"
            disabled={createCoopMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white"
          >
            ارسال درخواست همکاری
          </button>
        </form>
      </ModalDrawer>
    </div>
  );
}

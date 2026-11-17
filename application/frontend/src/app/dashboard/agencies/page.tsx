"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, GitMerge, Plus } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { AgencyItem, BranchItem, CooperationItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { StatusText } from "@/components/ui/StatusText";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";

export default function AgenciesBranchesPage() {
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();
  const [branchModal, setBranchModal] = useState(false);
  const [agencyModal, setAgencyModal] = useState(false);
  const [coopModal, setCoopModal] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const [branchForm, setBranchForm] = useState({ name: "", code: "", city: "تهران", address: "", phone: "" });
  const [agencyForm, setAgencyForm] = useState({ name: "", slug: "", phone: "", registration_number: "" });
  const [coopForm, setCoopForm] = useState({ provider_agency_id: "", default_split_percent: "50.00" });

  const agenciesQ = useQuery({
    queryKey: ["agencies-list"],
    enabled: !!accessToken,
    queryFn: async () => (await apiFetch<AgencyItem[]>("/api/v1/agencies", { token: accessToken })).data,
  });

  const branchesQ = useQuery({
    queryKey: ["branches-list", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<BranchItem[]>(`/api/v1/agencies/${activeAgencyId}/branches`, { token: accessToken })).data,
  });

  const coopsQ = useQuery({
    queryKey: ["coops-list", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<CooperationItem[]>(`/api/v1/agencies/${activeAgencyId}/cooperations`, { token: accessToken })).data,
  });

  const createAgencyMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/agencies", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify(agencyForm),
      }),
    onSuccess: () => {
      setAgencyModal(false);
      setAgencyForm({ name: "", slug: "", phone: "", registration_number: "" });
      setNotice("آژانس جدید ثبت شد و در انتظار تأیید مدیر کل است.");
      qc.invalidateQueries({ queryKey: ["agencies-list"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const createBranchMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/agencies/${activeAgencyId}/branches`, {
        method: "POST",
        token: accessToken,
        body: JSON.stringify(branchForm),
      }),
    onSuccess: () => {
      setBranchModal(false);
      setBranchForm({ name: "", code: "", city: "تهران", address: "", phone: "" });
      setNotice("شعبه جدید با موفقیت ثبت شد.");
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
        subtitle="مدیریت شعب محلی و تفاهم‌نامه‌های فایل مشترک بین آژانس‌ها"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "آژانس‌ها و شعب" }]}
        actions={
          <div className="flex flex-wrap gap-2">
            {activeAgencyId && (
              <>
                <button
                  type="button"
                  onClick={() => setBranchModal(true)}
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
                >
                  <Plus className="h-4 w-4" />
                  شعبه جدید
                </button>
                <button
                  type="button"
                  onClick={() => setCoopModal(true)}
                  className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 text-xs font-semibold text-slate-800 hover:bg-slate-50"
                >
                  <GitMerge className="h-4 w-4" />
                  همکاری بین‌آژانسی
                </button>
              </>
            )}
            <button
              type="button"
              onClick={() => setAgencyModal(true)}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 text-xs font-semibold text-slate-800 hover:bg-slate-50"
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
          <h2 className="text-sm font-bold text-slate-900">شعب آژانس فعال</h2>
          <DataTable
            rows={branchesQ.data || []}
            rowKey={(b) => b.id}
            isLoading={branchesQ.isLoading}
            searchPlaceholder="جستجو در شعب..."
            columns={[
              { key: "code", header: "کد شعبه", render: (b) => <span className="font-mono text-xs">{b.code}</span> },
              { key: "name", header: "نام شعبه", render: (b) => <span className="font-semibold">{b.name}</span> },
              { key: "city", header: "شهر", render: (b) => b.city },
              { key: "address", header: "نشانی", render: (b) => b.address || "—" },
              { key: "main", header: "نوع", render: (b) => (b.is_main ? "شعبه مرکزی" : "فرعی") },
            ]}
          />
        </div>
      )}

      {activeAgencyId && (
        <div className="space-y-3">
          <h2 className="text-sm font-bold text-slate-900">همکاری‌های بین‌آژانسی (Co-op)</h2>
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
        <h2 className="text-sm font-bold text-slate-900">فهرست آژانس‌های قابل مشاهده</h2>
        <DataTable
          rows={agenciesQ.data || []}
          rowKey={(a) => a.id}
          isLoading={agenciesQ.isLoading}
          searchPlaceholder="جستجو در نام آژانس..."
          columns={[
            { key: "name", header: "نام آژانس", render: (a) => <span className="font-semibold">{a.name}</span> },
            { key: "slug", header: "شناسه یکتا", render: (a) => <span className="font-mono text-xs">{a.slug}</span> },
            { key: "owner", header: "مدیر مسئول", render: (a) => a.owner_name },
            { key: "currency", header: "ارز پیش‌فرض", render: (a) => a.default_currency },
            { key: "status", header: "وضعیت", render: (a) => <StatusText status={a.status} /> },
          ]}
        />
      </div>

      <ModalDrawer open={branchModal} onClose={() => setBranchModal(false)} title="ثبت شعبه جدید">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createBranchMut.mutate();
          }}
          className="space-y-3"
        >
          <input
            required
            placeholder="نام شعبه"
            value={branchForm.name}
            onChange={(e) => setBranchForm({ ...branchForm, name: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
          />
          <input
            required
            placeholder="کد شعبه (مثال: TEH-W2)"
            value={branchForm.code}
            onChange={(e) => setBranchForm({ ...branchForm, code: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 font-mono text-sm"
          />
          <input
            placeholder="شهر"
            value={branchForm.city}
            onChange={(e) => setBranchForm({ ...branchForm, city: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
          />
          <input
            placeholder="نشانی"
            value={branchForm.address}
            onChange={(e) => setBranchForm({ ...branchForm, address: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
          />
          <button
            type="submit"
            disabled={createBranchMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white"
          >
            ثبت شعبه
          </button>
        </form>
      </ModalDrawer>

      <ModalDrawer open={agencyModal} onClose={() => setAgencyModal(false)} title="ایجاد آژانس جدید">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createAgencyMut.mutate();
          }}
          className="space-y-3"
        >
          <input
            required
            placeholder="نام رسمی آژانس"
            value={agencyForm.name}
            onChange={(e) => setAgencyForm({ ...agencyForm, name: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
          />
          <input
            required
            placeholder="نامک انگلیسی (slug)"
            value={agencyForm.slug}
            onChange={(e) => setAgencyForm({ ...agencyForm, slug: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 font-mono text-sm"
          />
          <input
            placeholder="شماره تماس"
            value={agencyForm.phone}
            onChange={(e) => setAgencyForm({ ...agencyForm, phone: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
          />
          <button
            type="submit"
            disabled={createAgencyMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white"
          >
            ثبت آژانس
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
            className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"
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
            className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
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

"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { AgencyItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { StatusText } from "@/components/ui/StatusText";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";

interface AdminUserRow {
  id: string;
  phone_number: string;
  email: string | null;
  full_name: string;
  platform_role: string;
  status: string;
  date_joined: string;
  agencies: string[];
}

interface AdminSubRow {
  id: string;
  agency_name: string;
  plan_code: string;
  plan_name: string;
  billing_cycle: string;
  status: string;
  expires_at: string;
}

export default function AdminPlatformPage() {
  const { accessToken, effectiveRole } = useAuth();
  const isSuperAdmin = effectiveRole === "SUPER_ADMIN";
  const qc = useQueryClient();
  const [tab, setTab] = useState<"agencies" | "users" | "subs">("agencies");
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const agenciesQ = useQuery({
    queryKey: ["admin-agencies"],
    enabled: !!accessToken && isSuperAdmin,
    queryFn: async () => (await apiFetch<AgencyItem[]>("/api/v1/agencies", { token: accessToken })).data,
  });

  const usersQ = useQuery({
    queryKey: ["admin-users"],
    enabled: !!accessToken && isSuperAdmin,
    queryFn: async () => (await apiFetch<AdminUserRow[]>("/api/v1/admin/users", { token: accessToken })).data,
  });

  const subsQ = useQuery({
    queryKey: ["admin-subs"],
    enabled: !!accessToken && isSuperAdmin,
    queryFn: async () =>
      (await apiFetch<AdminSubRow[]>("/api/v1/admin/subscriptions", { token: accessToken })).data,
  });

  const agencyStatusMut = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) =>
      apiFetch(`/api/v1/agencies/${id}/status`, {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      setNotice("وضعیت آژانس با موفقیت به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["admin-agencies"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const userStatusMut = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) =>
      apiFetch(`/api/v1/admin/users/${id}/status`, {
        method: "PATCH",
        token: accessToken,
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      setNotice("وضعیت حساب کاربری تغییر یافت.");
      qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  if (!isSuperAdmin) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="مدیریت کل پلتفرم (Super Admin)"
          breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "مدیریت کل پلتفرم" }]}
        />
        <ErrorState message="این بخش فقط در دسترس مدیر کل سامانه (Super Admin) است." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="مدیریت کل پلتفرم (Super Admin)"
        subtitle="تأیید و نظارت بر آژانس‌ها، کاربران سراسری و اشتراک‌های فعال"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "مدیریت کل پلتفرم" }]}
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-3">
        {[
          { key: "agencies", label: "آژانس‌های املاک" },
          { key: "users", label: "کاربران پلتفرم" },
          { key: "subs", label: "اشتراک‌ها" },
        ].map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => setTab(item.key as typeof tab)}
            className={`h-9 rounded-lg border px-4 text-xs font-semibold transition-colors ${
              tab === item.key
                ? "border-teal-700 bg-teal-700 text-white"
                : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === "agencies" && (
        <DataTable
          rows={agenciesQ.data || []}
          rowKey={(r) => r.id}
          isLoading={agenciesQ.isLoading}
          error={agenciesQ.error instanceof Error ? agenciesQ.error.message : null}
          onRetry={() => agenciesQ.refetch()}
          searchPlaceholder="جستجو در نام یا کد ثبت آژانس..."
          columns={[
            { key: "name", header: "نام آژانس", render: (r) => <span className="font-semibold">{r.name}</span> },
            { key: "owner", header: "مالک / مدیر", render: (r) => r.owner_name },
            { key: "phone", header: "تلفن", render: (r) => <span className="font-mono text-xs">{r.phone || "—"}</span> },
            { key: "status", header: "وضعیت", render: (r) => <StatusText status={r.status} /> },
            {
              key: "actions",
              header: "عملیات",
              render: (r) => (
                <div className="flex items-center gap-2">
                  {r.status !== "ACTIVE" && (
                    <button
                      type="button"
                      onClick={() => agencyStatusMut.mutate({ id: r.id, status: "ACTIVE" })}
                      className="rounded-md bg-emerald-700 px-2.5 py-1 text-xs font-semibold text-white hover:bg-emerald-800"
                    >
                      تأیید و فعال‌سازی
                    </button>
                  )}
                  {r.status === "ACTIVE" && (
                    <button
                      type="button"
                      onClick={() => agencyStatusMut.mutate({ id: r.id, status: "SUSPENDED" })}
                      className="rounded-md border border-rose-200 bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-700 hover:bg-rose-100"
                    >
                      تعلیق
                    </button>
                  )}
                </div>
              ),
            },
          ]}
        />
      )}

      {tab === "users" && (
        <DataTable
          rows={usersQ.data || []}
          rowKey={(r) => r.id}
          isLoading={usersQ.isLoading}
          error={usersQ.error instanceof Error ? usersQ.error.message : null}
          onRetry={() => usersQ.refetch()}
          searchPlaceholder="جستجو در نام یا موبایل کاربر..."
          columns={[
            { key: "name", header: "نام کامل", render: (r) => <span className="font-semibold">{r.full_name}</span> },
            { key: "phone", header: "موبایل", render: (r) => <span className="font-mono text-xs">{r.phone_number}</span> },
            { key: "role", header: "نقش پلتفرم", render: (r) => r.platform_role },
            { key: "agencies", header: "آژانس‌ها", render: (r) => r.agencies.join("، ") || "—" },
            { key: "status", header: "وضعیت", render: (r) => <StatusText status={r.status} /> },
            {
              key: "actions",
              header: "تغییر وضعیت",
              render: (r) => (
                <button
                  type="button"
                  onClick={() =>
                    userStatusMut.mutate({
                      id: r.id,
                      status: r.status === "ACTIVE" ? "SUSPENDED" : "ACTIVE",
                    })
                  }
                  className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  {r.status === "ACTIVE" ? "تعلیق کاربر" : "فعال‌سازی"}
                </button>
              ),
            },
          ]}
        />
      )}

      {tab === "subs" && (
        <DataTable
          rows={subsQ.data || []}
          rowKey={(r) => r.id}
          isLoading={subsQ.isLoading}
          error={subsQ.error instanceof Error ? subsQ.error.message : null}
          searchPlaceholder="جستجو در اشتراک آژانس‌ها..."
          columns={[
            { key: "agency", header: "آژانس", render: (r) => <span className="font-semibold">{r.agency_name}</span> },
            { key: "plan", header: "پلن", render: (r) => r.plan_name },
            { key: "cycle", header: "دوره", render: (r) => (r.billing_cycle === "ANNUAL" ? "سالانه" : "ماهانه") },
            { key: "status", header: "وضعیت", render: (r) => <StatusText status={r.status} /> },
            { key: "exp", header: "انقضا", render: (r) => <DateDisplay value={r.expires_at} /> },
          ]}
        />
      )}
    </div>
  );
}

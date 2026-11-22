"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Edit3, Plus, ShieldPlus, Trash2, UserPlus } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { AgencyItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { StatusText } from "@/components/ui/StatusText";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";

interface AdminUserRow {
  id: string;
  phone_number: string;
  email: string | null;
  first_name?: string;
  last_name?: string;
  full_name: string;
  platform_role: string;
  status: string;
  date_joined: string;
  agencies: string[];
  memberships?: {
    id: string;
    agency_id: string;
    agency_name: string;
    role_code: string;
    role_name: string;
    branch_id: string | null;
    branch_name: string | null;
    status: string;
  }[];
}

interface AdminSubRow {
  id: string;
  agency_id: string;
  agency_name: string;
  plan_code: string;
  plan_name: string;
  billing_cycle: string;
  status: string;
  expires_at: string;
}

interface PlanOption {
  id: string;
  code: string;
  name_fa: string;
}

const ROLE_OPTIONS = [
  { code: "AGENCY_MANAGER", label: "مدیر آژانس" },
  { code: "BRANCH_MANAGER", label: "مدیر شعبه" },
  { code: "SALES_MANAGER", label: "مدیر فروش" },
  { code: "AGENCY_ACCOUNTANT", label: "حسابدار آژانس" },
  { code: "REAL_ESTATE_AGENT", label: "مشاور املاک" },
  { code: "SUPPORT_AGENT", label: "پشتیبان آژانس" },
];

export default function AdminPlatformPage() {
  const { accessToken, effectiveRole } = useAuth();
  const isSuperAdmin = effectiveRole === "SUPER_ADMIN";
  const qc = useQueryClient();
  const [tab, setTab] = useState<"agencies" | "users" | "subs">("agencies");
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  // User modal state
  const [userModal, setUserModal] = useState(false);
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const emptyUserForm = {
    phone_number: "",
    first_name: "",
    last_name: "",
    email: "",
    password: "",
    platform_role: "AGENCY_USER",
    agency_id: "",
    role_code: "REAL_ESTATE_AGENT",
  };
  const [userForm, setUserForm] = useState(emptyUserForm);

  // Membership assign modal
  const [assignUser, setAssignUser] = useState<AdminUserRow | null>(null);
  const [assignForm, setAssignForm] = useState({ agency_id: "", role_code: "REAL_ESTATE_AGENT", status: "ACTIVE" });

  // Subscription assign/edit modal
  const [subModal, setSubModal] = useState(false);
  const [editingSub, setEditingSub] = useState<AdminSubRow | null>(null);
  const [subForm, setSubForm] = useState({
    agency_id: "",
    plan_code: "PRO",
    billing_cycle: "MONTHLY",
    duration_days: 30,
    status: "ACTIVE",
    extend_days: 30,
  });

  const agenciesQ = useQuery({
    queryKey: ["admin-agencies"],
    enabled: !!accessToken && isSuperAdmin,
    queryFn: async () => (await apiFetch<AgencyItem[]>("/api/v1/agencies?page_size=100", { token: accessToken })).data,
  });

  const usersQ = useQuery({
    queryKey: ["admin-users"],
    enabled: !!accessToken && isSuperAdmin,
    queryFn: async () => (await apiFetch<AdminUserRow[]>("/api/v1/admin/users?page_size=100", { token: accessToken })).data,
  });

  const subsQ = useQuery({
    queryKey: ["admin-subs"],
    enabled: !!accessToken && isSuperAdmin,
    queryFn: async () => (await apiFetch<AdminSubRow[]>("/api/v1/admin/subscriptions", { token: accessToken })).data,
  });

  const plansQ = useQuery({
    queryKey: ["admin-plans"],
    enabled: !!accessToken && isSuperAdmin,
    queryFn: async () =>
      (await apiFetch<PlanOption[]>("/api/v1/subscriptions/plans?include_inactive=true", { token: accessToken })).data,
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
      qc.invalidateQueries({ queryKey: ["header-agencies"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const archiveAgencyMut = useMutation({
    mutationFn: async (id: string) =>
      apiFetch(`/api/v1/agencies/${id}`, { method: "DELETE", token: accessToken }),
    onSuccess: () => {
      setNotice("آژانس با موفقیت بایگانی شد.");
      qc.invalidateQueries({ queryKey: ["admin-agencies"] });
      qc.invalidateQueries({ queryKey: ["header-agencies"] });
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

  const saveUserMut = useMutation({
    mutationFn: async () => {
      if (editingUserId) {
        return apiFetch(`/api/v1/admin/users/${editingUserId}`, {
          method: "PATCH",
          token: accessToken,
          body: JSON.stringify({
            phone_number: userForm.phone_number,
            first_name: userForm.first_name,
            last_name: userForm.last_name,
            email: userForm.email || null,
            password: userForm.password || undefined,
            platform_role: userForm.platform_role,
          }),
        });
      }
      return apiFetch("/api/v1/admin/users", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({
          ...userForm,
          email: userForm.email || null,
          password: userForm.password || null,
          agency_id: userForm.agency_id || null,
          role_code: userForm.agency_id ? userForm.role_code : null,
        }),
      });
    },
    onSuccess: () => {
      setUserModal(false);
      setEditingUserId(null);
      setUserForm(emptyUserForm);
      setNotice(editingUserId ? "اطلاعات کاربر ویرایش شد." : "کاربر جدید ایجاد شد.");
      qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const deleteUserMut = useMutation({
    mutationFn: async (id: string) => apiFetch(`/api/v1/admin/users/${id}`, { method: "DELETE", token: accessToken }),
    onSuccess: () => {
      setNotice("کاربر حذف نرم (غیرفعال) شد.");
      qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const assignMembershipMut = useMutation({
    mutationFn: async () => {
      if (!assignUser) return;
      return apiFetch(`/api/v1/admin/users/${assignUser.id}/memberships`, {
        method: "POST",
        token: accessToken,
        body: JSON.stringify(assignForm),
      });
    },
    onSuccess: () => {
      setAssignUser(null);
      setNotice("تخصیص آژانس و نقش با موفقیت انجام شد.");
      qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const saveSubMut = useMutation({
    mutationFn: async () => {
      if (editingSub) {
        return apiFetch(`/api/v1/admin/subscriptions/${editingSub.id}`, {
          method: "PATCH",
          token: accessToken,
          body: JSON.stringify({
            plan_code: subForm.plan_code,
            billing_cycle: subForm.billing_cycle,
            status: subForm.status,
            extend_days: subForm.extend_days > 0 ? subForm.extend_days : undefined,
          }),
        });
      }
      return apiFetch("/api/v1/admin/subscriptions", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({
          agency_id: subForm.agency_id,
          plan_code: subForm.plan_code,
          billing_cycle: subForm.billing_cycle,
          duration_days: subForm.duration_days,
          status: subForm.status,
        }),
      });
    },
    onSuccess: () => {
      setSubModal(false);
      setEditingSub(null);
      setNotice(editingSub ? "اشتراک آژانس به‌روزرسانی/تمدید شد." : "اشتراک جدید برای آژانس ثبت شد.");
      qc.invalidateQueries({ queryKey: ["admin-subs"] });
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
        subtitle="تأیید و مدیریت آژانس‌ها، ایجاد/ویرایش/تخصیص کاربران و کنترل کامل اشتراک‌ها"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "مدیریت کل پلتفرم" }]}
        actions={
          <div className="flex flex-wrap gap-2">
            {tab === "users" && (
              <button
                type="button"
                onClick={() => {
                  setEditingUserId(null);
                  setUserForm(emptyUserForm);
                  setUserModal(true);
                }}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
              >
                <UserPlus className="h-4 w-4" />
                کاربر جدید
              </button>
            )}
            {tab === "subs" && (
              <button
                type="button"
                onClick={() => {
                  setEditingSub(null);
                  setSubForm({
                    agency_id: agenciesQ.data?.[0]?.id || "",
                    plan_code: plansQ.data?.[0]?.code || "PRO",
                    billing_cycle: "MONTHLY",
                    duration_days: 30,
                    status: "ACTIVE",
                    extend_days: 0,
                  });
                  setSubModal(true);
                }}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
              >
                <Plus className="h-4 w-4" />
                تخصیص اشتراک به آژانس
              </button>
            )}
          </div>
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      <div className="flex flex-wrap gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
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
                : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
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
                <div className="flex flex-wrap items-center gap-1.5">
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
                      className="rounded-md border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-800 hover:bg-amber-100"
                    >
                      تعلیق
                    </button>
                  )}
                  {r.status !== "ARCHIVED" && (
                    <button
                      type="button"
                      onClick={() => archiveAgencyMut.mutate(r.id)}
                      className="inline-flex items-center gap-1 rounded-md border border-rose-200 bg-rose-50 px-2 py-1 text-xs font-semibold text-rose-700"
                      title="بایگانی آژانس"
                    >
                      <Trash2 className="h-3 w-3" />
                      بایگانی
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
            {
              key: "agencies",
              header: "عضویت‌ها",
              render: (r) =>
                (r.memberships || []).length > 0
                  ? r.memberships!.map((m) => `${m.agency_name} (${m.role_name})`).join("، ")
                  : r.agencies.join("، ") || "—",
            },
            { key: "status", header: "وضعیت", render: (r) => <StatusText status={r.status} /> },
            {
              key: "actions",
              header: "عملیات",
              render: (r) => (
                <div className="flex flex-wrap items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => {
                      setEditingUserId(r.id);
                      setUserForm({
                        phone_number: r.phone_number,
                        first_name: r.first_name || r.full_name.split(" ")[0] || "",
                        last_name: r.last_name || r.full_name.split(" ").slice(1).join(" ") || "",
                        email: r.email || "",
                        password: "",
                        platform_role: r.platform_role,
                        agency_id: "",
                        role_code: "REAL_ESTATE_AGENT",
                      });
                      setUserModal(true);
                    }}
                    className="inline-flex items-center gap-1 rounded-md border border-slate-300 dark:border-slate-700 px-2 py-1 text-xs font-semibold"
                  >
                    <Edit3 className="h-3 w-3" />
                    ویرایش
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setAssignUser(r);
                      setAssignForm({
                        agency_id: agenciesQ.data?.[0]?.id || "",
                        role_code: "REAL_ESTATE_AGENT",
                        status: "ACTIVE",
                      });
                    }}
                    className="inline-flex items-center gap-1 rounded-md border border-teal-700 px-2 py-1 text-xs font-semibold text-teal-700 dark:text-teal-400"
                  >
                    <ShieldPlus className="h-3 w-3" />
                    تخصیص آژانس
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      userStatusMut.mutate({
                        id: r.id,
                        status: r.status === "ACTIVE" ? "SUSPENDED" : "ACTIVE",
                      })
                    }
                    className="rounded-md border border-slate-300 dark:border-slate-700 px-2 py-1 text-xs font-medium"
                  >
                    {r.status === "ACTIVE" ? "تعلیق" : "فعال‌سازی"}
                  </button>
                  <button
                    type="button"
                    onClick={() => deleteUserMut.mutate(r.id)}
                    className="inline-flex items-center gap-1 rounded-md border border-rose-200 bg-rose-50 px-2 py-1 text-xs font-semibold text-rose-700"
                    title="حذف کاربر"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
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
            { key: "plan", header: "پلن", render: (r) => `${r.plan_name} (${r.plan_code})` },
            { key: "cycle", header: "دوره", render: (r) => (r.billing_cycle === "ANNUAL" ? "سالانه" : "ماهانه") },
            { key: "status", header: "وضعیت", render: (r) => <StatusText status={r.status} /> },
            { key: "exp", header: "انقضا", render: (r) => <DateDisplay value={r.expires_at} /> },
            {
              key: "act",
              header: "مدیریت اشتراک",
              render: (r) => (
                <button
                  type="button"
                  onClick={() => {
                    setEditingSub(r);
                    setSubForm({
                      agency_id: r.agency_id,
                      plan_code: r.plan_code,
                      billing_cycle: r.billing_cycle,
                      duration_days: 30,
                      status: r.status,
                      extend_days: 30,
                    });
                    setSubModal(true);
                  }}
                  className="inline-flex items-center gap-1 rounded-md border border-slate-300 dark:border-slate-700 px-2.5 py-1 text-xs font-semibold"
                >
                  <Edit3 className="h-3 w-3" />
                  تغییر / تمدید
                </button>
              ),
            },
          ]}
        />
      )}

      {/* Create / Edit User Drawer */}
      <ModalDrawer
        open={userModal}
        onClose={() => {
          setUserModal(false);
          setEditingUserId(null);
        }}
        title={editingUserId ? "ویرایش کاربر پلتفرم" : "ایجاد کاربر جدید"}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            saveUserMut.mutate();
          }}
          className="space-y-3"
        >
          <div className="grid grid-cols-2 gap-2">
            <input
              required
              placeholder="نام"
              value={userForm.first_name}
              onChange={(e) => setUserForm({ ...userForm, first_name: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
            />
            <input
              required
              placeholder="نام خانوادگی"
              value={userForm.last_name}
              onChange={(e) => setUserForm({ ...userForm, last_name: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
            />
          </div>
          <input
            required
            dir="ltr"
            placeholder="0912..."
            value={userForm.phone_number}
            onChange={(e) => setUserForm({ ...userForm, phone_number: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-sm"
          />
          <input
            dir="ltr"
            type="email"
            placeholder="ایمیل (اختیاری)"
            value={userForm.email}
            onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
          />
          <input
            dir="ltr"
            type="password"
            placeholder={editingUserId ? "رمز عبور جدید (در صورت نیاز به تغییر)" : "رمز عبور اولیه (اختیاری)"}
            value={userForm.password}
            onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
          />
          <select
            value={userForm.platform_role}
            onChange={(e) => setUserForm({ ...userForm, platform_role: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
          >
            <option value="AGENCY_USER">کاربر آژانس (AGENCY_USER)</option>
            <option value="CUSTOMER">مشتری پورتال (CUSTOMER)</option>
            <option value="SUPER_ADMIN">مدیر کل سامانه (SUPER_ADMIN)</option>
          </select>
          {!editingUserId && (
            <div className="grid grid-cols-2 gap-2">
              <select
                value={userForm.agency_id}
                onChange={(e) => setUserForm({ ...userForm, agency_id: e.target.value })}
                className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-2 text-xs"
              >
                <option value="">بدون تخصیص آژانس</option>
                {(agenciesQ.data || []).map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
              <select
                value={userForm.role_code}
                onChange={(e) => setUserForm({ ...userForm, role_code: e.target.value })}
                className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-2 text-xs"
              >
                {ROLE_OPTIONS.map((ro) => (
                  <option key={ro.code} value={ro.code}>
                    {ro.label}
                  </option>
                ))}
              </select>
            </div>
          )}
          <button
            type="submit"
            disabled={saveUserMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white"
          >
            {editingUserId ? "ذخیره تغییرات کاربر" : "ایجاد کاربر"}
          </button>
        </form>
      </ModalDrawer>

      {/* Assign User to Agency/Role Drawer */}
      <ModalDrawer
        open={!!assignUser}
        onClose={() => setAssignUser(null)}
        title={`تخصیص آژانس و نقش — ${assignUser?.full_name || ""}`}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            assignMembershipMut.mutate();
          }}
          className="space-y-3"
        >
          <select
            required
            value={assignForm.agency_id}
            onChange={(e) => setAssignForm({ ...assignForm, agency_id: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
          >
            <option value="">انتخاب آژانس...</option>
            {(agenciesQ.data || []).map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
          <select
            value={assignForm.role_code}
            onChange={(e) => setAssignForm({ ...assignForm, role_code: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
          >
            {ROLE_OPTIONS.map((ro) => (
              <option key={ro.code} value={ro.code}>
                {ro.label}
              </option>
            ))}
          </select>
          <select
            value={assignForm.status}
            onChange={(e) => setAssignForm({ ...assignForm, status: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
          >
            <option value="ACTIVE">فعال (ACTIVE)</option>
            <option value="SUSPENDED">معلق (SUSPENDED)</option>
          </select>
          <button
            type="submit"
            disabled={assignMembershipMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white"
          >
            ثبت عضویت
          </button>
        </form>
      </ModalDrawer>

      {/* Create / Update Subscription Drawer */}
      <ModalDrawer
        open={subModal}
        onClose={() => {
          setSubModal(false);
          setEditingSub(null);
        }}
        title={editingSub ? `مدیریت اشتراک — ${editingSub.agency_name}` : "تخصیص اشتراک به آژانس"}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            saveSubMut.mutate();
          }}
          className="space-y-3"
        >
          {!editingSub && (
            <select
              required
              value={subForm.agency_id}
              onChange={(e) => setSubForm({ ...subForm, agency_id: e.target.value })}
              className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
            >
              <option value="">انتخاب آژانس...</option>
              {(agenciesQ.data || []).map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          )}
          <select
            value={subForm.plan_code}
            onChange={(e) => setSubForm({ ...subForm, plan_code: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
          >
            {(plansQ.data || []).map((p) => (
              <option key={p.id} value={p.code}>
                {p.name_fa} ({p.code})
              </option>
            ))}
          </select>
          <div className="grid grid-cols-2 gap-2">
            <select
              value={subForm.billing_cycle}
              onChange={(e) => setSubForm({ ...subForm, billing_cycle: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
            >
              <option value="MONTHLY">ماهانه</option>
              <option value="ANNUAL">سالانه</option>
            </select>
            <select
              value={subForm.status}
              onChange={(e) => setSubForm({ ...subForm, status: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 text-sm"
            >
              <option value="ACTIVE">فعال (ACTIVE)</option>
              <option value="TRIAL">آزمایشی (TRIAL)</option>
              <option value="PAST_DUE">معوق (PAST_DUE)</option>
              <option value="CANCELLED">لغوشده (CANCELLED)</option>
            </select>
          </div>
          {editingSub ? (
            <div>
              <label className="mb-1 block text-xs text-slate-500">افزودن روز به تاریخ انقضا (تمدید)</label>
              <input
                type="number"
                min={0}
                value={subForm.extend_days}
                onChange={(e) => setSubForm({ ...subForm, extend_days: Number(e.target.value) })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-sm"
              />
            </div>
          ) : (
            <div>
              <label className="mb-1 block text-xs text-slate-500">مدت اعتبار اولیه (روز)</label>
              <input
                type="number"
                min={1}
                value={subForm.duration_days}
                onChange={(e) => setSubForm({ ...subForm, duration_days: Number(e.target.value) })}
                className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 font-mono text-sm"
              />
            </div>
          )}
          <button
            type="submit"
            disabled={saveSubMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white"
          >
            {editingSub ? "ذخیره و اعمال تمدید اشتراک" : "ثبت اشتراک برای آژانس"}
          </button>
        </form>
      </ModalDrawer>
    </div>
  );
}

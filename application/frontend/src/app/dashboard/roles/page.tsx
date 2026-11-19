// Path: frontend/src/app/dashboard/roles/page.tsx

"use client";

import React, { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Save, Shield } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { AgencyAccessPolicy, PermissionItem, RoleItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, LoadingState, SuccessBanner } from "@/components/ui/StateNotice";

interface PolicyFieldMeta {
  key: keyof Omit<AgencyAccessPolicy, "id" | "agency_id">;
  label: string;
  description: string;
  options: { value: string; label: string }[];
}

const SCOPE_OPTIONS = [
  { value: "ALL_AGENCY", label: "تمام اعضای آژانس" },
  { value: "BRANCH_ONLY", label: "فقط هم‌شعبه" },
  { value: "OWN_AND_SHARED", label: "ملک/مشتری خود و اشتراک‌گذاشته‌شده" },
  { value: "OWN_ONLY", label: "فقط موارد اختصاصی خود مشاور" },
];

const VISIBILITY_OPTIONS = [
  { value: "ALL_WITH_VIEW", label: "هر کاربر دارای مجوز مشاهده" },
  { value: "ONLY_OWNER_AGENT_AND_MANAGERS", label: "فقط مشاور مسئول و مدیران آژانس" },
  { value: "NONE", label: "مخفی برای مشاوران (فقط مدیریت)" },
];

const POLICY_FIELDS: PolicyFieldMeta[] = [
  {
    key: "property_view_scope",
    label: "۱. دامنه مشاهده املاک",
    description: "مشاوران به کدام فایل‌های ملکی آژانس دسترسی خواندن داشته باشند.",
    options: SCOPE_OPTIONS,
  },
  {
    key: "property_edit_scope",
    label: "۲. دامنه ویرایش املاک",
    description: "چه کسانی مجاز به ویرایش مشخصات املاک ثبت‌شده هستند.",
    options: SCOPE_OPTIONS,
  },
  {
    key: "customer_view_scope",
    label: "۳. دامنه مشاهده مشتریان",
    description: "محدوده دسترسی مشاوران به لیست متقاضیان و مشتریان آژانس.",
    options: SCOPE_OPTIONS,
  },
  {
    key: "customer_edit_scope",
    label: "۴. دامنه ویرایش مشتریان",
    description: "چه کسانی مجاز به ویرایش پرونده مشتریان هستند.",
    options: SCOPE_OPTIONS,
  },
  {
    key: "owner_pii_visibility",
    label: "۵. نمایش اطلاعات تماس مالکین (Owner PII)",
    description: "کنترل محرمانگی شماره تماس و مشخصات مالک ملک.",
    options: VISIBILITY_OPTIONS,
  },
  {
    key: "negotiation_visibility",
    label: "۶. سطح مشاهده مذاکرات و قیمت‌های پیشنهادی",
    description: "محدوده نمایش تاریخچه پیشنهادهای خرید و اجاره.",
    options: VISIBILITY_OPTIONS,
  },
  {
    key: "contract_visibility",
    label: "۷. سطح مشاهده قراردادها",
    description: "دسترسی به مفاد قراردادها و کدهای رهگیری داخلی.",
    options: VISIBILITY_OPTIONS,
  },
  {
    key: "financial_visibility",
    label: "۸. دسترسی به اطلاعات مالی و حسابداری",
    description: "مشاهده اسناد حسابداری، خزانه‌داری و گردش مالی معاملات.",
    options: [
      { value: "ONLY_OWNER_AGENT_AND_MANAGERS", label: "مدیران و حسابدار آژانس" },
      { value: "ALL_WITH_VIEW", label: "کاربران دارای مجوز مالی" },
      { value: "NONE", label: "محدود به مدیر آژانس" },
    ],
  },
  {
    key: "commission_visibility",
    label: "۹. سطح مشاهده کمیسیون‌ها",
    description: "نحوه نمایش جزئیات درصد و مبالغ کمیسیون معاملات.",
    options: [
      { value: "OWN_ONLY_WITH_TEAM_TOTAL", label: "سهم شخصی مشاور + جمع تیم" },
      { value: "ONLY_OWNER_AGENT_AND_MANAGERS", label: "مشاور معامله و مدیران" },
      { value: "ALL_WITH_VIEW", label: "تمام کاربران دارای مجوز" },
    ],
  },
  {
    key: "agent_performance_visibility",
    label: "۱۰. نمایش آمار عملکرد و رتبه‌بندی مشاوران",
    description: "سیاست نمایش شاخص‌های فروش و جدول رتبه‌بندی.",
    options: [
      { value: "AGGREGATED_ONLY", label: "آمار تجمیعی و کلی" },
      { value: "OWN_ONLY", label: "فقط عملکرد شخصی" },
      { value: "ALL_AGENCY", label: "نمایش کامل برای همه اعضای آژانس" },
    ],
  },
];

export default function RolesAndPolicyPage() {
  const { accessToken, activeAgencyId, effectiveRole } = useAuth();
  const qc = useQueryClient();
  const [policyState, setPolicyState] = useState<Partial<AgencyAccessPolicy>>({});
  const [roleModal, setRoleModal] = useState(false);
  const [roleForm, setRoleForm] = useState({ code: "", name: "", permission_codes: [] as string[] });
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const canManage = ["SUPER_ADMIN", "AGENCY_MANAGER"].includes(effectiveRole);

  const policyQ = useQuery({
    queryKey: ["agency-access-policy", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<AgencyAccessPolicy>(`/api/v1/agencies/${activeAgencyId}/access-policy`, {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const rolesQ = useQuery({
    queryKey: ["team-roles", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<{ roles: RoleItem[]; permissions: PermissionItem[] }>("/api/v1/team/roles", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  useEffect(() => {
    if (policyQ.data) setPolicyState(policyQ.data);
  }, [policyQ.data]);

  const savePolicyMut = useMutation({
    mutationFn: async () =>
      apiFetch(`/api/v1/agencies/${activeAgencyId}/access-policy`, {
        method: "PATCH",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          property_view_scope: policyState.property_view_scope,
          property_edit_scope: policyState.property_edit_scope,
          customer_view_scope: policyState.customer_view_scope,
          customer_edit_scope: policyState.customer_edit_scope,
          owner_pii_visibility: policyState.owner_pii_visibility,
          negotiation_visibility: policyState.negotiation_visibility,
          contract_visibility: policyState.contract_visibility,
          financial_visibility: policyState.financial_visibility,
          commission_visibility: policyState.commission_visibility,
          agent_performance_visibility: policyState.agent_performance_visibility,
        }),
      }),
    onSuccess: () => {
      setErrMsg(null);
      setNotice("سیاست‌های ۱۰گانه دسترسی آژانس با موفقیت ذخیره و در سطح سرویس‌ها اعمال شد.");
      qc.invalidateQueries({ queryKey: ["agency-access-policy"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const createRoleMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/team/roles", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify(roleForm),
      }),
    onSuccess: () => {
      setRoleModal(false);
      setRoleForm({ code: "", name: "", permission_codes: [] });
      setErrMsg(null);
      setNotice("نقش سفارشی جدید تعریف شد.");
      qc.invalidateQueries({ queryKey: ["team-roles"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="نقش‌ها و سیاست‌های دسترسی (۱۰گانه)"
        subtitle="تنظیم دقیق سطح محرمانگی اطلاعات مالکین، مشتریان، مذاکرات، قراردادها و مدیریت نقش‌های RBAC"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "نقش‌ها و سیاست‌های دسترسی" }]}
        actions={
          canManage ? (
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={savePolicyMut.isPending}
                onClick={() => savePolicyMut.mutate()}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
              >
                <Save className="h-4 w-4" />
                ذخیره سیاست‌های دسترسی
              </button>
              <button
                type="button"
                onClick={() => setRoleModal(true)}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3.5 text-xs font-semibold text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                <Plus className="h-4 w-4" />
                تعریف نقش سفارشی
              </button>
            </div>
          ) : null
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      {policyQ.isLoading ? (
        <LoadingState />
      ) : policyQ.error instanceof Error ? (
        <ErrorState message={policyQ.error.message} onRetry={() => policyQ.refetch()} />
      ) : (
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
          <div className="mb-4 flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
            <Shield className="h-5 w-5 text-teal-700 dark:text-teal-400" />
            <div>
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">ماتریس سیاست‌های ۱۰گانه آژانس (AgencyAccessPolicy)</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">این تنظیمات مستقیماً بر تمام استعلام‌ها و لایه FastAPI/Django اعمال می‌شوند.</p>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {POLICY_FIELDS.map((field) => (
              <div key={field.key} className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 p-4 space-y-2">
                <div>
                  <label className="block text-xs font-bold text-slate-900 dark:text-slate-100">{field.label}</label>
                  <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">{field.description}</p>
                </div>
                <select
                  disabled={!canManage}
                  value={(policyState[field.key] as string) || ""}
                  onChange={(e) => setPolicyState({ ...policyState, [field.key]: e.target.value })}
                  className="h-9 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-xs font-medium text-slate-800 dark:text-slate-200"
                >
                  {field.options.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label} ({opt.value})
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4">
        <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">نقش‌های تعریف‌شده در آژانس</h2>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {(rolesQ.data?.roles || []).map((r) => (
            <div key={r.id} className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm text-slate-900 dark:text-slate-100">{r.name}</span>
                <span className="font-mono text-xs text-slate-500 dark:text-slate-400">{r.code}</span>
              </div>
              <div className="text-xs text-slate-600 dark:text-slate-400">
                تعداد مجوزها: <span className="font-semibold tabular-nums">{r.permissions.length}</span> مجوز
                {r.is_system_role ? " (نقش سیستمی)" : " (نقش سفارشی)"}
              </div>
            </div>
          ))}
        </div>
      </div>

      <ModalDrawer open={roleModal} onClose={() => setRoleModal(false)} title="تعریف نقش سفارشی جدید" widthClass="max-w-2xl">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createRoleMut.mutate();
          }}
          className="space-y-4"
        >
          <div className="grid grid-cols-2 gap-3">
            <input
              required
              placeholder="کد انگلیسی نقش (مثال: SENIOR_AGENT)"
              value={roleForm.code}
              onChange={(e) => setRoleForm({ ...roleForm, code: e.target.value.toUpperCase() })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 px-3 font-mono text-sm"
            />
            <input
              required
              placeholder="نام فارسی نقش (مثال: مشاور ارشد)"
              value={roleForm.name}
              onChange={(e) => setRoleForm({ ...roleForm, name: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm"
            />
          </div>

          <div className="space-y-2">
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300">انتخاب مجوزهای نقش</label>
            <div className="max-h-60 overflow-y-auto rounded-lg border border-slate-200 dark:border-slate-800 p-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
              {(rolesQ.data?.permissions || []).map((p) => {
                const checked = roleForm.permission_codes.includes(p.code);
                return (
                  <label key={p.code} className="flex items-start gap-2 text-xs text-slate-700 dark:text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={(e) => {
                        const next = e.target.checked
                          ? [...roleForm.permission_codes, p.code]
                          : roleForm.permission_codes.filter((c) => c !== p.code);
                        setRoleForm({ ...roleForm, permission_codes: next });
                      }}
                      className="mt-0.5 accent-teal-700"
                    />
                    <span>
                      <span className="font-mono text-[11px] font-semibold">{p.code}</span>
                      <span className="block text-[11px] text-slate-500 dark:text-slate-400">{p.description}</span>
                    </span>
                  </label>
                );
              })}
            </div>
          </div>

          <button type="submit" className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white">
            ثبت نقش سفارشی
          </button>
        </form>
      </ModalDrawer>
    </div>
  );
}

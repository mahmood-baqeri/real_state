"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, ShieldAlert } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { BranchItem, PermissionItem, RoleItem, TeamMemberItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { StatusText } from "@/components/ui/StatusText";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";

export default function TeamMembersPage() {
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();
  const [inviteOpen, setInviteOpen] = useState(false);
  const [overrideTarget, setOverrideTarget] = useState<TeamMemberItem | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const [form, setForm] = useState({
    phone_number: "",
    first_name: "",
    last_name: "",
    role_code: "REAL_ESTATE_AGENT",
    branch_id: "",
    password: "",
  });

  const [overridesMap, setOverridesMap] = useState<Record<string, "ALLOW" | "DENY" | "INHERIT">>({});

  const membersQ = useQuery({
    queryKey: ["team-members", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<TeamMemberItem[]>("/api/v1/team/members", {
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

  const branchesQ = useQuery({
    queryKey: ["team-branches", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<BranchItem[]>(`/api/v1/agencies/${activeAgencyId}/branches`, {
        token: accessToken,
      })).data,
  });

  const addMemberMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/team/members", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          ...form,
          branch_id: form.branch_id || null,
          password: form.password || null,
        }),
      }),
    onSuccess: () => {
      setInviteOpen(false);
      setForm({
        phone_number: "",
        first_name: "",
        last_name: "",
        role_code: "REAL_ESTATE_AGENT",
        branch_id: "",
        password: "",
      });
      setNotice("عضو جدید به تیم آژانس اضافه شد.");
      qc.invalidateQueries({ queryKey: ["team-members", activeAgencyId] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const patchMemberMut = useMutation({
    mutationFn: async ({ id, status, role_code }: { id: string; status?: string; role_code?: string }) =>
      apiFetch(`/api/v1/team/members/${id}`, {
        method: "PATCH",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ status, role_code }),
      }),
    onSuccess: () => {
      setNotice("نقش یا وضعیت عضو به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["team-members", activeAgencyId] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const saveOverridesMut = useMutation({
    mutationFn: async () => {
      if (!overrideTarget) return;
      const overrides = Object.entries(overridesMap)
        .filter(([, eff]) => eff !== "INHERIT")
        .map(([permission_code, effect]) => ({ permission_code, effect }));
      return apiFetch(`/api/v1/team/members/${overrideTarget.id}/overrides`, {
        method: "PUT",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({ overrides }),
      });
    },
    onSuccess: () => {
      setOverrideTarget(null);
      setNotice("مجوزهای استثنای فردی با موفقیت ذخیره شد.");
      qc.invalidateQueries({ queryKey: ["team-members", activeAgencyId] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const openOverrides = (m: TeamMemberItem) => {
    const nextMap: Record<string, "ALLOW" | "DENY" | "INHERIT"> = {};
    for (const ov of m.overrides || []) {
      nextMap[ov.permission_code] = ov.effect as "ALLOW" | "DENY";
    }
    setOverridesMap(nextMap);
    setOverrideTarget(m);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="مدیریت اعضای تیم آژانس"
        subtitle="افزودن مشاوران و حسابداران، تخصیص شعبه و مدیریت استثناهای مجوز فردی"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "تیم آژانس" }]}
        actions={
          <button
            type="button"
            onClick={() => setInviteOpen(true)}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
          >
            <Plus className="h-4 w-4" />
            افزودن عضو جدید
          </button>
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      <DataTable
        rows={membersQ.data || []}
        rowKey={(m) => m.id}
        isLoading={membersQ.isLoading}
        error={membersQ.error instanceof Error ? membersQ.error.message : null}
        onRetry={() => membersQ.refetch()}
        searchPlaceholder="جستجو در نام، موبایل یا نقش..."
        columns={[
          { key: "name", header: "نام کامل", render: (m) => <span className="font-semibold">{m.full_name}</span> },
          { key: "phone", header: "موبایل", render: (m) => <span className="font-mono text-xs">{m.phone_number}</span> },
          {
            key: "role",
            header: "نقش",
            render: (m) => (
              <select
                value={m.role_code}
                onChange={(e) => patchMemberMut.mutate({ id: m.id, role_code: e.target.value })}
                className="h-8 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 text-xs font-medium"
              >
                {(rolesQ.data?.roles || []).map((r) => (
                  <option key={r.code} value={r.code}>
                    {r.name}
                  </option>
                ))}
              </select>
            ),
          },
          { key: "branch", header: "شعبه", render: (m) => m.branch_name || "—" },
          { key: "status", header: "وضعیت", render: (m) => <StatusText status={m.status} /> },
          {
            key: "actions",
            header: "مجوز و وضعیت",
            render: (m) => (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => openOverrides(m)}
                  className="inline-flex items-center gap-1 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2.5 py-1 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  <ShieldAlert className="h-3.5 w-3.5 text-amber-700" />
                  استثنای دسترسی ({m.overrides?.length || 0})
                </button>
                <button
                  type="button"
                  onClick={() =>
                    patchMemberMut.mutate({
                      id: m.id,
                      status: m.status === "ACTIVE" ? "SUSPENDED" : "ACTIVE",
                    })
                  }
                  className="rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2.5 py-1 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  {m.status === "ACTIVE" ? "تعلیق" : "فعال"}
                </button>
              </div>
            ),
          },
        ]}
      />

      <ModalDrawer open={inviteOpen} onClose={() => setInviteOpen(false)} title="افزودن عضو جدید به آژانس">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            addMemberMut.mutate();
          }}
          className="space-y-3"
        >
          <div className="grid grid-cols-2 gap-3">
            <input
              required
              placeholder="نام"
              value={form.first_name}
              onChange={(e) => setForm({ ...form, first_name: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm"
            />
            <input
              required
              placeholder="نام خانوادگی"
              value={form.last_name}
              onChange={(e) => setForm({ ...form, last_name: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-sm"
            />
          </div>
          <input
            required
            dir="ltr"
            placeholder="0912..."
            value={form.phone_number}
            onChange={(e) => setForm({ ...form, phone_number: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-left font-mono text-sm"
          />
          <input
            type="password"
            dir="ltr"
            placeholder="رمز عبور اولیه (اختیاری)"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 text-left font-mono text-sm"
          />
          <select
            value={form.role_code}
            onChange={(e) => setForm({ ...form, role_code: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
          >
            {(rolesQ.data?.roles || []).map((r) => (
              <option key={r.code} value={r.code}>
                {r.name}
              </option>
            ))}
          </select>
          <select
            value={form.branch_id}
            onChange={(e) => setForm({ ...form, branch_id: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm"
          >
            <option value="">بدون شعبه خاص</option>
            {(branchesQ.data || []).map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
          <button
            type="submit"
            disabled={addMemberMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white"
          >
            ثبت عضو در آژانس
          </button>
        </form>
      </ModalDrawer>

      <ModalDrawer
        open={!!overrideTarget}
        onClose={() => setOverrideTarget(null)}
        title={`استثنای مجوزهای فردی — ${overrideTarget?.full_name || ""}`}
        subtitle="این تنظیمات بر مجوز نقش اصلی کاربر اولویت دارد"
      >
        <div className="space-y-2.5">
          {(rolesQ.data?.permissions || []).map((p) => {
            const val = overridesMap[p.code] || "INHERIT";
            return (
              <div
                key={p.code}
                className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 dark:border-slate-800 px-3 py-2"
              >
                <div>
                  <div className="text-xs font-semibold text-slate-900 dark:text-slate-100">{p.description}</div>
                  <div className="font-mono text-[11px] text-slate-400">{p.code}</div>
                </div>
                <select
                  value={val}
                  onChange={(e) =>
                    setOverridesMap({
                      ...overridesMap,
                      [p.code]: e.target.value as "ALLOW" | "DENY" | "INHERIT",
                    })
                  }
                  className="h-8 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 text-xs"
                >
                  <option value="INHERIT">پیروی از نقش</option>
                  <option value="ALLOW">مجاز (ALLOW)</option>
                  <option value="DENY">ممنوع (DENY)</option>
                </select>
              </div>
            );
          })}
          <button
            type="button"
            onClick={() => saveOverridesMut.mutate()}
            disabled={saveOverridesMut.isPending}
            className="mt-4 h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white"
          >
            ذخیره مجوزهای فردی
          </button>
        </div>
      </ModalDrawer>
    </div>
  );
}

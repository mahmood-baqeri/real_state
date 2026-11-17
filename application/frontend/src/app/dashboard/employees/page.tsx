"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Sliders } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { EmployeeItem, TeamMemberItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";

export default function EmployeesHrPage() {
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();
  const [empModal, setEmpModal] = useState(false);
  const [planTarget, setPlanTarget] = useState<EmployeeItem | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const [empForm, setEmpForm] = useState({
    membership_id: "",
    employee_code: "",
    job_title: "مشاور ارشد املاک",
    employment_type: "FIXED_PLUS_COMMISSION",
    monthly_sales_target: "1000000000",
    base_salary: "15000000",
    commission_multiplier: "1.0000",
  });

  const [planForm, setPlanForm] = useState({
    model_type: "FIXED_PLUS_COMMISSION",
    base_salary: "18000000",
    commission_multiplier: "1.0000",
  });

  const employeesQ = useQuery({
    queryKey: ["employees", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<EmployeeItem[]>("/api/v1/employees", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const membersQ = useQuery({
    queryKey: ["team-members", activeAgencyId],
    enabled: !!accessToken && !!activeAgencyId,
    queryFn: async () =>
      (await apiFetch<TeamMemberItem[]>("/api/v1/team/members", {
        token: accessToken,
        agencyId: activeAgencyId,
      })).data,
  });

  const createEmpMut = useMutation({
    mutationFn: async () =>
      apiFetch("/api/v1/employees", {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify(empForm),
      }),
    onSuccess: () => {
      setEmpModal(false);
      setNotice("پرونده پرسنلی و طرح جبران خدمت با موفقیت ثبت شد.");
      qc.invalidateQueries({ queryKey: ["employees", activeAgencyId] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const createPlanMut = useMutation({
    mutationFn: async () => {
      if (!planTarget) return;
      return apiFetch(`/api/v1/employees/${planTarget.id}/compensation-plans`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify(planForm),
      });
    },
    onSuccess: () => {
      setPlanTarget(null);
      setNotice("طرح جدید حقوق و ضریب پورسانت اعمال شد.");
      qc.invalidateQueries({ queryKey: ["employees", activeAgencyId] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="کارکنان و طرح‌های جبران خدمت (HR)"
        subtitle="پرونده‌های پرسنلی، حقوق پایه، تارگت فروش ماهانه و ضریب پورسانت"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "کارکنان و جبران خدمت" }]}
        actions={
          <button
            type="button"
            onClick={() => setEmpModal(true)}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
          >
            <Plus className="h-4 w-4" />
            تشکیل پرونده پرسنلی
          </button>
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      <DataTable
        rows={employeesQ.data || []}
        rowKey={(e) => e.id}
        isLoading={employeesQ.isLoading}
        error={employeesQ.error instanceof Error ? employeesQ.error.message : null}
        searchPlaceholder="جستجو در کد پرسنلی یا نام..."
        columns={[
          { key: "code", header: "کد پرسنلی", render: (e) => <span className="font-mono text-xs">{e.employee_code}</span> },
          { key: "name", header: "نام و سمت", render: (e) => <div><div className="font-semibold">{e.full_name}</div><div className="text-xs text-slate-500">{e.job_title}</div></div> },
          { key: "hire", header: "تاریخ استخدام", render: (e) => <DateDisplay value={e.hire_date} /> },
          {
            key: "salary",
            header: "حقوق پایه فعال",
            render: (e) => {
              const active = e.compensation_plans.find((p) => p.is_active) || e.compensation_plans[0];
              return active ? <MoneyDisplay amount={active.base_salary} /> : "—";
            },
          },
          {
            key: "mult",
            header: "ضریب پورسانت",
            render: (e) => {
              const active = e.compensation_plans.find((p) => p.is_active) || e.compensation_plans[0];
              return active ? <span className="tabular-nums font-mono">{active.commission_multiplier}x</span> : "—";
            },
          },
          { key: "target", header: "تارگت ماهانه", render: (e) => <MoneyDisplay amount={e.monthly_sales_target} /> },
          {
            key: "act",
            header: "عملیات",
            render: (e) => (
              <button
                type="button"
                onClick={() => setPlanTarget(e)}
                className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                <Sliders className="h-3.5 w-3.5" />
                تغییر طرح حقوق
              </button>
            ),
          },
        ]}
      />

      <ModalDrawer open={empModal} onClose={() => setEmpModal(false)} title="تشکیل پرونده پرسنلی جدید">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createEmpMut.mutate();
          }}
          className="space-y-3"
        >
          <select
            required
            value={empForm.membership_id}
            onChange={(e) => setEmpForm({ ...empForm, membership_id: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"
          >
            <option value="">انتخاب عضو آژانس...</option>
            {(membersQ.data || []).map((m) => (
              <option key={m.id} value={m.id}>
                {m.full_name} ({m.role_name})
              </option>
            ))}
          </select>
          <input
            required
            placeholder="کد پرسنلی (مثال: EMP-105)"
            value={empForm.employee_code}
            onChange={(e) => setEmpForm({ ...empForm, employee_code: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 font-mono text-sm"
          />
          <input
            required
            placeholder="عنوان شغلی"
            value={empForm.job_title}
            onChange={(e) => setEmpForm({ ...empForm, job_title: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
          />
          <div className="grid grid-cols-2 gap-3">
            <input
              type="number"
              placeholder="حقوق پایه (تومان)"
              value={empForm.base_salary}
              onChange={(e) => setEmpForm({ ...empForm, base_salary: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 px-3 text-sm tabular-nums"
            />
            <input
              type="number"
              step="0.05"
              placeholder="ضریب پورسانت"
              value={empForm.commission_multiplier}
              onChange={(e) => setEmpForm({ ...empForm, commission_multiplier: e.target.value })}
              className="h-10 rounded-lg border border-slate-300 px-3 text-sm tabular-nums"
            />
          </div>
          <button
            type="submit"
            disabled={createEmpMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white"
          >
            ذخیره پرونده پرسنلی
          </button>
        </form>
      </ModalDrawer>

      <ModalDrawer
        open={!!planTarget}
        onClose={() => setPlanTarget(null)}
        title={`به‌روزرسانی طرح جبران خدمت — ${planTarget?.full_name || ""}`}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createPlanMut.mutate();
          }}
          className="space-y-3"
        >
          <select
            value={planForm.model_type}
            onChange={(e) => setPlanForm({ ...planForm, model_type: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"
          >
            <option value="FIXED_SALARY">حقوق ثابت</option>
            <option value="COMMISSION_ONLY">فقط پورسانتی</option>
            <option value="FIXED_PLUS_COMMISSION">ثابت + پورسانتی</option>
          </select>
          <input
            type="number"
            placeholder="حقوق پایه جدید (تومان)"
            value={planForm.base_salary}
            onChange={(e) => setPlanForm({ ...planForm, base_salary: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm tabular-nums"
          />
          <input
            type="number"
            step="0.05"
            placeholder="ضریب پورسانت"
            value={planForm.commission_multiplier}
            onChange={(e) => setPlanForm({ ...planForm, commission_multiplier: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm tabular-nums"
          />
          <button
            type="submit"
            disabled={createPlanMut.isPending}
            className="h-10 w-full rounded-lg bg-teal-700 text-sm font-semibold text-white"
          >
            اعمال طرح جدید
          </button>
        </form>
      </ModalDrawer>
    </div>
  );
}

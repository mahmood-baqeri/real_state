// Path: frontend/src/app/dashboard/properties/page.tsx

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Edit3, ExternalLink, Plus, Trash2 } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { formatArea } from "@/lib/formatters";
import type { PropertyItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { StatusText } from "@/components/ui/StatusText";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";

export default function DashboardPropertiesPage() {
  const { accessToken, activeAgencyId, hasPermission, effectiveRole } = useAuth();
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const propsQ = useQuery({
    queryKey: ["agency-properties", activeAgencyId, statusFilter],
    enabled: !!accessToken,
    queryFn: async () => {
      const q = statusFilter ? `?status=${statusFilter}&page_size=50` : "?page_size=50";
      return (
        await apiFetch<PropertyItem[]>(`/api/v1/properties${q}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data;
    },
  });

  const actionMut = useMutation({
    mutationFn: async ({ id, action }: { id: string; action: "submit" | "publish" | "delete" }) => {
      if (action === "delete") {
        return apiFetch(`/api/v1/properties/${id}`, {
          method: "DELETE",
          token: accessToken,
          agencyId: activeAgencyId,
        });
      }
      return apiFetch(`/api/v1/properties/${id}/${action}`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
      });
    },
    onSuccess: () => {
      setNotice("عملیات روی ملک با موفقیت انجام شد.");
      qc.invalidateQueries({ queryKey: ["agency-properties"] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const canPublish = effectiveRole === "SUPER_ADMIN" || effectiveRole === "AGENCY_MANAGER" || hasPermission("property.publish");

  return (
    <div className="space-y-6">
      <PageHeader
        title="مدیریت فایل‌های املاک"
        subtitle="فهرست فایل‌های داخلی و منتشرشده، تغییر وضعیت چرخه تایید و دسترسی به مشخصات مالک"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "فهرست املاک" }]}
        actions={
          <Link
            href="/dashboard/properties/new"
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800"
          >
            <Plus className="h-4 w-4" />
            ثبت ملک جدید
          </Link>
        }
      />

      {notice && <SuccessBanner message={notice} />}
      {errMsg && <ErrorState message={errMsg} />}

      <DataTable
        rows={propsQ.data || []}
        rowKey={(p) => p.id}
        isLoading={propsQ.isLoading}
        error={propsQ.error instanceof Error ? propsQ.error.message : null}
        onRetry={() => propsQ.refetch()}
        exportFileName="bonyan-properties"
        selectable
        bulkActions={(selectedRows, clearSelection) =>
          canPublish ? (
            <button
              type="button"
              onClick={async () => {
                for (const row of selectedRows) {
                  if (row.status !== "PUBLISHED") {
                    await actionMut.mutateAsync({ id: row.id, action: "publish" });
                  }
                }
                clearSelection();
              }}
              className="rounded-lg bg-teal-700 px-3 py-1.5 font-semibold text-white hover:bg-teal-800"
            >
              انتشار گروهی فایل‌های انتخابی
            </button>
          ) : null
        }
        searchPlaceholder="جستجو در کد ملک، عنوان یا منطقه..."
        activeFilter={statusFilter}
        onFilterChange={setStatusFilter}
        filterTabs={[
          { value: "", label: "همه وضعیت‌ها" },
          { value: "DRAFT", label: "پیش‌نویس" },
          { value: "PENDING_APPROVAL", label: "در انتظار تأیید" },
          { value: "PUBLISHED", label: "منتشرشده" },
          { value: "SOLD", label: "فروخته‌شده" },
        ]}
        emptyTitle="ملکی ثبت نشده است"
        emptyDescription="برای شروع مدیریت فایل‌ها، اولین ملک آژانس را ثبت کنید."
        emptyAction={
          <Link
            href="/dashboard/properties/new"
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white"
          >
            ثبت ملک جدید
          </Link>
        }
        columns={[
          {
            key: "code",
            header: "کد ملک",
            sortValue: (p) => p.property_code,
            render: (p) => <span className="font-mono text-xs font-semibold">{p.property_code}</span>,
          },
          {
            key: "title",
            header: "عنوان و موقعیت",
            sortValue: (p) => p.title,
            render: (p) => (
              <div>
                <Link
                  href={`/dashboard/properties/${p.id}`}
                  className="font-semibold text-slate-900 hover:text-teal-700 dark:text-slate-100 dark:hover:text-teal-400"
                >
                  {p.title}
                </Link>
                <div className="text-xs text-slate-500 dark:text-slate-400">
                  {p.location?.city || "—"} {p.location?.district ? `— ${p.location.district}` : ""}
                </div>
              </div>
            ),
          },
          {
            key: "type",
            header: "نوع / معامله",
            render: (p) => (
              <div className="text-xs">
                <div className="font-medium">{p.property_type.name_fa}</div>
                <div className="text-slate-500 dark:text-slate-400">{p.deal_type.name_fa}</div>
              </div>
            ),
          },
          {
            key: "area",
            header: "متراژ",
            sortValue: (p) => Number(p.built_area_sqm),
            render: (p) => <span className="tabular-nums text-xs">{formatArea(p.built_area_sqm)}</span>,
          },
          {
            key: "price",
            header: "قیمت / ودیعه",
            sortValue: (p) => Number(p.total_price || p.deposit_amount),
            render: (p) =>
              p.deal_type.is_rental ? (
                <div className="text-xs">
                  <MoneyDisplay amount={p.deposit_amount} sourceCurrency={p.currency} />
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">
                    اجاره: <MoneyDisplay amount={p.rent_amount} sourceCurrency={p.currency} />
                  </div>
                </div>
              ) : (
                <MoneyDisplay amount={p.total_price} sourceCurrency={p.currency} className="font-semibold text-xs" />
              ),
          },
          {
            key: "status",
            header: "وضعیت",
            render: (p) => <StatusText status={p.status} />,
          },
          {
            key: "actions",
            header: "عملیات",
            render: (p) => (
              <div className="flex flex-wrap items-center gap-1.5">
                <Link
                  href={`/dashboard/properties/${p.id}/edit`}
                  className="inline-flex h-7 items-center gap-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  <Edit3 className="h-3 w-3" />
                  ویرایش
                </Link>
                {p.status === "DRAFT" && (
                  <button
                    type="button"
                    onClick={() => actionMut.mutate({ id: p.id, action: "submit" })}
                    className="h-7 rounded bg-amber-600 px-2 text-xs font-semibold text-white hover:bg-amber-700"
                  >
                    ارسال برای تأیید
                  </button>
                )}
                {p.status !== "PUBLISHED" && canPublish && (
                  <button
                    type="button"
                    onClick={() => actionMut.mutate({ id: p.id, action: "publish" })}
                    className="h-7 rounded bg-teal-700 px-2 text-xs font-semibold text-white hover:bg-teal-800"
                  >
                    انتشار
                  </button>
                )}
                <Link
                  href={`/properties/${p.id}`}
                  className="inline-flex h-7 items-center justify-center rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 px-2 text-slate-600 dark:text-slate-400 hover:text-teal-700"
                  title="نمای عمومی"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                </Link>
                <button
                  type="button"
                  onClick={() => actionMut.mutate({ id: p.id, action: "delete" })}
                  className="inline-flex h-7 items-center justify-center rounded border border-rose-200 bg-rose-50 px-2 text-rose-700 hover:bg-rose-100"
                  title="حذف"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ),
          },
        ]}
      />
    </div>
  );
}

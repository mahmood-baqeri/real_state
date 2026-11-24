"use client";
import { confirmDialog } from "@/lib/confirm-dialog";

import React, { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, Edit3, ExternalLink, EyeOff, Plus, Trash2, XCircle } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { formatArea } from "@/lib/formatters";
import type { PropertyItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { StatusText } from "@/components/ui/StatusText";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { SavedViewsBar } from "@/components/ui/SavedViewsBar";
import { ImportExportDialog } from "@/components/ui/ImportExportDialog";
import { ModalDrawer } from "@/components/ui/ModalDrawer";
import { ErrorState, SuccessBanner } from "@/components/ui/StateNotice";

export default function DashboardPropertiesPage() {
  const { accessToken, activeAgencyId, hasPermission, effectiveRole } = useAuth();
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);
  const [rejectTarget, setRejectTarget] = useState<PropertyItem | null>(null);
  const [rejectReason, setRejectReason] = useState("");

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
    mutationFn: async ({
      id,
      agencyId,
      action,
      reason,
    }: {
      id: string;
      agencyId?: string;
      action: "submit" | "publish" | "unpublish" | "reject" | "delete";
      reason?: string;
    }) => {
      const targetAgencyId = activeAgencyId || agencyId || null;
      if (action === "delete") {
        return apiFetch(`/api/v1/properties/${id}`, {
          method: "DELETE",
          token: accessToken,
          agencyId: targetAgencyId,
        });
      }
      if (action === "unpublish") {
        return apiFetch(`/api/v1/properties/${id}/status`, {
          method: "POST",
          token: accessToken,
          agencyId: targetAgencyId,
          body: JSON.stringify({
            status: "DRAFT",
            reason: reason?.trim() || "لغو انتشار از پورتال عمومی",
          }),
        });
      }
      if (action === "reject") {
        return apiFetch(`/api/v1/properties/${id}/status`, {
          method: "POST",
          token: accessToken,
          agencyId: targetAgencyId,
          body: JSON.stringify({
            status: "REJECTED",
            reason: (reason || "").trim(),
          }),
        });
      }
      return apiFetch(`/api/v1/properties/${id}/${action}`, {
        method: "POST",
        token: accessToken,
        agencyId: targetAgencyId,
      });
    },
    onSuccess: (_, vars) => {
      setErrMsg(null);
      if (vars.action === "reject") {
        setNotice("ملک با ثبت دلیل رد شد و به آژانس بازگشت داده شد.");
        setRejectTarget(null);
        setRejectReason("");
      } else if (vars.action === "unpublish") {
        setNotice("انتشار ملک در پورتال عمومی لغو و به پیش‌نویس منتقل شد.");
      } else if (vars.action === "delete") {
        setNotice("ملک با موفقیت حذف (بایگانی) شد.");
      } else {
        setNotice("وضعیت ملک با موفقیت به‌روزرسانی شد.");
      }
      qc.invalidateQueries({ queryKey: ["agency-properties"] });
      qc.invalidateQueries({ queryKey: ["dashboard-property-detail", vars.id] });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  const canPublish =
    effectiveRole === "SUPER_ADMIN" ||
    effectiveRole === "AGENCY_MANAGER" ||
    hasPermission("property.publish");

  return (
    <div className="space-y-6">
      <PageHeader
        title="مدیریت فایل‌های املاک"
        subtitle="فهرست فایل‌های داخلی و منتشرشده، بررسی، تأیید یا رد با ثبت دلیل، لغو انتشار و مدیریت پرونده‌ها"
        breadcrumbs={[{ label: "میز کار", href: "/dashboard" }, { label: "فهرست املاک" }]}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Link href="/dashboard/property-intelligence" className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 px-3 text-xs font-semibold hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800">
              <AlertCircle className="h-4 w-4" /> هوشمندی فایل
            </Link>
            <ImportExportDialog
              module="properties"
              moduleLabel="املاک"
              onImported={() => qc.invalidateQueries({ queryKey: ["agency-properties"] })}
            />
            <Link
              href="/dashboard/properties/new"
              className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white hover:bg-teal-800 whitespace-nowrap"
            >
              <Plus className="h-4 w-4" />
              ثبت ملک جدید
            </Link>
          </div>
        }
      />

      {effectiveRole === "SUPER_ADMIN" && !activeAgencyId && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
          شما در نمای سراسری همه آژانس‌ها هستید. برای ثبت ملک جدید، ابتدا از منوی بالای صفحه آژانس مقصد را انتخاب کنید.
        </div>
      )}

      <SavedViewsBar
        module="properties"
        currentFilters={{ status: statusFilter }}
        onApply={(f) => setStatusFilter(f.status || "")}
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
                    await actionMut.mutateAsync({
                      id: row.id,
                      agencyId: row.agency_id,
                      action: "publish",
                    });
                  }
                }
                clearSelection();
              }}
              className="rounded-lg bg-teal-700 px-3 py-1.5 font-semibold text-white hover:bg-teal-800 whitespace-nowrap"
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
          { value: "REJECTED", label: "ردشده" },
          { value: "SOLD", label: "فروخته‌شده" },
        ]}
        emptyTitle="ملکی ثبت نشده است"
        emptyDescription="برای شروع مدیریت فایل‌ها، اولین ملک آژانس را ثبت کنید."
        emptyAction={
          <Link
            href="/dashboard/properties/new"
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white whitespace-nowrap"
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
              <div className="space-y-0.5">
                <Link
                  href={`/dashboard/properties/${p.id}`}
                  className="font-semibold text-slate-900 hover:text-teal-700 dark:text-slate-100 dark:hover:text-teal-400"
                >
                  {p.title}
                </Link>
                <div className="text-xs text-slate-500 dark:text-slate-400">
                  {p.location?.city || "—"} {p.location?.district ? `— ${p.location.district}` : ""}
                  {!activeAgencyId && p.agency_name ? ` · ${p.agency_name}` : ""}
                </div>
                {p.status === "REJECTED" && p.latest_rejection_reason && (
                  <div className="flex items-center gap-1 text-[11px] text-rose-700 dark:text-rose-400">
                    <AlertCircle className="h-3 w-3 shrink-0" />
                    <span className="line-clamp-1">دلیل رد: {p.latest_rejection_reason}</span>
                  </div>
                )}
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
                  href={`/dashboard/properties/${p.id}`}
                  className="inline-flex h-7 items-center gap-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 whitespace-nowrap"
                >
                  <ExternalLink className="h-3 w-3" />
                  جزئیات
                </Link>
                <Link
                  href={`/dashboard/properties/${p.id}/virtual-tour`}
                  className="inline-flex h-7 items-center gap-1 rounded border border-teal-300 bg-teal-50 px-2 text-xs font-semibold text-teal-800 hover:bg-teal-100 dark:border-teal-800 dark:bg-teal-950/40 dark:text-teal-300 whitespace-nowrap"
                >
                  تور مجازی
                </Link>
                <Link
                  href={`/dashboard/properties/${p.id}/edit`}
                  className="inline-flex h-7 items-center gap-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 whitespace-nowrap"
                >
                  <Edit3 className="h-3 w-3" />
                  ویرایش
                </Link>
                {p.status === "DRAFT" && (
                  <button
                    type="button"
                    disabled={actionMut.isPending}
                    onClick={() =>
                      actionMut.mutate({ id: p.id, agencyId: p.agency_id, action: "submit" })
                    }
                    className="h-7 rounded bg-amber-600 px-2 text-xs font-semibold text-white hover:bg-amber-700 whitespace-nowrap"
                  >
                    ارسال برای تأیید
                  </button>
                )}
                {p.status !== "PUBLISHED" && canPublish && (
                  <button
                    type="button"
                    disabled={actionMut.isPending}
                    onClick={() =>
                      actionMut.mutate({ id: p.id, agencyId: p.agency_id, action: "publish" })
                    }
                    className="inline-flex h-7 items-center gap-1 rounded bg-teal-700 px-2 text-xs font-semibold text-white hover:bg-teal-800 whitespace-nowrap"
                  >
                    <CheckCircle2 className="h-3 w-3" />
                    تأیید و انتشار
                  </button>
                )}
                {p.status === "PUBLISHED" && canPublish && (
                  <button
                    type="button"
                    disabled={actionMut.isPending}
                    onClick={() =>
                      actionMut.mutate({ id: p.id, agencyId: p.agency_id, action: "unpublish" })
                    }
                    className="inline-flex h-7 items-center gap-1 rounded border border-amber-300 bg-amber-50 px-2 text-xs font-medium text-amber-800 hover:bg-amber-100 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300 whitespace-nowrap"
                  >
                    <EyeOff className="h-3 w-3" />
                    لغو انتشار
                  </button>
                )}
                {canPublish && p.status !== "REJECTED" && (
                  <button
                    type="button"
                    onClick={() => {
                      setRejectTarget(p);
                      setRejectReason("");
                    }}
                    className="inline-flex h-7 items-center gap-1 rounded border border-rose-200 bg-rose-50 px-2 text-xs font-medium text-rose-700 hover:bg-rose-100 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-300 whitespace-nowrap"
                  >
                    <XCircle className="h-3 w-3" />
                    رد
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
                  disabled={actionMut.isPending}
                  onClick={async () => {
                    if (await confirmDialog({ title: "تأیید حذف", message: `آیا از حذف (بایگانی) ملک «${p.title}» مطمئن هستید؟`, danger: true })) {
                      actionMut.mutate({ id: p.id, agencyId: p.agency_id, action: "delete" });
                    }
                  }}
                  className="inline-flex h-7 items-center justify-center rounded border border-rose-200 bg-rose-50 px-2 text-rose-700 hover:bg-rose-100 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-300"
                  title="حذف"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ),
          },
        ]}
      />

      <ModalDrawer
        open={Boolean(rejectTarget)}
        onClose={() => {
          setRejectTarget(null);
          setRejectReason("");
        }}
        title={`رد فایل ملک ${rejectTarget?.property_code || ""}`}
        subtitle="ثبت دلیل رد برای اصلاح توسط مشاور الزامی است و در تاریخچه ملک ذخیره می‌شود."
      >
        <div className="space-y-4">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700 dark:border-slate-800 dark:bg-slate-800/60 dark:text-slate-300">
            <div className="font-bold">{rejectTarget?.title}</div>
            <div className="mt-0.5 text-slate-500">آژانس: {rejectTarget?.agency_name}</div>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-slate-700 dark:text-slate-300">
              دلیل رد ملک *
            </label>
            <textarea
              rows={4}
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="مثال: تصاویر با کیفیت پایین یا نقص مدارک احراز مالکیت..."
              className="w-full rounded-lg border border-slate-300 bg-white p-3 text-sm text-slate-900 focus:border-teal-600 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
            />
          </div>
          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => setRejectTarget(null)}
              className="h-9 rounded-lg border border-slate-300 px-4 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300"
            >
              انصراف
            </button>
            <button
              type="button"
              disabled={!rejectReason.trim() || actionMut.isPending}
              onClick={() => {
                if (!rejectTarget || !rejectReason.trim()) return;
                actionMut.mutate({
                  id: rejectTarget.id,
                  agencyId: rejectTarget.agency_id,
                  action: "reject",
                  reason: rejectReason.trim(),
                });
              }}
              className="h-9 rounded-lg bg-rose-600 px-4 text-xs font-semibold text-white hover:bg-rose-700 disabled:opacity-50"
            >
              {actionMut.isPending ? "در حال ثبت..." : "ثبت رد و ارجاع برای اصلاح"}
            </button>
          </div>
        </div>
      </ModalDrawer>
    </div>
  );
}

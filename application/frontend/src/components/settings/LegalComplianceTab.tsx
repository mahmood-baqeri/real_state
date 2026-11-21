"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertOctagon, CheckCircle2, FileText, History, RotateCcw, Save, Shield } from "lucide-react";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { formatNumberFa } from "@/lib/formatters";
import type {
  LegalAcceptanceItem,
  LegalDocumentItem,
  PropertyViolationReportItem,
  SystemSettingItem,
} from "@/lib/types";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { StatusText } from "@/components/ui/StatusText";
import { LoadingState } from "@/components/ui/StateNotice";

interface Props {
  onNotice: (msg: string) => void;
  onError: (msg: string) => void;
}

export function LegalComplianceTab({ onNotice, onError }: Props) {
  const { accessToken, activeAgencyId } = useAuth();
  const qc = useQueryClient();

  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [docForm, setDocForm] = useState({
    slug: "",
    doc_type: "LEGAL",
    title_fa: "",
    title_en: "",
    summary: "",
    body_html: "",
    status: "DRAFT",
    requires_acceptance: false,
    meta_title: "",
    meta_description: "",
    sort_order: 100,
    is_system_doc: false,
    change_note: "به‌روزرسانی سند حقوقی",
  });

  const [resNotes, setResNotes] = useState<Record<string, string>>({});

  const legalDocsQ = useQuery({
    queryKey: ["admin-legal-docs"],
    enabled: !!accessToken,
    queryFn: async () =>
      (await apiFetch<LegalDocumentItem[]>("/api/v1/cms/legal", { token: accessToken })).data,
  });

  const acceptancesQ = useQuery({
    queryKey: ["admin-legal-acceptances", selectedDocId],
    enabled: !!accessToken,
    queryFn: async () => {
      const qs = selectedDocId ? `?doc_id=${selectedDocId}` : "";
      return (
        await apiFetch<LegalAcceptanceItem[]>(`/api/v1/cms/legal/acceptances${qs}`, {
          token: accessToken,
        })
      ).data;
    },
  });

  const legalSettingsQ = useQuery({
    queryKey: ["legal-registry-settings", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<SystemSettingItem[]>("/api/v1/settings/registry?category=LEGAL", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const violationsQ = useQuery({
    queryKey: ["admin-property-violations", activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<PropertyViolationReportItem[]>("/api/v1/properties/violations", {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  const selectedDoc = (legalDocsQ.data || []).find((d) => d.id === selectedDocId) || null;

  const pickDoc = (doc: LegalDocumentItem) => {
    setSelectedDocId(doc.id);
    setDocForm({
      slug: doc.slug,
      doc_type: doc.doc_type,
      title_fa: doc.title_fa,
      title_en: doc.title_en || "",
      summary: doc.summary || "",
      body_html: doc.body_html || "",
      status: doc.status,
      requires_acceptance: doc.requires_acceptance,
      meta_title: doc.meta_title || "",
      meta_description: doc.meta_description || "",
      sort_order: doc.sort_order ?? 100,
      is_system_doc: doc.is_system_doc,
      change_note: "ویرایش نسخه جدید از پنل مدیریت",
    });
  };

  const resetNewDoc = () => {
    setSelectedDocId(null);
    setDocForm({
      slug: "",
      doc_type: "LEGAL",
      title_fa: "",
      title_en: "",
      summary: "",
      body_html: "<h2>عنوان بند</h2><p>متن رسمی مقررات...</p>",
      status: "DRAFT",
      requires_acceptance: false,
      meta_title: "",
      meta_description: "",
      sort_order: 100,
      is_system_doc: false,
      change_note: "ایجاد سند جدید",
    });
  };

  const saveDocMut = useMutation({
    mutationFn: async () =>
      apiFetch<LegalDocumentItem>("/api/v1/cms/legal", {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({
          ...docForm,
          slug: docForm.slug.trim().toLowerCase(),
        }),
      }),
    onSuccess: (res) => {
      setSelectedDocId(res.data.id);
      onNotice(`سند «${res.data.title_fa}» در نسخه ${formatNumberFa(res.data.version_number)} ذخیره شد.`);
      qc.invalidateQueries({ queryKey: ["admin-legal-docs"] });
      qc.invalidateQueries({ queryKey: ["public-bootstrap"] });
      qc.invalidateQueries({ queryKey: ["public-legal-doc", res.data.slug] });
    },
    onError: (e: Error) => onError(e.message),
  });

  const transitionStatusMut = useMutation({
    mutationFn: async ({ docId, status }: { docId: string; status: string }) =>
      apiFetch<LegalDocumentItem>(`/api/v1/cms/legal/${docId}/status`, {
        method: "POST",
        token: accessToken,
        body: JSON.stringify({ status }),
      }),
    onSuccess: (res) => {
      setDocForm((f) => ({ ...f, status: res.data.status }));
      onNotice(`وضعیت سند به «${res.data.status}» تغییر یافت.`);
      qc.invalidateQueries({ queryKey: ["admin-legal-docs"] });
      qc.invalidateQueries({ queryKey: ["public-bootstrap"] });
      qc.invalidateQueries({ queryKey: ["public-legal-doc", res.data.slug] });
    },
    onError: (e: Error) => onError(e.message),
  });

  const restoreVersionMut = useMutation({
    mutationFn: async ({ docId, ver }: { docId: string; ver: number }) =>
      apiFetch<LegalDocumentItem>(`/api/v1/cms/legal/${docId}/restore/${ver}`, {
        method: "POST",
        token: accessToken,
      }),
    onSuccess: (res) => {
      pickDoc(res.data);
      onNotice("نسخه پیشین با موفقیت بازیابی و نسخه جدید ثبت شد.");
      qc.invalidateQueries({ queryKey: ["admin-legal-docs"] });
      qc.invalidateQueries({ queryKey: ["public-bootstrap"] });
    },
    onError: (e: Error) => onError(e.message),
  });

  const toggleComplianceRuleMut = useMutation({
    mutationFn: async ({ key, value }: { key: string; value: unknown }) =>
      apiFetch("/api/v1/settings/registry", {
        method: "PUT",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          updates: [{ key, value }],
          change_reason: "تغییر سیاست اجرایی انطباق و مقررات",
        }),
      }),
    onSuccess: () => {
      onNotice("قاعده اجرایی انطباق با موفقیت به‌روزرسانی شد.");
      qc.invalidateQueries({ queryKey: ["legal-registry-settings"] });
      qc.invalidateQueries({ queryKey: ["public-bootstrap"] });
    },
    onError: (e: Error) => onError(e.message),
  });

  const resolveViolationMut = useMutation({
    mutationFn: async ({
      reportId,
      resolution_status,
      suspend_listing,
    }: {
      reportId: string;
      resolution_status: string;
      suspend_listing: boolean;
    }) =>
      apiFetch(`/api/v1/properties/violations/${reportId}/resolve`, {
        method: "POST",
        token: accessToken,
        agencyId: activeAgencyId,
        body: JSON.stringify({
          resolution_status,
          resolution_note: resNotes[reportId] || "بررسی توسط تیم بازرسی پلتفرم",
          suspend_listing,
        }),
      }),
    onSuccess: () => {
      onNotice("گزارش تخلف بررسی و وضعیت آگهی مطابق تصمیم بازرسی اعمال شد.");
      qc.invalidateQueries({ queryKey: ["admin-property-violations"] });
    },
    onError: (e: Error) => onError(e.message),
  });

  return (
    <div className="space-y-6">
      {/* 1. Enforceable Legal Compliance Switches */}
      <div className="surface-card rounded-xl p-5 space-y-3">
        <div className="flex items-center gap-2 border-b border-slate-200 pb-3 dark:border-slate-800">
          <Shield className="h-5 w-5 text-teal-700 dark:text-teal-400" />
          <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
            قواعد اجرایی انطباق و حاکمیت پلتفرم (Enforceable Rules)
          </h2>
        </div>
        {legalSettingsQ.isLoading ? (
          <LoadingState />
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            {(legalSettingsQ.data || []).map((s) => (
              <div
                key={s.id}
                className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2.5 text-xs dark:border-slate-800 dark:bg-slate-800/40"
              >
                <div>
                  <div className="font-bold text-slate-900 dark:text-slate-100">{s.title_fa}</div>
                  <div className="font-mono text-[10px] text-slate-400">{s.key}</div>
                </div>
                {s.value_type === "BOOLEAN" ? (
                  <input
                    type="checkbox"
                    checked={Boolean(s.value)}
                    onChange={(e) =>
                      toggleComplianceRuleMut.mutate({ key: s.key, value: e.target.checked })
                    }
                    className="h-4 w-4 accent-teal-700"
                  />
                ) : (
                  <span className="font-mono text-xs">{String(s.value)}</span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 2. Legal Documents CMS Editor & Versioning */}
      <div className="surface-card rounded-xl p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-teal-700 dark:text-teal-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              مدیریت جامع قوانین، حریم خصوصی، شرایط استفاده و متون حقوقی
            </h2>
          </div>
          <button
            type="button"
            onClick={resetNewDoc}
            className="h-8 rounded-lg border border-slate-300 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
          >
            + ایجاد سند حقوقی جدید
          </button>
        </div>

        {legalDocsQ.isLoading ? (
          <LoadingState />
        ) : (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
            {/* Document list */}
            <div className="lg:col-span-4 space-y-1.5 max-h-[540px] overflow-y-auto">
              {(legalDocsQ.data || []).map((doc) => (
                <button
                  key={doc.id}
                  type="button"
                  onClick={() => pickDoc(doc)}
                  className={`flex w-full items-center justify-between gap-2 rounded-lg border px-3 py-2.5 text-right text-xs ${
                    selectedDocId === doc.id
                      ? "border-teal-700 bg-teal-50/70 font-bold text-teal-900 dark:border-teal-500 dark:bg-teal-950/40 dark:text-teal-200"
                      : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300"
                  }`}
                >
                  <div className="min-w-0">
                    <div className="truncate">{doc.title_fa}</div>
                    <div className="font-mono text-[10px] text-slate-400">
                      /{doc.slug} · v{doc.version_number}
                    </div>
                  </div>
                  <StatusText status={doc.status} />
                </button>
              ))}
            </div>

            {/* Editor */}
            <div className="lg:col-span-8 space-y-4">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  saveDocMut.mutate();
                }}
                className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 space-y-3 dark:border-slate-800 dark:bg-slate-800/40"
              >
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                  <input
                    required
                    dir="ltr"
                    placeholder="Slug (مثال: privacy-policy)"
                    value={docForm.slug}
                    onChange={(e) => setDocForm({ ...docForm, slug: e.target.value })}
                    className="h-9 rounded-lg border border-slate-300 bg-white px-2.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
                  />
                  <select
                    value={docForm.doc_type}
                    onChange={(e) => setDocForm({ ...docForm, doc_type: e.target.value })}
                    className="h-9 rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
                  >
                    <option value="RULES">قوانین پلتفرم (RULES)</option>
                    <option value="PRIVACY">حریم خصوصی (PRIVACY)</option>
                    <option value="TERMS">شرایط استفاده (TERMS)</option>
                    <option value="LEGAL">سند حقوقی (LEGAL)</option>
                    <option value="POLICY">سیاست اجرایی (POLICY)</option>
                    <option value="ABOUT">معرفی پلتفرم (ABOUT)</option>
                  </select>
                  <select
                    value={docForm.status}
                    onChange={(e) => setDocForm({ ...docForm, status: e.target.value })}
                    className="h-9 rounded-lg border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
                  >
                    <option value="DRAFT">پیش‌نویس (DRAFT)</option>
                    <option value="REVIEW">در حال بررسی (REVIEW)</option>
                    <option value="APPROVED">تأییدشده (APPROVED)</option>
                    <option value="PUBLISHED">منتشرشده (PUBLISHED)</option>
                    <option value="ARCHIVED">بایگانی (ARCHIVED)</option>
                  </select>
                </div>

                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  <input
                    required
                    placeholder="عنوان فارسی سند"
                    value={docForm.title_fa}
                    onChange={(e) => setDocForm({ ...docForm, title_fa: e.target.value })}
                    className="h-9 rounded-lg border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                  />
                  <input
                    dir="ltr"
                    placeholder="عنوان انگلیسی"
                    value={docForm.title_en}
                    onChange={(e) => setDocForm({ ...docForm, title_en: e.target.value })}
                    className="h-9 rounded-lg border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                  />
                </div>

                <textarea
                  rows={2}
                  placeholder="خلاصه سند"
                  value={docForm.summary}
                  onChange={(e) => setDocForm({ ...docForm, summary: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 bg-white p-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                />

                <textarea
                  rows={6}
                  placeholder="متن کامل HTML (تگ‌های مجاز؛ اسکریپت‌ها به‌صورت خودکار پاکسازی می‌شوند)"
                  value={docForm.body_html}
                  onChange={(e) => setDocForm({ ...docForm, body_html: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 bg-white p-2.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
                />

                <div className="flex flex-wrap items-center justify-between gap-3">
                  <label className="inline-flex items-center gap-2 text-xs">
                    <input
                      type="checkbox"
                      checked={docForm.requires_acceptance}
                      onChange={(e) =>
                        setDocForm({ ...docForm, requires_acceptance: e.target.checked })
                      }
                      className="accent-teal-700"
                    />
                    نیازمند تأیید صریح کاربر هنگام ثبت‌نام
                  </label>
                  <input
                    placeholder="شرح تغییرات این نسخه"
                    value={docForm.change_note}
                    onChange={(e) => setDocForm({ ...docForm, change_note: e.target.value })}
                    className="h-8 flex-1 min-w-[180px] rounded-lg border border-slate-300 bg-white px-2.5 text-xs dark:border-slate-700 dark:bg-slate-950"
                  />
                  <button
                    type="submit"
                    disabled={saveDocMut.isPending}
                    className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-teal-700 px-4 text-xs font-semibold text-white hover:bg-teal-800"
                  >
                    <Save className="h-3.5 w-3.5" />
                    ذخیره و ثبت نسخه
                  </button>
                </div>
              </form>

              {/* Lifecycle Transitions & Version History */}
              {selectedDoc && (
                <div className="space-y-3 rounded-xl border border-slate-200 p-4 dark:border-slate-800">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 text-xs font-bold">
                      <History className="h-4 w-4 text-teal-600" />
                      چرخه وضعیت و نسخه‌های قبلی ({selectedDoc.slug})
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {(selectedDoc.status === "PUBLISHED"
                        ? ["ARCHIVED"]
                        : ["REVIEW", "APPROVED", "PUBLISHED", "ARCHIVED"]
                      )
                        .filter((st) => st !== selectedDoc.status)
                        .map((st) => (
                          <button
                            key={st}
                            type="button"
                            onClick={() =>
                              transitionStatusMut.mutate({ docId: selectedDoc.id, status: st })
                            }
                            className="h-7 rounded border border-slate-300 bg-white px-2.5 text-[11px] font-semibold hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900"
                          >
                            تغییر به {st}
                          </button>
                        ))}
                    </div>
                  </div>

                  {selectedDoc.versions && selectedDoc.versions.length > 0 && (
                    <div className="max-h-40 space-y-1.5 overflow-y-auto text-xs">
                      {selectedDoc.versions.map((v) => (
                        <div
                          key={v.id}
                          className="flex items-center justify-between rounded border border-slate-200 bg-slate-50/70 px-3 py-1.5 dark:border-slate-800 dark:bg-slate-800/40"
                        >
                          <div>
                            <span className="font-mono font-bold">v{v.version_number}</span> —{" "}
                            {v.change_note || v.title_fa} ({v.edited_by_name})
                          </div>
                          <div className="flex items-center gap-2">
                            <DateDisplay value={v.created_at} />
                            <button
                              type="button"
                              onClick={() =>
                                restoreVersionMut.mutate({
                                  docId: selectedDoc.id,
                                  ver: v.version_number,
                                })
                              }
                              className="inline-flex items-center gap-1 text-[11px] font-semibold text-teal-700 dark:text-teal-400"
                            >
                              <RotateCcw className="h-3 w-3" />
                              بازیابی
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 3. Property Violation Inspection Queue */}
      <div className="surface-card rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-200 pb-3 dark:border-slate-800">
          <AlertOctagon className="h-5 w-5 text-rose-600 dark:text-rose-400" />
          <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
            صف بررسی و بازرسی گزارش‌های تخلف و قیمت صوری آگهی‌ها
          </h2>
        </div>

        {violationsQ.isLoading ? (
          <LoadingState />
        ) : (violationsQ.data || []).length === 0 ? (
          <div className="text-xs text-slate-500">گزارش تخلفی ثبت نشده است.</div>
        ) : (
          <div className="space-y-3">
            {(violationsQ.data || []).map((rep) => (
              <div
                key={rep.id}
                className="rounded-lg border border-slate-200 bg-slate-50/70 p-3.5 text-xs space-y-2 dark:border-slate-800 dark:bg-slate-800/40"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <span className="font-bold text-slate-900 dark:text-slate-100">
                      {rep.property_title} ({rep.property_code})
                    </span>{" "}
                    <span className="text-slate-500">— {rep.agency_name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[11px] text-amber-700 dark:text-amber-400">
                      {rep.reason_type}
                    </span>
                    <StatusText status={rep.status} />
                  </div>
                </div>
                <p className="text-slate-600 dark:text-slate-300">{rep.details}</p>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[11px] text-slate-400">
                    گزارش‌دهنده: {rep.reporter_name} · <DateDisplay value={rep.created_at} withTime />
                  </span>
                  {rep.status !== "RESOLVED_SUSPENDED" &&
                    rep.status !== "RESOLVED_CONFIRMED" &&
                    rep.status !== "DISMISSED" && (
                      <div className="mr-auto flex flex-wrap items-center gap-2">
                        <input
                          placeholder="یادداشت بازرسی..."
                          value={resNotes[rep.id] || ""}
                          onChange={(e) =>
                            setResNotes((p) => ({ ...p, [rep.id]: e.target.value }))
                          }
                          className="h-8 rounded border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-950"
                        />
                        <button
                          type="button"
                          onClick={() =>
                            resolveViolationMut.mutate({
                              reportId: rep.id,
                              resolution_status: "RESOLVED_SUSPENDED",
                              suspend_listing: true,
                            })
                          }
                          className="h-8 rounded bg-rose-700 px-3 text-[11px] font-semibold text-white hover:bg-rose-800"
                        >
                          تأیید تخلف و تعلیق آگهی
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            resolveViolationMut.mutate({
                              reportId: rep.id,
                              resolution_status: "DISMISSED",
                              suspend_listing: false,
                            })
                          }
                          className="h-8 rounded border border-slate-300 bg-white px-3 text-[11px] font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                        >
                          رد گزارش
                        </button>
                      </div>
                    )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 4. Legal Acceptance Log */}
      <div className="surface-card rounded-xl p-5 space-y-3">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-teal-600" />
          <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
            سوابق پذیرش و تأیید قوانین توسط کاربران
          </h2>
        </div>
        {acceptancesQ.isLoading ? (
          <LoadingState />
        ) : (
          <div className="max-h-52 overflow-y-auto">
            <table className="w-full text-right text-xs">
              <thead className="border-b border-slate-200 text-slate-500 dark:border-slate-800">
                <tr>
                  <th className="py-2 px-2">سند</th>
                  <th className="py-2 px-2">نسخه</th>
                  <th className="py-2 px-2">کاربر</th>
                  <th className="py-2 px-2">IP</th>
                  <th className="py-2 px-2">زمان ثبت</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {(acceptancesQ.data || []).map((a) => (
                  <tr key={a.id}>
                    <td className="py-2 px-2 font-semibold">{a.document_title}</td>
                    <td className="py-2 px-2 font-mono">v{a.version_number}</td>
                    <td className="py-2 px-2">
                      {a.user_name}{" "}
                      <span className="font-mono text-[11px] text-slate-400" dir="ltr">
                        ({a.user_phone})
                      </span>
                    </td>
                    <td className="py-2 px-2 font-mono" dir="ltr">
                      {a.ip_address || "—"}
                    </td>
                    <td className="py-2 px-2">
                      <DateDisplay value={a.accepted_at} withTime />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

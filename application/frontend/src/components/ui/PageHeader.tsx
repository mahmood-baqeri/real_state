// Path: frontend/src/components/ui/PageHeader.tsx

import React from "react";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  breadcrumbs?: BreadcrumbItem[];
  actions?: React.ReactNode;
}

export function PageHeader({ title, subtitle, breadcrumbs, actions }: PageHeaderProps) {
  return (
    <div className="mb-6 flex flex-col gap-3 border-b border-slate-200 pb-5 dark:border-slate-800 sm:flex-row sm:items-center sm:justify-between">
      <div className="space-y-1">
        {breadcrumbs && breadcrumbs.length > 0 && (
          <nav
            aria-label="breadcrumb"
            className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400"
          >
            {breadcrumbs.map((b, idx) => (
              <React.Fragment key={idx}>
                {idx > 0 && (
                  <ChevronLeft className="h-3.5 w-3.5 text-slate-400 dark:text-slate-600" />
                )}
                {b.href ? (
                  <Link
                    href={b.href}
                    className="transition-colors hover:text-teal-700 dark:hover:text-teal-400"
                  >
                    {b.label}
                  </Link>
                ) : (
                  <span className="font-medium text-slate-700 dark:text-slate-200">{b.label}</span>
                )}
              </React.Fragment>
            ))}
          </nav>
        )}
        <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 sm:text-2xl">
          {title}
        </h1>
        {subtitle && <p className="text-sm text-slate-600 dark:text-slate-400">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2.5">{actions}</div>}
    </div>
  );
}

"use client";

import React from "react";
import { Check } from "lucide-react";

export interface StepItem {
  id: string;
  title: string;
  subtitle?: string;
}

interface StepWizardProps {
  steps: StepItem[];
  currentStepIndex: number;
  onStepSelect?: (index: number) => void;
}

export function StepWizard({ steps, currentStepIndex, onStepSelect }: StepWizardProps) {
  return (
    <nav aria-label="مراحل ثبت" className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <ol className="grid grid-cols-1 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {steps.map((step, idx) => {
          const isCompleted = idx < currentStepIndex;
          const isCurrent = idx === currentStepIndex;
          return (
            <li key={step.id}>
              <button
                type="button"
                disabled={!onStepSelect}
                onClick={() => onStepSelect?.(idx)}
                className={`flex w-full items-center gap-3 rounded-lg border px-3 py-2.5 text-right transition-colors ${
                  isCurrent
                    ? "border-teal-600 bg-teal-50/70 dark:border-teal-500 dark:bg-teal-950/40"
                    : isCompleted
                    ? "border-emerald-200 bg-emerald-50/50 dark:border-emerald-900/60 dark:bg-emerald-950/20"
                    : "border-slate-200 bg-slate-50/70 dark:border-slate-800 dark:bg-slate-800/40"
                }`}
              >
                <span
                  className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-xs font-bold tabular-nums ${
                    isCurrent
                      ? "bg-teal-700 text-white dark:bg-teal-500 dark:text-slate-950"
                      : isCompleted
                      ? "bg-emerald-600 text-white"
                      : "bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-300"
                  }`}
                >
                  {isCompleted ? <Check className="h-3.5 w-3.5" /> : idx + 1}
                </span>
                <span className="min-w-0">
                  <span className="block truncate text-xs font-bold text-slate-900 dark:text-slate-100">
                    {step.title}
                  </span>
                  {step.subtitle && (
                    <span className="block truncate text-[11px] text-slate-500 dark:text-slate-400">
                      {step.subtitle}
                    </span>
                  )}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

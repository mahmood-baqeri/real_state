// Path: frontend/src/app/dashboard/layout.tsx

import React from "react";
import type { Metadata } from "next";
import { DashboardShell } from "@/components/layout/DashboardShell";

export const metadata: Metadata = {
  robots: {
    index: false,
    follow: false,
  },
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return <DashboardShell>{children}</DashboardShell>;
}

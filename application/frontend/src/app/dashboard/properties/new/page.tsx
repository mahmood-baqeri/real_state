// Path: frontend/src/app/dashboard/properties/new/page.tsx

"use client";

import React from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { PropertyForm } from "@/components/properties/PropertyForm";

export default function NewPropertyPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="ثبت ملک جدید"
        subtitle="تکمیل اطلاعات فنی، قیمت‌گذاری، موقعیت و سطح انتشار فایل"
        breadcrumbs={[
          { label: "میز کار", href: "/dashboard" },
          { label: "املاک", href: "/dashboard/properties" },
          { label: "ملک جدید" },
        ]}
      />
      <PropertyForm />
    </div>
  );
}

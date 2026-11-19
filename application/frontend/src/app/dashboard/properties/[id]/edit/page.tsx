// Path: frontend/src/app/dashboard/properties/[id]/edit/page.tsx

"use client";

import React from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { PropertyItem } from "@/lib/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { PropertyForm } from "@/components/properties/PropertyForm";
import { ErrorState, LoadingState } from "@/components/ui/StateNotice";

export default function EditPropertyPage() {
  const params = useParams<{ id: string }>();
  const { accessToken, activeAgencyId } = useAuth();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["property-edit", params.id, activeAgencyId],
    enabled: !!accessToken,
    queryFn: async () =>
      (
        await apiFetch<PropertyItem>(`/api/v1/properties/${params.id}`, {
          token: accessToken,
          agencyId: activeAgencyId,
        })
      ).data,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title={`ویرایش ملک ${data?.property_code || ""}`}
        subtitle={data?.title || "به‌روزرسانی مشخصات ملک"}
        breadcrumbs={[
          { label: "میز کار", href: "/dashboard" },
          { label: "املاک", href: "/dashboard/properties" },
          { label: "ویرایش" },
        ]}
      />
      {isLoading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState
          message={error instanceof Error ? error.message : "خطا در دریافت اطلاعات ملک"}
          onRetry={() => refetch()}
        />
      ) : (
        <PropertyForm propertyId={params.id} initialData={data} />
      )}
    </div>
  );
}

import React from "react";
import type { Metadata } from "next";
import { LegalDocumentView } from "@/components/legal/LegalDocumentView";

export const metadata: Metadata = {
  title: "سیاست حریم خصوصی",
  description: "نحوه حفاظت از اطلاعات هویتی مالکین، مشتریان و رمزنگاری داده‌های حساس در بنیان ملک",
};

export default function PrivacyPage() {
  return (
    <LegalDocumentView
      slug="privacy-policy"
      fallbackTitle="سیاست حریم خصوصی و حفاظت از داده‌ها"
    />
  );
}

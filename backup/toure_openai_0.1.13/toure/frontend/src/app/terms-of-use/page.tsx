import React from "react";
import type { Metadata } from "next";
import { LegalDocumentView } from "@/components/legal/LegalDocumentView";

export const metadata: Metadata = {
  title: "شرایط استفاده از خدمات",
  description: "شرایط بهره‌برداری از خدمات نرم‌افزاری، اشتراک‌های ماهانه و درگاه‌های پرداخت در بنیان ملک",
};

export default function TermsOfUsePage() {
  return (
    <LegalDocumentView
      slug="terms-of-use"
      fallbackTitle="شرایط استفاده از خدمات (Terms of Use)"
    />
  );
}

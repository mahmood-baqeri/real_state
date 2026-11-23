import React from "react";
import type { Metadata } from "next";
import { LegalDocumentView } from "@/components/legal/LegalDocumentView";

export const metadata: Metadata = {
  title: "اسناد حقوقی و مقررات پلتفرم",
  description: "مطالعه آخرین نسخه رسمی قوانین، مقررات، سیاست حریم خصوصی و شرایط استفاده بنیان ملک",
};

export default function DynamicLegalPage() {
  return <LegalDocumentView />;
}

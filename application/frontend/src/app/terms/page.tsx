import React from "react";
import type { Metadata } from "next";
import { LegalDocumentView } from "@/components/legal/LegalDocumentView";

export const metadata: Metadata = {
  title: "قوانین و مقررات پلتفرم",
  description: "قوانین انتشار آگهی، اصالت اسناد، محاسبه کمیسیون و مسئولیت‌های آژانس‌های عضو بنیان ملک",
};

export default function TermsPage() {
  return (
    <LegalDocumentView
      slug="platform-rules"
      fallbackTitle="قوانین و مقررات پلتفرم بنیان ملک"
    />
  );
}

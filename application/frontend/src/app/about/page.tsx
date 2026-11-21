import React from "react";
import type { Metadata } from "next";
import { AboutPageContent } from "@/components/legal/AboutPageContent";

export const metadata: Metadata = {
  title: "درباره ما",
  description: "آشنایی با ماموریت، معماری امنیتی و استانداردهای سازمانی پلتفرم املاک بنیان ملک",
};

export default function AboutPage() {
  return <AboutPageContent />;
}

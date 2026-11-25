// نمایش داده‌های ساخت‌یافتهٔ صفحات برای موتورهای جست‌وجو.
import React from "react";

/** داده را برای قرار گرفتن داخل عنصر اسکریپت سریال می‌کند. */
export function JsonLd({ data }: { data: Record<string, unknown> }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data).replace(/</g, "\\u003c") }}
    />
  );
}

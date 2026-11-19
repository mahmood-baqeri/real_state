// Path: frontend/src/app/sitemap.ts

import type { MetadataRoute } from "next";
import { getApiOrigin, getSiteUrl } from "@/lib/seo";

export const dynamic = "force-dynamic";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const siteUrl = getSiteUrl();
  const apiOrigin = getApiOrigin();
  const now = new Date();

  const staticPaths = [
    "",
    "/properties",
    "/search",
    "/about",
    "/contact",
    "/services",
    "/cooperation",
    "/careers",
    "/terms",
    "/privacy",
    "/terms-of-use",
    "/faq",
    "/guide",
    "/features",
    "/pricing",
    "/agency-application",
    "/requests/new",
    "/requests/track",
    "/complaints/new",
    "/complaints/track",
    "/blog",
    "/explore/tehran",
    "/explore/tehran/zafaranieh",
  ];

  const entries: MetadataRoute.Sitemap = staticPaths.map((p) => ({
    url: `${siteUrl}${p}`,
    lastModified: now,
    changeFrequency: p === "" || p === "/properties" || p === "/blog" ? "daily" : "weekly",
    priority: p === "" ? 1 : 0.7,
  }));

  try {
    const [propsRes, blogRes] = await Promise.all([
      fetch(`${apiOrigin}/api/v1/properties/public?page_size=50`, { cache: "no-store" }),
      fetch(`${apiOrigin}/api/v1/cms/public/articles?page_size=50`, { cache: "no-store" }),
    ]);

    if (propsRes.ok) {
      const propsJson = await propsRes.json();
      for (const p of propsJson?.data || []) {
        entries.push({
          url: `${siteUrl}/properties/${p.id}`,
          lastModified: p.created_at ? new Date(p.created_at) : now,
          changeFrequency: "daily",
          priority: 0.85,
        });
      }
    }

    if (blogRes.ok) {
      const blogJson = await blogRes.json();
      for (const a of blogJson?.data || []) {
        entries.push({
          url: `${siteUrl}/blog/${a.slug}`,
          lastModified: a.published_at ? new Date(a.published_at) : now,
          changeFrequency: "weekly",
          priority: 0.8,
        });
      }
    }
  } catch {
    // Graceful fallback if API backend is offline during static build checks
  }

  return entries;
}

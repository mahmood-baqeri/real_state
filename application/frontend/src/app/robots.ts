// Path: frontend/src/app/robots.ts

import type { MetadataRoute } from "next";
import { getSiteUrl } from "@/lib/seo";

export default function robots(): MetadataRoute.Robots {
  const siteUrl = getSiteUrl();
  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/properties", "/search", "/blog", "/features", "/pricing", "/faq", "/about", "/contact"],
        disallow: ["/dashboard", "/dashboard/*", "/api/*", "/login", "/register"],
      },
    ],
    sitemap: `${siteUrl}/sitemap.xml`,
  };
}

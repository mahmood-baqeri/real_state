export function getSiteUrl(): string {
  return process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") || "http://localhost:3000";
}

export function getApiOrigin(): string {
  return (
    process.env.INTERNAL_FASTAPI_URL?.replace(/\/$/, "") ||
    process.env.INTERNAL_API_ORIGIN?.replace(/\/$/, "") ||
    "http://127.0.0.1:8020"
  );
}

export function buildOrganizationJsonLd() {
  const siteUrl = getSiteUrl();
  return {
    "@context": "https://schema.org",
    "@type": "RealEstateAgent",
    name: "بنیان ملک",
    alternateName: "Bonyan Melk",
    url: siteUrl,
    logo: `${siteUrl}/icon.svg`,
    description:
      "پلتفرم سازمانی چندآژانسی مدیریت املاک، CRM فروش، محاسبه کمیسیون، حسابداری دوطرفه و پرتال آگهی‌های احراز‌شده",
    areaServed: "IR",
  };
}

export function buildResidenceJsonLd(prop: {
  id: string;
  title: string;
  description: string;
  total_price?: string;
  deposit_amount?: string;
  currency?: string;
  built_area_sqm?: string;
  bedrooms?: number;
  location?: { city?: string; district?: string } | null;
}) {
  const siteUrl = getSiteUrl();
  const priceNum = Number(prop.total_price || prop.deposit_amount || 0);
  return {
    "@context": "https://schema.org",
    "@type": "Residence",
    name: prop.title,
    description: prop.description,
    url: `${siteUrl}/properties/${prop.id}`,
    numberOfRooms: prop.bedrooms ?? undefined,
    floorSize: prop.built_area_sqm
      ? { "@type": "QuantitativeValue", value: Number(prop.built_area_sqm), unitCode: "MTK" }
      : undefined,
    address: prop.location
      ? {
          "@type": "PostalAddress",
          addressLocality: prop.location.city || "تهران",
          addressRegion: prop.location.district || "",
          addressCountry: "IR",
        }
      : undefined,
    offers:
      priceNum > 0
        ? {
            "@type": "Offer",
            price: priceNum,
            priceCurrency: prop.currency || "IRR",
            availability: "https://schema.org/InStock",
          }
        : undefined,
  };
}

export function buildArticleJsonLd(article: {
  slug: string;
  title: string;
  summary: string;
  published_at: string | null;
  author?: { display_name: string } | null;
}) {
  const siteUrl = getSiteUrl();
  return {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: article.title,
    description: article.summary,
    datePublished: article.published_at || undefined,
    mainEntityOfPage: `${siteUrl}/blog/${article.slug}`,
    author: {
      "@type": "Person",
      name: article.author?.display_name || "تحریریه بنیان ملک",
    },
    publisher: {
      "@type": "Organization",
      name: "بنیان ملک",
    },
  };
}

export function buildFaqJsonLd(faqs: { question: string; answer: string }[]) {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqs.map((f) => ({
      "@type": "Question",
      name: f.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: f.answer,
      },
    })),
  };
}

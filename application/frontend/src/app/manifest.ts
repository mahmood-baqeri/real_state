import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "بنیان ملک | سامانه جامع مدیریت املاک",
    short_name: "بنیان ملک",
    description: "پلتفرم جامع چندآژانسی مدیریت املاک، CRM، قراردادها، حسابداری و نظرسنجی",
    start_url: "/",
    scope: "/",
    display: "standalone",
    dir: "rtl",
    lang: "fa",
    background_color: "#0b1120",
    theme_color: "#0f766e",
    icons: [
      {
        src: "/pwa-192x192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/pwa-512x512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/pwa-maskable-512x512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}

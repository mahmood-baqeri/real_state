// Path: frontend/src/app/layout.tsx

import type { Metadata, Viewport } from "next";
import { IBM_Plex_Mono, Vazirmatn } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/Providers";

const vazirmatn = Vazirmatn({
  subsets: ["arabic", "latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-vazirmatn",
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "600"],
  variable: "--font-mono",
  display: "swap",
});

export const viewport: Viewport = {
  themeColor: "#0f766e",
  width: "device-width",
  initialScale: 1,
};

export const metadata: Metadata = {
  title: {
    default: "بنیان ملک | پلتفرم جامع و سازمانی مدیریت املاک",
    template: "%s | بنیان ملک",
  },
  description:
    "سامانه یکپارچه چندآژانسی مدیریت املاک، CRM، بازدید، قراردادها، کمیسیون، حسابداری دوطرفه و حقوق و دستمزد",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "بنیان ملک",
  },
  icons: {
    icon: "/icon.svg",
    apple: "/apple-touch-icon.png",
  },
  openGraph: {
    title: "بنیان ملک | پلتفرم جامع و سازمانی مدیریت املاک",
    description:
      "پلتفرم سازمانی مدیریت املاک، CRM، قراردادها، کمیسیون، حسابداری و حقوق مشاوران",
    type: "website",
    locale: "fa_IR",
  },
};

const THEME_INIT_SCRIPT = `
(function() {
  try {
    var pref = localStorage.getItem('bonyan-theme') || 'system';
    var sysDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    var isDark = pref === 'dark' || (pref === 'system' && sysDark);
    var root = document.documentElement;
    if (isDark) {
      root.classList.add('dark');
      root.style.colorScheme = 'dark';
    } else {
      root.classList.remove('dark');
      root.style.colorScheme = 'light';
    }
  } catch (e) {}
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="fa"
      dir="rtl"
      suppressHydrationWarning
      className={`${vazirmatn.variable} ${ibmPlexMono.variable}`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100 font-[family-name:var(--font-vazirmatn)] antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

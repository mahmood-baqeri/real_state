import type { Metadata } from "next";
import { IBM_Plex_Mono, Vazirmatn } from "next/font/google";
import "@/styles/globals.css";
import { Providers } from "@/components/Providers";
import { THEME_INIT_SCRIPT } from "@/lib/theme-provider";

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

export const metadata: Metadata = {
  title: {
    default: "بنیان ملک | پلتفرم جامع مدیریت املاک",
    template: "%s | بنیان ملک",
  },
  description:
    "سامانه یکپارچه چندآژانسی مدیریت املاک، CRM، بازدید، قراردادها، کمیسیون، حسابداری دوبل و منابع انسانی",
  applicationName: "بنیان ملک",
  openGraph: {
    title: "بنیان ملک | پلتفرم جامع مدیریت املاک",
    description:
      "پلتفرم سازمانی مدیریت املاک، CRM، قراردادها، کمیسیون، حسابداری و منابع انسانی",
    type: "website",
    locale: "fa_IR",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="fa"
      dir="rtl"
      className={`${vazirmatn.variable} ${ibmPlexMono.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script
          dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }}
          suppressHydrationWarning
        />
      </head>
      <body className="min-h-screen bg-canvas font-sans text-fg antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
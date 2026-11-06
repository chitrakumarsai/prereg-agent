import type { Metadata, Viewport } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import "./globals.css";

const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-sans",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex-mono",
  display: "swap",
});

const TITLE = "Prereg — AI data analysis with receipts";
const DESCRIPTION =
  "Upload a CSV and ask a question. Prereg commits to its statistical test before it sees a result, runs its own code in a gVisor sandbox with no network and no secrets, and independently re-checks every number.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  applicationName: "Prereg",
  keywords: ["AI data analyst", "sandbox", "gVisor", "pre-registration", "Vultr", "statistics", "agent"],
  openGraph: { title: TITLE, description: DESCRIPTION, type: "website", siteName: "Prereg" },
  twitter: { card: "summary_large_image", title: TITLE, description: DESCRIPTION },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: "#eeecea",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-type="software" data-radius="sharp" className={`${plexSans.variable} ${plexMono.variable}`}>
      <head>
        <meta name="page-type" content="software" />
        <meta name="site-kind" content="software" />
      </head>
      <body>{children}</body>
    </html>
  );
}

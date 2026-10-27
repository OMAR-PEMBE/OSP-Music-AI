import type { Metadata, Viewport } from "next";
import { LocaleProvider } from "@/components/locale-provider";
import { PwaInstallPrompt } from "@/components/pwa-install-prompt";
import "./globals.css";

export const metadata: Metadata = {
  title: "OSP Music AI",
  description: "Muziki wako, kwa mawazo yako.",
  applicationName: "OSP Music AI",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "OSP Music AI",
  },
  icons: {
    icon: [
      { url: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icon.svg", type: "image/svg+xml" },
    ],
    apple: "/icon-192.png",
  },
};

export const viewport: Viewport = {
  colorScheme: "light dark",
  themeColor: "#b6f36b",
};

const preferenceBootstrap = `(()=>{try{const l=localStorage.getItem("osp-locale");const t=localStorage.getItem("osp-theme");document.documentElement.lang=l==="en"?"en":"sw";document.documentElement.dataset.theme=t==="dark"||t==="light"?t:window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}catch{document.documentElement.dataset.theme=window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}})()`;

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="sw" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: preferenceBootstrap }} />
      </head>
      <body>
        <LocaleProvider>
          {children}
          <PwaInstallPrompt />
        </LocaleProvider>
      </body>
    </html>
  );
}

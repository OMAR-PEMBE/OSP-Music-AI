import type { Metadata, Viewport } from "next";
import { LocaleProvider } from "@/components/locale-provider";
import { PwaInstallPrompt } from "@/components/pwa-install-prompt";
import { WhatsAppSupportButton } from "@/components/whatsapp-support-button";
import "./globals.css";

export const metadata: Metadata = {
  title: "OSP Music AI",
  description: "Your music, from your imagination.",
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

const preferenceBootstrap = `(()=>{document.documentElement.lang="en";try{const t=localStorage.getItem("osp-theme");document.documentElement.dataset.theme=t==="dark"||t==="light"?t:window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}catch{document.documentElement.dataset.theme=window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}})()`;

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: preferenceBootstrap }} />
      </head>
      <body>
        <LocaleProvider>
          {children}
          <WhatsAppSupportButton />
          <PwaInstallPrompt />
        </LocaleProvider>
      </body>
    </html>
  );
}

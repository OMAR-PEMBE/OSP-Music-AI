import type { Metadata } from "next";
import { LocaleProvider } from "@/components/locale-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "OSP Music AI",
  description: "Muziki wako, kwa mawazo yako.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="sw">
      <body>
        <LocaleProvider>{children}</LocaleProvider>
      </body>
    </html>
  );
}

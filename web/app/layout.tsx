import type { Metadata } from "next";
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
      <body>{children}</body>
    </html>
  );
}

import type english from "@/messages/en.json";

declare module "next-intl" {
  interface AppConfig {
    Locale: "en";
    Messages: typeof english;
  }
}

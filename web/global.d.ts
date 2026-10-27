import type swahili from "@/messages/sw.json";

declare module "next-intl" {
  interface AppConfig {
    Locale: "sw" | "en";
    Messages: typeof swahili;
  }
}

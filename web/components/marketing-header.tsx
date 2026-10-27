"use client";

import Link from "next/link";
import { Icon } from "@/components/icon";
import { useLocaleMessages } from "@/components/locale-provider";

export function MarketingHeader() {
  const { t, locale, setLocale, resolvedTheme, toggleTheme } =
    useLocaleMessages();
  return (
    <header className="marketing-header">
      <Link className="brand-lockup" href="/" aria-label={t("brand")}>
        <span className="brand-glyph">
          <Icon name="music" />
        </span>
        <span>{t("brand")}</span>
      </Link>
      <div className="marketing-actions">
        <button
          className="icon-button compact"
          onClick={() => setLocale(locale === "sw" ? "en" : "sw")}
          aria-label={t("changeLanguage")}
        >
          {locale === "sw" ? "EN" : "SW"}
        </button>
        <button
          className="icon-button"
          onClick={toggleTheme}
          aria-label={t("theme")}
        >
          <Icon name={resolvedTheme === "light" ? "moon" : "sun"} />
        </button>
        <Link className="text-link" href="/login">
          {t("login")}
        </Link>
        <Link className="button button-small button-dark" href="/signup">
          {t("getStarted")} <Icon name="arrow" />
        </Link>
      </div>
    </header>
  );
}

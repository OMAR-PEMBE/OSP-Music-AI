"use client";

import Link from "next/link";
import { Icon } from "@/components/icon";
import { useLocaleMessages } from "@/components/locale-provider";

export function MarketingHeader() {
  const { t, resolvedTheme, toggleTheme } = useLocaleMessages();
  return (
    <header className="marketing-header">
      <Link className="brand-lockup" href="/" aria-label={t("brand")}>
        <span className="brand-glyph" aria-hidden="true">
          <i />
          <i />
          <i />
          <i />
          <i />
        </span>
        <span>{t("brand")}</span>
      </Link>
      <nav className="marketing-nav" aria-label={t("landingNavigation")}>
        <Link href="/#top">{t("home")}</Link>
        <Link href="/create">{t("create")}</Link>
        <Link href="/#pricing">{t("priceLabel")}</Link>
        <Link href="/faq">{t("help")}</Link>
      </nav>
      <div className="marketing-actions">
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

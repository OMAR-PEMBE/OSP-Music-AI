"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, ApiError, formatTzs, type Me } from "@/lib/api";
import { Icon } from "@/components/icon";
import { useLocaleMessages } from "@/components/locale-provider";

const navItems = [
  { href: "/create", key: "create" as const, icon: "plus" as const },
  { href: "/music", key: "music" as const, icon: "music" as const },
  { href: "/wallet", key: "wallet" as const, icon: "wallet" as const },
  { href: "/settings", key: "settings" as const, icon: "settings" as const },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { t, locale, setLocale, theme, toggleTheme } = useLocaleMessages();
  const [me, setMe] = useState<Me | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let alive = true;
    api<Me>("/api/me")
      .then((profile) => {
        if (alive) setMe(profile);
      })
      .catch((error: unknown) => {
        if (alive && error instanceof ApiError && error.status === 401) {
          router.replace(`/login?next=${encodeURIComponent(pathname)}`);
        }
      })
      .finally(() => {
        if (alive) setReady(true);
      });
    return () => {
      alive = false;
    };
  }, [pathname, router]);

  useEffect(() => {
    const onSongsSeen = () =>
      setMe((current) => (current ? { ...current, unseen_songs: 0 } : current));
    window.addEventListener("osp:songs-seen", onSongsSeen);
    return () => window.removeEventListener("osp:songs-seen", onSongsSeen);
  }, []);

  async function logout() {
    try {
      await api("/api/auth/browser/v1/auth/session", { method: "DELETE" });
    } finally {
      router.push("/");
      router.refresh();
    }
  }

  if (!ready || !me) {
    return (
      <main className="loading-screen">
        <span className="loading-mark">
          <Icon name="music" />
        </span>
        <p>{t("loading")}</p>
      </main>
    );
  }

  return (
    <div className="app-frame">
      <header className="app-header">
        <Link className="brand-lockup" href="/create" aria-label={t("brand")}>
          <span className="brand-glyph">
            <Icon name="music" />
          </span>
          <span>{t("brand")}</span>
        </Link>
        <nav className="top-nav" aria-label={t("home")}>
          {navItems.slice(0, 3).map((item) => (
            <Link
              className={
                pathname.startsWith(item.href) ? "top-link active" : "top-link"
              }
              href={item.href}
              key={item.href}
            >
              {t(item.key)}
              {item.key === "music" && me.unseen_songs > 0 && (
                <span className="nav-unseen-dot" />
              )}
            </Link>
          ))}
        </nav>
        <div className="header-actions">
          <Link
            href="/wallet"
            className="balance-chip"
            aria-label={`${t("balance")}: ${formatTzs(me.balance_tzs)}`}
          >
            <span className="balance-chip-label">{t("balance")}</span>
            <strong>{formatTzs(me.balance_tzs)}</strong>
          </Link>
          <div className="header-tools">
            <button
              className="icon-button compact"
              onClick={() => setLocale(locale === "sw" ? "en" : "sw")}
              aria-label="Change language"
            >
              {locale === "sw" ? "EN" : "SW"}
            </button>
            <button
              className="icon-button"
              onClick={toggleTheme}
              aria-label={t("theme")}
            >
              <Icon name={theme === "light" ? "moon" : "sun"} />
            </button>
          </div>
          <Link
            className="avatar-link"
            href="/settings"
            aria-label={t("account")}
          >
            {me.avatar_url ? (
              <Image
                src={me.avatar_url}
                alt=""
                width={38}
                height={38}
                unoptimized
              />
            ) : (
              <span>{me.first_name?.[0] ?? me.email[0]}</span>
            )}
          </Link>
          <button
            className="icon-button logout-button"
            onClick={logout}
            aria-label={t("logout")}
          >
            <Icon name="logout" />
          </button>
        </div>
      </header>

      <div className="app-content-wrap">
        {!me.email_verified && (
          <div className="notice-banner">
            <span>{t("emailNotVerified")}</span>
            <Link href="/verify-email">{t("verifyAction")}</Link>
          </div>
        )}
        <main className="app-content">{children}</main>
      </div>

      <nav className="mobile-nav" aria-label={t("settings")}>
        {navItems.map((item) => (
          <Link
            className={
              pathname.startsWith(item.href)
                ? "mobile-nav-item active"
                : "mobile-nav-item"
            }
            href={item.href}
            key={item.href}
          >
            <span className="mobile-nav-icon">
              <Icon name={item.icon} />
            </span>
            <span>
              {t(item.key)}
              {item.key === "music" && me.unseen_songs > 0 && (
                <span className="nav-unseen-dot" />
              )}
            </span>
          </Link>
        ))}
      </nav>
    </div>
  );
}

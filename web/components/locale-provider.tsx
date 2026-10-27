"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { NextIntlClientProvider, useTranslations } from "next-intl";
import english from "@/messages/en.json";
import { api, ApiError, type Me } from "@/lib/api";

export type Theme = "system" | "light" | "dark";
export type ResolvedTheme = Exclude<Theme, "system">;

const preferenceKeys = { theme: "osp-theme" } as const;

type LocaleContextValue = {
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  preferenceError: boolean;
};

const LocaleContext = createContext<LocaleContextValue | null>(null);

function isTheme(value: string | null): value is Theme {
  return value === "system" || value === "light" || value === "dark";
}

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [theme, updateTheme] = useState<Theme>("system");
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>("light");
  const [hydrated, setHydrated] = useState(false);
  const [preferenceError, setPreferenceError] = useState(false);
  const preferenceQueue = useRef(Promise.resolve());

  const savePreference = useCallback((updates: Partial<Pick<Me, "theme">>) => {
    preferenceQueue.current = preferenceQueue.current.then(async () => {
      try {
        await api<Me>("/api/me", { method: "PATCH", body: updates });
        setPreferenceError(false);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return;
        setPreferenceError(true);
      }
    });
  }, []);

  const setTheme = useCallback(
    (nextTheme: Theme) => {
      updateTheme(nextTheme);
      if (hydrated) savePreference({ theme: nextTheme });
    },
    [hydrated, savePreference],
  );

  const toggleTheme = useCallback(() => {
    setTheme(resolvedTheme === "light" ? "dark" : "light");
  }, [resolvedTheme, setTheme]);

  useEffect(() => {
    localStorage.removeItem("osp-locale");
    const savedTheme = localStorage.getItem(preferenceKeys.theme);
    if (isTheme(savedTheme)) updateTheme(savedTheme);
    setHydrated(true);

    let active = true;
    const syncProfile = () => {
      api<Me>("/api/me")
        .then((profile) => {
          if (!active) return;
          if (isTheme(profile.theme)) {
            updateTheme(profile.theme);
            localStorage.setItem(preferenceKeys.theme, profile.theme);
          }
        })
        .catch((error: unknown) => {
          if (error instanceof ApiError && error.status === 401) return;
          if (active) setPreferenceError(true);
        });
    };
    syncProfile();
    window.addEventListener("osp:session-changed", syncProfile);
    return () => {
      active = false;
      window.removeEventListener("osp:session-changed", syncProfile);
    };
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    localStorage.setItem(preferenceKeys.theme, theme);
    document.documentElement.lang = "en";
  }, [hydrated, theme]);

  useEffect(() => {
    if (!hydrated) return;
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const applyTheme = () => {
      const nextTheme =
        theme === "system" ? (mediaQuery.matches ? "dark" : "light") : theme;
      setResolvedTheme(nextTheme);
      document.documentElement.dataset.theme = nextTheme;
    };
    applyTheme();
    mediaQuery.addEventListener("change", applyTheme);
    return () => mediaQuery.removeEventListener("change", applyTheme);
  }, [hydrated, theme]);

  const value = useMemo(
    () => ({
      theme,
      resolvedTheme,
      setTheme,
      toggleTheme,
      preferenceError,
    }),
    [theme, resolvedTheme, setTheme, toggleTheme, preferenceError],
  );

  return (
    <LocaleContext.Provider value={value}>
      <NextIntlClientProvider
        locale="en"
        messages={english}
        timeZone="Africa/Dar_es_Salaam"
      >
        {children}
      </NextIntlClientProvider>
    </LocaleContext.Provider>
  );
}

export function useLocaleMessages() {
  const context = useContext(LocaleContext);
  if (!context)
    throw new Error("useLocaleMessages must be used inside LocaleProvider");
  return { ...context, t: useTranslations() };
}

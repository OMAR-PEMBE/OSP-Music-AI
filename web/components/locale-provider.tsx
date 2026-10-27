"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import swahili from "@/messages/sw.json";
import english from "@/messages/en.json";

export type Locale = "sw" | "en";
export type Theme = "light" | "dark";
type MessageKey = keyof typeof swahili;

const dictionaries: Record<Locale, typeof swahili> = {
  sw: swahili,
  en: english as typeof swahili,
};

type LocaleContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  theme: Theme;
  toggleTheme: () => void;
  t: (key: MessageKey) => string;
};

const LocaleContext = createContext<LocaleContextValue | null>(null);

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, updateLocale] = useState<Locale>("sw");
  const [theme, updateTheme] = useState<Theme>("light");

  useEffect(() => {
    const savedLocale = localStorage.getItem("osp-locale");
    if (savedLocale === "sw" || savedLocale === "en") updateLocale(savedLocale);
    const savedTheme = localStorage.getItem("osp-theme");
    if (savedTheme === "dark" || savedTheme === "light")
      updateTheme(savedTheme);
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("osp-locale", locale);
    localStorage.setItem("osp-theme", theme);
  }, [locale, theme]);

  const setLocale = useCallback((nextLocale: Locale) => {
    updateLocale(nextLocale);
    localStorage.setItem("osp-locale", nextLocale);
  }, []);
  const toggleTheme = useCallback(() => {
    updateTheme((current) => {
      const next = current === "light" ? "dark" : "light";
      localStorage.setItem("osp-theme", next);
      return next;
    });
  }, []);
  const t = useCallback(
    (key: MessageKey) => dictionaries[locale][key],
    [locale],
  );
  const value = useMemo(
    () => ({ locale, setLocale, theme, toggleTheme, t }),
    [locale, setLocale, theme, toggleTheme, t],
  );

  return (
    <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
  );
}

export function useLocaleMessages() {
  const context = useContext(LocaleContext);
  if (!context)
    throw new Error("useLocaleMessages must be used inside LocaleProvider");
  return context;
}

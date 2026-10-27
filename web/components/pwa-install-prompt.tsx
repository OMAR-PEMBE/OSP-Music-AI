"use client";

import { useEffect, useState } from "react";
import { useLocaleMessages } from "@/components/locale-provider";

type InstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
};

export function PwaInstallPrompt() {
  const { t } = useLocaleMessages();
  const [installEvent, setInstallEvent] = useState<InstallPromptEvent | null>(
    null,
  );
  const [showIosHelp, setShowIosHelp] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const standalone =
      window.matchMedia("(display-mode: standalone)").matches ||
      ("standalone" in navigator &&
        (navigator as Navigator & { standalone?: boolean }).standalone ===
          true);
    if (standalone) return;

    const isIos = /iphone|ipad|ipod/i.test(window.navigator.userAgent);
    if (isIos) setShowIosHelp(true);

    const onBeforeInstallPrompt = (event: Event) => {
      event.preventDefault();
      setInstallEvent(event as InstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", onBeforeInstallPrompt);
    return () =>
      window.removeEventListener("beforeinstallprompt", onBeforeInstallPrompt);
  }, []);

  async function install() {
    if (!installEvent) {
      setShowIosHelp((open) => !open);
      return;
    }
    setError("");
    try {
      await installEvent.prompt();
      await installEvent.userChoice;
      setInstallEvent(null);
    } catch {
      setInstallEvent(null);
      setError(t("installFailed"));
    }
  }

  if (!installEvent && !showIosHelp) return null;

  return (
    <aside className="pwa-install" aria-label={t("installApp")}>
      {showIosHelp && (
        <div className="pwa-install-card">
          <button
            className="pwa-install-close"
            type="button"
            onClick={() => setShowIosHelp(false)}
            aria-label={t("dismiss")}
          >
            ×
          </button>
          <strong>{t("installApp")}</strong>
          <p>{t("installIosHelp")}</p>
        </div>
      )}
      {error && <p className="pwa-install-error">{error}</p>}
      <button className="button button-dark" type="button" onClick={install}>
        {t("installApp")}
      </button>
    </aside>
  );
}

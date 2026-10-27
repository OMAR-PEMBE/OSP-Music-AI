"use client";

import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import Image from "next/image";
import { AppShell } from "@/components/app-shell";
import { Icon } from "@/components/icon";
import { useLocaleMessages } from "@/components/locale-provider";
import { api, ApiError, type Me } from "@/lib/api";

export function SettingsPage() {
  const { t, locale, setLocale, theme, toggleTheme } = useLocaleMessages();
  const [profile, setProfile] = useState<Me | null>(null);
  const [name, setName] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    api<Me>("/api/me")
      .then((data) => {
        if (!active) return;
        setProfile(data);
        setName(data.display_name);
        setFirstName(data.first_name);
        setLastName(data.last_name);
      })
      .catch((reason: unknown) => {
        if (active)
          setError(
            reason instanceof ApiError ? reason.message : t("errorNetwork"),
          );
      });
    return () => {
      active = false;
    };
  }, [t]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const updated = await api<Me>("/api/me", {
        method: "PATCH",
        body: {
          display_name: name,
          first_name: firstName,
          last_name: lastName,
        },
      });
      setProfile(updated);
      setMessage(t("profileSaved"));
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : t("errorNetwork"));
    } finally {
      setBusy(false);
    }
  }

  async function uploadAvatar(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError("");
    setMessage("");
    const body = new FormData();
    body.set("avatar", file);
    try {
      const updated = await api<Me>("/api/me/avatar", { method: "POST", body });
      setProfile(updated);
      setMessage(t("avatarUpdated"));
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : t("errorNetwork"));
    } finally {
      setBusy(false);
      event.target.value = "";
    }
  }

  return (
    <AppShell>
      <div className="page-heading">
        <div>
          <p className="eyebrow">04 / OSP ACCOUNT</p>
          <h1>{t("settings")}</h1>
          <p>{t("profile")}</p>
        </div>
      </div>
      {error && (
        <div className="feedback error" role="alert">
          {error}
        </div>
      )}
      {message && (
        <div className="feedback success" role="status">
          {message}
        </div>
      )}
      <div className="settings-grid">
        <section className="panel settings-profile">
          <div className="panel-heading">
            <span className="panel-step">01</span>
            <div>
              <h2>{t("profile")}</h2>
              <p>{t("account")}</p>
            </div>
          </div>
          <div className="profile-avatar-row">
            <span className="profile-avatar">
              {profile?.avatar_url ? (
                <Image
                  src={profile.avatar_url}
                  alt=""
                  width={58}
                  height={58}
                  unoptimized
                />
              ) : (
                (profile?.display_name?.[0] ?? "O")
              )}
            </span>
            <label className="button button-outline upload-button">
              {t("uploadAvatar")}
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={uploadAvatar}
                disabled={busy}
              />
            </label>
            <small>{t("avatarHint")}</small>
          </div>
          <form className="form-stack" onSubmit={save}>
            <label className="field">
              <span>{t("accountEmail")}</span>
              <input type="email" value={profile?.email ?? ""} readOnly />
            </label>
            <div className="field-row">
              <label className="field">
                <span>{t("firstName")}</span>
                <input
                  value={firstName}
                  onChange={(event) => setFirstName(event.target.value)}
                  maxLength={50}
                />
              </label>
              <label className="field">
                <span>{t("lastName")}</span>
                <input
                  value={lastName}
                  onChange={(event) => setLastName(event.target.value)}
                  maxLength={50}
                />
              </label>
            </div>
            <label className="field">
              <span>{t("displayName")}</span>
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                maxLength={30}
                required
              />
            </label>
            <button
              className="button button-dark"
              type="submit"
              disabled={busy}
            >
              {busy ? t("loading") : t("saveChanges")} <Icon name="arrow" />
            </button>
          </form>
        </section>
        <section className="panel settings-options">
          <div className="panel-heading">
            <span className="panel-step">02</span>
            <div>
              <h2>{t("theme")}</h2>
              <p>{t("appearanceHint")}</p>
            </div>
          </div>
          <div className="setting-row">
            <div>
              <strong>{t("languageSetting")}</strong>
              <small>{t("language")}</small>
            </div>
            <div className="segmented-control">
              <button
                type="button"
                className={locale === "sw" ? "selected" : ""}
                onClick={() => setLocale("sw")}
              >
                SW
              </button>
              <button
                type="button"
                className={locale === "en" ? "selected" : ""}
                onClick={() => setLocale("en")}
              >
                EN
              </button>
            </div>
          </div>
          <div className="setting-row">
            <div>
              <strong>{t("theme")}</strong>
              <small>{t(theme === "light" ? "themeLight" : "themeDark")}</small>
            </div>
            <button
              type="button"
              className="button button-outline"
              onClick={toggleTheme}
            >
              <Icon name={theme === "light" ? "moon" : "sun"} />
              {t(theme === "light" ? "themeDark" : "themeLight")}
            </button>
          </div>
          <div className="account-status">
            <span
              className={
                profile?.email_verified
                  ? "status-check verified"
                  : "status-check"
              }
            >
              <Icon name="check" />
            </span>
            <div>
              <strong>{t("account")}</strong>
              <small>
                {t(
                  profile?.email_verified
                    ? "emailVerified"
                    : "emailNotVerified",
                )}
              </small>
            </div>
          </div>
        </section>
      </div>
    </AppShell>
  );
}

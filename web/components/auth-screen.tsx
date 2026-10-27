"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { MarketingHeader } from "@/components/marketing-header";
import { Icon } from "@/components/icon";
import { useLocaleMessages } from "@/components/locale-provider";
import { api, ApiError } from "@/lib/api";

export type AuthMode = "login" | "signup" | "forgot" | "reset" | "verify";

export function AuthScreen({
  mode,
  token,
}: {
  mode: AuthMode;
  token?: string;
}) {
  const { t } = useLocaleMessages();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setNotice("");
    setError("");
    const form = new FormData(event.currentTarget);
    const value = (name: string) => String(form.get(name) ?? "").trim();

    try {
      if (mode === "signup") {
        if (value("password") !== value("confirm_password"))
          throw new Error(t("passwordMismatch"));
        try {
          await api("/api/auth/browser/v1/auth/signup", {
            method: "POST",
            body: {
              email: value("email"),
              password: value("password"),
              first_name: value("first_name"),
              last_name: value("last_name"),
              display_name: value("display_name"),
            },
          });
        } catch (signupError) {
          if (!(signupError instanceof ApiError) || signupError.status !== 401)
            throw signupError;
        }
        setNotice(t("signupSuccess"));
      } else if (mode === "login") {
        await api("/api/auth/browser/v1/auth/login", {
          method: "POST",
          body: { email: value("email"), password: value("password") },
        });
        const next =
          new URLSearchParams(window.location.search).get("next") || "/create";
        router.replace(next.startsWith("/") ? next : "/create");
        router.refresh();
      } else if (mode === "forgot") {
        await api("/api/auth/browser/v1/auth/password/request", {
          method: "POST",
          body: { email: value("email") },
        });
        setNotice(t("resetSent"));
      } else if (mode === "reset") {
        const key =
          token || new URLSearchParams(window.location.search).get("key") || "";
        if (value("password") !== value("confirm_password"))
          throw new Error(t("passwordMismatch"));
        await api("/api/auth/browser/v1/auth/password/reset", {
          method: "POST",
          body: { key, password: value("password") },
        });
        setNotice(t("loginSuccess"));
      } else {
        const key =
          token ||
          value("key") ||
          new URLSearchParams(window.location.search).get("key") ||
          "";
        await api("/api/auth/browser/v1/auth/email/verify", {
          method: "POST",
          body: { key },
        });
        setNotice(t("emailVerified"));
      }
    } catch (submitError) {
      if (submitError instanceof ApiError)
        setError(submitError.message || t("errorGeneric"));
      else if (submitError instanceof Error) setError(submitError.message);
      else setError(t("errorGeneric"));
    } finally {
      setBusy(false);
    }
  }

  const heading =
    mode === "login"
      ? t("welcomeBack")
      : mode === "signup"
        ? t("createAccountTitle")
        : mode === "forgot"
          ? t("forgotPassword")
          : mode === "reset"
            ? t("resetPasswordTitle")
            : t("verifyTitle");
  const submitLabel =
    mode === "login"
      ? t("login")
      : mode === "signup"
        ? t("signup")
        : mode === "forgot"
          ? t("sendReset")
          : mode === "reset"
            ? t("save")
            : t("verifyAction");

  return (
    <div className="marketing-page auth-page">
      <MarketingHeader />
      <main className="auth-layout">
        <section className="auth-story">
          <div className="auth-story-mark">
            <Icon name="sparkle" />
          </div>
          <p className="eyebrow">{t("heroEyebrow")}</p>
          <h1>{t("heroTitle")}</h1>
          <p>{t("heroBody")}</p>
          <div className="auth-story-line">
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
          </div>
        </section>
        <section className="auth-card">
          <p className="eyebrow">{t("brand")}</p>
          <h2>{heading}</h2>
          <p className="auth-subtitle">
            {mode === "verify" ? t("verifyBody") : t("authSubtitle")}
          </p>
          {notice && (
            <div className="feedback success" role="status">
              {notice}
            </div>
          )}
          {error && (
            <div className="feedback error" role="alert">
              {error}
            </div>
          )}
          <form onSubmit={submit} className="form-stack">
            {mode === "signup" && (
              <>
                <div className="form-grid-two">
                  <Field name="first_name" label={t("firstName")} required />
                  <Field name="last_name" label={t("lastName")} required />
                </div>
                <Field name="display_name" label={t("displayName")} required />
              </>
            )}
            {mode !== "verify" && (
              <Field
                name="email"
                label={t("email")}
                type="email"
                required
                autoComplete="email"
              />
            )}
            {mode === "verify" && (
              <Field
                name="key"
                label={t("verifyKey")}
                defaultValue={token ?? ""}
                required
              />
            )}
            {mode === "login" && (
              <Field
                name="password"
                label={t("password")}
                type="password"
                required
                autoComplete="current-password"
              />
            )}
            {(mode === "signup" || mode === "reset") && (
              <>
                <Field
                  name="password"
                  label={t("password")}
                  type="password"
                  required
                  autoComplete={
                    mode === "signup" ? "new-password" : "new-password"
                  }
                />
                <Field
                  name="confirm_password"
                  label={t("confirmPassword")}
                  type="password"
                  required
                  autoComplete="new-password"
                />
              </>
            )}
            <button
              className="button button-dark full-width"
              type="submit"
              disabled={busy}
            >
              {busy ? t("loading") : submitLabel}
              <Icon name="arrow" />
            </button>
          </form>
          <div className="auth-links">
            {mode === "login" && (
              <>
                <Link href="/forgot-password">{t("forgotPassword")}</Link>
                <span>
                  {t("noAccount")} <Link href="/signup">{t("signup")}</Link>
                </span>
              </>
            )}
            {mode === "signup" && (
              <span>
                {t("hasAccount")} <Link href="/login">{t("login")}</Link>
              </span>
            )}
            {mode === "forgot" && <Link href="/login">{t("back")}</Link>}
            {mode === "reset" && <Link href="/login">{t("login")}</Link>}
            {mode === "verify" && <Link href="/login">{t("login")}</Link>}
          </div>
        </section>
      </main>
    </div>
  );
}

function Field({
  name,
  label,
  type = "text",
  required = false,
  autoComplete,
  defaultValue,
}: {
  name: string;
  label: string;
  type?: string;
  required?: boolean;
  autoComplete?: string;
  defaultValue?: string;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        name={name}
        type={type}
        required={required}
        autoComplete={autoComplete}
        defaultValue={defaultValue}
      />
    </label>
  );
}

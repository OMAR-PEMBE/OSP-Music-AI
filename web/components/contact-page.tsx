"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { MarketingHeader } from "@/components/marketing-header";
import { useLocaleMessages } from "@/components/locale-provider";
import { api, ApiError } from "@/lib/api";

export function ContactPage() {
  const { t } = useLocaleMessages();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setSent(false);
    try {
      await api("/api/support", {
        method: "POST",
        body: { name, email, message },
      });
      setName("");
      setEmail("");
      setMessage("");
      setSent(true);
    } catch (reason) {
      setError(
        reason instanceof ApiError && reason.status === 429
          ? t("contactRateLimit")
          : reason instanceof ApiError && reason.status === 400
            ? t("contactMinLength")
            : t("contactError"),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="marketing-page">
      <MarketingHeader />
      <main className="information-page">
        <p className="eyebrow">{t("contactUs")}</p>
        <h1>{t("contactTitle")}</h1>
        <p className="information-intro">{t("contactIntro")}</p>
        {sent && (
          <div className="feedback success" role="status">
            {t("contactSuccess")}
          </div>
        )}
        {error && (
          <div className="feedback error" role="alert">
            {error}
          </div>
        )}
        <form className="panel contact-form form-stack" onSubmit={submit}>
          <label className="field">
            <span>{t("contactName")}</span>
            <input
              autoComplete="name"
              maxLength={100}
              onChange={(event) => setName(event.target.value)}
              required
              value={name}
            />
          </label>
          <label className="field">
            <span>{t("contactEmail")}</span>
            <input
              autoComplete="email"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>
          <label className="field">
            <span>{t("contactMessage")}</span>
            <textarea
              maxLength={2000}
              minLength={10}
              onChange={(event) => setMessage(event.target.value)}
              required
              rows={7}
              value={message}
            />
          </label>
          <button className="button button-dark" disabled={busy} type="submit">
            {busy ? t("contactSending") : t("contactSubmit")}
          </button>
        </form>
        <Link className="information-back" href="/faq">
          {t("faqPageTitle")}
        </Link>
      </main>
    </div>
  );
}

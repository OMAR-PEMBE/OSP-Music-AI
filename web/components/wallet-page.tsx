"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import { AppShell } from "@/components/app-shell";
import { Icon } from "@/components/icon";
import { useLocaleMessages } from "@/components/locale-provider";
import {
  api,
  ApiError,
  formatDate,
  formatTzs,
  type ApiConfig,
  type Me,
  type PageResult,
  type Transaction,
} from "@/lib/api";

type Payment = {
  id: string;
  amount_tzs: number;
  phone_masked: string;
  status: "pending" | "completed" | "failed" | "expired" | "voided";
  created_at: string;
  completed_at: string | null;
};

export function WalletPage() {
  const { t, locale } = useLocaleMessages();
  const [config, setConfig] = useState<ApiConfig | null>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [amount, setAmount] = useState("1000");
  const [phone, setPhone] = useState("");
  const [payment, setPayment] = useState<Payment | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const alive = useRef(true);

  const refresh = useCallback(async () => {
    try {
      const [publicConfig, profile, history] = await Promise.all([
        api<ApiConfig>("/api/config"),
        api<Me>("/api/me"),
        api<PageResult<Transaction>>("/api/wallet/transactions?page=1"),
      ]);
      if (!alive.current) return;
      setConfig(publicConfig);
      setMe(profile);
      setTransactions(history.results);
    } catch (refreshError) {
      if (alive.current)
        setError(
          refreshError instanceof ApiError
            ? refreshError.message
            : t("errorNetwork"),
        );
    }
  }, [t]);

  useEffect(() => {
    alive.current = true;
    void refresh();
    return () => {
      alive.current = false;
    };
  }, [refresh]);

  async function submitTopup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const numericAmount = Number(amount);
    setError("");
    setNotice("");
    if (
      !Number.isSafeInteger(numericAmount) ||
      numericAmount < (config?.min_topup_tzs ?? 1000) ||
      numericAmount > (config?.max_topup_tzs ?? 500000)
    ) {
      setError(
        `${t("topUpAmount")}: ${formatTzs(config?.min_topup_tzs ?? 1000)}–${formatTzs(config?.max_topup_tzs ?? 500000)}`,
      );
      return;
    }
    setBusy(true);
    setPayment(null);
    try {
      const created = await api<Payment>("/api/wallet/topups", {
        method: "POST",
        body: { amount_tzs: numericAmount, phone },
      });
      if (alive.current) setPayment(created);
      if (created.status === "completed") {
        setNotice(t("paymentComplete"));
        await refresh();
      } else {
        setNotice(t("paymentPending"));
        await pollPayment(created.id);
      }
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : t("errorNetwork"),
      );
    } finally {
      if (alive.current) setBusy(false);
    }
  }

  async function pollPayment(paymentId: string) {
    for (let attempt = 0; attempt < 60 && alive.current; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 3000));
      if (!alive.current) return;
      try {
        const next = await api<Payment>(`/api/wallet/topups/${paymentId}`);
        if (!alive.current) return;
        setPayment(next);
        if (next.status === "completed") {
          setNotice(t("paymentComplete"));
          await refresh();
          return;
        }
        if (next.status !== "pending") {
          setNotice(t("paymentFailed"));
          return;
        }
      } catch {
        setError(t("errorNetwork"));
        return;
      }
    }
  }

  return (
    <AppShell>
      <div className="page-heading">
        <div>
          <p className="eyebrow">03 / {t("walletEyebrow")}</p>
          <h1>{t("walletTitle")}</h1>
          <p>{t("priceDisclaimer")}</p>
        </div>
        <div className="heading-price wallet-heading-balance">
          <span>{t("balance")}</span>
          <strong>{formatTzs(me?.balance_tzs ?? 0)}</strong>
        </div>
      </div>
      {error && (
        <div className="feedback error" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div
          className={
            payment?.status === "completed"
              ? "feedback success"
              : "feedback info"
          }
          role="status"
        >
          {notice}
        </div>
      )}
      <div className="wallet-grid">
        <section className="panel topup-panel">
          <div className="panel-heading">
            <span className="panel-step">01</span>
            <div>
              <h2>{t("topUp")}</h2>
              <p>{t("mobileMoney")}</p>
            </div>
          </div>
          {config?.payment_demo && (
            <div className="demo-banner">
              <Icon name="sparkle" />
              <span>{t("demoPayment")}</span>
            </div>
          )}
          <form className="form-stack" onSubmit={submitTopup}>
            <div className="field">
              <span>{t("topUpAmount")}</span>
              <div className="amount-presets">
                {(config?.topup_presets_tzs ?? [1000, 3000, 5000, 10000]).map(
                  (preset) => (
                    <button
                      type="button"
                      key={preset}
                      className={
                        amount === String(preset)
                          ? "preset-button selected"
                          : "preset-button"
                      }
                      onClick={() => setAmount(String(preset))}
                    >
                      {formatTzs(preset)}
                    </button>
                  ),
                )}
              </div>
              <input
                type="number"
                min={config?.min_topup_tzs ?? 1000}
                max={config?.max_topup_tzs ?? 500000}
                step="1"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                required
              />
            </div>
            <label className="field">
              <span>{t("phone")}</span>
              <input
                type="tel"
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
                placeholder={t("phoneHint")}
                autoComplete="tel"
                maxLength={32}
                required
              />
            </label>
            <p className="form-note">
              <Icon name="check" />
              {t("nonRefundableNotice")}
            </p>
            <button
              className="button button-dark full-width"
              type="submit"
              disabled={busy || !me?.email_verified}
            >
              {busy ? t("loading") : t("payNow")} <Icon name="arrow" />
            </button>
          </form>
          {payment && (
            <div className="payment-ticket">
              <div>
                <span>{t("topUp")}</span>
                <strong>{formatTzs(payment.amount_tzs)}</strong>
              </div>
              <div>
                <span>{t("phone")}</span>
                <strong>{payment.phone_masked}</strong>
              </div>
              <div>
                <span>{t(`paymentStatus_${payment.status}`)}</span>
                <strong>{formatDate(payment.created_at, locale)}</strong>
              </div>
            </div>
          )}
        </section>
        <aside className="wallet-side-card">
          <div className="wallet-orbit">
            <span />
            <span />
            <span />
          </div>
          <p className="eyebrow">OSP / TZS</p>
          <h2>{formatTzs(me?.balance_tzs ?? 0)}</h2>
          <p>{t("balance")}</p>
          <div className="summary-divider" />
          <p className="wallet-side-note">{t("priceDisclaimer")}</p>
          <Link className="inline-arrow" href="/create">
            {t("create")} <Icon name="arrow" />
          </Link>
        </aside>
      </div>
      <section className="panel transaction-panel">
        <div className="panel-heading">
          <span className="panel-step">02</span>
          <div>
            <h2>{t("transactions")}</h2>
            <p>{t("walletTitle")}</p>
          </div>
        </div>
        {transactions.length === 0 ? (
          <p className="empty-inline">{t("noTransactions")}</p>
        ) : (
          <div className="transaction-list">
            {transactions.map((entry) => (
              <article className="transaction-row" key={entry.id}>
                <span
                  className={`transaction-icon ${entry.amount_tzs > 0 ? "positive" : "negative"}`}
                >
                  <Icon name={entry.amount_tzs > 0 ? "check" : "music"} />
                </span>
                <div className="transaction-copy">
                  <strong>{t(`transaction_${entry.type}` as never)}</strong>
                  <small>
                    {entry.song_title || formatDate(entry.created_at, locale)}
                  </small>
                </div>
                <div className="transaction-amount">
                  <strong
                    className={entry.amount_tzs > 0 ? "amount-positive" : ""}
                  >
                    {entry.amount_tzs > 0 ? "+" : ""}
                    {formatTzs(entry.amount_tzs)}
                  </strong>
                  <small>{formatTzs(entry.balance_after_tzs)}</small>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </AppShell>
  );
}

"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Icon } from "@/components/icon";
import { MarketingHeader } from "@/components/marketing-header";
import { useLocaleMessages } from "@/components/locale-provider";
import { api, formatTzs, type ApiConfig } from "@/lib/api";

export function LandingPage() {
  const { t } = useLocaleMessages();
  const [price, setPrice] = useState(1000);
  useEffect(() => {
    api<ApiConfig>("/api/config")
      .then((config) => setPrice(config.song_price_tzs))
      .catch(() => undefined);
  }, []);

  return (
    <div className="marketing-page">
      <MarketingHeader />
      <main>
        <section className="hero-section">
          <div className="hero-copy">
            <p className="eyebrow">
              <span className="eyebrow-dot" />
              {t("heroEyebrow")}
            </p>
            <h1>{t("heroTitle")}</h1>
            <p className="hero-description">{t("heroBody")}</p>
            <div className="hero-actions">
              <Link className="button button-lime" href="/signup">
                {t("getStarted")} <Icon name="arrow" />
              </Link>
              <span className="hero-trust">
                <Icon name="check" /> {t("priceUnit")}
              </span>
            </div>
            <div className="hero-proof">
              <div className="proof-avatars">
                <span>O</span>
                <span>A</span>
                <span>M</span>
              </div>
              <p>
                <strong>{formatTzs(price)}</strong>
                <span>{t("priceLabel").toLowerCase()}</span>
              </p>
            </div>
          </div>
          <div className="hero-art" aria-label={t("sampleTitle")}>
            <div className="art-orbit orbit-one" />
            <div className="art-orbit orbit-two" />
            <div className="art-star">
              <Icon name="sparkle" />
            </div>
            <div className="art-note note-one">♫</div>
            <div className="art-note note-two">♪</div>
            <div className="art-disc">
              <div className="disc-grooves">
                <span />
                <span />
                <span />
              </div>
              <div className="disc-center">
                <Icon name="music" />
              </div>
            </div>
            <div className="art-caption">
              <span className="live-dot" /> OSP SOUND STUDIO
            </div>
            <div className="art-card">
              <span className="art-card-icon">
                <Icon name="play" />
              </span>
              <div>
                <strong>{t("sampleTitle")}</strong>
                <small>{t("priceUnit")}</small>
              </div>
              <span className="waveform">
                <i />
                <i />
                <i />
                <i />
                <i />
                <i />
                <i />
                <i />
                <i />
              </span>
            </div>
          </div>
        </section>

        <section className="how-section section-wrap" id="how">
          <div className="section-heading">
            <p className="eyebrow">01 / {t("howItWorks")}</p>
            <h2>{t("howItWorks")}</h2>
          </div>
          <div className="steps-grid">
            {(
              [
                ["01", "stepOne", "stepOneBody", "sparkle"],
                ["02", "stepTwo", "stepTwoBody", "settings"],
                ["03", "stepThree", "stepThreeBody", "music"],
              ] as const
            ).map(([number, title, body, icon]) => (
              <article className="step-card" key={number}>
                <div className="step-top">
                  <span>{number}</span>
                  <Icon name={icon} />
                </div>
                <h3>{t(title)}</h3>
                <p>{t(body)}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="feature-section">
          <div className="feature-visual">
            <div className="feature-disc">
              <span />
              <span />
              <span />
            </div>
            <div className="feature-equalizer">
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
            </div>
            <div className="feature-stamp">
              2×<small>VERSIONS</small>
            </div>
          </div>
          <div className="feature-copy">
            <p className="eyebrow">02 / {t("sampleLabel")}</p>
            <h2>{t("sampleTitle")}</h2>
            <p>{t("sampleBody")}</p>
            <Link href="/signup" className="inline-arrow">
              {t("getStarted")} <Icon name="arrow" />
            </Link>
          </div>
        </section>

        <section className="price-band">
          <div>
            <p className="eyebrow">03 / {t("priceLabel")}</p>
            <h2>{formatTzs(price)}</h2>
            <p>
              {t("priceUnit")} <span className="price-separator">·</span>{" "}
              {t("mobileMoney")}
            </p>
          </div>
          <Link href="/signup" className="button button-dark">
            {t("getStarted")} <Icon name="arrow" />
          </Link>
        </section>

        <section className="faq-section section-wrap" id="faq">
          <div className="section-heading">
            <p className="eyebrow">04 / FAQ</p>
            <h2>{t("faqTitle")}</h2>
          </div>
          <div className="faq-list">
            <article>
              <h3>{t("faqOneQ")}</h3>
              <p>{t("faqOneA")}</p>
            </article>
            <article>
              <h3>{t("faqTwoQ")}</h3>
              <p>{t("faqTwoA")}</p>
            </article>
          </div>
        </section>
      </main>
      <footer className="marketing-footer" id="footer">
        <Link className="brand-lockup" href="/">
          <span className="brand-glyph">
            <Icon name="music" />
          </span>
          <span>{t("brand")}</span>
        </Link>
        <p>{t("footerNote")}</p>
        <div className="footer-links">
          <Link href="/signup">{t("getStarted")}</Link>
          <Link href="/login">{t("login")}</Link>
          <a href="#faq">{t("help")}</a>
        </div>
        <small>{t("copyright")}</small>
      </footer>
    </div>
  );
}

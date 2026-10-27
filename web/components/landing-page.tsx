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
    <div className="marketing-page" id="top">
      <MarketingHeader />
      <main>
        <section className="landing-hero">
          <div className="landing-hero-copy">
            <p className="landing-badge">
              <Icon name="sparkle" /> {t("heroEyebrow")}
            </p>
            <h1>
              {t("landingHeroPrefix")} <span>{t("landingHeroAccent")}</span>
            </h1>
            <p className="landing-hero-description">{t("heroBody")}</p>
            <Link className="button landing-primary-button" href="/signup">
              {t("landingHeroCta")} <Icon name="arrow" />
            </Link>
          </div>
          <div className="landing-hero-art" aria-hidden="true">
            <div className="landing-wave landing-wave-left">
              {Array.from({ length: 25 }, (_, index) => (
                <i key={index} />
              ))}
            </div>
            <div className="landing-wave landing-wave-right">
              {Array.from({ length: 25 }, (_, index) => (
                <i key={index} />
              ))}
            </div>
            <div className="landing-app-icon">
              <span className="brand-glyph">
                <i />
                <i />
                <i />
                <i />
                <i />
              </span>
            </div>
          </div>
        </section>

        <section className="landing-benefits" aria-label={t("landingBenefits")}>
          {(
            [
              ["music", "landingBenefitIdea", "landingBenefitIdeaBody"],
              ["settings", "landingBenefitStyles", "landingBenefitStylesBody"],
              [
                "sparkle",
                "landingBenefitVersions",
                "landingBenefitVersionsBody",
              ],
              ["check", "landingBenefitPrivate", "landingBenefitPrivateBody"],
            ] as const
          ).map(([icon, title, body]) => (
            <article className="landing-benefit" key={title}>
              <Icon name={icon} />
              <div>
                <h2>{t(title)}</h2>
                <p>{t(body)}</p>
              </div>
            </article>
          ))}
        </section>

        <section className="landing-how" id="how">
          <div className="landing-section-heading">
            <h2>{t("howItWorks")}</h2>
            <p>{t("landingStepsIntro")}</p>
          </div>
          <div className="landing-step-grid">
            {(
              [
                ["01", "stepOne", "stepOneBody", "music"],
                ["02", "stepTwo", "stepTwoBody", "settings"],
                ["03", "stepThree", "stepThreeBody", "music"],
              ] as const
            ).map(([number, title, body, icon]) => (
              <div className="landing-step-wrap" key={number}>
                <article className="landing-step-card">
                  <span className="landing-step-icon">
                    <Icon name={icon} />
                  </span>
                  <div>
                    <h3>
                      {number}. {t(title)}
                    </h3>
                    <p>{t(body)}</p>
                  </div>
                </article>
                {number !== "03" && (
                  <Icon
                    className="landing-step-arrow"
                    name="arrow"
                    aria-hidden="true"
                  />
                )}
              </div>
            ))}
          </div>
          <Link
            className="button landing-primary-button landing-bottom-cta"
            href="/signup"
          >
            {t("landingBottomCta")} <Icon name="arrow" />
          </Link>
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
              2×<small>{t("versions")}</small>
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

        <section className="price-band" id="pricing">
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
            <p className="eyebrow">04 / {t("faqShort")}</p>
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
          <span className="brand-glyph" aria-hidden="true">
            <i />
            <i />
            <i />
            <i />
            <i />
          </span>
          <span>{t("brand")}</span>
        </Link>
        <p>{t("footerNote")}</p>
        <div className="footer-links">
          <Link href="/signup">{t("getStarted")}</Link>
          <Link href="/login">{t("login")}</Link>
          <Link href="/faq">{t("help")}</Link>
          <Link href="/contact">{t("contactUs")}</Link>
          <Link href="/terms">{t("termsLink")}</Link>
          <Link href="/privacy">{t("privacyLink")}</Link>
          <Link href="/refunds">{t("refundLink")}</Link>
        </div>
        <small>{t("copyright")}</small>
      </footer>
    </div>
  );
}

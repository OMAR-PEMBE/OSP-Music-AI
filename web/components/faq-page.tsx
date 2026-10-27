"use client";

import Link from "next/link";
import { MarketingHeader } from "@/components/marketing-header";
import { useLocaleMessages } from "@/components/locale-provider";

const faqKeys = [
  ["faqOneQ", "faqOneA"],
  ["faqTwoQ", "faqTwoA"],
  ["faqThreeQ", "faqThreeA"],
  ["faqFourQ", "faqFourA"],
  ["faqFiveQ", "faqFiveA"],
  ["faqSixQ", "faqSixA"],
  ["faqSevenQ", "faqSevenA"],
] as const;

export function FaqPage() {
  const { t } = useLocaleMessages();

  return (
    <div className="marketing-page">
      <MarketingHeader />
      <main className="information-page">
        <p className="eyebrow">{t("faqShort")}</p>
        <h1>{t("faqPageTitle")}</h1>
        <p className="information-intro">{t("faqPageIntro")}</p>
        <div className="information-faq">
          {faqKeys.map(([question, answer]) => (
            <article key={question}>
              <h2>{t(question)}</h2>
              <p>{t(answer)}</p>
            </article>
          ))}
        </div>
        <Link className="button button-dark" href="/contact">
          {t("contactUs")}
        </Link>
      </main>
    </div>
  );
}

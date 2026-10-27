"use client";

import Link from "next/link";
import { MarketingHeader } from "@/components/marketing-header";
import { useLocaleMessages } from "@/components/locale-provider";

const legalDocuments = {
  terms: {
    title: "termsPageTitle",
    sections: [
      ["termsIntroTitle", "termsIntroBody"],
      ["termsWalletTitle", "termsWalletBody"],
      ["termsMusicTitle", "termsMusicBody"],
      ["termsDeletionTitle", "termsDeletionBody"],
    ],
  },
  privacy: {
    title: "privacyPageTitle",
    sections: [
      ["privacyDataTitle", "privacyDataBody"],
      ["privacyUseTitle", "privacyUseBody"],
      ["privacyStorageTitle", "privacyStorageBody"],
      ["privacyContactTitle", "privacyContactBody"],
    ],
  },
  refunds: {
    title: "refundPageTitle",
    sections: [
      ["refundTopupsTitle", "refundTopupsBody"],
      ["refundSongsTitle", "refundSongsBody"],
      ["refundDeletionTitle", "refundDeletionBody"],
    ],
  },
} as const;

type LegalDocument = keyof typeof legalDocuments;

export function LegalPage({ document }: { document: LegalDocument }) {
  const { t } = useLocaleMessages();
  const content = legalDocuments[document];

  return (
    <div className="marketing-page">
      <MarketingHeader />
      <main className="information-page legal-page">
        <p className="eyebrow">{t("brand")}</p>
        <h1>{t(content.title)}</h1>
        <p className="feedback info legal-draft-notice" role="note">
          {t("legalDraftNotice")}
        </p>
        <div className="information-faq">
          {content.sections.map(([heading, body]) => (
            <article key={heading}>
              <h2>{t(heading)}</h2>
              <p>{t(body)}</p>
            </article>
          ))}
        </div>
        <div className="legal-page-links">
          <Link className="information-back" href="/">
            {t("legalBackHome")}
          </Link>
          <Link className="information-back" href="/contact">
            {t("contactUs")}
          </Link>
        </div>
      </main>
    </div>
  );
}

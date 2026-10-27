"use client";

import { useEffect, useState } from "react";
import { useLocaleMessages } from "@/components/locale-provider";
import { api, type ApiConfig } from "@/lib/api";

export function WhatsAppSupportButton() {
  const { t } = useLocaleMessages();
  const [phone, setPhone] = useState("");

  useEffect(() => {
    api<ApiConfig>("/api/config")
      .then((config) => {
        const digits = config.support_whatsapp.replace(/\D/g, "");
        if (digits.length >= 8) setPhone(digits);
      })
      .catch(() => setPhone(""));
  }, []);

  if (!phone) return null;

  return (
    <a
      className="whatsapp-support"
      href={`https://wa.me/${phone}`}
      target="_blank"
      rel="noreferrer"
      aria-label={t("whatsappSupport")}
    >
      {t("whatsappSupport")}
    </a>
  );
}

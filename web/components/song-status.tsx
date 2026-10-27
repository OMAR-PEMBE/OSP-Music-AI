"use client";

import { useLocaleMessages } from "@/components/locale-provider";
import type { SongJob } from "@/lib/api";

export function SongStatus({ status }: { status: SongJob["status"] }) {
  const { t } = useLocaleMessages();
  const key = `status_${status}` as const;
  const final = ["ready", "partial", "failed"].includes(status);
  return (
    <span
      className={`status-pill ${final ? `status-${status}` : "status-progress"}`}
    >
      <i />
      {t(key)}
    </span>
  );
}

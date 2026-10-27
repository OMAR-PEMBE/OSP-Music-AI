"use client";

import { useEffect, useState } from "react";

type Health = { db: string; redis: string };

export default function Home() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then(async (response) => {
        const data = (await response.json()) as Health;
        setHealth(data);
        if (!response.ok) setError("Health check reported a problem.");
      })
      .catch(() => setError("Could not reach the API."));
  }, []);

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-5 px-6">
      <p className="text-sm font-semibold uppercase tracking-widest text-violet-700">
        OSP Music AI
      </p>
      <h1 className="text-4xl font-bold">Karibu</h1>
      <p className="text-slate-600">
        Andika wazo lako la wimbo. Tutakusaidia kulifanya muziki.
      </p>
      <section
        className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
        aria-live="polite"
      >
        <h2 className="font-semibold">Hali ya huduma</h2>
        {health ? (
          <p className="mt-2">
            db: {health.db} · redis: {health.redis}
          </p>
        ) : (
          <p className="mt-2">Inakagua…</p>
        )}
        {error && <p className="mt-2 text-red-700">{error}</p>}
      </section>
    </main>
  );
}

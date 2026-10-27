"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { Icon } from "@/components/icon";
import { useLocaleMessages } from "@/components/locale-provider";
import {
  api,
  ApiError,
  formatTzs,
  type ApiConfig,
  type Me,
  type SongJob,
} from "@/lib/api";

const genres = [
  "bongo_flava",
  "rnb",
  "afrobeats",
  "amapiano",
  "gospel",
  "hiphop",
  "other",
];

export function CreatePage() {
  const { t } = useLocaleMessages();
  const router = useRouter();
  const [config, setConfig] = useState<ApiConfig | null>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [idea, setIdea] = useState("");
  const [genre, setGenre] = useState("bongo_flava");
  const [genreOther, setGenreOther] = useState("");
  const [language, setLanguage] = useState("sw");
  const [voice, setVoice] = useState("auto");
  const [lyrics, setLyrics] = useState("");
  const [remainingLyrics, setRemainingLyrics] = useState<number | null>(null);
  const [idempotencyKey, setIdempotencyKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [lyricsBusy, setLyricsBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    setIdempotencyKey(crypto.randomUUID());
    api<ApiConfig>("/api/config")
      .then(setConfig)
      .catch(() => setError(t("errorNetwork")));
    api<Me>("/api/me")
      .then(setMe)
      .catch(() => undefined);
  }, [t]);

  const genreLabels = useMemo(
    () => ({
      bongo_flava: t("genre_bongo_flava"),
      rnb: t("genre_rnb"),
      afrobeats: t("genre_afrobeats"),
      amapiano: t("genre_amapiano"),
      gospel: t("genre_gospel"),
      hiphop: t("genre_hiphop"),
      other: t("genre_other"),
    }),
    [t],
  );

  async function writeLyrics() {
    if (idea.trim().length < 3) {
      setError(t("ideaRequired"));
      return;
    }
    setLyricsBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await api<{
        title: string;
        lyrics: string;
        remaining_today: number;
      }>("/api/lyrics", {
        method: "POST",
        body: { idea: idea.trim(), genre, genre_other: genreOther, language },
      });
      setLyrics(result.lyrics);
      setRemainingLyrics(result.remaining_today);
      setNotice(result.title);
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : t("errorNetwork"),
      );
    } finally {
      setLyricsBusy(false);
    }
  }

  async function createSong(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setNotice("");
    if (idea.trim().length < 3) {
      setError(t("ideaRequired"));
      return;
    }
    if (genre === "other" && !genreOther.trim()) {
      setError(t("otherGenreRequired"));
      return;
    }
    if (!config?.generation_enabled) {
      setError(t("generationDisabled"));
      return;
    }
    setBusy(true);
    try {
      const job = await api<SongJob>("/api/songs", {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey || crypto.randomUUID() },
        body: {
          idea: idea.trim(),
          genre,
          genre_other: genre === "other" ? genreOther.trim() : "",
          language,
          voice,
          lyrics,
        },
      });
      router.push(`/music/${job.id}`);
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 402) {
        setError(t("insufficient_balance" as never));
      } else {
        setError(
          requestError instanceof ApiError
            ? requestError.message
            : t("errorNetwork"),
        );
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <div className="page-heading create-heading">
        <div>
          <p className="eyebrow">01 / {t("studioEyebrow")}</p>
          <h1>{t("create")}</h1>
          <p>{t("heroBody")}</p>
        </div>
        <div className="heading-price">
          <span>{t("priceLabel")}</span>
          <strong>{formatTzs(config?.song_price_tzs ?? 1000)}</strong>
          <small>{t("priceUnit")}</small>
        </div>
      </div>
      {!me?.email_verified && me && (
        <div className="notice-banner inline-notice">
          {t("emailNotVerified")}{" "}
          <Link href="/verify-email">{t("verifyAction")}</Link>
        </div>
      )}
      {error && (
        <div className="feedback error" role="alert">
          {error}
          {error === t("insufficient_balance" as never) && (
            <>
              {" "}
              <Link href="/wallet">{t("topUpFirst")}</Link>
            </>
          )}
        </div>
      )}
      {notice && (
        <div className="feedback success" role="status">
          {notice}
        </div>
      )}
      <form className="create-grid" onSubmit={createSong}>
        <section className="panel create-form-panel">
          <div className="panel-heading">
            <span className="panel-step">01</span>
            <div>
              <h2>{t("idea")}</h2>
              <p>{t("stepOneBody")}</p>
            </div>
          </div>
          <label className="field">
            <span>{t("idea")}</span>
            <textarea
              value={idea}
              onChange={(event) => setIdea(event.target.value)}
              placeholder={t("ideaPlaceholder")}
              rows={4}
              maxLength={1000}
              required
              minLength={3}
            />
          </label>
          <div className="field-row">
            <label className="field">
              <span>{t("genre")}</span>
              <select
                value={genre}
                onChange={(event) => setGenre(event.target.value)}
              >
                {genres.map((item) => (
                  <option key={item} value={item}>
                    {genreLabels[item as keyof typeof genreLabels]}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>{t("language")}</span>
              <select
                value={language}
                onChange={(event) => setLanguage(event.target.value)}
              >
                <option value="sw">{t("language_sw")}</option>
                <option value="en">{t("language_en")}</option>
                <option value="mixed">{t("language_mixed")}</option>
              </select>
            </label>
          </div>
          {genre === "other" && (
            <label className="field">
              <span>{t("genreOtherLabel")}</span>
              <input
                value={genreOther}
                onChange={(event) => setGenreOther(event.target.value)}
                maxLength={30}
                required
              />
            </label>
          )}
          <label className="field">
            <span>{t("voice")}</span>
            <select
              value={voice}
              onChange={(event) => setVoice(event.target.value)}
            >
              <option value="auto">{t("voice_auto")}</option>
              <option value="male">{t("voice_male")}</option>
              <option value="female">{t("voice_female")}</option>
            </select>
          </label>
          <label className="field">
            <span>{t("lyrics")}</span>
            <textarea
              value={lyrics}
              onChange={(event) => setLyrics(event.target.value)}
              placeholder={t("lyricsPlaceholder")}
              rows={6}
              maxLength={5000}
            />
          </label>
          <div className="lyrics-tools">
            <span>
              {t("lyricsHint")}
              {remainingLyrics !== null && ` · ${remainingLyrics}`}
            </span>
            <button
              className="button button-soft"
              type="button"
              onClick={writeLyrics}
              disabled={lyricsBusy || !idea.trim()}
            >
              <Icon name="sparkle" />
              {lyricsBusy ? t("loading") : t("writeLyrics")}
            </button>
          </div>
        </section>
        <aside className="create-summary">
          <section className="summary-card dark-panel">
            <p className="eyebrow">02 / {t("priceLabel")}</p>
            <h2>{formatTzs(config?.song_price_tzs ?? 1000)}</h2>
            <p>{t("priceUnit")}</p>
            <div className="summary-divider" />
            <div className="summary-balance">
              <span>{t("balance")}</span>
              <strong>{formatTzs(me?.balance_tzs ?? 0)}</strong>
            </div>
            <div className="summary-mini">
              <span>
                <Icon name="check" /> {t("versionA")}
              </span>
              <span>
                <Icon name="check" /> {t("versionB")}
              </span>
            </div>
            {me && me.balance_tzs < (config?.song_price_tzs ?? 1000) ? (
              <Link href="/wallet" className="button button-lime full-width">
                {t("topUpFirst")} <Icon name="arrow" />
              </Link>
            ) : (
              <button
                type="submit"
                disabled={
                  busy || !config?.generation_enabled || !me?.email_verified
                }
                className="button button-lime full-width"
              >
                {busy ? t("loading") : t("generate")} <Icon name="arrow" />
              </button>
            )}
          </section>
          <p className="summary-note">
            <Icon name="check" /> {t("doubleChargeNote" as never)}
          </p>
        </aside>
      </form>
    </AppShell>
  );
}

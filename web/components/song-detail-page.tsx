"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { Icon } from "@/components/icon";
import { SongStatus } from "@/components/song-status";
import { useLocaleMessages } from "@/components/locale-provider";
import { api, ApiError, formatDate, type SongJob } from "@/lib/api";

export function SongDetailPage({ id }: { id: string }) {
  const { t, locale } = useLocaleMessages();
  const router = useRouter();
  const [song, setSong] = useState<SongJob | null>(null);
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const genreLabel =
    (
      {
        bongo_flava: t("genre_bongo_flava"),
        rnb: t("genre_rnb"),
        afrobeats: t("genre_afrobeats"),
        amapiano: t("genre_amapiano"),
        gospel: t("genre_gospel"),
        hiphop: t("genre_hiphop"),
        other: t("genre_other"),
      } as Record<string, string>
    )[song?.genre ?? ""] ?? song?.genre;

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let finishedNoticeShown = false;
    async function load() {
      try {
        const result = await api<SongJob>(`/api/songs/${id}`);
        if (!alive) return;
        setSong(result);
        setTitle(result.title);
        setLoading(false);
        const final = ["ready", "partial", "failed"].includes(result.status);
        if (final && !finishedNoticeShown) {
          finishedNoticeShown = true;
          setNotice(t("songReadyToast" as never));
        }
        if (!final) timer = setTimeout(load, 3000);
      } catch (requestError) {
        if (!alive) return;
        setLoading(false);
        setError(
          requestError instanceof ApiError
            ? requestError.message
            : t("errorNetwork"),
        );
      }
    }
    void load();
    return () => {
      alive = false;
      if (timer) clearTimeout(timer);
    };
  }, [id, t]);

  async function rename(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const updated = await api<SongJob>(`/api/songs/${id}`, {
        method: "PATCH",
        body: { title },
      });
      setSong(updated);
      setNotice(t("saveChanges"));
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : t("errorNetwork"),
      );
    } finally {
      setSaving(false);
    }
  }

  async function deleteSong() {
    if (!window.confirm(t("deleteConfirm"))) return;
    try {
      await api(`/api/songs/${id}`, { method: "DELETE" });
      router.replace("/music");
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : t("errorNetwork"),
      );
    }
  }

  return (
    <AppShell>
      <Link href="/music" className="back-link">
        <Icon name="arrow" />
        {t("mySongs")}
      </Link>
      {error && (
        <div className="feedback error" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="feedback success" role="status">
          {notice}
        </div>
      )}
      {loading ? (
        <div className="empty-card">
          <p>{t("loading")}</p>
        </div>
      ) : !song ? (
        <div className="empty-card">
          <h2>{error || t("errorGeneric")}</h2>
          <Link href="/music" className="button button-dark">
            {t("back")}
          </Link>
        </div>
      ) : (
        <>
          <section className="song-detail-hero">
            <div className="detail-artwork">
              <Icon name="music" />
              <span className="detail-art-orbit" />
            </div>
            <div className="detail-copy">
              <p className="eyebrow">
                {t("songDetail")} / {formatDate(song.created_at, locale)}
              </p>
              <h1>{song.title || t("sampleTitle")}</h1>
              <SongStatus status={song.status} />
              <p className="detail-meta">
                {genreLabel} <span>·</span>{" "}
                {t(
                  song.language === "sw"
                    ? "language_sw"
                    : song.language === "en"
                      ? "language_en"
                      : "language_mixed",
                )}
              </p>
            </div>
          </section>
          <section className="panel versions-panel">
            <div className="panel-heading">
              <span className="panel-step">02</span>
              <div>
                <h2>{t("music")}</h2>
                <p>{t("stepThreeBody")}</p>
              </div>
            </div>
            <div className="version-grid">
              {[0, 1].map((index) => {
                const version = song.versions.find(
                  (item) => item.index === index,
                );
                const versionLabel =
                  index === 0 ? t("versionA") : t("versionB");
                const streamUrl =
                  version?.stream_url && !version.stream_url.startsWith("fake:")
                    ? version.stream_url
                    : null;
                const audioSrc =
                  version?.status === "ready"
                    ? `/api/songs/${song.id}/versions/${index}/audio`
                    : streamUrl;
                return (
                  <article className="version-card" key={index}>
                    <div className="version-card-top">
                      <span>{versionLabel}</span>
                      <span
                        className={`version-state ${version?.status ?? "pending"}`}
                      >
                        {version?.status === "ready"
                          ? t("status_ready")
                          : version?.status === "failed"
                            ? t("status_failed")
                            : t("status_queued")}
                      </span>
                    </div>
                    <div className="version-wave">
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
                      <i />
                      <i />
                      <i />
                    </div>
                    {audioSrc ? (
                      <audio
                        controls
                        preload="none"
                        aria-label={versionLabel}
                        src={audioSrc}
                      />
                    ) : (
                      <div className="audio-placeholder">
                        <Icon
                          name={version?.status === "failed" ? "close" : "play"}
                        />
                        <span>
                          {version?.status === "failed"
                            ? t("status_failed")
                            : t("audioUnavailable")}
                        </span>
                      </div>
                    )}
                    {version?.status === "ready" && (
                      <a
                        className="button button-soft download-button"
                        href={`/api/songs/${song.id}/versions/${index}/audio?download=1`}
                      >
                        <Icon name="download" />
                        {t("download")}
                      </a>
                    )}
                  </article>
                );
              })}
            </div>
          </section>
          <section className="panel lyrics-panel">
            <div className="panel-heading">
              <span className="panel-step">03</span>
              <div>
                <h2>{t("lyricsUsed")}</h2>
                <p>
                  {t("idea")}: {song.title}
                </p>
              </div>
            </div>
            <pre>{song.lyrics || "—"}</pre>
          </section>
          <div className="song-management">
            <form className="panel rename-panel" onSubmit={rename}>
              <label className="field">
                <span>{t("title")}</span>
                <input
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  maxLength={120}
                  minLength={1}
                  required
                />
              </label>
              <button
                className="button button-dark"
                type="submit"
                disabled={saving}
              >
                {saving ? t("loading") : t("rename")}
              </button>
            </form>
            <button className="button button-danger" onClick={deleteSong}>
              <Icon name="close" />
              {t("deleteSong")}
            </button>
          </div>
        </>
      )}
    </AppShell>
  );
}

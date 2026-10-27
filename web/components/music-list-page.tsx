"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { Icon } from "@/components/icon";
import { SongStatus } from "@/components/song-status";
import { useLocaleMessages } from "@/components/locale-provider";
import { api, formatDate, type PageResult, type SongJob } from "@/lib/api";

export function MusicListPage() {
  const { t } = useLocaleMessages();
  const [songs, setSongs] = useState<SongJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    async function load() {
      try {
        const page = await api<PageResult<SongJob>>("/api/songs?page=1");
        if (alive) setSongs(page.results);
        await api("/api/songs/mark-seen", { method: "POST", body: {} });
        window.dispatchEvent(new Event("osp:songs-seen"));
      } catch {
        if (alive) setError(t("errorNetwork"));
      } finally {
        if (alive) setLoading(false);
      }
    }
    void load();
    return () => {
      alive = false;
    };
  }, [t]);

  return (
    <AppShell>
      <div className="page-heading">
        <div>
          <p className="eyebrow">02 / OSP LIBRARY</p>
          <h1>{t("mySongs")}</h1>
          <p>{t("sampleBody")}</p>
        </div>
        <Link className="button button-dark" href="/create">
          <Icon name="plus" />
          {t("create")}
        </Link>
      </div>
      {error && (
        <div className="feedback error" role="alert">
          {error}
        </div>
      )}
      {loading ? (
        <div className="empty-card">
          <span className="loading-mark">
            <Icon name="music" />
          </span>
          <p>{t("loading")}</p>
        </div>
      ) : songs.length === 0 ? (
        <div className="empty-card">
          <span className="empty-icon">
            <Icon name="music" />
          </span>
          <h2>{t("noSongs")}</h2>
          <p>{t("startFirstSong")}</p>
          <Link className="button button-lime" href="/create">
            {t("getStarted")} <Icon name="arrow" />
          </Link>
        </div>
      ) : (
        <div className="song-list">
          {songs.map((song) => (
            <SongCard song={song} key={song.id} />
          ))}
        </div>
      )}
    </AppShell>
  );
}

function SongCard({ song }: { song: SongJob }) {
  const { t } = useLocaleMessages();
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
    )[song.genre] ?? song.genre;
  return (
    <article className="song-card">
      <Link href={`/music/${song.id}`} className="song-card-main">
        <div className="song-artwork">
          <Icon name="music" />
          <span className="artwork-lines">
            <i />
            <i />
            <i />
            <i />
            <i />
          </span>
        </div>
        <div className="song-card-copy">
          <div className="song-card-title">
            <h2>{song.title || t("sampleTitle")}</h2>
            <SongStatus status={song.status} />
          </div>
          <p>
            {genreLabel} <span>·</span> {formatDate(song.created_at)}
          </p>
          <span className="song-card-lyrics">
            {song.lyrics.slice(0, 100) || t("songDetail")}
          </span>
        </div>
        <span className="song-card-arrow">
          <Icon name="arrow" />
        </span>
      </Link>
      <div className="song-card-versions">
        {[0, 1].map((index) => {
          const version = song.versions.find((entry) => entry.index === index);
          return (
            <div className="mini-version" key={index}>
              <span className="version-label">
                {index === 0 ? t("versionA") : t("versionB")}
              </span>
              {version?.status === "ready" ? (
                <audio
                  controls
                  preload="none"
                  aria-label={index === 0 ? t("versionA") : t("versionB")}
                  src={`/api/songs/${song.id}/versions/${index}/audio`}
                />
              ) : (
                <span className="version-pending">
                  {version?.status === "failed"
                    ? t("status_failed")
                    : t("status_queued")}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </article>
  );
}

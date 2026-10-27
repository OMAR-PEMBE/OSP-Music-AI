from django.urls import path

from .views import (
    AudioRedirectView,
    LyricsView,
    MarkSongsSeenView,
    SongDetailView,
    SongsView,
)

urlpatterns = [
    path("lyrics", LyricsView.as_view(), name="lyrics"),
    path("songs", SongsView.as_view(), name="songs"),
    path("songs/mark-seen", MarkSongsSeenView.as_view(), name="songs-mark-seen"),
    path("songs/<uuid:job_id>", SongDetailView.as_view(), name="song-detail"),
    path(
        "songs/<uuid:job_id>/versions/<int:index>/audio",
        AudioRedirectView.as_view(),
        name="song-version-audio",
    ),
]

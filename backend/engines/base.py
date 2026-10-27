from dataclasses import dataclass, field
from typing import Protocol


class EngineError(Exception):
    def __init__(self, message, *, status_code=None, trace_id=None):
        super().__init__(message)
        self.status_code = status_code
        self.trace_id = trace_id


class EngineUnavailable(EngineError):
    """An engine cannot safely accept another paid job right now."""


@dataclass(frozen=True)
class LyricsResult:
    title: str
    lyrics: str


@dataclass(frozen=True)
class SongRequest:
    job_id: str
    idea: str
    lyrics: str
    model: str
    prompt: str
    voice: str


@dataclass(frozen=True)
class SongChoice:
    index: int
    provider_song_id: str | None = None
    url: str | None = None
    stream_url: str | None = None
    duration_ms: int | None = None


@dataclass(frozen=True)
class SongStatus:
    status: str
    provider_status: str
    failed_reason: str | None = None
    choices: list[SongChoice] = field(default_factory=list)


class MusicEngine(Protocol):
    name: str

    def generate_lyrics(self, prompt: str) -> LyricsResult: ...

    def submit_song(self, request: SongRequest) -> str: ...

    def get_status(self, task_id: str, *, poll_attempt: int = 0) -> SongStatus: ...

    def get_capacity(self) -> int: ...

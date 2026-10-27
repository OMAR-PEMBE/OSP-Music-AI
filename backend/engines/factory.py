"""Compatibility exports for the engine router's task-facing API."""

from .router import get_engine_for_job, get_engine_for_lyrics, get_engine_for_new_job

__all__ = ["get_engine_for_job", "get_engine_for_lyrics", "get_engine_for_new_job"]

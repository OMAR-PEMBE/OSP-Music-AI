from .base import EngineUnavailable
from .mureka import MurekaEngine


class SunoEngine:
    """Suno adapter scaffold; the official API contract is not in SUNO.md §3 yet."""

    name = "suno"

    def generate_lyrics(self, prompt):
        return MurekaEngine().generate_lyrics(prompt)

    def submit_song(self, request):
        del request
        if not self._has_api_key():
            raise EngineUnavailable("Suno API key is not configured.")
        raise EngineUnavailable("Official Suno API details are not configured.")

    def get_status(self, task_id, *, poll_attempt=0):
        del task_id, poll_attempt
        raise EngineUnavailable("Official Suno API details are not configured.")

    def get_capacity(self):
        # SUNO.md §3 has no official concurrency or rate-limit details.
        return 0

    @staticmethod
    def _has_api_key():
        from django.conf import settings

        return bool(settings.SUNO_API_KEY)

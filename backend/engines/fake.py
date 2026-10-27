from .base import LyricsResult, SongChoice, SongRequest, SongStatus

FAKE_LYRICS = """[Verse]
Nakuona mwanga wa asubuhi
Unanipa tumaini moyoni

[Chorus]
Wimbo huu ni wetu milele
Sauti zetu ziungane pamoja

[Bridge]
Tukiimba, furaha inarudi
Upendo wetu hauishi"""


class FakeEngine:
    def __init__(self, engine_name="fake"):
        self.name = engine_name

    def generate_lyrics(self, prompt: str) -> LyricsResult:
        del prompt
        return LyricsResult(title="Wimbo Wako", lyrics=FAKE_LYRICS)

    def submit_song(self, request: SongRequest) -> str:
        mode = "timeout" if "#timeout" in request.idea else ""
        if "#fail1" in request.idea:
            mode = "fail1"
        elif "#fail2" in request.idea:
            mode = "fail2"
        return f"fake-{request.job_id}-{mode}".rstrip("-")

    def get_status(self, task_id: str, *, poll_attempt: int = 0) -> SongStatus:
        mode = (
            task_id.rsplit("-", 1)[-1]
            if task_id.endswith(("-timeout", "-fail1", "-fail2"))
            else ""
        )
        if mode == "timeout":
            return SongStatus(status="running", provider_status="running")
        if poll_attempt < 2:
            return SongStatus(status="running", provider_status="running")
        if poll_attempt == 2:
            choices = [
                SongChoice(index=i, stream_url="fake://sample.mp3") for i in range(2)
            ]
            return SongStatus(
                status="streaming",
                provider_status="streaming",
                choices=choices,
            )
        if mode == "fail2":
            return SongStatus(
                status="failed",
                provider_status="failed",
                failed_reason="fake_failure",
            )
        indexes = [0] if mode == "fail1" else [0, 1]
        return SongStatus(
            status="succeeded",
            provider_status="succeeded",
            choices=[
                SongChoice(
                    index=index,
                    provider_song_id=f"fake-song-{index}",
                    url="fake://sample.mp3",
                    duration_ms=1000,
                )
                for index in indexes
            ],
        )

    def get_capacity(self) -> int:
        return 10

import uuid

from rest_framework import serializers

from .models import SongJob, SongVersion

GENRES = ("bongo_flava", "rnb", "afrobeats", "amapiano", "gospel", "hiphop", "other")
LANGUAGES = ("sw", "en", "mixed")
VOICES = ("male", "female", "auto")


class LyricsSerializer(serializers.Serializer):
    idea = serializers.CharField(min_length=3, max_length=1000)
    genre = serializers.ChoiceField(choices=GENRES)
    genre_other = serializers.CharField(
        required=False, allow_blank=True, max_length=30, default=""
    )
    language = serializers.ChoiceField(choices=LANGUAGES, default="sw")

    def validate(self, attrs):
        if attrs["genre"] == "other" and not attrs.get("genre_other", "").strip():
            raise serializers.ValidationError(
                {"genre_other": "Provide a genre when genre is other."}
            )
        return attrs


class SongCreateSerializer(serializers.Serializer):
    idea = serializers.CharField(min_length=3, max_length=1000)
    genre = serializers.ChoiceField(choices=GENRES)
    genre_other = serializers.CharField(required=False, allow_blank=True, max_length=30)
    language = serializers.ChoiceField(choices=LANGUAGES, default="sw")
    voice = serializers.ChoiceField(choices=VOICES, default="auto")
    lyrics = serializers.CharField(
        required=False, allow_blank=True, max_length=5000, default=""
    )

    def validate(self, attrs):
        if attrs["genre"] == "other" and not attrs.get("genre_other", "").strip():
            raise serializers.ValidationError(
                {"genre_other": "Provide a genre when genre is other."}
            )
        return attrs


class SongVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SongVersion
        fields = ["index", "status", "stream_url", "duration_ms"]


class SongJobSerializer(serializers.ModelSerializer):
    refund_tzs = serializers.SerializerMethodField()
    versions = SongVersionSerializer(many=True, read_only=True)

    class Meta:
        model = SongJob
        fields = [
            "id",
            "title",
            "genre",
            "language",
            "status",
            "price_tzs",
            "refund_tzs",
            "created_at",
            "finished_at",
            "lyrics",
            "versions",
        ]

    def get_refund_tzs(self, job):
        from apps.wallet.models import LedgerEntry

        return sum(
            job.ledger_entries.filter(type=LedgerEntry.Type.SONG_REFUND).values_list(
                "amount_tzs", flat=True
            )
        )


def parse_idempotency_key(value):
    try:
        return uuid.UUID(value)
    except (ValueError, TypeError, AttributeError):
        raise serializers.ValidationError(
            {"Idempotency-Key": "A valid UUID Idempotency-Key header is required."}
        )

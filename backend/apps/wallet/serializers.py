from rest_framework import serializers

from .models import LedgerEntry


class LedgerEntrySerializer(serializers.ModelSerializer):
    song_title = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = LedgerEntry
        fields = [
            "id",
            "type",
            "amount_tzs",
            "balance_after_tzs",
            "created_at",
            "song_title",
            "payment_status",
        ]

    def get_song_title(self, entry):
        return getattr(entry.song_job, "title", None) if entry.song_job_id else None

    def get_payment_status(self, entry):
        return entry.payment.status if entry.payment_id else None

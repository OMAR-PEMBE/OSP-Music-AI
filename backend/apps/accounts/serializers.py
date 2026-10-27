from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from rest_framework import serializers

from apps.wallet.models import Wallet

User = get_user_model()


class MeSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    email_verified = serializers.SerializerMethodField()
    balance_tzs = serializers.SerializerMethodField()
    unseen_songs = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "display_name",
            "avatar_url",
            "language",
            "theme",
            "email_verified",
            "balance_tzs",
            "unseen_songs",
        ]
        read_only_fields = [
            "id",
            "email",
            "avatar_url",
            "email_verified",
            "balance_tzs",
            "unseen_songs",
        ]

    def get_avatar_url(self, user):
        if not user.avatar:
            return None
        url = default_storage.url(user.avatar)
        if url.startswith(("http://", "https://")):
            return url
        return self.context["request"].build_absolute_uri(url)

    def get_email_verified(self, user):
        from allauth.account.models import EmailAddress

        return EmailAddress.objects.filter(user=user, verified=True).exists()

    def get_balance_tzs(self, user):
        return (
            Wallet.objects.filter(user=user)
            .values_list("balance_tzs", flat=True)
            .first()
            or 0
        )

    def get_unseen_songs(self, user):
        from apps.songs.models import SongJob

        return SongJob.objects.filter(
            user_id=user.pk,
            deleted_at__isnull=True,
            seen_by_user=False,
        ).count()

    def validate_display_name(self, value):
        value = value.strip()
        matches = User.objects.filter(display_name__iexact=value).exclude(
            pk=self.instance.pk
        )
        if matches.exists():
            raise serializers.ValidationError(
                "Jina hili la kuonekana tayari linatumika."
            )
        return value

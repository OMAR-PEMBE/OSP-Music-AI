from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class AppSettings(models.Model):
    ENGINE_CHOICES = (("mureka", "Mureka"), ("suno", "Suno"))
    FALLBACK_CHOICES = (("none", "None"), *ENGINE_CHOICES)
    MUREKA_MODELS = (
        ("mureka-7.6", "Mureka 7.6"),
        ("mureka-8", "Mureka 8"),
        ("mureka-9", "Mureka 9"),
        ("mureka-9.5", "Mureka 9.5"),
    )

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    song_price_tzs = models.PositiveBigIntegerField(default=1000)
    mureka_model = models.CharField(
        max_length=30,
        choices=MUREKA_MODELS,
        default="mureka-9",
    )
    suno_model = models.CharField(max_length=30, blank=True, default="")
    generation_enabled = models.BooleanField(default=True)
    active_engine = models.CharField(
        max_length=10, choices=ENGINE_CHOICES, default="mureka"
    )
    fallback_engine = models.CharField(
        max_length=10, choices=FALLBACK_CHOICES, default="none"
    )
    lyrics_daily_limit = models.PositiveSmallIntegerField(default=10)
    min_topup_tzs = models.PositiveBigIntegerField(default=1000)
    max_topup_tzs = models.PositiveBigIntegerField(default=500000)
    usd_to_tzs = models.PositiveIntegerField(default=2640)
    cost_per_version_usd_cents = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("4.50"),
    )
    cost_per_lyrics_usd_cents = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.90"),
    )
    suno_cost_per_version_usd_cents = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
    )
    mureka_balance_usd_cents = models.PositiveBigIntegerField(null=True, blank=True)
    mureka_low_balance_usd = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("20.00"),
    )
    support_whatsapp = models.CharField(max_length=20, blank=True, default="")
    support_email = models.EmailField(blank=True, default="")

    class Meta:
        verbose_name = "application settings"
        verbose_name_plural = "application settings"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(song_price_tzs__gt=0),
                name="app_song_price_positive",
            )
        ]

    def clean(self):
        super().clean()
        if self.pk != 1:
            raise ValidationError("AppSettings uses the single row with id=1.")
        if self.max_topup_tzs < self.min_topup_tzs:
            raise ValidationError("Maximum top-up must be at least the minimum.")
        if self.fallback_engine == self.active_engine:
            raise ValidationError(
                {"fallback_engine": "Fallback must differ from the active engine."}
            )

        errors = {}
        for engine in {self.active_engine, self.fallback_engine} - {"none"}:
            if engine == "suno":
                cost = self.suno_cost_per_version_usd_cents
                if not settings.SUNO_API_KEY:
                    key_field = (
                        "active_engine"
                        if self.active_engine == "suno"
                        else "fallback_engine"
                    )
                    errors[key_field] = (
                        "Configure SUNO_API_KEY before selecting Suno as active or fallback."
                    )
            else:
                cost = self.cost_per_version_usd_cents
            if cost is None or cost <= 0:
                errors["suno_cost_per_version_usd_cents"] = (
                    "Set a positive per-version cost before selecting this engine."
                    if engine == "suno"
                    else "Set a positive Mureka per-version cost."
                )
                continue
            total_cost_cents = cost * 2 + self.cost_per_lyrics_usd_cents
            if total_cost_cents * self.usd_to_tzs > Decimal(self.song_price_tzs * 60):
                errors["song_price_tzs"] = (
                    f"The {engine} estimate exceeds the 60% margin limit."
                )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.pk = 1
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return "Application settings"


def get_app_settings():
    settings_obj, _created = AppSettings.objects.get_or_create(pk=1)
    return settings_obj


class SupportMessage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_messages",
    )
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    handled = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"Support message from {self.email}"

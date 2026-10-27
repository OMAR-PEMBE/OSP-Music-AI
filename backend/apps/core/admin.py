from django.contrib import admin

from .models import AppSettings


@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "song_price_tzs",
        "active_engine",
        "fallback_engine",
        "generation_enabled",
    )
    fieldsets = (
        (
            "Generation",
            {
                "fields": (
                    "song_price_tzs",
                    "active_engine",
                    "fallback_engine",
                    "mureka_model",
                    "suno_model",
                    "generation_enabled",
                    "lyrics_daily_limit",
                )
            },
        ),
        ("Top-ups", {"fields": ("min_topup_tzs", "max_topup_tzs")}),
        (
            "Cost estimates",
            {
                "fields": (
                    "usd_to_tzs",
                    "cost_per_version_usd_cents",
                    "cost_per_lyrics_usd_cents",
                    "suno_cost_per_version_usd_cents",
                    "mureka_low_balance_usd",
                    "mureka_balance_usd_cents",
                )
            },
        ),
        ("Support", {"fields": ("support_whatsapp", "support_email")}),
    )

    def has_add_permission(self, request):
        return not AppSettings.objects.filter(pk=1).exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return ("mureka_balance_usd_cents",)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["song_price_tzs"].help_text = (
            "Use at least TZS 1,500 when Mureka model mureka-9.5 is selected."
        )
        form.base_fields["suno_cost_per_version_usd_cents"].help_text = (
            "Required to enable Suno; include this engine cost in the 60% margin guard."
        )
        form.base_fields["active_engine"].help_text = (
            "New jobs use this engine. Suno song submission remains unavailable until "
            "DOCS/SUNO.md §3 contains the official API contract."
        )
        return form

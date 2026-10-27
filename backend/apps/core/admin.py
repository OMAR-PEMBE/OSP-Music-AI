from django.contrib import admin, messages

from apps.songs.models import SongJob
from apps.songs.tasks import recheck_job_status

from .models import AppSettings, SupportMessage


@admin.register(SongJob)
class SongJobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "user",
        "engine",
        "status",
        "price_tzs",
        "created_at",
        "finished_at",
        "failure_reason",
    )
    list_filter = ("status", "engine", "created_at", "finished_at")
    search_fields = (
        "id",
        "title",
        "idea",
        "provider_task_id",
        "user__email",
        "user__display_name",
    )
    readonly_fields = tuple(field.name for field in SongJob._meta.fields)
    actions = ("recheck_status",)
    ordering = ("-created_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Re-check status (poll only; never resubmits)")
    def recheck_status(self, request, queryset):
        checked = 0
        skipped = 0
        for job_id in queryset.values_list("pk", flat=True).iterator():
            if recheck_job_status(job_id):
                checked += 1
            else:
                skipped += 1

        if checked:
            self.message_user(
                request,
                f"Polled {checked} job(s). No generation was resubmitted.",
            )
        if skipped:
            self.message_user(
                request,
                f"Skipped {skipped} job(s) without an active provider task.",
                level=messages.WARNING,
            )


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


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ("created_at", "name", "email", "handled")
    list_filter = ("handled", "created_at")
    search_fields = ("name", "email", "message")
    readonly_fields = ("user", "name", "email", "message", "created_at")

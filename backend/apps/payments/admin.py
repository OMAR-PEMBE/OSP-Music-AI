from django.contrib import admin

from .models import Payment, WebhookEvent


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "short_id",
        "user",
        "amount_tzs",
        "status",
        "failure_reason",
        "snippe_reference",
        "created_at",
    )
    list_filter = ("status", "failure_reason", "created_at")
    search_fields = ("short_id", "snippe_reference", "user__email")
    readonly_fields = (
        "id",
        "short_id",
        "user",
        "amount_tzs",
        "phone",
        "status",
        "snippe_reference",
        "channel_provider",
        "fee_tzs",
        "confirmed_amount_tzs",
        "expires_at",
        "completed_at",
        "failure_reason",
        "raw_create_response",
        "created_at",
        "updated_at",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = (
        "event_id",
        "event_type",
        "reference",
        "signature_valid",
        "processed_at",
        "created_at",
    )
    list_filter = ("signature_valid", "event_type", "created_at")
    search_fields = ("event_id", "reference")
    readonly_fields = tuple(field.name for field in WebhookEvent._meta.fields)

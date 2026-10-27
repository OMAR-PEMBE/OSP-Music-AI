from django.contrib import admin, messages
from django.template.response import TemplateResponse

from .forms import WalletAdjustmentForm
from .models import LedgerEntry, Wallet
from .services import InsufficientBalance, adjust


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "balance_tzs", "created_at", "updated_at")
    search_fields = ("user__email", "user__display_name")
    actions = ("adjust_balance",)

    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Adjust balance (TZS)")
    def adjust_balance(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(
                request,
                "Select exactly one wallet to adjust.",
                level=messages.ERROR,
            )
            return None

        wallet = queryset.get()
        form = WalletAdjustmentForm(request.POST or None)
        if "apply_adjustment" in request.POST and form.is_valid():
            try:
                entry = adjust(
                    wallet,
                    form.cleaned_data["amount_tzs"],
                    form.cleaned_data["note"],
                    request.user,
                )
            except InsufficientBalance as exc:
                self.message_user(request, str(exc.detail), level=messages.ERROR)
            except (ValueError, PermissionError) as exc:
                self.message_user(request, str(exc), level=messages.ERROR)
            else:
                self.message_user(
                    request,
                    f"Recorded {entry.amount_tzs} TZS adjustment for {wallet.user}.",
                )
            return None

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Adjust wallet balance",
            "wallet": wallet,
            "form": form,
        }
        return TemplateResponse(request, "admin/wallet/adjustment_form.html", context)


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "wallet",
        "type",
        "amount_tzs",
        "balance_after_tzs",
        "idempotency_key",
    )
    list_filter = ("type", "created_at")
    search_fields = ("idempotency_key", "wallet__user__email")
    readonly_fields = tuple(field.name for field in LedgerEntry._meta.fields)
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

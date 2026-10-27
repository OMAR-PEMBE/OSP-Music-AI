from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "display_name",
        "first_name",
        "last_name",
        "is_active",
        "is_staff",
        "date_joined",
    )
    list_filter = ("is_active", "is_staff", "date_joined", "deleted_at")
    search_fields = ("email", "display_name", "first_name", "last_name")
    readonly_fields = tuple(field.name for field in User._meta.fields)
    ordering = ("-date_joined",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

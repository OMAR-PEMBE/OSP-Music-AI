from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.dashboard.views import daily_summary
from apps.payments.views import snippe_webhook_view

urlpatterns = [
    path(
        "admin/summary/",
        admin.site.admin_view(daily_summary),
        name="admin-daily-summary",
    ),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("api/auth/", include("allauth.headless.urls")),
    path("api/", include("apps.core.urls")),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.wallet.urls")),
    path("api/", include("apps.payments.urls")),
    path("api/", include("apps.songs.urls")),
    path("webhooks/snippe", snippe_webhook_view, name="snippe-webhook"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

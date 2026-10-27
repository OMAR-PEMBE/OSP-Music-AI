from django.urls import path

from .views import ConfigView, SupportView, csrf_cookie, health

urlpatterns = [
    path("health", health, name="health"),
    path("config", ConfigView.as_view(), name="public-config"),
    path("csrf", csrf_cookie, name="csrf-cookie"),
    path("support", SupportView.as_view(), name="support"),
]

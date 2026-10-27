from django.urls import path

from .views import TopupDetailView, TopupsView

urlpatterns = [
    path("wallet/topups", TopupsView.as_view(), name="wallet-topups"),
    path(
        "wallet/topups/<uuid:payment_id>",
        TopupDetailView.as_view(),
        name="wallet-topup-detail",
    ),
]

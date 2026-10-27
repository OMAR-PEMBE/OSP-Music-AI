from django.urls import path

from .views import WalletTransactionsView, WalletView

urlpatterns = [
    path("wallet", WalletView.as_view(), name="wallet"),
    path(
        "wallet/transactions",
        WalletTransactionsView.as_view(),
        name="wallet-transactions",
    ),
]

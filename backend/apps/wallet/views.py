from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LedgerEntry, Wallet
from .permissions import IsEmailVerified
from .serializers import LedgerEntrySerializer


class WalletView(APIView):
    permission_classes = [IsAuthenticated, IsEmailVerified]

    def get(self, request):
        wallet = Wallet.objects.get(user_id=request.user.pk)
        return Response({"balance_tzs": wallet.balance_tzs})


class WalletTransactionsView(ListAPIView):
    permission_classes = [IsAuthenticated, IsEmailVerified]
    serializer_class = LedgerEntrySerializer

    def get_queryset(self):
        return (
            LedgerEntry.objects.filter(wallet__user_id=self.request.user.pk)
            .select_related("payment", "song_job", "wallet")
            .order_by("-created_at", "-id")
        )

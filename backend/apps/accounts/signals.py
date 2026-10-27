from allauth.account.signals import user_signed_up
from django.dispatch import receiver


@receiver(user_signed_up)
def create_wallet_for_new_user(request, user, **kwargs):
    from apps.wallet.models import Wallet

    Wallet.objects.get_or_create(user=user, defaults={"balance_tzs": 0})

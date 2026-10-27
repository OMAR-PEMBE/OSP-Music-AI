import logging

from celery import shared_task
from django.db.models import BigIntegerField, F, Sum, Value
from django.db.models.functions import Coalesce

from .models import Wallet

logger = logging.getLogger(__name__)


@shared_task(name="apps.wallet.check_wallet_integrity")
def check_wallet_integrity():
    mismatches = Wallet.objects.annotate(
        ledger_total=Coalesce(
            Sum("ledger_entries__amount_tzs"),
            Value(0),
            output_field=BigIntegerField(),
        )
    ).exclude(balance_tzs=F("ledger_total"))

    mismatch_count = 0
    for wallet in mismatches.iterator():
        mismatch_count += 1
        logger.error(
            "wallet_integrity_mismatch",
            extra={
                "wallet_id": str(wallet.pk),
                "balance_tzs": wallet.balance_tzs,
                "ledger_total_tzs": wallet.ledger_total,
            },
        )
    return mismatch_count

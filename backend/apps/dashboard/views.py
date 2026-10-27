from datetime import datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.contrib.admin import site
from django.db.models import BigIntegerField, F, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import get_app_settings
from apps.songs.models import LyricsRequest, SongJob
from apps.wallet.models import LedgerEntry, Wallet


def daily_summary(request):
    today = timezone.localdate()
    start = timezone.make_aware(datetime.combine(today, time.min))
    end = start + timedelta(days=1)

    app_settings = get_app_settings()
    ledger_today = LedgerEntry.objects.filter(created_at__gte=start, created_at__lt=end)
    jobs_created_today = SongJob.objects.filter(
        created_at__gte=start,
        created_at__lt=end,
    )
    jobs_finished_today = SongJob.objects.filter(
        finished_at__gte=start,
        finished_at__lt=end,
    )

    topups_tzs = ledger_today.filter(type=LedgerEntry.Type.TOPUP).aggregate(
        total=Coalesce(Sum("amount_tzs"), Value(0), output_field=BigIntegerField())
    )["total"]
    song_charges_tzs = -ledger_today.filter(
        type=LedgerEntry.Type.SONG_CHARGE
    ).aggregate(
        total=Coalesce(Sum("amount_tzs"), Value(0), output_field=BigIntegerField())
    )[
        "total"
    ]
    refunds_tzs = ledger_today.filter(type=LedgerEntry.Type.SONG_REFUND).aggregate(
        total=Coalesce(Sum("amount_tzs"), Value(0), output_field=BigIntegerField())
    )["total"]
    mureka_cost_usd_cents = jobs_created_today.filter(
        engine=SongJob.Engine.MUREKA
    ).aggregate(
        total=Coalesce(
            Sum("est_cost_usd_cents"),
            Value(0),
            output_field=BigIntegerField(),
        )
    )[
        "total"
    ]
    song_cost_tzs = (mureka_cost_usd_cents * app_settings.usd_to_tzs + 50) // 100
    lyrics_requests_today = LyricsRequest.objects.filter(
        created_at__gte=start,
        created_at__lt=end,
    ).count()
    lyrics_cost_tzs = int(
        (
            Decimal(lyrics_requests_today)
            * app_settings.cost_per_lyrics_usd_cents
            * app_settings.usd_to_tzs
            / 100
        ).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    )
    estimated_mureka_cost_tzs = song_cost_tzs + lyrics_cost_tzs

    wallet_mismatches = Wallet.objects.annotate(
        ledger_total=Coalesce(
            Sum("ledger_entries__amount_tzs"),
            Value(0),
            output_field=BigIntegerField(),
        )
    ).exclude(balance_tzs=F("ledger_total"))
    mismatch_count = wallet_mismatches.count()

    balance_cents = app_settings.mureka_balance_usd_cents
    low_balance_threshold_cents = int(app_settings.mureka_low_balance_usd * 100)
    mureka_balance_is_low = (
        balance_cents is not None and balance_cents < low_balance_threshold_cents
    )
    summary_context = {
        **site.each_context(request),
        "title": "Daily summary",
        "summary_date": today,
        "new_users": User.objects.filter(
            date_joined__gte=start,
            date_joined__lt=end,
            is_staff=False,
            deleted_at__isnull=True,
        ).count(),
        "topups_tzs": topups_tzs,
        "songs_generated": jobs_finished_today.filter(
            status__in=[SongJob.Status.READY, SongJob.Status.PARTIAL]
        ).count(),
        "jobs_with_failed_versions": jobs_finished_today.filter(
            status__in=[SongJob.Status.PARTIAL, SongJob.Status.FAILED]
        ).count(),
        "refunds_tzs": refunds_tzs,
        "estimated_mureka_cost_tzs": estimated_mureka_cost_tzs,
        "estimated_profit_tzs": (
            song_charges_tzs - refunds_tzs - estimated_mureka_cost_tzs
        ),
        "mureka_balance_usd": (
            None
            if balance_cents is None
            else f"{balance_cents // 100}.{balance_cents % 100:02d}"
        ),
        "mureka_balance_is_low": mureka_balance_is_low,
        "wallet_integrity_warning_count": mismatch_count,
    }
    return render(request, "admin/dashboard/daily_summary.html", summary_context)

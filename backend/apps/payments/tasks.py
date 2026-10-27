from celery import shared_task
from django.utils import timezone

from .models import Payment, WebhookEvent
from .services import confirm_payment, sweep_payments


@shared_task(name="apps.payments.process_snippe_event")
def process_snippe_event(event_pk):
    event = WebhookEvent.objects.get(pk=event_pk)
    payment = Payment.objects.filter(snippe_reference=event.reference).first()
    if payment and event.event_type in {
        "payment.completed",
        "payment.failed",
        "payment.voided",
        "payment.expired",
    }:
        confirm_payment(payment)
    event.processed_at = timezone.now()
    event.save(update_fields=["processed_at"])


@shared_task(name="apps.payments.sweep_pending_payments")
def sweep_pending_payments():
    sweep_payments()

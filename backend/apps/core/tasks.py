from celery import shared_task


@shared_task(name="apps.core.sample_task")
def sample_task():
    return "sample task ran"

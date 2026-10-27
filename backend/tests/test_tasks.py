from celery import Celery
from celery.contrib.testing.worker import start_worker

from apps.core.tasks import sample_task


def test_sample_task_runs_on_worker():
    test_app = Celery(
        "osp_music_worker_test",
        broker="memory://",
        backend="cache+memory://",
    )
    test_app.register_task(sample_task._get_current_object())

    with start_worker(test_app, pool="solo", perform_ping_check=False):
        result = test_app.send_task(sample_task.name)
    assert result.get(timeout=10) == "sample task ran"

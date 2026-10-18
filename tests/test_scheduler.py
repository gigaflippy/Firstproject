import asyncio
from datetime import timedelta

from pulsewatch.config import Target
from pulsewatch.metrics import Metrics
from pulsewatch.scheduler import Scheduler
from pulsewatch.storage import Storage


async def test_scheduler_runs_probes_and_stops(tmp_path, mock_client, monkeypatch):
    monkeypatch.setattr("pulsewatch.scheduler.random.uniform", lambda a, b: 0)
    target = Target(name="good", url="https://good.test", interval_seconds=1)
    storage = Storage(tmp_path / "s.db")
    sched = Scheduler([target], storage, Metrics(), "r", timedelta(hours=1), client=mock_client)
    await sched.start()
    await asyncio.sleep(0.1)
    await sched.stop()
    assert len(storage.recent("good")) >= 1
    assert sched._tasks == []

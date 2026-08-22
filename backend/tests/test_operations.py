import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import app.services.operations as operations


class DummySession:
    def close(self) -> None:
        pass


def test_scheduler_detail_is_json_safe():
    retrieved_at = datetime(2026, 8, 22, 15, 17, tzinfo=timezone.utc)

    result = operations._json_safe(
        {"refresh": [{"source": "example", "last_successful_retrieval": retrieved_at}]}
    )

    assert result == {
        "refresh": [{"source": "example", "last_successful_retrieval": retrieved_at.isoformat()}]
    }


def test_maintenance_records_checks_before_refresh_and_heartbeats(monkeypatch):
    events: list[str] = []
    finished: list[tuple[str, dict]] = []

    monkeypatch.setattr(operations, "acquire_scheduler_lease", lambda: True)
    monkeypatch.setattr(
        operations,
        "update_scheduler_progress",
        lambda phase, **_kwargs: events.append(phase),
    )
    monkeypatch.setattr(
        operations,
        "run_operational_checks",
        lambda: events.append("checks_run") or [SimpleNamespace(check_name="transaction_database", status="ok")],
    )

    def refresh_due_sources(*, on_progress):
        events.append("refresh_run")
        result = {"source": "example", "status": "skipped_not_due"}
        on_progress(result)
        return [result]

    monkeypatch.setattr(operations, "refresh_due_sources", refresh_due_sources)
    monkeypatch.setattr(operations, "SessionLocal", DummySession)
    monkeypatch.setattr(operations, "BillingSessionLocal", DummySession)

    async def scan_live_watchlists(_public, _billing):
        events.append("watchlists_run")
        return []

    monkeypatch.setattr(operations, "scan_live_watchlists", scan_live_watchlists)
    monkeypatch.setattr(operations, "retry_pending_alerts", lambda _session: {"attempted": 0})
    monkeypatch.setattr(operations, "finish_scheduler_lease", lambda status, detail: finished.append((status, detail)))

    result = asyncio.run(operations.run_maintenance_cycle())

    assert result["status"] == "ok"
    assert events.index("checks_run") < events.index("refresh_run")
    assert events.count("public_data_refresh") == 2
    assert events[-2:] == ["watchlists", "watchlists_run"]
    assert finished[-1][0] == "ok"


def test_bounded_cycle_marks_timeout_as_failed(monkeypatch):
    finished: list[tuple[str, dict]] = []

    async def never_finishes():
        await asyncio.Event().wait()

    monkeypatch.setattr(operations, "run_maintenance_cycle", never_finishes)
    monkeypatch.setattr(operations, "finish_scheduler_lease", lambda status, detail: finished.append((status, detail)))

    result = asyncio.run(operations.run_bounded_maintenance_cycle(0.01))

    assert result["status"] == "failed"
    assert result["error"] == "maintenance_cycle_timeout"
    assert finished == [("failed", {"error": "maintenance_cycle_timeout", "timeout_seconds": 0.01})]

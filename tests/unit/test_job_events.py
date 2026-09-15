from uuid import uuid4

from app.orchestrator.events import JobEventLog


def test_job_event_log_appends_monotonic_sequences(tmp_path):
    project_id = uuid4()
    log = JobEventLog(tmp_path, project_id)

    first = log.append("job_started", job_id=uuid4(), state="running")
    second = log.append("stage_started", stage="audio", state="running")

    assert first.sequence == 1
    assert second.sequence == 2
    assert second.project_id == project_id
    assert [event.event for event in log.read()] == ["job_started", "stage_started"]


def test_job_event_log_read_is_bounded_and_skips_invalid_records(tmp_path):
    project_id = uuid4()
    log = JobEventLog(tmp_path, project_id)
    log.append("one")
    log.append("two")
    log.append("three")
    log.path.write_text(
        log.path.read_text(encoding="utf-8") + '{"broken": true}\n',
        encoding="utf-8",
    )

    events = log.read(limit=2)

    assert [event.event for event in events] == ["two", "three"]

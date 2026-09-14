from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.orchestrator.planning_jobs import PlanningJob, PlanningJobManager
from app.storage.filesystem import FilesystemStore


def _write_job(root: Path, state: str) -> PlanningJob:
    job = PlanningJob(
        id=uuid4(),
        project_id=uuid4(),
        state=state,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    jobs = root / "planning-jobs"
    jobs.mkdir(parents=True)
    (jobs / f"{job.id}.json").write_text(job.model_dump_json(), encoding="utf-8")
    return job


def test_manager_marks_running_job_interrupted_after_restart(tmp_path: Path) -> None:
    original = _write_job(tmp_path, "running")

    manager = PlanningJobManager(FilesystemStore(tmp_path))
    recovered = manager.get(original.id)

    assert recovered.state == "interrupted"
    assert recovered.error == "worker process restarted"


def test_manager_leaves_completed_job_unchanged(tmp_path: Path) -> None:
    original = _write_job(tmp_path, "completed")

    manager = PlanningJobManager(FilesystemStore(tmp_path))
    recovered = manager.get(original.id)

    assert recovered.state == "completed"
    assert recovered.error is None

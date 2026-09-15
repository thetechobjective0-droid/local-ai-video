import re

from app.web_ui import HTML


def _function_body(name: str) -> str:
    match = re.search(
        rf"async function {name}\([^)]*\)\{{(.*?)(?:\}}\n(?:async function|loadProjects\(\);))",
        HTML,
    )
    assert match is not None, f"missing {name} function"
    return match.group(1)


def test_poll_job_does_not_refresh_jobs_on_every_tick() -> None:
    body = _function_body("pollJob")

    assert "refreshJobs()" not in body
    assert "setInterval(check,3000)" in body


def test_refresh_jobs_returns_active_job_without_starting_a_poller() -> None:
    body = _function_body("refreshJobs")

    assert "pollJob(" not in body
    assert "return active||null" in body
    assert "setProgress('media',percent(active.completed_scenes,active.scene_count))" in body


def test_dashboard_contains_determinate_progress_bars() -> None:
    assert 'id="planningProgress"' in HTML
    assert 'id="planningPercent"' in HTML
    assert 'id="mediaProgress"' in HTML
    assert 'id="mediaPercent"' in HTML
    assert "const percent=(done,total)=>" in HTML
    assert "setProgress('media',percent(j.completed_scenes,j.scene_count))" in HTML


def test_planning_progress_is_updated_from_job_state() -> None:
    body = _function_body("pollPlanning")

    assert "setProgress('planning',j.state==='completed'?100:(j.state==='running'?60:0))" in body

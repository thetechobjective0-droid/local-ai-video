import re

from app.web_ui import HTML


def _function_body(name: str) -> str:
    match = re.search(rf"async function {name}\([^)]*\)\{{(.*?)(?:\}}\n(?:async function|loadProjects\(\);))", HTML)
    assert match is not None, f"missing {name} function"
    return match.group(1)


def test_poll_job_does_not_refresh_jobs_on_every_tick() -> None:
    body = _function_body("pollJob")

    assert "refreshJobs()" not in body
    assert "setInterval(check,3000)" in body


def test_refresh_jobs_returns_active_job_without_starting_a_poller() -> None:
    body = _function_body("refreshJobs")

    assert "pollJob(" not in body
    assert "return jobs.find(j=>j.state==='queued'||j.state==='running')||null" in body

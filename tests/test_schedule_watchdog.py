from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from src import schedule_watchdog


NOW = datetime(2026, 7, 27, 4, 0, tzinfo=timezone.utc)


def _run(
    *,
    status: str = "completed",
    conclusion: str | None = "success",
    updated_at: datetime,
    branch: str = "main",
    run_id: int = 1,
) -> dict[str, object]:
    return {
        "id": run_id,
        "status": status,
        "conclusion": conclusion,
        "head_branch": branch,
        "created_at": updated_at.isoformat(),
        "updated_at": updated_at.isoformat(),
        "html_url": f"https://github.com/ohxiyu/bmtnews/actions/runs/{run_id}",
    }


def test_recent_success_is_healthy() -> None:
    decision = schedule_watchdog.evaluate_workflow_runs(
        [_run(updated_at=NOW - timedelta(hours=4, minutes=59))],
        now=NOW,
        threshold=timedelta(hours=5),
        ref="main",
    )

    assert decision.state == "healthy"
    assert decision.should_dispatch is False
    assert decision.age(NOW) == timedelta(hours=4, minutes=59)


def test_stale_success_requests_recovery_dispatch() -> None:
    decision = schedule_watchdog.evaluate_workflow_runs(
        [_run(updated_at=NOW - timedelta(hours=5, seconds=1))],
        now=NOW,
        threshold=timedelta(hours=5),
        ref="main",
    )

    assert decision.state == "stale"
    assert decision.should_dispatch is True


def test_stale_success_does_not_duplicate_active_run() -> None:
    decision = schedule_watchdog.evaluate_workflow_runs(
        [
            _run(updated_at=NOW - timedelta(hours=6)),
            _run(
                status="in_progress",
                conclusion=None,
                updated_at=NOW - timedelta(minutes=2),
                run_id=2,
            ),
        ],
        now=NOW,
        threshold=timedelta(hours=5),
        ref="main",
    )

    assert decision.state == "stale_with_active_run"
    assert decision.should_dispatch is False
    assert decision.active_run_url is not None


def test_runs_from_other_branches_do_not_reset_main_heartbeat() -> None:
    decision = schedule_watchdog.evaluate_workflow_runs(
        [_run(updated_at=NOW - timedelta(minutes=1), branch="agent/example")],
        now=NOW,
        threshold=timedelta(hours=5),
        ref="main",
    )

    assert decision.state == "stale"
    assert decision.latest_success_at is None


def test_main_dispatches_recovery_and_fails_for_notification(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    summary = tmp_path / "summary.md"
    dispatches: list[dict[str, str]] = []
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "ohxiyu/bmtnews")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setattr(
        schedule_watchdog,
        "fetch_workflow_runs",
        lambda **kwargs: [
            _run(updated_at=datetime.now(timezone.utc) - timedelta(hours=26))
        ],
    )
    monkeypatch.setattr(
        schedule_watchdog,
        "dispatch_workflow",
        lambda **kwargs: dispatches.append(kwargs),
    )

    exit_code = schedule_watchdog.main([])

    assert exit_code == 1
    assert dispatches == [
        {
            "token": "test-token",
            "repository": "ohxiyu/bmtnews",
            "workflow": "daily-summary.yml",
            "ref": "main",
        }
    ]
    assert "已触发一次 `workflow_dispatch` 补跑" in summary.read_text(
        encoding="utf-8"
    )
    assert "::error title=BMTNews schedule watchdog::" in capsys.readouterr().out


def test_watchdog_workflow_has_required_schedule_and_permissions() -> None:
    workflow = (
        Path(__file__).parents[1]
        / ".github"
        / "workflows"
        / "schedule-watchdog.yml"
    ).read_text(encoding="utf-8")

    assert "cron: '43 * * * *'" in workflow
    assert "actions: write" in workflow
    assert "--threshold-hours 25" in workflow

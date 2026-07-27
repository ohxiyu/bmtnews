"""Detect a stale scheduled feed and dispatch one recovery run."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_WORKFLOW = "daily-summary.yml"
DEFAULT_REF = "main"
DEFAULT_THRESHOLD_HOURS = 5.0
ACTIVE_STATUSES = frozenset(
    {"queued", "in_progress", "waiting", "pending", "requested"}
)
DecisionState = Literal["healthy", "stale", "stale_with_active_run"]


class GitHubApiError(RuntimeError):
    """A safe-to-publish GitHub API failure."""


@dataclass(frozen=True)
class WatchdogDecision:
    """Health decision for the target workflow and branch."""

    state: DecisionState
    threshold: timedelta
    latest_success_at: datetime | None
    latest_success_url: str | None
    active_run_url: str | None

    @property
    def should_dispatch(self) -> bool:
        return self.state == "stale"

    def age(self, now: datetime) -> timedelta | None:
        if self.latest_success_at is None:
            return None
        return max(timedelta(0), now - self.latest_success_at)


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("workflow run is missing a timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _run_timestamp(run: dict[str, Any]) -> datetime:
    for field in ("updated_at", "run_started_at", "created_at"):
        if run.get(field):
            return _parse_timestamp(run[field])
    raise ValueError("workflow run is missing all known timestamps")


def evaluate_workflow_runs(
    workflow_runs: Sequence[dict[str, Any]],
    *,
    now: datetime,
    threshold: timedelta,
    ref: str,
) -> WatchdogDecision:
    """Evaluate successful and active runs for the canonical branch."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)

    branch_runs = [run for run in workflow_runs if run.get("head_branch") == ref]
    successful_runs = [
        run
        for run in branch_runs
        if run.get("status") == "completed" and run.get("conclusion") == "success"
    ]
    active_runs = [
        run for run in branch_runs if run.get("status") in ACTIVE_STATUSES
    ]

    latest_success = (
        max(successful_runs, key=_run_timestamp) if successful_runs else None
    )
    latest_success_at = (
        _run_timestamp(latest_success) if latest_success is not None else None
    )
    latest_success_url = (
        str(latest_success.get("html_url") or "") or None
        if latest_success is not None
        else None
    )

    latest_active = max(active_runs, key=_run_timestamp) if active_runs else None
    active_run_url = (
        str(latest_active.get("html_url") or "") or None
        if latest_active is not None
        else None
    )

    if (
        latest_success_at is not None
        and max(timedelta(0), now - latest_success_at) <= threshold
    ):
        state: DecisionState = "healthy"
    elif latest_active is not None:
        state = "stale_with_active_run"
    else:
        state = "stale"

    return WatchdogDecision(
        state=state,
        threshold=threshold,
        latest_success_at=latest_success_at,
        latest_success_url=latest_success_url,
        active_run_url=active_run_url,
    )


def _validate_repository(repository: str) -> str:
    parts = repository.split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError("repository must use the owner/name format")
    return repository


def _github_api_request(
    method: str,
    path: str,
    *,
    token: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    request = Request(
        f"https://api.github.com{path}",
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "bmtnews-schedule-watchdog",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read()
    except HTTPError as error:
        raise GitHubApiError(
            f"GitHub API {method} request failed with HTTP {error.code}"
        ) from None
    except URLError:
        raise GitHubApiError(f"GitHub API {method} request could not connect") from None

    if not body:
        return None
    try:
        result = json.loads(body)
    except json.JSONDecodeError:
        raise GitHubApiError("GitHub API returned invalid JSON") from None
    if not isinstance(result, dict):
        raise GitHubApiError("GitHub API returned an unexpected response")
    return result


def fetch_workflow_runs(
    *,
    token: str,
    repository: str,
    workflow: str,
) -> list[dict[str, Any]]:
    repository = _validate_repository(repository)
    workflow_id = quote(workflow, safe="")
    payload = _github_api_request(
        "GET",
        f"/repos/{repository}/actions/workflows/{workflow_id}/runs?per_page=30",
        token=token,
    )
    runs = payload.get("workflow_runs") if payload is not None else None
    if not isinstance(runs, list) or not all(isinstance(run, dict) for run in runs):
        raise GitHubApiError("GitHub API response is missing workflow_runs")
    return runs


def dispatch_workflow(
    *,
    token: str,
    repository: str,
    workflow: str,
    ref: str,
) -> None:
    repository = _validate_repository(repository)
    workflow_id = quote(workflow, safe="")
    _github_api_request(
        "POST",
        f"/repos/{repository}/actions/workflows/{workflow_id}/dispatches",
        token=token,
        payload={"ref": ref},
    )


def _format_timestamp(value: datetime | None) -> str:
    return value.isoformat().replace("+00:00", "Z") if value is not None else "无"


def render_summary(
    decision: WatchdogDecision,
    *,
    now: datetime,
    repository: str,
    workflow: str,
    ref: str,
    recovery_dispatched: bool,
) -> str:
    status = {
        "healthy": "✅ 正常",
        "stale": "❌ 已超过心跳阈值",
        "stale_with_active_run": "⚠️ 已超过心跳阈值，但已有采集运行中",
    }[decision.state]
    age = decision.age(now)
    age_text = f"{age.total_seconds() / 3600:.2f} 小时" if age else "无成功记录"
    success_text = _format_timestamp(decision.latest_success_at)
    if decision.latest_success_url:
        success_text = f"[{success_text}]({decision.latest_success_url})"

    lines = [
        "## BMTNews 定时采集心跳",
        "",
        f"**状态：{status}**",
        "",
        f"- 仓库：`{repository}`",
        f"- 工作流：`{workflow}`",
        f"- 分支：`{ref}`",
        f"- 心跳阈值：{decision.threshold.total_seconds() / 3600:g} 小时",
        f"- 最近成功：{success_text}",
        f"- 距今：{age_text}",
    ]
    if decision.active_run_url:
        lines.append(f"- 正在运行：[查看采集]({decision.active_run_url})")
    if recovery_dispatched:
        lines.append("- 自动处置：已触发一次 `workflow_dispatch` 补跑")
    elif decision.state == "stale_with_active_run":
        lines.append("- 自动处置：未重复触发，等待现有采集完成")
    else:
        lines.append("- 自动处置：无需补跑")
    return "\n".join(lines) + "\n"


def _append_summary(markdown: str) -> None:
    output = os.getenv("GITHUB_STEP_SUMMARY")
    if output:
        with Path(output).open("a", encoding="utf-8") as summary:
            summary.write(markdown)
    else:
        print(markdown)


def _escape_workflow_command(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _emit_error(message: str) -> None:
    print(
        "::error title=BMTNews schedule watchdog::"
        f"{_escape_workflow_command(message)}"
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check the BMTNews feed workflow heartbeat"
    )
    parser.add_argument(
        "--repository",
        default=os.getenv("GITHUB_REPOSITORY", ""),
        help="GitHub repository in owner/name form",
    )
    parser.add_argument("--workflow", default=DEFAULT_WORKFLOW)
    parser.add_argument("--ref", default=DEFAULT_REF)
    parser.add_argument(
        "--threshold-hours",
        type=float,
        default=DEFAULT_THRESHOLD_HOURS,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    token = os.getenv("GITHUB_TOKEN", "")
    now = datetime.now(timezone.utc)

    if not token or not args.repository or args.threshold_hours <= 0:
        message = (
            "缺少 GITHUB_TOKEN/GITHUB_REPOSITORY，或 threshold-hours 不是正数"
        )
        _emit_error(message)
        return 1

    try:
        runs = fetch_workflow_runs(
            token=token,
            repository=args.repository,
            workflow=args.workflow,
        )
        decision = evaluate_workflow_runs(
            runs,
            now=now,
            threshold=timedelta(hours=args.threshold_hours),
            ref=args.ref,
        )
        recovery_dispatched = False
        if decision.should_dispatch:
            dispatch_workflow(
                token=token,
                repository=args.repository,
                workflow=args.workflow,
                ref=args.ref,
            )
            recovery_dispatched = True
        _append_summary(
            render_summary(
                decision,
                now=now,
                repository=args.repository,
                workflow=args.workflow,
                ref=args.ref,
                recovery_dispatched=recovery_dispatched,
            )
        )
    except (GitHubApiError, OSError, ValueError) as error:
        _emit_error(str(error))
        return 1

    if decision.state == "healthy":
        print("BMTNews schedule heartbeat is healthy.")
        return 0
    if recovery_dispatched:
        _emit_error("最近一次成功采集已超过 5 小时，已自动触发补跑")
    else:
        _emit_error("最近一次成功采集已超过 5 小时，已有采集正在运行")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

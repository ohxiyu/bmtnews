"""Structured reporting for one native Horizon pipeline run."""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit

from ._file_utils import _atomic_write_text


DEFAULT_RUN_REPORT_PATH = Path("data/run-report.json")
AlertSeverity = Literal["info", "warning", "failure"]

_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(api[-_]?key|authorization|cookie|credential|password|secret|signature|token)"
    r"(\s*[:=]\s*)([^\s,;]+)"
)
_HTTP_URL = re.compile(r"https?://[^\s<>'\"]+")

_METRIC_LABELS = (
    ("fetched_raw", "本次采集"),
    ("unique_after_url_dedup", "URL 去重后"),
    ("staged_total", "暂存累计"),
    ("edition_candidates", "本期候选"),
    ("current_day_items", "属于当日"),
    ("skipped_published_history", "跳过历史发布"),
    ("skipped_already_analyzed", "跳过已分析"),
    ("analyzed_this_run", "本次分析"),
    ("analyzed_today", "今日累计分析"),
    ("above_threshold", "分数达标"),
    ("topic_duplicates_removed", "主题去重删除"),
    ("balanced_digest_removed", "配额筛选删除"),
    ("newly_displayed", "本次新增展示"),
    ("displayed_today", "今日页面展示"),
    ("high_priority", "高优先级"),
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _sanitize_url(match: re.Match[str]) -> str:
    raw = match.group(0).rstrip(".,);]")
    suffix = match.group(0)[len(raw) :]
    try:
        parsed = urlsplit(raw)
        host = parsed.hostname or ""
        if parsed.port is not None:
            host = f"{host}:{parsed.port}"
        safe = urlunsplit((parsed.scheme, host, parsed.path, "", ""))
        return safe + suffix
    except ValueError:
        return "<redacted-url>" + suffix


def sanitize_diagnostic(value: object, limit: int = 500) -> str:
    """Remove common credentials and URL query data from public diagnostics."""
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    text = _HTTP_URL.sub(_sanitize_url, text)
    text = _SECRET_ASSIGNMENT.sub(
        lambda match: f"{match.group(1)}{match.group(2)}<redacted>",
        text,
    )
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


def _public_fetch_report(payload: dict[str, Any]) -> dict[str, Any]:
    report: dict[str, Any] = {
        key: payload[key]
        for key in (
            "status",
            "attempted",
            "successful",
            "empty",
            "failed",
            "item_count",
        )
        if key in payload
    }
    sources = []
    for source in payload.get("sources", []):
        if not isinstance(source, dict):
            continue
        public_source = {
            key: source[key]
            for key in ("source", "status", "item_count", "subsource_counts")
            if key in source
        }
        if source.get("error"):
            public_source["error"] = sanitize_diagnostic(source["error"])
        sources.append(public_source)
    report["sources"] = sources
    return report


@dataclass
class RunAlert:
    """One informational, warning, or failure signal for the run."""

    severity: AlertSeverity
    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": sanitize_diagnostic(self.message),
        }


@dataclass
class RunReport:
    """Mutable report populated as the native pipeline advances."""

    run_id: str
    date: str
    timezone_name: str
    started_at: datetime
    status: Literal["running", "success", "warning", "failure"] = "running"
    finished_at: datetime | None = None
    duration_seconds: float | None = None
    metrics: dict[str, int] = field(default_factory=dict)
    fetch_report: dict[str, Any] | None = None
    summaries: list[str] = field(default_factory=list)
    alerts: list[RunAlert] = field(default_factory=list)
    error: str | None = None

    @classmethod
    def start(
        cls,
        *,
        date: str,
        timezone_name: str,
        started_at: datetime | None = None,
    ) -> "RunReport":
        moment = started_at or _utc_now()
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        run_id = moment.astimezone(timezone.utc).strftime("run-%Y%m%dT%H%M%S.%fZ")
        return cls(
            run_id=run_id,
            date=date,
            timezone_name=timezone_name,
            started_at=moment,
        )

    def set_metric(self, name: str, value: int) -> None:
        self.metrics[name] = max(0, int(value))

    def attach_fetch_report(self, payload: dict[str, Any] | None) -> None:
        if payload is None:
            return
        self.fetch_report = _public_fetch_report(payload)
        if payload.get("status") == "partial_failure":
            failed = int(payload.get("failed", 0))
            attempted = int(payload.get("attempted", 0))
            self.add_alert(
                "warning",
                "partial_source_failure",
                f"{failed}/{attempted} 个顶层来源采集失败，已使用其余来源继续生成。",
            )

    def add_alert(
        self,
        severity: AlertSeverity,
        code: str,
        message: str,
    ) -> None:
        if any(alert.code == code for alert in self.alerts):
            return
        self.alerts.append(RunAlert(severity, code, message))

    def record_summary(self, language: str) -> None:
        if language not in self.summaries:
            self.summaries.append(language)

    def fail(self, error: object) -> None:
        self.error = sanitize_diagnostic(error)
        self.status = "failure"
        self.add_alert("failure", "pipeline_failed", self.error)

    def finish(self, finished_at: datetime | None = None) -> None:
        moment = finished_at or _utc_now()
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        self.finished_at = moment
        self.duration_seconds = round(
            max(0.0, (moment - self.started_at).total_seconds()),
            3,
        )
        if self.status == "running":
            self.status = (
                "warning"
                if any(alert.severity == "warning" for alert in self.alerts)
                else "success"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "run_id": self.run_id,
            "date": self.date,
            "timezone": self.timezone_name,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "finished_at": (
                self.finished_at.isoformat() if self.finished_at is not None else None
            ),
            "duration_seconds": self.duration_seconds,
            "metrics": dict(self.metrics),
            "fetch_report": self.fetch_report,
            "summaries": list(self.summaries),
            "alerts": [alert.to_dict() for alert in self.alerts],
            "error": self.error,
        }


def save_run_report(
    report: RunReport,
    path: Path = DEFAULT_RUN_REPORT_PATH,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
    _atomic_write_text(path, f"{payload}\n")
    return path


def load_run_report(path: Path = DEFAULT_RUN_REPORT_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _markdown_cell(value: object) -> str:
    return sanitize_diagnostic(value, limit=240).replace("|", "\\|")


def render_markdown_report(payload: dict[str, Any]) -> str:
    """Render a compact GitHub Actions job summary."""
    status = str(payload.get("status", "unknown"))
    icons = {
        "success": "✅",
        "warning": "⚠️",
        "failure": "❌",
        "running": "⏳",
    }
    lines = [
        "## BMTNews 采集运行报告",
        "",
        f"{icons.get(status, 'ℹ️')} **状态：{status}**",
        "",
        f"- 运行：`{_markdown_cell(payload.get('run_id', 'unknown'))}`",
        f"- 日期：{_markdown_cell(payload.get('date', '—'))} "
        f"({_markdown_cell(payload.get('timezone', '—'))})",
        f"- 耗时：{_markdown_cell(payload.get('duration_seconds', '—'))} 秒",
        "",
        "### 处理漏斗",
        "",
        "| 阶段 | 数量 |",
        "| --- | ---: |",
    ]
    metrics = payload.get("metrics") or {}
    for key, label in _METRIC_LABELS:
        lines.append(f"| {label} | {int(metrics.get(key, 0))} |")

    fetch_report = payload.get("fetch_report") or {}
    sources = fetch_report.get("sources") or []
    if sources:
        lines += [
            "",
            "### 来源状态",
            "",
            "| 来源 | 状态 | 条数 | 诊断 |",
            "| --- | --- | ---: | --- |",
        ]
        for source in sources:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _markdown_cell(source.get("source", "unknown")),
                        _markdown_cell(source.get("status", "unknown")),
                        str(int(source.get("item_count", 0))),
                        _markdown_cell(source.get("error", "")) or "—",
                    ]
                )
                + " |"
            )

    alerts = payload.get("alerts") or []
    if alerts:
        lines += ["", "### 提示与预警", ""]
        alert_icons = {"info": "ℹ️", "warning": "⚠️", "failure": "❌"}
        for alert in alerts:
            severity = str(alert.get("severity", "info"))
            lines.append(
                f"- {alert_icons.get(severity, 'ℹ️')} "
                f"`{_markdown_cell(alert.get('code', 'unknown'))}` "
                f"{_markdown_cell(alert.get('message', ''))}"
            )

    return "\n".join(lines).rstrip() + "\n"


def render_github_annotations(payload: dict[str, Any]) -> list[str]:
    """Return workflow commands for report warnings and failures."""
    annotations = []
    for alert in payload.get("alerts") or []:
        severity = str(alert.get("severity", "info"))
        if severity not in {"warning", "failure"}:
            continue
        command = "warning" if severity == "warning" else "error"
        title = sanitize_diagnostic(alert.get("code", "pipeline_alert"), limit=80)
        message = sanitize_diagnostic(alert.get("message", ""), limit=500)
        title = title.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        message = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        annotations.append(f"::{command} title=BMTNews {title}::{message}")
    return annotations


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a Horizon run report")
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_RUN_REPORT_PATH,
        help="Run report JSON path",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Markdown file to append to; defaults to GITHUB_STEP_SUMMARY or stdout",
    )
    args = parser.parse_args()

    output_path = args.output
    if output_path is None and os.getenv("GITHUB_STEP_SUMMARY"):
        output_path = Path(os.environ["GITHUB_STEP_SUMMARY"])

    payload = None
    if args.input.exists():
        payload = load_run_report(args.input)
        markdown = render_markdown_report(payload)
    else:
        markdown = (
            "## BMTNews 采集运行报告\n\n"
            "⚠️ 本次任务没有生成结构化运行报告，请检查初始化或依赖安装步骤。\n"
        )

    if payload is not None and os.getenv("GITHUB_ACTIONS") == "true":
        for annotation in render_github_annotations(payload):
            print(annotation)

    if output_path is None:
        print(markdown, end="")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("a", encoding="utf-8") as output_file:
            output_file.write(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

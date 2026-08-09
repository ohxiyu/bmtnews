"""Static thread, entity, and weekly pages generated from the archive.

These pages turn the daily stream into durable, linkable assets: a thread
page follows one event across days, an entity page collects everything
published about a company, protocol, or regulator. They are plain Jekyll
pages written by the pipeline, so no runtime service is involved.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable, List, Sequence

from ._file_utils import _atomic_write_text
from .archive import ArchiveRecord
from .threads import EntitySummary
# Shared HTML helpers; same escaping rules as the daily feed rendering.
from .web_feed import _escape as escape_text, _safe_url as safe_url

logger = logging.getLogger(__name__)

THREADS_ROOT = Path("docs/threads")
ENTITY_ROOT = Path("docs/entity")
WEEKLY_ROOT = Path("docs/weekly")
DATA_ROOT = Path("docs/_data")

_LABELS = {
    "zh": {
        "threads_title": "事件线",
        "threads_intro": "跨天追踪的持续事件，最新进展在最上面。",
        "entities_title": "实体索引",
        "entities_intro": "按公司、协议、监管机构聚合的历史报道。",
        "thread_prefix": "事件线",
        "entity_prefix": "实体",
        "days": "天",
        "entries": "条",
        "timeline": "时间线",
        "mentions": "报道",
        "empty": "暂无内容。",
        "back": "返回首页",
        "weekly_title": "本周回顾",
    },
    "en": {
        "threads_title": "Story Threads",
        "threads_intro": "Continuing events tracked across days, most recent first.",
        "entities_title": "Entity Index",
        "entities_intro": "Coverage grouped by company, protocol, and regulator.",
        "thread_prefix": "Thread",
        "entity_prefix": "Entity",
        "days": "days",
        "entries": "entries",
        "timeline": "Timeline",
        "mentions": "Coverage",
        "empty": "Nothing here yet.",
        "back": "Back to the feed",
        "weekly_title": "Weekly Review",
    },
}


def _front_matter(
    *,
    title: str,
    permalink: str,
    language: str,
    description: str = "",
) -> str:
    # Titles reach the raw <title> element through Liquid, so markup
    # characters are removed here rather than escaped downstream.
    def _plain(value: str) -> str:
        return (
            str(value)
            .replace('"', "'")
            .replace("<", "")
            .replace(">", "")
            .replace("\n", " ")
            .strip()
        )

    safe_title = _plain(title)
    safe_description = _plain(description)[:180]
    return (
        "---\n"
        "layout: default\n"
        f'title: "{safe_title}"\n'
        f"permalink: {permalink}\n"
        f"interface_language: {language}\n"
        f'description: "{safe_description}"\n'
        "page_type: archive\n"
        "---\n\n"
    )


def _record_row(record: ArchiveRecord, language: str) -> str:
    labels = _LABELS[language]
    title = escape_text(record.title_for(language) or record.url)
    url = safe_url(record.url)
    title_html = (
        f'<a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a>'
        if url
        else title
    )
    score = (
        f'<span class="score-badge" data-tier="'
        f'{"high" if (record.score or 0) >= 9 else "good" if (record.score or 0) >= 7 else "mid"}'
        f'">{record.score:.1f}</span>'
        if record.score is not None
        else ""
    )
    summary = escape_text(record.summary_for(language))
    source = escape_text(record.source_label or record.source_type)
    return (
        '<li class="archive-row">'
        f'<time datetime="{escape_text(record.date)}">{escape_text(record.date)}</time>'
        f'<div class="archive-row-body"><h3>{title_html}</h3>'
        + (f'<p class="archive-row-summary">{summary}</p>' if summary else "")
        + f'<p class="archive-row-meta">{source}</p></div>'
        f"{score}</li>"
    )


def _records_list(records: Sequence[ArchiveRecord], language: str) -> str:
    if not records:
        return f'<p class="empty-state">{_LABELS[language]["empty"]}</p>'
    rows = "".join(_record_row(record, language) for record in records)
    return f'<ul class="archive-list">{rows}</ul>'


def render_thread_page(
    thread_id: str,
    records: Sequence[ArchiveRecord],
    language: str,
) -> str:
    labels = _LABELS[language]
    ordered = sorted(records, key=lambda r: (r.date, r.rank), reverse=True)
    latest = ordered[0]
    days = len({record.date for record in records})
    title = latest.title_for(language) or thread_id
    prefix = "" if language == "zh" else "/en"
    body = (
        f'<p class="archive-lede">{labels["thread_prefix"]} · '
        f"{days} {labels['days']} · {len(ordered)} {labels['entries']}</p>"
        f"<h2>{escape_text(labels['timeline'])}</h2>"
        f"{_records_list(ordered, language)}"
        f'<p class="archive-back"><a href="{prefix}/">{labels["back"]}</a></p>'
    )
    return (
        _front_matter(
            title=title,
            permalink=f"{prefix}/threads/{thread_id}/",
            language=language,
            description=latest.summary_for(language),
        )
        + body
        + "\n"
    )


def render_entity_page(entity: EntitySummary, language: str) -> str:
    labels = _LABELS[language]
    prefix = "" if language == "zh" else "/en"
    body = (
        f"<h2>{escape_text(entity.label)}</h2>"
        f'<p class="archive-lede">{labels["entity_prefix"]} · '
        f"{entity.count} {labels['entries']}</p>"
        f"<h2>{escape_text(labels['mentions'])}</h2>"
        f"{_records_list(entity.records[:60], language)}"
        f'<p class="archive-back"><a href="{prefix}/">{labels["back"]}</a></p>'
    )
    description = (
        entity.records[0].summary_for(language) if entity.records else ""
    )
    return (
        _front_matter(
            title=entity.label,
            permalink=f"{prefix}/entity/{entity.slug}/",
            language=language,
            description=description,
        )
        + body
        + "\n"
    )


def build_thread_index_data(
    threads: Sequence[tuple[str, List[ArchiveRecord]]],
) -> dict:
    """Data consumed by the always-present /threads/ index page."""
    rows = []
    for thread_id, records in threads:
        latest = max(records, key=lambda record: (record.date, record.rank))
        rows.append(
            {
                "thread_id": thread_id,
                "latest_date": latest.date,
                "days": len({record.date for record in records}),
                "entries": len(records),
                "title_zh": latest.title_zh,
                "title_en": latest.title_en,
            }
        )
    return {"threads": rows}


def build_entity_index_data(entities: Sequence[EntitySummary]) -> dict:
    """Data consumed by the always-present /entity/ index page."""
    return {
        "entities": [
            {"slug": entity.slug, "label": entity.label, "mentions": entity.count}
            for entity in entities
        ]
    }


def write_index_data(
    threads: Sequence[tuple[str, List[ArchiveRecord]]],
    entities: Sequence[EntitySummary],
    *,
    data_root: Path = DATA_ROOT,
) -> List[Path]:
    """Write the Jekyll data files backing the index pages."""
    data_root.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    for name, payload in (
        ("threads.json", build_thread_index_data(threads)),
        ("entities.json", build_entity_index_data(entities)),
    ):
        path = data_root / name
        _atomic_write_text(
            path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        )
        written.append(path)
    return written


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(path, content)


def publish_archive_pages(
    threads: Sequence[tuple[str, List[ArchiveRecord]]],
    entities: Sequence[EntitySummary],
    languages: Iterable[str],
    *,
    threads_root: Path = THREADS_ROOT,
    entity_root: Path = ENTITY_ROOT,
    data_root: Path = DATA_ROOT,
) -> dict[str, int]:
    """Write every thread and entity page plus the index data files.

    The index pages themselves are committed Jekyll pages that read these
    data files, so /threads/ and /entity/ resolve from the first deploy
    even before any archive content exists.
    """
    written = {"threads": 0, "entities": 0}
    write_index_data(threads, entities, data_root=data_root)
    for language in languages:
        normalized = "en" if str(language).lower().startswith("en") else "zh"
        suffix = "" if normalized == "zh" else "en-"
        for thread_id, records in threads:
            _write(
                threads_root / f"{suffix}{thread_id}.html",
                render_thread_page(thread_id, records, normalized),
            )
            written["threads"] += 1
        for entity in entities:
            _write(
                entity_root / f"{suffix}{entity.slug}.html",
                render_entity_page(entity, normalized),
            )
            written["entities"] += 1
    return written

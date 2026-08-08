"""Tests for the archive layer, thread linking, and entity grouping."""

from datetime import date, datetime, timezone
from pathlib import Path

from src.archive import (
    ArchiveRecord,
    build_records,
    load_archive,
    load_recent_archive,
    save_edition_records,
)
from src.models import ContentItem, SourceType
from src.threads import (
    assign_threads,
    collect_entities,
    collect_threads,
    fingerprint,
    normalize_tag,
    same_thread,
    thread_id_for,
)


def make_item(
    item_id: str,
    *,
    title: str = "Title",
    tags: list[str] | None = None,
    score: float = 8.0,
    merged: list[str] | None = None,
) -> ContentItem:
    metadata = {"category": "crypto-markets", "feed_name": "Feed"}
    if merged:
        metadata["merged_sources"] = merged
    return ContentItem(
        id=item_id,
        source_type=SourceType.RSS,
        title=title,
        url=f"https://example.com/{item_id}",
        published_at=datetime(2026, 8, 9, tzinfo=timezone.utc),
        ai_score=score,
        ai_tags=tags or [],
        metadata=metadata,
    )


def make_record(
    date_str: str,
    *,
    rank: int = 1,
    title_en: str = "",
    tags: list[str] | None = None,
    thread_id: str | None = None,
    url: str | None = None,
    score: float = 8.0,
) -> ArchiveRecord:
    return ArchiveRecord(
        date=date_str,
        rank=rank,
        item_id=f"{date_str}-{rank}",
        url=url or f"https://example.com/{date_str}-{rank}",
        title_en=title_en,
        title_zh=title_en,
        score=score,
        tags=tags or [],
        thread_id=thread_id,
    )


def test_save_edition_records_replaces_same_date(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    save_edition_records(
        [make_record("2026-08-09", rank=1, title_en="First run")],
        date="2026-08-09",
        root=root,
    )
    save_edition_records(
        [
            make_record("2026-08-09", rank=1, title_en="Rebuilt"),
            make_record("2026-08-09", rank=2, title_en="Second"),
        ],
        date="2026-08-09",
        root=root,
    )
    records = load_archive(root=root)
    assert [record.title_en for record in records] == ["Rebuilt", "Second"]


def test_save_edition_records_keeps_other_dates(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    save_edition_records(
        [make_record("2026-08-08", title_en="Older")],
        date="2026-08-08",
        root=root,
    )
    save_edition_records(
        [make_record("2026-08-09", title_en="Newer")],
        date="2026-08-09",
        root=root,
    )
    assert [r.title_en for r in load_archive(root=root)] == ["Older", "Newer"]


def test_load_archive_skips_corrupt_lines(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    root.mkdir()
    path = root / "2026-08.jsonl"
    good = make_record("2026-08-09", title_en="Good").model_dump_json()
    path.write_text(f"{good}\nnot json\n\n", encoding="utf-8")
    records = load_archive(root=root)
    assert [record.title_en for record in records] == ["Good"]


def test_load_recent_archive_filters_by_window(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    save_edition_records(
        [make_record("2026-07-01", title_en="Old")], date="2026-07-01", root=root
    )
    save_edition_records(
        [make_record("2026-08-09", title_en="Fresh")], date="2026-08-09", root=root
    )
    recent = load_recent_archive(7, today=date(2026, 8, 9), root=root)
    assert [record.title_en for record in recent] == ["Fresh"]


def test_build_records_captures_provenance_and_threads() -> None:
    item = make_item(
        "story",
        title="Bybit hack",
        tags=["bybit", "security"],
        merged=["rss", "telegram"],
    )
    item.metadata["thread_id"] = "tabc"
    item.metadata["thread_day"] = 2
    records = build_records(
        [item], date="2026-08-09", top_category_of=lambda _item: "crypto"
    )
    assert records[0].sources_count == 2
    assert records[0].top_category == "crypto"
    assert records[0].thread_id == "tabc"
    assert records[0].thread_day == 2
    assert records[0].rank == 1


def test_normalize_tag_slugifies() -> None:
    assert normalize_tag("#Lazarus Group") == "lazarus-group"
    assert normalize_tag("X Layer") == "x-layer"
    assert normalize_tag("  ") == ""


def test_same_thread_matches_continuing_coverage() -> None:
    first = fingerprint(
        title_en="Bybit loses $1.5B in Lazarus Group hack",
        tags=["bybit", "lazarus-group", "security"],
    )
    follow_up = fingerprint(
        title_en="Bybit sues North Korea and Lazarus Group over hack",
        tags=["bybit", "lazarus-group", "north-korea"],
    )
    unrelated = fingerprint(
        title_en="Kraken details war-game load testing",
        tags=["kraken", "engineering"],
    )
    assert same_thread(first, follow_up)
    assert not same_thread(first, unrelated)


def test_same_thread_ignores_empty_fingerprints() -> None:
    assert not same_thread(fingerprint(), fingerprint(title_en="Anything here"))


def test_assign_threads_links_into_archive_and_counts_days() -> None:
    history = [
        make_record(
            "2026-08-07",
            title_en="Bybit loses funds in Lazarus Group hack",
            tags=["bybit", "lazarus-group"],
            thread_id="tseed",
        ),
        make_record(
            "2026-08-08",
            title_en="Bybit traces stolen Lazarus Group funds",
            tags=["bybit", "lazarus-group"],
            thread_id="tseed",
        ),
    ]
    story = (
        "https://example.com/new",
        fingerprint(
            title_en="Bybit sues North Korea and Lazarus Group",
            tags=["bybit", "lazarus-group"],
        ),
    )
    assignments = assign_threads([story], history, edition_date="2026-08-09")
    assignment = assignments["https://example.com/new"]
    assert assignment.thread_id == "tseed"
    assert assignment.day == 3
    assert assignment.is_continuation


def test_assign_threads_starts_fresh_without_a_match() -> None:
    story = (
        "https://example.com/solo",
        fingerprint(title_en="Kraken publishes load testing writeup", tags=["kraken"]),
    )
    assignments = assign_threads([story], [], edition_date="2026-08-09")
    assignment = assignments["https://example.com/solo"]
    assert assignment.thread_id == thread_id_for("https://example.com/solo")
    assert assignment.day == 1
    assert not assignment.is_continuation


def test_collect_threads_requires_multiple_days() -> None:
    records = [
        make_record("2026-08-08", thread_id="ta", title_en="A1"),
        make_record("2026-08-09", thread_id="ta", title_en="A2"),
        make_record("2026-08-09", rank=2, thread_id="tb", title_en="B1"),
    ]
    threads = collect_threads(records)
    assert [thread_id for thread_id, _ in threads] == ["ta"]


def test_collect_entities_sanitizes_model_generated_labels() -> None:
    records = [
        make_record(f"2026-08-0{i}", tags=['Bybit <script>alert("x")</script>'])
        for i in range(1, 4)
    ]
    entities = collect_entities(records, minimum_mentions=3)
    assert entities[0].label == "Bybit scriptalert(x)/script"
    assert "<" not in entities[0].label


def test_collect_entities_skips_generic_tags() -> None:
    records = [
        make_record(f"2026-08-0{i}", tags=["Binance", "crypto", "security"])
        for i in range(1, 5)
    ]
    entities = collect_entities(records, minimum_mentions=3)
    assert [entity.slug for entity in entities] == ["binance"]
    assert entities[0].count == 4

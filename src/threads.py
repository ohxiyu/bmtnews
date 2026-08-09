"""Story threads and entity extraction derived from the archive.

A *thread* groups coverage of one continuing event across days ("Bybit
hacked" → "Bybit sues North Korea"), so a reader can follow a story instead
of seeing disconnected daily items. Matching is deterministic and offline:
it compares normalized tag and title tokens, with no extra AI calls.

An *entity* is a recurring tag (Binance, Lazarus Group, SEC, ...). Entities
with enough mentions get their own aggregated page.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence

from .archive import ArchiveRecord

# Tokens that carry no discriminating power for thread matching.
_STOPWORDS = {
    "about", "after", "against", "amid", "announce", "announced",
    "announcement", "another", "over", "with", "from", "into", "that",
    "this", "their", "there", "these", "those", "will", "would", "could",
    "have", "has", "been", "being", "more", "most", "than", "then", "they",
    "what", "when", "where", "which", "while", "your", "news", "report",
    "reports", "update", "updates", "says", "said", "new", "now",
    "crypto", "cryptocurrency", "blockchain", "market", "markets",
}

# Tags too generic to deserve an entity page.
_GENERIC_TAGS = {
    "ai", "ai-safety", "blockchain", "crypto", "cryptocurrency", "defi",
    "engineering", "exchange", "exchange-announcements",
    "exchange-operations", "crypto-markets", "crypto-protocols",
    "crypto-regulation", "macro-regulation", "markets", "news", "onchain",
    "regulation", "security", "stablecoin", "technology", "trading",
}

_CJK = re.compile(r"[一-鿿㐀-䶿]{2,}")
_WORD = re.compile(r"[a-z0-9]+")


def clean_label(tag: str) -> str:
    """Sanitize a model-generated tag for display.

    Entity labels reach page front matter and therefore the raw ``<title>``
    element, so markup characters are stripped at the source rather than
    relying on every downstream renderer to escape them.
    """
    text = unicodedata.normalize("NFKC", str(tag or "")).strip().lstrip("#")
    text = re.sub(r"[<>\"'&`]", "", text)
    return re.sub(r"\s+", " ", text).strip()[:60]


def normalize_tag(tag: str) -> str:
    """Lowercase, ASCII-fold, and hyphenate a tag into a stable slug."""
    text = unicodedata.normalize("NFKC", str(tag or "")).strip().lstrip("#")
    text = text.lower()
    text = re.sub(r"[\s_/]+", "-", text)
    text = re.sub(r"[^a-z0-9一-鿿-]", "", text)
    return re.sub(r"-{2,}", "-", text).strip("-")


def _title_tokens(title: str) -> set[str]:
    tokens = {
        word
        for word in _WORD.findall(title.lower())
        if len(word) >= 4 and word not in _STOPWORDS
    }
    for run in _CJK.findall(title):
        tokens.update(run[i : i + 2] for i in range(len(run) - 1))
    return tokens


@dataclass
class StoryFingerprint:
    """Comparable token sets for one story."""

    tags: set[str] = field(default_factory=set)
    tokens: set[str] = field(default_factory=set)

    @property
    def is_empty(self) -> bool:
        return not (self.tags or self.tokens)


def fingerprint(
    *,
    title_zh: str = "",
    title_en: str = "",
    tags: Iterable[str] = (),
) -> StoryFingerprint:
    normalized_tags = {
        slug for slug in (normalize_tag(tag) for tag in tags) if slug
    }
    tokens = set(normalized_tags)
    tokens |= _title_tokens(title_en or "")
    tokens |= _title_tokens(title_zh or "")
    return StoryFingerprint(tags=normalized_tags, tokens=tokens)


def fingerprint_of_record(record: ArchiveRecord) -> StoryFingerprint:
    return fingerprint(
        title_zh=record.title_zh,
        title_en=record.title_en,
        tags=record.tags,
    )


def _overlap(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / min(len(left), len(right))


def same_thread(
    left: StoryFingerprint,
    right: StoryFingerprint,
    *,
    strong_tag_matches: int = 2,
    strong_threshold: float = 0.30,
    loose_threshold: float = 0.55,
) -> bool:
    """Decide whether two stories continue the same event.

    Two independent signals, either of which is enough: several shared
    entity tags plus moderate token overlap, or high token overlap alone.
    Both sides are intentionally conservative — a missed link only costs a
    badge, while a wrong link merges unrelated stories.
    """
    if left.is_empty or right.is_empty:
        return False
    shared_tags = len(left.tags & right.tags)
    overlap = _overlap(left.tokens, right.tokens)
    if shared_tags >= strong_tag_matches and overlap >= strong_threshold:
        return True
    return overlap >= loose_threshold


def thread_id_for(seed_url: str) -> str:
    """Stable thread id derived from the first story's URL."""
    digest = hashlib.sha256(seed_url.encode("utf-8")).hexdigest()[:10]
    return f"t{digest}"


@dataclass
class ThreadAssignment:
    """Thread membership computed for one story."""

    thread_id: str
    day: int
    previous_dates: List[str] = field(default_factory=list)

    @property
    def is_continuation(self) -> bool:
        return self.day > 1


def assign_threads(
    stories: Sequence[tuple[str, StoryFingerprint]],
    history: Sequence[ArchiveRecord],
    *,
    edition_date: str,
) -> Dict[str, ThreadAssignment]:
    """Map each story key to its thread, linking into archived coverage.

    ``stories`` is a sequence of ``(key, fingerprint)`` pairs where ``key``
    identifies the story (its URL). ``history`` should already be limited
    to a recent window by the caller.
    """
    history_prints = [
        (record, fingerprint_of_record(record))
        for record in history
        if record.date != edition_date
    ]
    # Existing threads: id -> dates already published under it.
    thread_dates: Dict[str, set[str]] = {}
    for record in history:
        if record.thread_id:
            thread_dates.setdefault(record.thread_id, set()).add(record.date)

    assignments: Dict[str, ThreadAssignment] = {}
    for key, print_ in stories:
        if print_.is_empty:
            continue
        matched_id: Optional[str] = None
        matched_dates: set[str] = set()

        # Prefer the most recent archived match.
        for record, record_print in sorted(
            history_prints, key=lambda pair: pair[0].date, reverse=True
        ):
            if not same_thread(print_, record_print):
                continue
            matched_id = record.thread_id or thread_id_for(record.url)
            matched_dates = set(thread_dates.get(matched_id, set()))
            matched_dates.add(record.date)
            break

        # Otherwise join a same-edition sibling so one event stays one thread.
        if matched_id is None:
            for other_key, other_print in stories:
                if other_key == key or other_key not in assignments:
                    continue
                if same_thread(print_, other_print):
                    sibling = assignments[other_key]
                    matched_id = sibling.thread_id
                    matched_dates = set(sibling.previous_dates)
                    break

        if matched_id is None:
            matched_id = thread_id_for(key)

        previous = sorted(date for date in matched_dates if date != edition_date)
        assignments[key] = ThreadAssignment(
            thread_id=matched_id,
            day=len(previous) + 1,
            previous_dates=previous,
        )
    return assignments


@dataclass
class EntitySummary:
    """Aggregated mentions of one recurring entity."""

    slug: str
    label: str
    count: int
    records: List[ArchiveRecord] = field(default_factory=list)


def collect_entities(
    records: Sequence[ArchiveRecord],
    *,
    minimum_mentions: int = 3,
    limit: int = 60,
) -> List[EntitySummary]:
    """Group archive records by recurring, non-generic tag."""
    buckets: Dict[str, EntitySummary] = {}
    for record in records:
        seen: set[str] = set()
        for tag in record.tags:
            slug = normalize_tag(tag)
            if not slug or slug in _GENERIC_TAGS or len(slug) < 3:
                continue
            if slug in seen:
                continue
            seen.add(slug)
            entity = buckets.get(slug)
            if entity is None:
                entity = EntitySummary(
                    slug=slug,
                    label=clean_label(tag) or slug,
                    count=0,
                )
                buckets[slug] = entity
            entity.count += 1
            entity.records.append(record)

    entities = [
        entity for entity in buckets.values() if entity.count >= minimum_mentions
    ]
    entities.sort(key=lambda entity: (-entity.count, entity.slug))
    for entity in entities:
        entity.records.sort(key=lambda record: (record.date, record.rank), reverse=True)
    return entities[:limit]


def collect_threads(
    records: Sequence[ArchiveRecord],
    *,
    minimum_days: int = 2,
    limit: int = 80,
) -> List[tuple[str, List[ArchiveRecord]]]:
    """Return multi-day threads, newest activity first."""
    buckets: Dict[str, List[ArchiveRecord]] = {}
    for record in records:
        if record.thread_id:
            buckets.setdefault(record.thread_id, []).append(record)

    threads = []
    for thread_id, thread_records in buckets.items():
        if len({record.date for record in thread_records}) < minimum_days:
            continue
        thread_records.sort(key=lambda record: (record.date, record.rank))
        threads.append((thread_id, thread_records))
    threads.sort(key=lambda pair: pair[1][-1].date, reverse=True)
    return threads[:limit]

"""Persistent daily-feed state for incremental static-site updates."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, ValidationError

from ._file_utils import _atomic_write_text
from .models import ContentItem


DAILY_FEED_STATE_PATH = Path("docs/_data/bmtnews_state.json")
_TRACKING_QUERY_PARAMETERS = {
    "_ga",
    "dclid",
    "fbclid",
    "gclid",
    "igshid",
    "li_fat_id",
    "mc_cid",
    "mc_eid",
    "msclkid",
    "ttclid",
    "twclid",
    "vero_id",
}
_PERSISTED_METADATA_KEYS = {
    "category",
    "discussion_url",
    "feed_name",
    "sources",
    "subreddit",
}
_PERSISTED_METADATA_PREFIXES = (
    "background_",
    "community_discussion_",
    "detailed_summary_",
    "title_",
)


class DailyFeedStateError(ValueError):
    """Raised when persisted feed state cannot be read safely."""


class DailyFeedState(BaseModel):
    """Selected public items retained for one local calendar day."""

    version: int = 1
    date: str
    timezone: str
    updated_at: datetime
    analyzed_keys: list[str] = Field(default_factory=list)
    items: list[ContentItem] = Field(default_factory=list)


def local_date_for(moment: datetime, timezone_name: str) -> str:
    """Return the calendar date for ``moment`` in the configured timezone."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(ZoneInfo(timezone_name)).strftime("%Y-%m-%d")


def items_for_local_date(
    items: Iterable[ContentItem],
    date: str,
    timezone_name: str,
) -> list[ContentItem]:
    """Keep only items published on ``date`` in ``timezone_name``."""
    return [
        item
        for item in items
        if local_date_for(item.published_at, timezone_name) == date
    ]


def _canonical_url(url: str) -> str:
    parsed = urlsplit(url)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    port = parsed.port
    if (scheme, port) in {("http", 80), ("https", 443)}:
        port = None
    netloc = host if port is None else f"{host}:{port}"
    path = parsed.path.rstrip("/") or "/"
    query = urlencode(
        [
            (name, value)
            for name, value in parse_qsl(parsed.query, keep_blank_values=True)
            if not name.lower().startswith("utm_")
            and name.lower() not in _TRACKING_QUERY_PARAMETERS
        ],
        doseq=True,
    )
    return urlunsplit((scheme, netloc, path, query, ""))


def _item_identity(item: ContentItem) -> str:
    canonical_url = _canonical_url(str(item.url))
    return canonical_url or item.id


def analyzed_item_key(item: ContentItem) -> str:
    """Return a non-reversible key for cumulative analyzed-item statistics."""
    return hashlib.sha256(item.id.encode("utf-8")).hexdigest()


def _published_timestamp(item: ContentItem) -> float:
    moment = item.published_at
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.timestamp()


def sort_daily_items(items: Iterable[ContentItem]) -> list[ContentItem]:
    """Sort by impact, then recency, with a deterministic final tie-break."""
    return sorted(
        items,
        key=lambda item: (
            -(item.ai_score or 0),
            -_published_timestamp(item),
            _item_identity(item),
        ),
    )


def merge_daily_items(
    existing: Iterable[ContentItem],
    incoming: Iterable[ContentItem],
    date: str,
    timezone_name: str,
) -> list[ContentItem]:
    """Merge selected items without dropping earlier entries from the same day."""
    merged: dict[str, ContentItem] = {}
    for item in items_for_local_date(existing, date, timezone_name):
        merged[_item_identity(item)] = item
    for item in items_for_local_date(incoming, date, timezone_name):
        merged[_item_identity(item)] = item
    return sort_daily_items(merged.values())


def _public_state_item(item: ContentItem) -> ContentItem:
    """Remove fetched source bodies and unused analysis fields before publishing state."""
    metadata = {
        key: value
        for key, value in item.metadata.items()
        if key in _PERSISTED_METADATA_KEYS
        or key.startswith(_PERSISTED_METADATA_PREFIXES)
    }
    return item.model_copy(
        update={
            "content": None,
            "metadata": metadata,
            "ai_reason": None,
            "ai_tags": [],
        },
        deep=True,
    )


def load_daily_feed_state(
    date: str,
    timezone_name: str,
    path: Path = DAILY_FEED_STATE_PATH,
) -> DailyFeedState:
    """Load current-day state; a different day starts with an empty state."""
    empty = DailyFeedState(
        date=date,
        timezone=timezone_name,
        updated_at=datetime.now(timezone.utc),
    )
    if not path.exists():
        return empty

    try:
        state = DailyFeedState.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, ValueError) as exc:
        raise DailyFeedStateError(f"Invalid daily feed state: {path}") from exc

    if state.date != date or state.timezone != timezone_name:
        return empty
    return state


def save_daily_feed_state(
    state: DailyFeedState,
    path: Path = DAILY_FEED_STATE_PATH,
) -> Path:
    """Atomically persist the minimum public fields required for the next merge."""
    path.parent.mkdir(parents=True, exist_ok=True)
    public_state = state.model_copy(
        update={"items": [_public_state_item(item) for item in state.items]},
        deep=True,
    )
    payload = json.dumps(
        public_state.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
    )
    _atomic_write_text(path, f"{payload}\n")
    return path

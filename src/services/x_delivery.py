"""Publish the day's top stories to X (Twitter).

Disabled by default and doubly gated: the config block must set
``enabled: true`` **and** all four OAuth 1.0a credentials must be present in
the environment. Without both, the publisher reports SKIPPED and posts
nothing, so merging this code cannot by itself cause an outward-facing post.

Requests are signed with OAuth 1.0a user context, which is what the X API
v2 ``POST /2/tweets`` endpoint requires for posting on behalf of an account.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List
from urllib.parse import quote, urlsplit

import httpx
from rich.console import Console

from ..models import ContentItem, XDeliveryConfig

X_TWEETS_ENDPOINT = "https://api.x.com/2/tweets"
TWEET_LIMIT = 280
# X counts every URL as a fixed-width t.co link regardless of real length.
TCO_LENGTH = 23


class XDeliveryStatus(str, Enum):
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILURE = "failure"


@dataclass(frozen=True)
class XDeliveryResult:
    """Sanitized result safe for logs and public run reports."""

    status: XDeliveryStatus
    detail: str = ""
    posted: int = 0


def _percent_encode(value: str) -> str:
    return quote(str(value), safe="-._~")


def _oauth_header(
    method: str,
    url: str,
    *,
    consumer_key: str,
    consumer_secret: str,
    access_token: str,
    access_secret: str,
    nonce: str | None = None,
    timestamp: str | None = None,
) -> str:
    """Build an OAuth 1.0a Authorization header for a JSON-body request.

    A JSON body is not part of the signature base string; only the request
    method, URL, and OAuth parameters are signed.
    """
    oauth_params = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": nonce or secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": timestamp or str(int(time.time())),
        "oauth_token": access_token,
        "oauth_version": "1.0",
    }
    parameter_string = "&".join(
        f"{_percent_encode(key)}={_percent_encode(oauth_params[key])}"
        for key in sorted(oauth_params)
    )
    split = urlsplit(url)
    base_url = f"{split.scheme}://{split.netloc}{split.path}"
    base_string = "&".join(
        [
            method.upper(),
            _percent_encode(base_url),
            _percent_encode(parameter_string),
        ]
    )
    signing_key = (
        f"{_percent_encode(consumer_secret)}&{_percent_encode(access_secret)}"
    )
    signature = base64.b64encode(
        hmac.new(
            signing_key.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha1,
        ).digest()
    ).decode("ascii")
    header_params = {**oauth_params, "oauth_signature": signature}
    joined = ", ".join(
        f'{_percent_encode(key)}="{_percent_encode(header_params[key])}"'
        for key in sorted(header_params)
    )
    return f"OAuth {joined}"


def _weighted_length(text: str) -> int:
    """Approximate X's character counting: URLs collapse to a fixed width."""
    total = 0
    for token in text.split(" "):
        if token.startswith("http://") or token.startswith("https://"):
            total += TCO_LENGTH
        else:
            total += len(token)
    return total + max(0, len(text.split(" ")) - 1)


def _truncate_to_fit(headline: str, fixed_cost: int) -> str:
    """Shorten a headline so the whole post fits the character limit."""
    budget = TWEET_LIMIT - fixed_cost
    if budget <= 1:
        return ""
    if _weighted_length(headline) <= budget:
        return headline
    return headline[: max(1, budget - 1)].rstrip() + "…"


def build_post(
    items: Iterable[ContentItem],
    *,
    date: str,
    language: str,
    site_url: str,
    max_items: int = 3,
) -> str:
    """Compose one post linking back to the full edition."""
    selected = list(items)[:max_items]
    is_zh = language == "zh"
    header = f"BMTNews {date}" if is_zh else f"BMTNews {date}"
    link = site_url.rstrip("/") + ("/" if is_zh else "/en/")
    lines: List[str] = []
    # Reserve room for the header, the trailing link, and the newlines.
    fixed = _weighted_length(header) + TCO_LENGTH + 4
    for index, item in enumerate(selected, start=1):
        title = (
            item.metadata.get(f"title_{language}")
            or item.metadata.get("title_zh")
            or item.title
        )
        prefix = f"{index}. "
        remaining = TWEET_LIMIT - fixed - _weighted_length("\n".join(lines)) - len(prefix) - 2
        headline = _truncate_to_fit(str(title).strip(), TWEET_LIMIT - remaining)
        if not headline:
            break
        lines.append(f"{prefix}{headline}")
    body = "\n".join(lines)
    return f"{header}\n{body}\n{link}".strip()


class XEditionPublisher:
    """Post one compact edition summary to X."""

    def __init__(
        self,
        config: XDeliveryConfig,
        *,
        console: Console | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = config
        self.console = console or Console()
        self.transport = transport

    def _credentials(self) -> tuple[str, str, str, str]:
        return (
            os.getenv(self.config.consumer_key_env, "").strip(),
            os.getenv(self.config.consumer_secret_env, "").strip(),
            os.getenv(self.config.access_token_env, "").strip(),
            os.getenv(self.config.access_secret_env, "").strip(),
        )

    async def send_daily_edition(
        self,
        items: Iterable[ContentItem],
        *,
        date: str,
        language: str,
    ) -> XDeliveryResult:
        if not self.config.enabled:
            return XDeliveryResult(
                status=XDeliveryStatus.SKIPPED,
                detail="X delivery is disabled in the configuration.",
            )
        consumer_key, consumer_secret, access_token, access_secret = (
            self._credentials()
        )
        if not all((consumer_key, consumer_secret, access_token, access_secret)):
            return XDeliveryResult(
                status=XDeliveryStatus.SKIPPED,
                detail="X credentials are not fully configured; nothing posted.",
            )

        selected = list(items)
        if not selected:
            return XDeliveryResult(
                status=XDeliveryStatus.SKIPPED,
                detail="No stories to post.",
            )

        text = build_post(
            selected,
            date=date,
            language=language,
            site_url=self.config.site_url,
            max_items=self.config.max_items,
        )
        authorization = _oauth_header(
            "POST",
            X_TWEETS_ENDPOINT,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_secret=access_secret,
        )
        try:
            async with httpx.AsyncClient(
                timeout=20.0, transport=self.transport
            ) as client:
                response = await client.post(
                    X_TWEETS_ENDPOINT,
                    headers={
                        "Authorization": authorization,
                        "Content-Type": "application/json",
                    },
                    json={"text": text},
                )
        except httpx.HTTPError as exc:
            return XDeliveryResult(
                status=XDeliveryStatus.FAILURE,
                detail=f"X request failed: {type(exc).__name__}",
            )

        if response.status_code >= 400:
            # Response bodies can echo request content; report only the code.
            return XDeliveryResult(
                status=XDeliveryStatus.FAILURE,
                detail=f"X API returned HTTP {response.status_code}.",
            )
        self.console.print(f"🐦 Posted the {language.upper()} edition to X")
        return XDeliveryResult(status=XDeliveryStatus.SUCCESS, posted=1)

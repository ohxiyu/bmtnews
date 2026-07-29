from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from src.source_admin import (
    SourceChangeError,
    SourceChangeRequest,
    _source_pointers,
    apply_source_change,
    parse_issue_form,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def production_config():
    return json.loads(
        (REPO_ROOT / "data" / "config.github.json").read_text(encoding="utf-8")
    )


def request(
    *,
    operation="add",
    source_type="rss",
    source_key="new",
    name="Example Crypto",
    endpoint="https://example.com/feed.xml",
    category="crypto-markets",
    enabled=True,
    reason="Adds a focused public crypto feed.",
):
    return SourceChangeRequest(
        operation=operation,
        source_type=source_type,
        source_key=source_key,
        name=name,
        endpoint=endpoint,
        category=category,
        enabled=enabled,
        reason=reason,
    )


def test_parses_issue_form_body():
    body = """\
### 操作类型 / Operation

add — 新增

### 来源类型 / Source type

rss — RSS

### 来源键 / Source key

new

### 名称 / Name

Example Crypto

### 地址或标识 / Endpoint

https://example.com/feed.xml

### 分类 / Category

crypto-markets

### 目标状态 / Target state

true — 启用

### 调整原因 / Reason

补充加密市场覆盖。

### 提交确认 / Confirmation

- [x] 我确认信息中不包含密钥、凭据、私有地址或生产状态文件。
"""

    parsed = parse_issue_form(body)

    assert parsed.operation == "add"
    assert parsed.source_type == "rss"
    assert parsed.source_key == "new"
    assert parsed.enabled is True
    assert parsed.category == "crypto-markets"


def test_adds_rss_and_validates_result(production_config):
    config = deepcopy(production_config)
    before = len(config["sources"]["rss"])

    result = apply_source_change(
        config, request(), validate_network=False
    )

    assert len(config["sources"]["rss"]) == before + 1
    assert config["sources"]["rss"][-1] == {
        "name": "Example Crypto",
        "url": "https://example.com/feed.xml",
        "enabled": True,
        "category": "crypto-markets",
    }
    assert result["source_key"] == "rss|https://example.com/feed.xml"


def test_rejects_duplicate_rss_after_url_normalization(production_config):
    config = deepcopy(production_config)
    duplicate = request(
        name="CoinDesk duplicate",
        endpoint="https://www.coindesk.com/arc/outboundfeeds/rss",
    )

    with pytest.raises(SourceChangeError, match="already exists"):
        apply_source_change(config, duplicate, validate_network=False)


def test_pauses_and_removes_existing_rss(production_config):
    config = deepcopy(production_config)
    pointers = _source_pointers(config)
    key = next(
        pointer.key
        for pointer in pointers.values()
        if pointer.source_type == "rss"
        and pointer.item["name"] == "CoinDesk"
    )

    apply_source_change(
        config,
        request(
            operation="pause",
            source_key=key,
            name="CoinDesk",
            endpoint="https://www.coindesk.com/arc/outboundfeeds/rss/",
            enabled=False,
            reason="Temporarily pause this source.",
        ),
        validate_network=False,
    )
    assert _source_pointers(config)[key].item["enabled"] is False

    before = len(config["sources"]["rss"])
    apply_source_change(
        config,
        request(
            operation="remove",
            source_key=key,
            name="CoinDesk",
            endpoint="https://www.coindesk.com/arc/outboundfeeds/rss/",
            enabled=False,
            reason="Remove the retired duplicate source.",
        ),
        validate_network=False,
    )
    assert len(config["sources"]["rss"]) == before - 1
    assert key not in _source_pointers(config)


def test_updates_telegram_channel_without_losing_limits(production_config):
    config = deepcopy(production_config)
    key = "telegram|okxannouncements"

    result = apply_source_change(
        config,
        request(
            operation="update",
            source_type="telegram",
            source_key=key,
            name="@OKX_Announcements",
            endpoint="@OKX_Announcements",
            category="exchange-announcements",
            enabled=True,
            reason="Use the current public channel name.",
        ),
        validate_network=False,
    )

    updated = _source_pointers(config)[result["source_key"]].item
    assert updated["channel"] == "OKX_Announcements"
    assert updated["fetch_limit"] == 8


def test_rejects_unknown_category(production_config):
    with pytest.raises(SourceChangeError, match="Unknown category"):
        apply_source_change(
            deepcopy(production_config),
            request(category="unreviewed-category"),
            validate_network=False,
        )


def test_rejects_secret_backed_and_private_rss_urls(production_config):
    with pytest.raises(SourceChangeError, match="secret-backed"):
        apply_source_change(
            deepcopy(production_config),
            request(endpoint="https://example.com/feed?token=${PRIVATE_TOKEN}"),
            validate_network=False,
        )

    with pytest.raises(SourceChangeError, match="non-public"):
        apply_source_change(
            deepcopy(production_config),
            request(endpoint="http://127.0.0.1/feed.xml"),
            validate_network=True,
        )


def test_singleton_source_can_pause_but_not_remove(production_config):
    config = deepcopy(production_config)
    apply_source_change(
        config,
        request(
            operation="pause",
            source_type="hackernews",
            source_key="hackernews|main",
            name="Hacker News",
            endpoint="Top stories",
            category="tech-community",
            enabled=False,
            reason="Pause the general technology source.",
        ),
        validate_network=False,
    )
    assert config["sources"]["hackernews"]["enabled"] is False

    with pytest.raises(SourceChangeError, match="pause it instead"):
        apply_source_change(
            config,
            request(
                operation="remove",
                source_type="hackernews",
                source_key="hackernews|main",
                name="Hacker News",
                endpoint="Top stories",
                category="tech-community",
                enabled=False,
                reason="Do not allow singleton removal.",
            ),
            validate_network=False,
        )

"""Tests for drip-mode X distribution."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from rich.console import Console

from src.models import ContentItem, SourceType, XDeliveryConfig
from src.services.x_delivery import (
    TWEET_LIMIT,
    XDeliveryResult,
    XDeliveryStatus,
    _weighted_length,
    build_story_post,
)
from src.x_queue import (
    XQueueState,
    load_queue_state,
    next_pending_rank,
    save_queue_state,
    state_for_edition,
)


def make_item(title: str, *, summary: str = "", impact: str = "") -> ContentItem:
    metadata = {"title_zh": title}
    if summary:
        metadata["detailed_summary_zh"] = summary
    if impact:
        metadata["market_impact_zh"] = impact
    return ContentItem(
        id=title,
        source_type=SourceType.RSS,
        title=title,
        url="https://example.com/story",
        published_at=datetime(2026, 8, 9, tzinfo=timezone.utc),
        ai_score=9.0,
        metadata=metadata,
    )


def test_story_post_prefers_market_impact_and_fits() -> None:
    item = make_item(
        "Bybit 起诉朝鲜与 Lazarus Group",
        summary="这是摘要。第二句不应出现。",
        impact="影响集中在托管与合规成本。第二句不应出现。",
    )
    text = build_story_post(
        item, language="zh", site_url="https://bmt.news/", link_target="site"
    )
    assert "Bybit 起诉朝鲜与 Lazarus Group" in text
    assert "影响集中在托管与合规成本。" in text
    assert "第二句不应出现" not in text
    assert text.rstrip().endswith("https://bmt.news/")
    assert _weighted_length(text) <= TWEET_LIMIT


def test_story_post_falls_back_to_summary_and_source_link() -> None:
    item = make_item("标题", summary="只有摘要可用。")
    text = build_story_post(
        item, language="zh", site_url="https://bmt.news/", link_target="source"
    )
    assert "只有摘要可用。" in text
    assert text.rstrip().endswith("https://example.com/story")


def test_story_post_truncates_a_very_long_headline() -> None:
    item = make_item("超长标题" * 60)
    text = build_story_post(
        item, language="zh", site_url="https://bmt.news/", limit=TWEET_LIMIT
    )
    assert _weighted_length(text) <= TWEET_LIMIT
    # Truncation must respect CJK double-weighting, not slice by character.
    text_with_link = build_story_post(
        item,
        language="zh",
        site_url="https://bmt.news/",
        link_target="site",
        limit=TWEET_LIMIT,
    )
    assert _weighted_length(text_with_link) <= TWEET_LIMIT


def test_queue_state_round_trip_and_reset(tmp_path: Path) -> None:
    path = tmp_path / "x-queue.json"
    state = XQueueState(date="2026-08-09")
    state.mark_posted("zh", 1)
    save_queue_state(state, path)

    reloaded = load_queue_state(path)
    assert reloaded.posted_ranks("zh") == [1]

    # A new edition resets the queue.
    fresh = state_for_edition(reloaded, "2026-08-10")
    assert fresh.date == "2026-08-10"
    assert fresh.posted_ranks("zh") == []


def test_queue_state_is_fail_soft(tmp_path: Path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{oops", encoding="utf-8")
    assert load_queue_state(broken).date == ""
    assert load_queue_state(tmp_path / "missing.json").date == ""


def test_next_pending_rank_orders_and_stops() -> None:
    state = XQueueState(date="2026-08-09")
    assert next_pending_rank(state, language="zh", total_items=10, limit=4) == 1
    state.mark_posted("zh", 1)
    state.mark_posted("zh", 2)
    assert next_pending_rank(state, language="zh", total_items=10, limit=4) == 3
    state.mark_posted("zh", 3)
    state.mark_posted("zh", 4)
    assert next_pending_rank(state, language="zh", total_items=10, limit=4) is None
    # A short edition never promises more ranks than it has.
    assert next_pending_rank(
        XQueueState(), language="zh", total_items=2, limit=4
    ) == 1
    assert next_pending_rank(
        XQueueState(posted={"zh": [1, 2]}), language="zh", total_items=2, limit=4
    ) is None


class RecordingPublisher:
    def __init__(self, status=XDeliveryStatus.SUCCESS) -> None:
        self.posts: list[str] = []
        self.status = status

    async def send_text(self, text: str) -> XDeliveryResult:
        self.posts.append(text)
        return XDeliveryResult(status=self.status, posted=1)


def make_orchestrator(publisher, items, *, mode="drip"):
    from src.orchestrator import BMTNewsOrchestrator

    orchestrator = BMTNewsOrchestrator.__new__(BMTNewsOrchestrator)
    orchestrator.console = Console(record=True)
    orchestrator.config = SimpleNamespace(
        x_delivery=XDeliveryConfig(
            enabled=True, mode=mode, drip_items=4, languages=["zh"]
        ),
        filtering=SimpleNamespace(daily_timezone="Asia/Shanghai"),
    )
    orchestrator.x_publisher = publisher
    return orchestrator


def run_slot(monkeypatch, orchestrator, items, path, date="2026-08-09"):
    import src.orchestrator as module
    from src.daily_feed import DailyFeedState

    state = DailyFeedState(
        date=date,
        timezone="Asia/Shanghai",
        updated_at=datetime(2026, 8, 9, tzinfo=timezone.utc),
        items=items,
    )
    monkeypatch.setattr(module, "load_daily_feed_state", lambda *a, **k: state)
    monkeypatch.setattr(module, "save_run_report", lambda report: None)
    asyncio.run(
        orchestrator.run_x_slot(
            edition_date=datetime.fromisoformat(f"{date}T00:00").date(),
            state_path=path,
        )
    )


def test_slots_post_one_story_each_in_rank_order(monkeypatch, tmp_path) -> None:
    items = [make_item(f"第{i}条", summary=f"摘要{i}。") for i in range(1, 6)]
    publisher = RecordingPublisher()
    orchestrator = make_orchestrator(publisher, items)
    path = tmp_path / "x-queue.json"

    for _ in range(5):  # five slots, only four stories configured
        run_slot(monkeypatch, orchestrator, items, path)

    assert len(publisher.posts) == 4
    assert "第1条" in publisher.posts[0]
    assert "第4条" in publisher.posts[3]
    assert load_queue_state(path).posted_ranks("zh") == [1, 2, 3, 4]


def test_digest_mode_slot_posts_nothing(monkeypatch, tmp_path) -> None:
    items = [make_item("第1条")]
    publisher = RecordingPublisher()
    orchestrator = make_orchestrator(publisher, items, mode="digest")
    run_slot(monkeypatch, orchestrator, items, tmp_path / "q.json")
    assert publisher.posts == []


def test_failed_post_is_retried_by_the_next_slot(monkeypatch, tmp_path) -> None:
    items = [make_item("第1条"), make_item("第2条")]
    failing = RecordingPublisher(status=XDeliveryStatus.FAILURE)
    orchestrator = make_orchestrator(failing, items)
    path = tmp_path / "x-queue.json"
    run_slot(monkeypatch, orchestrator, items, path)
    assert load_queue_state(path).posted_ranks("zh") == []

    working = RecordingPublisher()
    orchestrator.x_publisher = working
    run_slot(monkeypatch, orchestrator, items, path)
    assert "第1条" in working.posts[0]


def test_story_post_does_not_break_on_abbreviations() -> None:
    item = make_item(
        "CLARITY法案将于9月面临参议院60票对决",
        summary=(
            "参议院多数党领袖约翰·图恩对《CLARITY法案》（H.R. 3633）表态支持。"
            "第二句不应出现。"
        ),
    )
    text = build_story_post(item, language="zh", site_url="https://bmt.news/")
    assert "（H.R. 3633）表态支持。" in text
    assert "第二句不应出现" not in text


def test_story_post_handles_english_sentences() -> None:
    item = ContentItem(
        id="en",
        source_type=SourceType.RSS,
        title="Headline",
        url="https://example.com/en",
        published_at=datetime(2026, 8, 9, tzinfo=timezone.utc),
        ai_score=9.0,
        metadata={
            "title_en": "US Senate schedules the vote",
            "detailed_summary_en": "The U.S. Senate set a date. A second sentence.",
        },
    )
    text = build_story_post(item, language="en", site_url="https://bmt.news/")
    assert "The U.S. Senate set a date." in text
    assert "A second sentence" not in text


# --- X character counting (twitter-text v3 weighting) ---------------------

def test_weighted_length_counts_cjk_as_two() -> None:
    from src.services.x_delivery import _weighted_length

    assert _weighted_length("abc") == 3
    assert _weighted_length("比特币") == 6
    assert _weighted_length("BTC 分叉") == 3 + 1 + 4


def test_weighted_length_collapses_urls_to_a_tco_token() -> None:
    from src.services.x_delivery import TCO_LENGTH, _weighted_length

    long_url = "https://example.com/" + "a" * 200
    assert _weighted_length(long_url) == TCO_LENGTH
    assert _weighted_length(f"甲 {long_url} 乙") == 2 + 1 + TCO_LENGTH + 1 + 2


# --- AI-composed posts ----------------------------------------------------

GOOD = (
    "比特币这次分叉，争的不是钱，是能不能往链上写图片。\n\n"
    "BIP-110 想把铭文这类非金融数据挤出交易，矿工信号只有 2.6%，"
    "远不到 55% 的门槛，支持者自己拉了条少数链。\n\n"
    "麻烦不在分叉本身，在没有重放保护：两条链前期认同同一笔已签名交易。"
)


def test_sanitize_keeps_a_clean_post() -> None:
    from src.services.x_delivery import sanitize_composed_post

    assert sanitize_composed_post(GOOD, limit=1000) == GOOD


def test_sanitize_strips_links_tags_and_markdown() -> None:
    from src.services.x_delivery import sanitize_composed_post

    raw = f'"**{GOOD}** #比特币 #BTC https://example.com/x"'
    cleaned = sanitize_composed_post(raw, limit=1000)
    assert cleaned is not None
    assert "#" not in cleaned
    assert "http" not in cleaned
    assert "**" not in cleaned
    assert not cleaned.startswith('"')
    assert "比特币这次分叉" in cleaned


def test_sanitize_rejects_unusable_output() -> None:
    from src.services.x_delivery import sanitize_composed_post

    assert sanitize_composed_post("", limit=1000) is None
    assert sanitize_composed_post("   ", limit=1000) is None
    # Too short to be a real post.
    assert sanitize_composed_post("分叉了。", limit=1000) is None
    # Over the configured limit.
    assert sanitize_composed_post("超长" * 400, limit=280) is None


class ComposingClient:
    def __init__(self, response) -> None:
        self.response = response
        self.calls: list[dict] = []

    async def complete(self, *, system: str, user: str) -> str:
        self.calls.append({"system": system, "user": user})
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


async def _test_compose_uses_enriched_fields() -> None:
    from src.services.x_delivery import compose_story_post

    item = make_item("标题")
    item.metadata.update(
        {
            "detailed_summary_zh": "摘要内容",
            "background_zh": "背景内容",
            "market_impact_zh": "影响内容",
        }
    )
    client = ComposingClient(GOOD)
    text = await compose_story_post(client, item, language="zh", limit=1000)
    assert text == GOOD
    sent = client.calls[0]["user"]
    assert "摘要内容" in sent and "背景内容" in sent and "影响内容" in sent
    assert "禁止话题标签" in client.calls[0]["system"]


async def _test_compose_returns_none_on_failure_or_bad_output() -> None:
    from src.services.x_delivery import compose_story_post

    item = make_item("标题")
    assert (
        await compose_story_post(
            ComposingClient(RuntimeError("boom")), item, language="zh"
        )
        is None
    )
    assert (
        await compose_story_post(ComposingClient("太短。"), item, language="zh")
        is None
    )


def test_compose_uses_enriched_fields() -> None:
    asyncio.run(_test_compose_uses_enriched_fields())


def test_compose_returns_none_on_failure_or_bad_output() -> None:
    asyncio.run(_test_compose_returns_none_on_failure_or_bad_output())


def test_template_post_omits_the_link_by_default() -> None:
    from src.services.x_delivery import build_story_post

    item = make_item("标题", summary="一句摘要内容。")
    text = build_story_post(item, language="zh", site_url="https://bmt.news/")
    assert "http" not in text
    assert "标题" in text and "一句摘要内容。" in text


def test_slot_falls_back_to_template_when_composer_fails(
    monkeypatch, tmp_path
) -> None:
    import src.orchestrator as module
    from src.services.x_delivery import XDeliveryResult

    items = [make_item("重要新闻", summary="一句摘要内容。")]
    posts: list[str] = []

    class Publisher:
        async def send_text(self, text: str) -> XDeliveryResult:
            posts.append(text)
            return XDeliveryResult(status=XDeliveryStatus.SUCCESS, posted=1)

    orchestrator = make_orchestrator(Publisher(), items)
    monkeypatch.setattr(
        module, "create_ai_client", lambda config: ComposingClient(RuntimeError("no key"))
    )
    run_slot(monkeypatch, orchestrator, items, tmp_path / "q.json")

    assert len(posts) == 1
    assert "重要新闻" in posts[0]
    assert "http" not in posts[0]




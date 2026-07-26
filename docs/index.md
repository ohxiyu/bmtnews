---
layout: default
title: Home
page_type: home
---

{% assign zh_posts = site.posts | where: "lang", "zh" %}
{% assign en_posts = site.posts | where: "lang", "en" %}
{% assign latest_zh = zh_posts | first %}
{% assign latest_en = en_posts | first %}

<div id="lang-zh" class="lang-section">
  {% if latest_zh %}
    <section class="daily-feed" data-language="zh" data-date="{{ latest_zh.date | date: '%Y-%m-%d' }}">
      <header class="daily-feed-header">
        <div class="daily-feed-heading">
          <p class="eyebrow">DAILY CRYPTO INTELLIGENCE</p>
          <div class="daily-title-row">
            <h1>加密市场日报</h1>
            <time datetime="{{ latest_zh.date | date: '%Y-%m-%d' }}">{{ latest_zh.date | date: "%Y.%m.%d" }}</time>
          </div>
          <p>交易所公告、安全事件、市场结构、监管变化与协议更新，按影响力浓缩为一页信息流。</p>
        </div>
        <div class="daily-feed-stats" aria-label="今日日报统计">
          <span><strong data-stat="selected">—</strong> 条精选</span>
          <span><strong data-stat="fetched">—</strong> 条已分析</span>
          <span><strong data-stat="critical">—</strong> 条高优先级</span>
          <span><strong data-stat="sources">—</strong> 个来源</span>
        </div>
      </header>

      <div class="daily-feed-content" data-language="zh" data-date="{{ latest_zh.date | date: '%Y-%m-%d' }}">
        {{ latest_zh.content }}
      </div>
    </section>
  {% else %}
    <div class="empty-state">首期日报生成后，完整信息流会直接显示在首页。</div>
  {% endif %}

  <section id="archive" class="archive-section">
    <header class="section-heading">
      <div>
        <p class="eyebrow">PREVIOUS EDITIONS</p>
        <h2>往期日报</h2>
      </div>
      <a class="rss-link" href="{{ '/feed-zh.xml' | relative_url }}">订阅 RSS</a>
    </header>
    <div class="archive-grid">
      {% for post in zh_posts limit:24 %}
        <a href="{{ post.url | relative_url }}" {% if forloop.first %}aria-current="page"{% endif %}>
          <strong>{{ post.date | date: "%m.%d" }}</strong>
          <span>{{ post.date | date: "%Y" }}</span>
        </a>
      {% else %}
        <span class="empty-state">暂无历史日报</span>
      {% endfor %}
    </div>
  </section>
</div>

<div id="lang-en" class="lang-section hidden">
  {% if latest_en %}
    <section class="daily-feed" data-language="en" data-date="{{ latest_en.date | date: '%Y-%m-%d' }}">
      <header class="daily-feed-header">
        <div class="daily-feed-heading">
          <p class="eyebrow">DAILY CRYPTO INTELLIGENCE</p>
          <div class="daily-title-row">
            <h1>Crypto Market Brief</h1>
            <time datetime="{{ latest_en.date | date: '%Y-%m-%d' }}">{{ latest_en.date | date: "%Y.%m.%d" }}</time>
          </div>
          <p>Exchange alerts, security incidents, market structure, regulation, and protocol updates in one ranked feed.</p>
        </div>
        <div class="daily-feed-stats" aria-label="Daily brief statistics">
          <span><strong data-stat="selected">—</strong> selected</span>
          <span><strong data-stat="fetched">—</strong> analyzed</span>
          <span><strong data-stat="critical">—</strong> high priority</span>
          <span><strong data-stat="sources">—</strong> sources</span>
        </div>
      </header>

      <div class="daily-feed-content" data-language="en" data-date="{{ latest_en.date | date: '%Y-%m-%d' }}">
        {{ latest_en.content }}
      </div>
    </section>
  {% else %}
    <div class="empty-state">The full feed will appear on the homepage after the first daily brief is generated.</div>
  {% endif %}

  <section id="archive-en" class="archive-section">
    <header class="section-heading">
      <div>
        <p class="eyebrow">PREVIOUS EDITIONS</p>
        <h2>Previous briefs</h2>
      </div>
      <a class="rss-link" href="{{ '/feed-en.xml' | relative_url }}">Subscribe via RSS</a>
    </header>
    <div class="archive-grid">
      {% for post in en_posts limit:24 %}
        <a href="{{ post.url | relative_url }}" {% if forloop.first %}aria-current="page"{% endif %}>
          <strong>{{ post.date | date: "%m.%d" }}</strong>
          <span>{{ post.date | date: "%Y" }}</span>
        </a>
      {% else %}
        <span class="empty-state">No previous briefs yet</span>
      {% endfor %}
    </div>
  </section>
</div>

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
  <section class="home-hero">
    <div class="home-hero-copy">
      <p class="eyebrow">CRYPTO SIGNAL, MINUS THE NOISE</p>
      <h1>每天一页，看懂加密市场。</h1>
      <p>聚合交易所公告、安全事件、市场结构、监管变化和协议更新，只保留真正影响资金与决策的信息。</p>
      {% if latest_zh %}
        <div class="home-hero-actions">
          <a class="primary-action" href="{{ latest_zh.url | relative_url }}">阅读完整日报</a>
          <a class="secondary-action" href="#latest">浏览今日重点</a>
        </div>
      {% endif %}
    </div>

    <div class="signal-board" aria-label="今日数据">
      <div class="signal-board-head">
        <span>今日情报</span>
        <span class="live-indicator"><i></i> Daily</span>
      </div>
      <div class="signal-stats">
        <div><strong data-stat="selected">—</strong><span>精选</span></div>
        <div><strong data-stat="fetched">—</strong><span>已分析</span></div>
        <div><strong data-stat="critical">—</strong><span>高优先级</span></div>
        <div><strong data-stat="sources">—</strong><span>来源</span></div>
      </div>
      <div class="signal-date">
        <span>最近更新</span>
        <strong>{% if latest_zh %}{{ latest_zh.date | date: "%Y-%m-%d" }}{% else %}等待首期日报{% endif %}</strong>
      </div>
    </div>
  </section>

  <section id="latest" class="dashboard-panel home-dashboard" data-language="zh" data-post-url="{% if latest_zh %}{{ latest_zh.url | relative_url }}{% endif %}">
    <header class="section-heading">
      <div>
        <p class="eyebrow">TODAY'S SIGNALS</p>
        <h2>今日重点</h2>
      </div>
      {% if latest_zh %}
        <a href="{{ latest_zh.url | relative_url }}">完整日报 →</a>
      {% endif %}
    </header>

    <div class="filter-host" aria-label="新闻分类"></div>
    {% if latest_zh %}
      <div class="latest-digest-source" hidden>{{ latest_zh.content }}</div>
      <div class="home-story-grid"></div>
    {% else %}
      <div class="empty-state">日报生成后，首页会在这里显示高密度新闻卡片。</div>
    {% endif %}
  </section>

  <section id="archive" class="archive-section">
    <header class="section-heading">
      <div>
        <p class="eyebrow">ARCHIVE</p>
        <h2>历史日报</h2>
      </div>
      <a class="rss-link" href="{{ '/feed-zh.xml' | relative_url }}">订阅 RSS</a>
    </header>
    <div class="archive-grid">
      {% for post in zh_posts limit:24 %}
        <a href="{{ post.url | relative_url }}">
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
  <section class="home-hero">
    <div class="home-hero-copy">
      <p class="eyebrow">CRYPTO SIGNAL, MINUS THE NOISE</p>
      <h1>One page for the crypto day.</h1>
      <p>Exchange alerts, security incidents, market structure, regulation, and protocol updates—filtered for real impact.</p>
      {% if latest_en %}
        <div class="home-hero-actions">
          <a class="primary-action" href="{{ latest_en.url | relative_url }}">Read full brief</a>
          <a class="secondary-action" href="#latest-en">Browse top signals</a>
        </div>
      {% endif %}
    </div>

    <div class="signal-board" aria-label="Daily metrics">
      <div class="signal-board-head">
        <span>Daily intelligence</span>
        <span class="live-indicator"><i></i> Daily</span>
      </div>
      <div class="signal-stats">
        <div><strong data-stat="selected">—</strong><span>Selected</span></div>
        <div><strong data-stat="fetched">—</strong><span>Analyzed</span></div>
        <div><strong data-stat="critical">—</strong><span>High priority</span></div>
        <div><strong data-stat="sources">—</strong><span>Sources</span></div>
      </div>
      <div class="signal-date">
        <span>Latest update</span>
        <strong>{% if latest_en %}{{ latest_en.date | date: "%Y-%m-%d" }}{% else %}Waiting for first brief{% endif %}</strong>
      </div>
    </div>
  </section>

  <section id="latest-en" class="dashboard-panel home-dashboard" data-language="en" data-post-url="{% if latest_en %}{{ latest_en.url | relative_url }}{% endif %}">
    <header class="section-heading">
      <div>
        <p class="eyebrow">TODAY'S SIGNALS</p>
        <h2>Top stories</h2>
      </div>
      {% if latest_en %}
        <a href="{{ latest_en.url | relative_url }}">Full brief →</a>
      {% endif %}
    </header>

    <div class="filter-host" aria-label="Story categories"></div>
    {% if latest_en %}
      <div class="latest-digest-source" hidden>{{ latest_en.content }}</div>
      <div class="home-story-grid"></div>
    {% else %}
      <div class="empty-state">Dense story cards will appear here after the first daily brief is generated.</div>
    {% endif %}
  </section>

  <section class="archive-section">
    <header class="section-heading">
      <div>
        <p class="eyebrow">ARCHIVE</p>
        <h2>Previous briefs</h2>
      </div>
      <a class="rss-link" href="{{ '/feed-en.xml' | relative_url }}">Subscribe via RSS</a>
    </header>
    <div class="archive-grid">
      {% for post in en_posts limit:24 %}
        <a href="{{ post.url | relative_url }}">
          <strong>{{ post.date | date: "%m.%d" }}</strong>
          <span>{{ post.date | date: "%Y" }}</span>
        </a>
      {% else %}
        <span class="empty-state">No previous briefs yet</span>
      {% endfor %}
    </div>
  </section>
</div>

<section class="utility-section">
  <div>
    <p class="eyebrow">HOW IT WORKS</p>
    <h2>从信息源到每日情报</h2>
  </div>
  <div class="utility-grid">
    <a href="{{ '/scrapers' | relative_url }}"><strong>01</strong><span>信息源</span><small>交易所、媒体、社区与协议更新</small></a>
    <a href="{{ '/scoring' | relative_url }}"><strong>02</strong><span>AI 评分</span><small>安全性、资金影响与市场重要性</small></a>
    <a href="{{ '/configuration' | relative_url }}"><strong>03</strong><span>自定义</span><small>来源、阈值、分类与分发方式</small></a>
  </div>
</section>

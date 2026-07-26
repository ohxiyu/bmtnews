---
layout: default
title: Home
page_type: home
---

{% assign zh_posts = site.posts | where: "lang", "zh" %}
{% assign en_posts = site.posts | where: "lang", "en" %}
{% assign latest_zh = zh_posts | first %}
{% assign latest_en = en_posts | first %}
{% assign today_key = site.time | date: "%Y-%m-%d" %}

<div id="lang-zh" class="lang-section">
  <section class="continuous-feed" data-language="zh">
    <header class="daily-feed-header">
      <div class="daily-feed-heading">
        <p class="eyebrow">CRYPTO MARKET INTELLIGENCE</p>
        <div class="daily-title-row">
          <h1>BMTNews</h1>
          <span class="brand-domain">bmt.news</span>
        </div>
        <p>交易所公告、安全事件、市场结构、监管变化与协议更新，按日期和影响力连续排列。</p>
      </div>
    </header>

    {% if latest_zh %}
      <div class="day-stream">
        {% for post in zh_posts limit:2 %}
          {% assign post_key = post.date | date: "%Y-%m-%d" %}
          <section class="daily-day" data-language="zh" data-date="{{ post_key }}">
            <header class="day-divider">
              <div class="day-divider-title">
                {% if forloop.first %}
                  <span class="day-state">{% if post_key == today_key %}今日{% else %}最新{% endif %}</span>
                {% endif %}
                <time datetime="{{ post_key }}">{{ post.date | date: "%Y.%m.%d" }}</time>
              </div>
              <div class="day-divider-stats" aria-label="{{ post_key }} 日报统计">
                <span data-short="选"><strong data-stat="selected">—</strong> 条精选</span>
                <span data-short="析"><strong data-stat="fetched">—</strong> 条分析</span>
                <span data-short="高"><strong data-stat="critical">—</strong> 条高优先级</span>
              </div>
            </header>
            <div class="daily-feed-content" data-language="zh" data-date="{{ post_key }}">
              {{ post.content }}
            </div>
          </section>
        {% endfor %}
      </div>

      <div class="feed-history-manifest" hidden aria-hidden="true">
        {% for post in zh_posts offset:2 %}
          <span data-url="{{ post.url | relative_url }}" data-date="{{ post.date | date: '%Y-%m-%d' }}"></span>
        {% endfor %}
      </div>
      {% if zh_posts.size > 2 %}
        <div class="load-earlier-wrap">
          <button class="load-earlier" type="button">加载更早</button>
        </div>
      {% endif %}
    {% else %}
      <div class="empty-state">首期日报生成后，完整信息流会直接显示在首页。</div>
    {% endif %}
  </section>
</div>

<div id="lang-en" class="lang-section hidden">
  <section class="continuous-feed" data-language="en">
    <header class="daily-feed-header">
      <div class="daily-feed-heading">
        <p class="eyebrow">CRYPTO MARKET INTELLIGENCE</p>
        <div class="daily-title-row">
          <h1>BMTNews</h1>
          <span class="brand-domain">bmt.news</span>
        </div>
        <p>Exchange alerts, security incidents, market structure, regulation, and protocol updates in one date-ranked feed.</p>
      </div>
    </header>

    {% if latest_en %}
      <div class="day-stream">
        {% for post in en_posts limit:2 %}
          {% assign post_key = post.date | date: "%Y-%m-%d" %}
          <section class="daily-day" data-language="en" data-date="{{ post_key }}">
            <header class="day-divider">
              <div class="day-divider-title">
                {% if forloop.first %}
                  <span class="day-state">{% if post_key == today_key %}Today{% else %}Latest{% endif %}</span>
                {% endif %}
                <time datetime="{{ post_key }}">{{ post.date | date: "%Y.%m.%d" }}</time>
              </div>
              <div class="day-divider-stats" aria-label="{{ post_key }} brief statistics">
                <span data-short="S"><strong data-stat="selected">—</strong> selected</span>
                <span data-short="A"><strong data-stat="fetched">—</strong> analyzed</span>
                <span data-short="H"><strong data-stat="critical">—</strong> high priority</span>
              </div>
            </header>
            <div class="daily-feed-content" data-language="en" data-date="{{ post_key }}">
              {{ post.content }}
            </div>
          </section>
        {% endfor %}
      </div>

      <div class="feed-history-manifest" hidden aria-hidden="true">
        {% for post in en_posts offset:2 %}
          <span data-url="{{ post.url | relative_url }}" data-date="{{ post.date | date: '%Y-%m-%d' }}"></span>
        {% endfor %}
      </div>
      {% if en_posts.size > 2 %}
        <div class="load-earlier-wrap">
          <button class="load-earlier" type="button">Load earlier</button>
        </div>
      {% endif %}
    {% else %}
      <div class="empty-state">The complete feed will appear here after the first daily brief is generated.</div>
    {% endif %}
  </section>
</div>

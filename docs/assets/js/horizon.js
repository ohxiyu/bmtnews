(function () {
  'use strict';

  var CATEGORY_ORDER = ['all', 'exchange', 'security', 'market', 'regulation', 'protocol'];
  var CATEGORY_LABELS = {
    zh: {
      all: '全部',
      exchange: '交易所',
      security: '安全',
      market: '市场',
      regulation: '监管',
      protocol: '协议'
    },
    en: {
      all: 'All',
      exchange: 'Exchanges',
      security: 'Security',
      market: 'Markets',
      regulation: 'Regulation',
      protocol: 'Protocols'
    }
  };

  var CATEGORY_PATTERNS = {
    security: [
      'security', 'exploit', 'hack', 'hacker', 'breach', 'stolen', 'theft', 'attack',
      'vulnerability', 'drain', '冻结', '黑客', '攻击', '漏洞', '被盗', '安全事件', '资金损失'
    ],
    exchange: [
      'exchange', 'binance', 'okx', 'bybit', 'coinbase', 'kraken', 'listing', 'delisting',
      'deposit', 'withdrawal', 'maintenance', 'trading suspension', '交易所', '上架', '下架',
      '充币', '提币', '暂停交易', '维护'
    ],
    regulation: [
      'regulation', 'regulatory', 'sec ', 'cftc', 'law', 'bill', 'compliance', 'license',
      '监管', '法案', '合规', '牌照', '禁令', '立法'
    ],
    protocol: [
      'protocol', 'bitcoin', 'ethereum', 'solana', 'arbitrum', 'layer 2', 'layer-2',
      'mainnet', 'testnet', 'upgrade', 'fork', 'defi', 'bridge', 'staking', '协议',
      '比特币', '以太坊', '主网', '升级', '跨链桥', '质押'
    ]
  };

  function normalizeLanguage(value) {
    return String(value || '').toLowerCase().indexOf('en') === 0 ? 'en' : 'zh';
  }

  function textOf(element) {
    return element ? (element.textContent || '').replace(/\s+/g, ' ').trim() : '';
  }

  function inferCategory(element) {
    var probe = element.cloneNode(true);
    probe.querySelectorAll('.source-line, details').forEach(function (node) {
      node.remove();
    });
    var text = textOf(probe).toLowerCase();
    var priority = ['security', 'exchange', 'regulation', 'protocol'];
    for (var i = 0; i < priority.length; i += 1) {
      var category = priority[i];
      var patterns = CATEGORY_PATTERNS[category];
      for (var j = 0; j < patterns.length; j += 1) {
        if (text.indexOf(patterns[j]) !== -1) return category;
      }
    }
    return 'market';
  }

  function scoreTier(score) {
    if (score >= 9) return 'high';
    if (score >= 7) return 'good';
    if (score >= 5) return 'mid';
    return 'low';
  }

  function readScore(element) {
    if (!element) return 0;
    var badge = element.querySelector('.score-badge');
    if (badge) return parseFloat(textOf(badge)) || 0;
    var match = textOf(element).match(/(\d+(?:\.\d+)?)\s*\/\s*10/);
    return match ? parseFloat(match[1]) : 0;
  }

  function createCategoryPill(category, language) {
    var pill = document.createElement('span');
    pill.className = 'category-pill';
    pill.dataset.category = category;
    pill.textContent = CATEGORY_LABELS[language][category] || CATEGORY_LABELS[language].market;
    return pill;
  }

  function createScoreBadge(score) {
    var badge = document.createElement('span');
    badge.className = 'score-badge';
    badge.dataset.tier = scoreTier(score);
    badge.textContent = score ? score.toFixed(1) : '—';
    return badge;
  }

  function processScoreBadges(root) {
    var scoreRe = /⭐️?\s*(\d+(?:\.\d+)?)\/10/;
    var targets = root.querySelectorAll('h2, h3, li');
    targets.forEach(function (element) {
      if (element.querySelector('.score-badge')) return;
      var match = element.innerHTML.match(scoreRe);
      if (!match) return;
      var score = parseFloat(match[1]);
      element.innerHTML = element.innerHTML.replace(
        scoreRe,
        '<span class="score-badge" data-tier="' + scoreTier(score) + '">' + score.toFixed(1) + '</span>'
      );
    });
  }

  function markSemanticElements(root) {
    root.querySelectorAll('p').forEach(function (paragraph) {
      var text = textOf(paragraph);
      if (/^(Tags|标签)\s*:/.test(text)) {
        paragraph.classList.add('tag-line');
        return;
      }
      if (/^(rss|reddit|github|hackernews|hn|telegram|google_news|gdelt|ossinsight)\s*·/i.test(text)) {
        paragraph.classList.add('source-line');
      }
    });
  }

  function setupFilters(host, cards, language, onFilter) {
    if (!host || !cards.length) return;

    var counts = {all: cards.length};
    cards.forEach(function (card) {
      var category = card.dataset.category || 'market';
      counts[category] = (counts[category] || 0) + 1;
    });

    var filterBar = document.createElement('div');
    filterBar.className = 'category-filters';

    CATEGORY_ORDER.forEach(function (category) {
      if (category !== 'all' && !counts[category]) return;
      var button = document.createElement('button');
      button.type = 'button';
      button.dataset.category = category;
      if (category === 'all') button.classList.add('active');
      button.appendChild(document.createTextNode(CATEGORY_LABELS[language][category]));

      var count = document.createElement('span');
      count.textContent = counts[category] || 0;
      button.appendChild(count);

      button.addEventListener('click', function () {
        filterBar.querySelectorAll('button').forEach(function (candidate) {
          candidate.classList.toggle('active', candidate === button);
        });
        cards.forEach(function (card) {
          card.hidden = category !== 'all' && card.dataset.category !== category;
        });
        if (onFilter) onFilter(category);
      });
      filterBar.appendChild(button);
    });

    host.replaceChildren(filterBar);
  }

  function sectionNodesAfter(heading) {
    var nodes = [];
    var node = heading.nextElementSibling;
    while (node && node.tagName !== 'H2' && node.tagName !== 'HR') {
      nodes.push(node);
      node = node.nextElementSibling;
    }
    return nodes;
  }

  function buildHomeCard(heading, index, postUrl, language) {
    var sectionNodes = sectionNodesAfter(heading);
    var probe = document.createElement('div');
    probe.appendChild(heading.cloneNode(true));
    sectionNodes.forEach(function (node) {
      probe.appendChild(node.cloneNode(true));
    });

    var category = inferCategory(probe);
    var score = readScore(heading);
    var titleLink = heading.querySelector('a');
    var title = titleLink ? textOf(titleLink) : textOf(heading).replace(/\d+(?:\.\d+)?\s*$/, '').trim();
    var summaryNode = sectionNodes.find(function (node) {
      return node.tagName === 'P' && !node.classList.contains('source-line') && !node.classList.contains('tag-line');
    });
    var sourceNode = sectionNodes.find(function (node) {
      return node.classList.contains('source-line');
    });
    var anchorUrl = postUrl ? postUrl + '#item-' + (index + 1) : (titleLink ? titleLink.href : '#');

    var card = document.createElement('article');
    card.className = 'home-story-card';
    card.dataset.category = category;
    card.dataset.score = String(score);

    var top = document.createElement('div');
    top.className = 'story-card-top';
    top.appendChild(createCategoryPill(category, language));
    top.appendChild(createScoreBadge(score));

    var titleElement = document.createElement('h3');
    var titleAnchor = document.createElement('a');
    titleAnchor.href = anchorUrl;
    titleAnchor.textContent = title;
    titleElement.appendChild(titleAnchor);

    var summary = document.createElement('p');
    summary.className = 'story-summary';
    summary.textContent = summaryNode ? textOf(summaryNode) : (language === 'zh' ? '打开日报查看完整内容。' : 'Open the brief for the full story.');

    var foot = document.createElement('div');
    foot.className = 'story-card-foot';
    var source = document.createElement('span');
    source.textContent = sourceNode ? textOf(sourceNode) : (language === 'zh' ? 'Horizon 来源' : 'Horizon source');
    var more = document.createElement('a');
    more.href = anchorUrl;
    more.textContent = language === 'zh' ? '详情 →' : 'Details →';
    foot.appendChild(source);
    foot.appendChild(more);

    card.appendChild(top);
    card.appendChild(titleElement);
    card.appendChild(summary);
    card.appendChild(foot);
    return card;
  }

  function parseFetchedCount(source) {
    var quote = source.querySelector('blockquote');
    var numbers = quote ? textOf(quote).match(/\d+/g) : null;
    return numbers && numbers.length ? parseInt(numbers[0], 10) : 0;
  }

  function updateDashboardStats(section, cards, source) {
    var fetched = parseFetchedCount(source);
    var critical = cards.filter(function (card) {
      return parseFloat(card.dataset.score || '0') >= 9;
    }).length;
    var sources = new Set();
    source.querySelectorAll('.source-line').forEach(function (line) {
      var parts = textOf(line).split('·');
      sources.add((parts[1] || parts[0] || '').trim());
    });

    var values = {
      selected: cards.length,
      fetched: fetched || '—',
      critical: critical,
      sources: sources.size || '—'
    };
    Object.keys(values).forEach(function (key) {
      section.querySelectorAll('[data-stat="' + key + '"]').forEach(function (element) {
        element.textContent = values[key];
      });
    });
  }

  function buildHomeDashboards() {
    document.querySelectorAll('.home-dashboard').forEach(function (dashboard) {
      var source = dashboard.querySelector('.latest-digest-source');
      var grid = dashboard.querySelector('.home-story-grid');
      if (!source || !grid) return;

      processScoreBadges(source);
      markSemanticElements(source);
      var language = normalizeLanguage(dashboard.dataset.language);
      var postUrl = dashboard.dataset.postUrl || '';
      var headings = Array.prototype.slice.call(source.querySelectorAll('h2'));
      var cards = headings.map(function (heading, index) {
        return buildHomeCard(heading, index, postUrl, language);
      });

      cards.sort(function (a, b) {
        return parseFloat(b.dataset.score || '0') - parseFloat(a.dataset.score || '0');
      });
      cards.forEach(function (card) {
        grid.appendChild(card);
      });

      var languageSection = dashboard.closest('.lang-section') || dashboard;
      updateDashboardStats(languageSection, cards, source);
      setupFilters(dashboard.querySelector('.filter-host'), cards, language);
    });
  }

  function isExtraStoryNode(node) {
    if (node.tagName === 'DETAILS' || node.classList.contains('tag-line')) return true;
    if (node.tagName !== 'P') return false;
    var strong = node.querySelector('strong:first-child');
    if (!strong) return false;
    return /^(Background|Discussion|背景|社区讨论)$/.test(textOf(strong));
  }

  function wrapDigestItems() {
    if (!document.body.classList.contains('digest-page')) return;
    var main = document.querySelector('.main-content');
    if (!main) return;

    processScoreBadges(main);
    markSemanticElements(main);
    var language = normalizeLanguage(document.documentElement.lang);
    var headings = Array.prototype.slice.call(main.children).filter(function (element) {
      return element.tagName === 'H2';
    });
    var articles = [];

    headings.forEach(function (heading) {
      var anchorParagraph = heading.previousElementSibling;
      if (!anchorParagraph || !anchorParagraph.matches('p') || !anchorParagraph.querySelector('a[id^="item-"]')) {
        anchorParagraph = null;
      }
      var article = document.createElement('article');
      article.className = 'digest-item';
      main.insertBefore(article, anchorParagraph || heading);
      if (anchorParagraph) {
        article.appendChild(anchorParagraph.querySelector('a[id^="item-"]'));
        anchorParagraph.remove();
      }

      var node = heading;
      while (node && node.tagName !== 'HR') {
        var next = node.nextElementSibling;
        article.appendChild(node);
        node = next;
      }
      if (node && node.tagName === 'HR') node.remove();

      var category = inferCategory(article);
      var score = readScore(heading);
      var headingBadge = heading.querySelector('.score-badge');
      if (headingBadge) headingBadge.remove();
      article.dataset.category = category;
      article.dataset.score = String(score);

      var meta = document.createElement('div');
      meta.className = 'digest-item-meta';
      meta.appendChild(createCategoryPill(category, language));
      meta.appendChild(createScoreBadge(score));
      article.insertBefore(meta, heading);

      var extras = Array.prototype.slice.call(article.children).filter(isExtraStoryNode);
      if (extras.length) {
        var details = document.createElement('details');
        details.className = 'story-more';
        var summary = document.createElement('summary');
        summary.textContent = language === 'zh' ? '背景、讨论与参考资料' : 'Background, discussion, and references';
        var content = document.createElement('div');
        content.className = 'story-more-content';
        extras.forEach(function (extra) {
          content.appendChild(extra);
        });
        details.appendChild(summary);
        details.appendChild(content);
        article.appendChild(details);
      }

      var summaryParagraph = Array.prototype.slice.call(article.children).find(function (element) {
        return element.tagName === 'P' &&
          !element.classList.contains('source-line') &&
          !element.classList.contains('tag-line') &&
          !element.querySelector('strong:first-child');
      });
      if (summaryParagraph && textOf(summaryParagraph).length > 180) {
        summaryParagraph.classList.add('story-summary-body');
        var summaryToggle = document.createElement('button');
        summaryToggle.type = 'button';
        summaryToggle.className = 'summary-toggle';
        summaryToggle.textContent = language === 'zh' ? '展开摘要' : 'Expand summary';
        summaryToggle.addEventListener('click', function () {
          var expanded = summaryParagraph.classList.toggle('expanded');
          summaryToggle.textContent = language === 'zh'
            ? (expanded ? '收起摘要' : '展开摘要')
            : (expanded ? 'Collapse summary' : 'Expand summary');
        });
        summaryParagraph.insertAdjacentElement('afterend', summaryToggle);
      }

      articles.push(article);
    });

    if (!articles.length) return;
    var toc = main.querySelector(':scope > ol');
    var tocItems = toc ? Array.prototype.slice.call(toc.querySelectorAll(':scope > li')) : [];
    tocItems.forEach(function (item, index) {
      if (articles[index]) item.dataset.category = articles[index].dataset.category;
    });

    var filterHost = document.createElement('div');
    filterHost.className = 'digest-filter-host';
    if (toc) toc.insertAdjacentElement('afterend', filterHost);
    else main.insertBefore(filterHost, articles[0]);

    setupFilters(filterHost, articles, language, function (category) {
      tocItems.forEach(function (item) {
        item.hidden = category !== 'all' && item.dataset.category !== category;
      });
    });
  }

  function setupLanguageToggle() {
    var slot = document.querySelector('.lang-toggle-slot');
    if (!slot) return;

    var toggle = document.createElement('div');
    toggle.className = 'lang-toggle';
    var buttonEn = document.createElement('button');
    var buttonZh = document.createElement('button');
    buttonEn.type = 'button';
    buttonZh.type = 'button';
    buttonEn.textContent = 'EN';
    buttonZh.textContent = '中文';
    toggle.appendChild(buttonEn);
    toggle.appendChild(buttonZh);
    slot.appendChild(toggle);

    var isDigest = document.body.classList.contains('digest-page');
    var pageLanguage = normalizeLanguage(document.documentElement.lang);
    var saved = null;
    try {
      saved = localStorage.getItem('horizon-lang');
    } catch (error) {
      saved = null;
    }
    var current = isDigest ? pageLanguage : (saved === 'en' ? 'en' : 'zh');
    var sectionZh = document.getElementById('lang-zh');
    var sectionEn = document.getElementById('lang-en');

    function update(language) {
      buttonEn.classList.toggle('active', language === 'en');
      buttonZh.classList.toggle('active', language === 'zh');
      if (sectionZh && sectionEn) {
        sectionZh.classList.toggle('hidden', language !== 'zh');
        sectionEn.classList.toggle('hidden', language !== 'en');
      }
    }

    function switchDigest(language) {
      var path = window.location.pathname.replace(/\/$/, '');
      var target = null;
      if (language === 'en' && /-zh(?:\.html)?$/.test(path)) {
        target = path.replace(/-zh(\.html)?$/, '-en$1');
      }
      if (language === 'zh' && /-en(?:\.html)?$/.test(path)) {
        target = path.replace(/-en(\.html)?$/, '-zh$1');
      }
      if (target) window.location.href = target;
    }

    function setLanguage(language) {
      try {
        localStorage.setItem('horizon-lang', language);
      } catch (error) {
        // Storage is an enhancement only.
      }
      if (isDigest) switchDigest(language);
      else update(language);
    }

    buttonEn.addEventListener('click', function () {
      setLanguage('en');
    });
    buttonZh.addEventListener('click', function () {
      setLanguage('zh');
    });
    update(current);
  }

  function setupThemeToggle() {
    var button = document.querySelector('.theme-toggle');
    if (!button) return;

    function systemDark() {
      return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    function currentDark() {
      var explicit = document.documentElement.dataset.theme;
      return explicit ? explicit === 'dark' : systemDark();
    }

    function updateLabel() {
      var dark = currentDark();
      button.textContent = dark ? '☀' : '◐';
      button.setAttribute('aria-label', dark ? '切换浅色模式' : '切换深色模式');
      button.title = button.getAttribute('aria-label');
    }

    button.addEventListener('click', function () {
      var next = currentDark() ? 'light' : 'dark';
      document.documentElement.dataset.theme = next;
      try {
        localStorage.setItem('horizon-theme', next);
      } catch (error) {
        // Storage is an enhancement only.
      }
      updateLabel();
    });

    try {
      var saved = localStorage.getItem('horizon-theme');
      if (saved === 'light' || saved === 'dark') {
        document.documentElement.dataset.theme = saved;
      }
    } catch (error) {
      // Use the system preference.
    }
    updateLabel();
  }

  document.addEventListener('DOMContentLoaded', function () {
    setupThemeToggle();
    setupLanguageToggle();
    buildHomeDashboards();
    wrapDigestItems();
  });
})();

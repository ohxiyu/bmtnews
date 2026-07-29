(function () {
  'use strict';

  var root = document.getElementById('source-console');
  if (!root) return;

  var TYPE_LABELS = {
    rss: 'RSS',
    telegram: 'Telegram',
    github: 'GitHub',
    reddit: 'Reddit',
    hackernews: 'Hacker News',
    google_news: 'Google News',
    gdelt: 'GDELT',
    ossinsight: 'OSS Insight'
  };

  var OPERATION_OPTIONS = {
    add: 'add — 新增',
    update: 'update — 编辑',
    pause: 'pause — 暂停',
    resume: 'resume — 恢复',
    remove: 'remove — 删除'
  };

  var SOURCE_TYPE_OPTIONS = {
    rss: 'rss — RSS',
    telegram: 'telegram — Telegram',
    github: 'github — GitHub Releases',
    reddit: 'reddit — Reddit',
    hackernews: 'hackernews — Hacker News',
    google_news: 'google_news — Google News',
    gdelt: 'gdelt — GDELT',
    ossinsight: 'ossinsight — OSS Insight'
  };

  var STATE_OPTIONS = {
    true: 'true — 启用',
    false: 'false — 暂停'
  };

  var TRACK_LABELS = {
    crypto: 'Crypto',
    technology: 'AI / 科技',
    policy: '政策',
    other: '其他'
  };

  var STATUS_LABELS = {
    active: '启用',
    paused: '暂停',
    'parent-paused': '采集器停用'
  };

  var ENDPOINT_HELP = {
    rss: {
      label: 'RSS 地址',
      placeholder: 'https://example.com/feed.xml',
      help: '请填写不含密钥和登录信息的公开 HTTP(S) Feed 地址。'
    },
    telegram: {
      label: 'Telegram 频道',
      placeholder: 'OKXAnnouncements',
      help: '填写公开频道用户名，不需要 @ 或完整 t.me 地址。'
    },
    github: {
      label: 'GitHub 仓库',
      placeholder: 'bitcoin/bitcoin',
      help: '使用 owner/repository 格式，当前控制台添加 Release 来源。'
    },
    reddit: {
      label: 'Subreddit',
      placeholder: 'CryptoCurrency',
      help: '填写 subreddit 名称，不需要 r/ 前缀。'
    }
  };

  var elements = {
    addButton: document.getElementById('source-add-button'),
    totalCount: document.getElementById('source-total-count'),
    activeCount: document.getElementById('source-active-count'),
    pausedCount: document.getElementById('source-paused-count'),
    cryptoCount: document.getElementById('source-crypto-count'),
    technologyCount: document.getElementById('source-technology-count'),
    policyCount: document.getElementById('source-policy-count'),
    search: document.getElementById('source-search-input'),
    typeFilter: document.getElementById('source-type-filter'),
    trackFilter: document.getElementById('source-track-filter'),
    statusFilter: document.getElementById('source-status-filter'),
    reset: document.getElementById('source-filter-reset'),
    resultCount: document.getElementById('source-result-count'),
    tableBody: document.getElementById('source-table-body'),
    loading: document.getElementById('source-loading-state'),
    empty: document.getElementById('source-empty-state'),
    dialog: document.getElementById('source-dialog'),
    dialogClose: document.getElementById('source-dialog-close'),
    dialogCancel: document.getElementById('source-dialog-cancel'),
    dialogTitle: document.getElementById('source-dialog-title'),
    dialogDescription: document.getElementById('source-dialog-description'),
    dialogWarning: document.getElementById('source-dialog-warning'),
    dialogSubmit: document.getElementById('source-dialog-submit'),
    form: document.getElementById('source-change-form'),
    operation: document.getElementById('source-operation'),
    sourceKey: document.getElementById('source-key'),
    formType: document.getElementById('source-form-type'),
    formEnabled: document.getElementById('source-form-enabled'),
    formName: document.getElementById('source-form-name'),
    formEndpoint: document.getElementById('source-form-endpoint'),
    formCategory: document.getElementById('source-form-category'),
    formReason: document.getElementById('source-form-reason'),
    endpointLabel: document.getElementById('source-endpoint-label'),
    endpointHelp: document.getElementById('source-endpoint-help')
  };

  var state = {
    config: null,
    records: [],
    categories: []
  };

  function normalizedUrl(value) {
    var url = new URL(value);
    url.hash = '';
    url.hostname = url.hostname.toLowerCase();
    if (
      (url.protocol === 'https:' && url.port === '443') ||
      (url.protocol === 'http:' && url.port === '80')
    ) {
      url.port = '';
    }
    if (url.pathname !== '/') {
      url.pathname = url.pathname.replace(/\/+$/, '');
    }
    return url.protocol.toLowerCase() + '//' + url.host + url.pathname + url.search;
  }

  function sourceKey(type, source) {
    if (type === 'rss') return 'rss|' + normalizedUrl(source.url);
    if (type === 'telegram') {
      return 'telegram|' + String(source.channel || '').replace(/^@/, '').toLowerCase();
    }
    if (type === 'github') {
      var identity = source.owner && source.repo
        ? source.owner + '/' + source.repo
        : source.username || '';
      return 'github|' + String(source.type || 'repo_releases').toLowerCase() +
        '|' + identity.toLowerCase();
    }
    if (type === 'reddit') {
      return 'reddit|subreddit|' + String(source.subreddit || '').toLowerCase();
    }
    return type + '|main';
  }

  function categoryTrack(category, config) {
    var filtering = config.filtering || {};
    var groups = filtering.category_groups || {};
    var primary = filtering.primary_groups || [];
    var matchedGroup = null;

    Object.keys(groups).some(function (groupName) {
      if ((groups[groupName].categories || []).indexOf(category) !== -1) {
        matchedGroup = groupName;
        return true;
      }
      return false;
    });

    if (matchedGroup && primary.indexOf(matchedGroup) !== -1) return 'crypto';
    if (matchedGroup === 'technology') return 'technology';
    if (matchedGroup === 'regulation') return 'policy';
    if (/^(exchange|crypto)-/.test(category || '')) return 'crypto';
    if (/^(ai-|tech-)/.test(category || '')) return 'technology';
    if (/regulation/.test(category || '')) return 'policy';
    return 'other';
  }

  function statusFor(itemEnabled, parentEnabled) {
    if (!parentEnabled && itemEnabled) return 'parent-paused';
    return itemEnabled ? 'active' : 'paused';
  }

  function createRecord(config, values) {
    var itemEnabled = values.enabled !== false;
    var parentEnabled = values.parentEnabled !== false;
    return {
      key: values.key,
      name: values.name,
      type: values.type,
      endpoint: values.endpoint,
      viewUrl: values.viewUrl || '',
      category: values.category || 'other',
      track: categoryTrack(values.category || '', config),
      enabled: itemEnabled,
      parentEnabled: parentEnabled,
      status: statusFor(itemEnabled, parentEnabled),
      editable: values.editable !== false,
      removable: values.removable === true
    };
  }

  function flattenSources(config) {
    var sources = config.sources || {};
    var records = [];

    (sources.rss || []).forEach(function (source) {
      records.push(createRecord(config, {
        key: sourceKey('rss', source),
        name: source.name,
        type: 'rss',
        endpoint: source.url,
        viewUrl: source.url,
        category: source.category,
        enabled: source.enabled,
        removable: true
      }));
    });

    (sources.github || []).forEach(function (source) {
      var identity = source.owner && source.repo
        ? source.owner + '/' + source.repo
        : source.username || 'GitHub source';
      records.push(createRecord(config, {
        key: sourceKey('github', source),
        name: identity,
        type: 'github',
        endpoint: identity,
        viewUrl: 'https://github.com/' + identity,
        category: source.category,
        enabled: source.enabled,
        removable: true
      }));
    });

    var telegram = sources.telegram || {};
    (telegram.channels || []).forEach(function (source) {
      var channel = String(source.channel || '').replace(/^@/, '');
      records.push(createRecord(config, {
        key: sourceKey('telegram', source),
        name: '@' + channel,
        type: 'telegram',
        endpoint: channel,
        viewUrl: 'https://t.me/' + channel,
        category: source.category,
        enabled: source.enabled,
        parentEnabled: telegram.enabled,
        removable: true
      }));
    });

    var reddit = sources.reddit || {};
    (reddit.subreddits || []).forEach(function (source) {
      var subreddit = String(source.subreddit || '');
      records.push(createRecord(config, {
        key: sourceKey('reddit', source),
        name: 'r/' + subreddit,
        type: 'reddit',
        endpoint: subreddit,
        viewUrl: 'https://www.reddit.com/r/' + subreddit + '/',
        category: source.category,
        enabled: source.enabled,
        parentEnabled: reddit.enabled,
        removable: true
      }));
    });

    if (sources.hackernews) {
      records.push(createRecord(config, {
        key: sourceKey('hackernews', sources.hackernews),
        name: 'Hacker News',
        type: 'hackernews',
        endpoint: 'Top stories · min score ' + sources.hackernews.min_score,
        viewUrl: 'https://news.ycombinator.com/',
        category: sources.hackernews.category,
        enabled: sources.hackernews.enabled,
        editable: false
      }));
    }

    if (sources.google_news) {
      records.push(createRecord(config, {
        key: sourceKey('google_news', sources.google_news),
        name: 'Google News Search',
        type: 'google_news',
        endpoint: sources.google_news.query,
        category: sources.google_news.category,
        enabled: sources.google_news.enabled,
        editable: false
      }));
    }

    if (sources.gdelt) {
      records.push(createRecord(config, {
        key: sourceKey('gdelt', sources.gdelt),
        name: 'GDELT Search',
        type: 'gdelt',
        endpoint: sources.gdelt.query,
        category: sources.gdelt.category,
        enabled: sources.gdelt.enabled,
        editable: false
      }));
    }

    if (sources.ossinsight) {
      records.push(createRecord(config, {
        key: sourceKey('ossinsight', sources.ossinsight),
        name: 'OSS Insight Trending',
        type: 'ossinsight',
        endpoint: (sources.ossinsight.keywords || []).join(', '),
        viewUrl: 'https://ossinsight.io/',
        category: sources.ossinsight.category,
        enabled: sources.ossinsight.enabled,
        editable: false
      }));
    }

    var trackOrder = {crypto: 0, policy: 1, technology: 2, other: 3};
    records.sort(function (left, right) {
      if (left.status === 'active' && right.status !== 'active') return -1;
      if (left.status !== 'active' && right.status === 'active') return 1;
      if (trackOrder[left.track] !== trackOrder[right.track]) {
        return trackOrder[left.track] - trackOrder[right.track];
      }
      return left.name.localeCompare(right.name, 'zh-CN');
    });
    return records;
  }

  function configuredCategories(config) {
    var groups = (config.filtering || {}).category_groups || {};
    var seen = {};
    var categories = [];
    Object.keys(groups).forEach(function (groupName) {
      (groups[groupName].categories || []).forEach(function (category) {
        if (seen[category]) return;
        seen[category] = true;
        categories.push({
          value: category,
          group: groups[groupName].name || groupName
        });
      });
    });
    return categories;
  }

  function setText(element, value) {
    if (element) element.textContent = String(value);
  }

  function updateMetrics(records) {
    var active = records.filter(function (record) {
      return record.status === 'active';
    });
    setText(elements.totalCount, records.length);
    setText(elements.activeCount, active.length);
    setText(elements.pausedCount, records.length - active.length);
    setText(elements.cryptoCount, active.filter(function (record) {
      return record.track === 'crypto';
    }).length);
    setText(elements.technologyCount, active.filter(function (record) {
      return record.track === 'technology';
    }).length);
    setText(elements.policyCount, active.filter(function (record) {
      return record.track === 'policy';
    }).length);
  }

  function addCell(row, label, className) {
    var cell = document.createElement('td');
    cell.dataset.label = label;
    if (className) cell.className = className;
    row.appendChild(cell);
    return cell;
  }

  function sourceLink(record) {
    if (!record.viewUrl) {
      var text = document.createElement('small');
      text.textContent = record.endpoint;
      return text;
    }
    var link = document.createElement('a');
    link.href = record.viewUrl;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = record.endpoint;
    link.title = record.endpoint;
    return link;
  }

  function actionButton(action, label, key) {
    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'source-row-action';
    button.dataset.action = action;
    button.dataset.key = key;
    button.textContent = label;
    return button;
  }

  function buildRow(record) {
    var row = document.createElement('tr');
    row.dataset.key = record.key;

    var main = addCell(row, '来源', 'source-main-cell');
    var name = document.createElement('strong');
    name.textContent = record.name;
    main.appendChild(name);
    main.appendChild(sourceLink(record));

    var type = addCell(row, '类型');
    var typePill = document.createElement('span');
    typePill.className = 'source-type-pill';
    typePill.textContent = TYPE_LABELS[record.type] || record.type;
    type.appendChild(typePill);

    var track = addCell(row, '方向');
    var trackPill = document.createElement('span');
    trackPill.className = 'source-track-pill';
    trackPill.dataset.track = record.track;
    trackPill.textContent = TRACK_LABELS[record.track];
    track.appendChild(trackPill);

    var category = addCell(row, '分类');
    var categoryValue = document.createElement('span');
    categoryValue.className = 'source-category';
    categoryValue.textContent = record.category;
    categoryValue.title = record.category;
    category.appendChild(categoryValue);

    var status = addCell(row, '状态');
    var statusPill = document.createElement('span');
    statusPill.className = 'source-status-pill';
    statusPill.dataset.status = record.status;
    statusPill.textContent = STATUS_LABELS[record.status];
    status.appendChild(statusPill);

    var actions = addCell(row, '操作', 'source-row-actions');
    if (record.editable) {
      actions.appendChild(actionButton('update', '编辑', record.key));
    }
    actions.appendChild(actionButton(
      record.enabled ? 'pause' : 'resume',
      record.enabled ? '暂停' : '恢复',
      record.key
    ));
    if (record.removable) {
      actions.appendChild(actionButton('remove', '删除', record.key));
    }
    return row;
  }

  function currentFilters() {
    return {
      search: elements.search.value.trim().toLowerCase(),
      type: elements.typeFilter.value,
      track: elements.trackFilter.value,
      status: elements.statusFilter.value
    };
  }

  function matchingRecords() {
    var filters = currentFilters();
    return state.records.filter(function (record) {
      var searchable = [
        record.name,
        record.endpoint,
        record.category,
        record.type
      ].join(' ').toLowerCase();
      if (filters.search && searchable.indexOf(filters.search) === -1) return false;
      if (filters.type !== 'all' && record.type !== filters.type) return false;
      if (filters.track !== 'all' && record.track !== filters.track) return false;
      if (filters.status !== 'all' && record.status !== filters.status) return false;
      return true;
    });
  }

  function renderTable() {
    var records = matchingRecords();
    var fragment = document.createDocumentFragment();
    records.forEach(function (record) {
      fragment.appendChild(buildRow(record));
    });
    elements.tableBody.replaceChildren(fragment);
    elements.empty.hidden = records.length !== 0;
    setText(
      elements.resultCount,
      '显示 ' + records.length + ' / ' + state.records.length + ' 个来源'
    );
  }

  function populateFilters(records) {
    var types = {};
    records.forEach(function (record) {
      types[record.type] = true;
    });
    Object.keys(types).sort().forEach(function (type) {
      var option = document.createElement('option');
      option.value = type;
      option.textContent = TYPE_LABELS[type] || type;
      elements.typeFilter.appendChild(option);
    });
  }

  function populateCategorySelect(categories) {
    elements.formCategory.replaceChildren();
    categories.forEach(function (category) {
      var option = document.createElement('option');
      option.value = category.value;
      option.textContent = category.value + ' · ' + category.group;
      elements.formCategory.appendChild(option);
    });
  }

  function updateEndpointHelp() {
    var help = ENDPOINT_HELP[elements.formType.value] || {
      label: '地址或标识',
      placeholder: '当前来源标识',
      help: '该来源只支持暂停或恢复。'
    };
    setText(elements.endpointLabel, help.label);
    elements.formEndpoint.placeholder = help.placeholder;
    setText(elements.endpointHelp, help.help);
  }

  function ensureTypeOption(type) {
    var option = Array.prototype.find.call(elements.formType.options, function (item) {
      return item.value === type;
    });
    if (option) return;
    option = document.createElement('option');
    option.value = type;
    option.textContent = TYPE_LABELS[type] || type;
    elements.formType.appendChild(option);
  }

  function setDialogFieldState(readOnly) {
    elements.formType.disabled = readOnly;
    elements.formName.disabled = readOnly;
    elements.formEndpoint.disabled = readOnly;
    elements.formCategory.disabled = readOnly;
    elements.formEnabled.disabled = readOnly;
  }

  function dialogCopy(operation, record) {
    if (operation === 'add') {
      return {
        title: '添加信息源',
        description: '填写后会打开预填的 GitHub 变更申请。',
        submit: '前往 GitHub 确认',
        warning: '',
        level: ''
      };
    }
    if (operation === 'update') {
      return {
        title: '编辑 ' + record.name,
        description: '修改内容将在独立配置 PR 中审核。',
        submit: '提交编辑申请',
        warning: '',
        level: ''
      };
    }
    if (operation === 'pause') {
      return {
        title: '暂停 ' + record.name,
        description: '来源会保留在配置中，合并后停止采集。',
        submit: '提交暂停申请',
        warning: record.status === 'parent-paused'
          ? '该来源的上层采集器当前已经停用；本次申请会同时记录单项暂停状态。'
          : '建议优先暂停而不是删除，以便保留配置和恢复路径。',
        level: ''
      };
    }
    if (operation === 'resume') {
      return {
        title: '恢复 ' + record.name,
        description: 'PR 合并后的下一次采集将使用该来源。',
        submit: '提交恢复申请',
        warning: record.parentEnabled
          ? ''
          : '该来源的上层采集器仍处于停用状态；恢复单项后不会立即产生内容。',
        level: ''
      };
    }
    return {
      title: '删除 ' + record.name,
      description: '来源会从生产配置中移除，但历史新闻不会被删除。',
      submit: '提交删除申请',
      warning: '永久删除前请确认暂停无法满足需求。Git 历史仍可用于恢复配置。',
      level: 'danger'
    };
  }

  function openDialog(operation, record) {
    elements.form.reset();
    elements.operation.value = operation;
    elements.formReason.value = '';

    if (operation === 'add') {
      elements.sourceKey.value = 'new';
      elements.formType.value = 'rss';
      elements.formEnabled.value = 'true';
      elements.formName.value = '';
      elements.formEndpoint.value = '';
      if (state.categories.length) {
        elements.formCategory.value = state.categories[0].value;
      }
      setDialogFieldState(false);
    } else {
      ensureTypeOption(record.type);
      elements.sourceKey.value = record.key;
      elements.formType.value = record.type;
      elements.formEnabled.value = operation === 'resume'
        ? 'true'
        : operation === 'pause'
          ? 'false'
          : String(record.enabled);
      elements.formName.value = record.name;
      elements.formEndpoint.value = record.endpoint;
      elements.formCategory.value = record.category;
      setDialogFieldState(operation !== 'update');
    }

    updateEndpointHelp();
    var copy = dialogCopy(operation, record || {});
    setText(elements.dialogTitle, copy.title);
    setText(elements.dialogDescription, copy.description);
    setText(elements.dialogSubmit, copy.submit);
    elements.dialogWarning.hidden = !copy.warning;
    elements.dialogWarning.dataset.level = copy.level;
    setText(elements.dialogWarning, copy.warning);

    if (typeof elements.dialog.showModal === 'function') {
      elements.dialog.showModal();
    } else {
      elements.dialog.setAttribute('open', '');
    }
    if (operation === 'add') {
      elements.formName.focus();
    } else {
      elements.formReason.focus();
    }
  }

  function closeDialog() {
    if (typeof elements.dialog.close === 'function') {
      elements.dialog.close();
    } else {
      elements.dialog.removeAttribute('open');
    }
  }

  function findRecord(key) {
    return state.records.find(function (record) {
      return record.key === key;
    });
  }

  function issueTitle(operation, name) {
    var labels = {
      add: 'Add',
      update: 'Update',
      pause: 'Pause',
      resume: 'Resume',
      remove: 'Remove'
    };
    return '[Source ' + labels[operation] + '] ' + name;
  }

  function buildIssueUrl() {
    var operation = elements.operation.value;
    var enabled = elements.formEnabled.value;
    if (operation === 'pause') enabled = 'false';
    if (operation === 'resume') enabled = 'true';

    var url = new URL(root.dataset.issueUrl);
    url.searchParams.set('template', root.dataset.issueTemplate);
    url.searchParams.set('title', issueTitle(operation, elements.formName.value.trim()));
    url.searchParams.set('operation', OPERATION_OPTIONS[operation]);
    url.searchParams.set('source-type', SOURCE_TYPE_OPTIONS[elements.formType.value]);
    url.searchParams.set('source-key', elements.sourceKey.value);
    url.searchParams.set('source-name', elements.formName.value.trim());
    url.searchParams.set('endpoint', elements.formEndpoint.value.trim());
    url.searchParams.set('category', elements.formCategory.value);
    url.searchParams.set('target-state', STATE_OPTIONS[enabled]);
    url.searchParams.set('reason', elements.formReason.value.trim());
    return url;
  }

  function resetFilters() {
    elements.search.value = '';
    elements.typeFilter.value = 'all';
    elements.trackFilter.value = 'all';
    elements.statusFilter.value = 'all';
    renderTable();
  }

  function bindEvents() {
    elements.addButton.addEventListener('click', function () {
      openDialog('add', null);
    });
    elements.search.addEventListener('input', renderTable);
    elements.typeFilter.addEventListener('change', renderTable);
    elements.trackFilter.addEventListener('change', renderTable);
    elements.statusFilter.addEventListener('change', renderTable);
    elements.reset.addEventListener('click', resetFilters);
    elements.formType.addEventListener('change', updateEndpointHelp);
    elements.dialogClose.addEventListener('click', closeDialog);
    elements.dialogCancel.addEventListener('click', closeDialog);

    elements.tableBody.addEventListener('click', function (event) {
      var button = event.target.closest('button[data-action][data-key]');
      if (!button) return;
      var record = findRecord(button.dataset.key);
      if (record) openDialog(button.dataset.action, record);
    });

    elements.dialog.addEventListener('click', function (event) {
      if (event.target === elements.dialog) closeDialog();
    });

    elements.form.addEventListener('submit', function (event) {
      event.preventDefault();
      if (!elements.form.reportValidity()) return;
      var issueUrl = buildIssueUrl();
      window.open(issueUrl.toString(), '_blank', 'noopener,noreferrer');
      closeDialog();
    });
  }

  async function loadConfig() {
    try {
      var response = await fetch(root.dataset.configUrl, {
        cache: 'no-store',
        credentials: 'omit'
      });
      if (!response.ok) {
        throw new Error('Configuration request failed: ' + response.status);
      }
      var config = await response.json();
      if (!config.sources || !config.filtering) {
        throw new Error('Production configuration is incomplete');
      }

      state.config = config;
      state.categories = configuredCategories(config);
      state.records = flattenSources(config);
      populateCategorySelect(state.categories);
      populateFilters(state.records);
      updateMetrics(state.records);
      elements.loading.hidden = true;
      renderTable();
    } catch (error) {
      elements.loading.hidden = true;
      elements.empty.hidden = false;
      elements.empty.textContent =
        '暂时无法读取生产配置，请稍后刷新或前往 GitHub 查看原始配置。';
      elements.addButton.disabled = true;
      setText(elements.resultCount, '生产配置读取失败');
    }
  }

  bindEvents();
  loadConfig();
})();

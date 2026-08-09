# 归档层、事件线与对外接口

日报从"每天一次性消费品"变成"可持续累积的情报资产"，靠的是一个跨天归档层。
所有派生内容（事件线、实体页、周报、JSON API、分类订阅）都从它生成，
不引入任何服务器或数据库——归档文件随站点一起发布到 `gh-pages`。

## 数据流

```
每日出刊
   └── docs/_data/archive/YYYY-MM.jsonl   每条展示新闻一行
          ├── 事件线   docs/threads/<id>.html
          ├── 实体页   docs/entity/<slug>.html
          ├── JSON API docs/editions/<date>/edition.json + docs/api/latest.json
          ├── 分类订阅 docs/feeds/<category>-<lang>.xml
          └── 周报     docs/weekly/<date>.md（每周一单独任务）
```

发布前 workflow 从 `gh-pages` 恢复 `_data/archive/`，出刊后重新写回，
和已有的 `bmtnews_state.json` 是同一套「git 即数据库」模式。
本地运行产生的这些文件都在 `.gitignore` 里，不会误提交到 `main`。

## 事件线（Story Threads）

跨天追踪同一事件：Bybit 被盗 → Bybit 起诉朝鲜，会归到同一条事件线，
页面上显示「事件线 · 第 N 天」并链到时间线页面。

- 匹配**完全离线、无额外 AI 调用**：比较归一化标签和标题分词
  （英文按词、中文按二元字组），满足「≥2 个共享标签且重合度 ≥0.30」
  或「重合度 ≥0.55」即判为同一事件
- 阈值刻意保守：漏判只是少一个角标，误判会把无关新闻并到一起
- 事件线 ID 由首条新闻 URL 的哈希决定，稳定且不会碰撞
- 只有跨 ≥2 天的事件线才会生成页面并显示角标

## 实体页（Entities）

从 `ai_tags` 提取重复出现的公司、协议、监管机构（过滤掉 crypto、security
这类通用词），累计 ≥3 次的实体生成聚合页。这也是站点主要的 SEO 入口：
没人搜"8 月 9 日日报"，但有人搜某个实体的历史脉络。

标签由 AI 生成，会进入页面 `<title>`，因此在入库时就剥离标记字符
（`clean_label`），而不依赖下游每个渲染点各自转义。

## 对外接口

| 路径 | 内容 |
|------|------|
| `/api/latest.json` | 最新一期完整数据 |
| `/editions/<date>/edition.json` | 指定某期 |
| `/api/editions.json` | 可用刊期索引 |
| `/feeds/crypto-zh.xml` 等 | 分类 Atom 订阅（crypto / technology / policy × zh / en） |

`edition.json` 含每条新闻的双语标题摘要、评分、分类、来源、标签、
多源确认数、事件线链接，以及当期行情快照和导语。

## 周报与评分校准

`uv run horizon --mode weekly`（每周一 09:30 自动触发，也可手动 dispatch）：

- **周报**：从归档取过去 7 天，AI 按「本周主线 / 持续追踪 / 值得记住」
  三段成文，发布到 `/weekly/<date>/`
- **评分校准复盘**：把上周高分和低分新闻与"后来是否发展成多天事件线"
  对照，产出评分偏差分析和 2-4 条可执行的调整建议，写入
  `docs/_data/calibration/<date>.md`（不对外链接，供你调 prompt 参考）

校准复盘是**建议性**的：它不会自动改评分规则，改不改由你决定。

## 多源确认

同一条新闻被多个来源报道时，跨源去重会记录 `merged_sources`，
页面来源行显示「N 源确认」（绿色）或「单一来源」，给读者一个
可信度信号。数据本来就有，只是以前没展示。

## X（Twitter）自动分发

**默认关闭，且双重开关**：`data/config.github.json` 里
`x_delivery.enabled` 必须为 `true`，**并且**四个 OAuth 1.0a 密钥
（`X_CONSUMER_KEY` / `X_CONSUMER_SECRET` / `X_ACCESS_TOKEN` /
`X_ACCESS_SECRET`）都要配置到仓库 secrets。缺任何一项都只会在 run report
里记一条 skip，不会发帖。

开启后每期发一条推：标题 + 前 3 条新闻 + 回链，字数按 X 的计数规则
（URL 固定占 23 字符）裁剪。失败只记录 HTTP 状态码，不回显响应体。

## MCP 历史查询

MCP server 新增只读工具，可以直接问历史问题：

- `hz_search_archive(query, since, until, category, min_score, limit)`
- `hz_get_thread(thread_id)` / `hz_list_threads(days, limit)`
- `hz_get_entity(name, limit)` / `hz_list_entities(days, limit)`

这些工具只读归档，不抓取、不调用 AI、不写任何文件。

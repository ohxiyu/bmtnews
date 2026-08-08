# 人工编辑层（Editorial Layer）

`data/editorial.json` 是日报的人工编辑入口：改这个文件、推送到 `main`，
`editorial-rebuild` workflow 会自动以 `force_publish` 重刊当天日报，
几分钟后网页更新。不需要任何服务器或后台系统；git 历史就是审计日志。

## 使用方式

在 GitHub 网页端（或手机 App）直接编辑 `data/editorial.json`，把条目加进
`items` 数组并 commit 到 `main` 即可。`enabled: false` 的条目会被忽略，
可以把示例留在文件里当模板。

## 条目类型

### `editorial` — 编辑精选（自己想加的新闻）

```json
{
  "type": "editorial",
  "url": "https://example.com/story",
  "title_zh": "中文标题",
  "title_en": "English title",
  "summary_zh": "一两句中文摘要。",
  "summary_en": "Optional English summary.",
  "date": "2026-08-09"
}
```

- 插入当天日报并**置顶**，页面上带「编辑精选」标签，不参与 AI 评分（评分位显示 —）
- 会随日报一起进入 Telegram / 邮件 / webhook 推送
- `date` 指定生效的刊期（东八区刊期日）；省略则每期都会插入，一般都应填
- 至少要有 `url` 和一个标题；缺某语言时自动回退另一语言

### `sponsored` — 广告位

```json
{
  "type": "sponsored",
  "url": "https://example.com/promo",
  "title_zh": "广告标题",
  "summary_zh": "一句话描述。",
  "position": 4,
  "starts": "2026-08-10",
  "expires": "2026-08-17"
}
```

- **仅网页展示**，带明显「广告 / Sponsored」标签，不进排行榜、不受分类过滤影响、不进 Telegram/邮件推送
- 每期最多渲染 1 条；`position` 是插入在第几条新闻的位置（默认 4，即第三条之后）
- `starts` / `expires` 区间内自动上刊，过期后下一次重刊自动消失
- 链接带 `rel="sponsored"`，符合搜索引擎规范

### `suppress` — 人工压稿

```json
{
  "type": "suppress",
  "url": "https://example.com/article-to-hide",
  "date": "2026-08-09"
}
```

- 按 URL（忽略跟踪参数等）把某条新闻从当期候选中剔除；已发布的日报改完文件后会自动重刊，从页面上消失

## 生效与失败行为

- 推送到 `main` 后 `editorial-rebuild` workflow 触发 `daily-summary`
  （`force_publish=true`），完整重跑当天固定窗口并重新发布
- 文件解析是**软失败**：JSON 写坏或某条目字段无效时，该条目被跳过并在
  run report 里记录告警，绝不会阻塞日报发布
- run report 中的相关指标：`editorial_items`、`sponsored_slots`、`suppressed_manual`

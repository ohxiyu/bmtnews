# X（Twitter）分发

两种模式，都默认关闭，且都需要四个 OAuth 1.0a 密钥齐全才会真正发帖。

## 模式对比

| | `digest` | `drip`（当前配置） |
|---|---|---|
| 时机 | 日报发布完成后（约 08:35 东八区） | 一天四个时段分开发 |
| 内容 | 一条推，含前 3 条标题 + 站点链接 | 每条推一个故事：标题 + 一句要点 + 链接 |
| 条数 | 每天 1 条（每语言） | 每天 4 条（`drip_items`） |
| 执行者 | 日报 workflow 尾部 | 独立的 `x-distribution` workflow |

`mode: "drip"` 时日报发布**不发帖**，避免两种模式重复。

## 分时时段

`x-distribution.yml` 的四个 cron（UTC 书写，注释标注东八区）：

| 东八区 | UTC cron | 场景 |
|---|---|---|
| 09:00 | `0 1 * * *` | 上班/开盘前 |
| 12:30 | `30 4 * * *` | 午休 |
| 18:30 | `30 10 * * *` | 晚间通勤 |
| 21:30 | `30 13 * * *` | 晚间高峰 |

要改时间直接改 cron。注意 GitHub Actions 的 schedule **不支持 timezone 字段**，
必须写 UTC；同时 Actions 的定时任务本身有几分钟到几十分钟的排队延迟，
高峰期尤其明显，所以不要指望精确到分钟。

## 顺序而非对表

每个时段发的是「今天还没发过的最小序号」，而不是「本时段对应第 N 条」。
好处是**跳过或延迟一个时段只会让内容顺延，不会漏发也不会重发**：

- 某次任务失败 → 下个时段补发同一条
- 某天日报没出 → 该时段直接退出，不发任何内容
- 一天四条发完 → 后续时段空跑

状态存在独立的 `x-queue` 分支（`data/x-queue.json`），记录
「哪一期的哪些序号、哪种语言已发」，换日自动重置。

## 配置

```json
"x_delivery": {
  "enabled": false,
  "mode": "drip",
  "drip_items": 4,
  "link_target": "site",
  "languages": ["zh"],
  "site_url": "https://bmt.news/",
  "max_items": 3
}
```

- `drip_items`：一天发几条（1-8）。日报当天条数不足时按实际条数发
- `link_target`：`site` 链回日报页（引流），`source` 直接链原文（给媒体署名）
- `languages`：加 `"en"` 就是中英各四条，共 8 条/天——**不建议**，容易被判定刷屏
- `max_items`：只在 `digest` 模式下生效

## 启用步骤

1. X Developer Portal 建 App，权限选 **Read and Write**，生成四个凭证
2. 仓库 Secrets 添加 `X_CONSUMER_KEY`、`X_CONSUMER_SECRET`、
   `X_ACCESS_TOKEN`、`X_ACCESS_SECRET`
3. 把 `data/config.github.json` 的 `x_delivery.enabled` 改为 `true`

三者缺一都只会在 run report 记一条 skip，不会发帖。

## 手动测试

Actions 里手动运行 `BMTNews X Distribution`，可指定 `edition_date`。
每次手动运行会消耗一条队列序号，测试时注意。

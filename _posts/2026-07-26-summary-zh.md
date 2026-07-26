---
layout: default
title: "Horizon Summary: 2026-07-26 (ZH)"
date: 2026-07-26
lang: zh
---

> 从 27 条内容中筛选出 5 条重要资讯。

---

1. [vLLM v0.26.0：支持 Inkling 模型并优化 DeepSeek-V4](#item-1) ⭐️ 8.0/10
2. [开放权重 AI 的 Kubernetes 时刻：标准化在即](#item-2) ⭐️ 8.0/10
3. [安卓可能限制设备上的 ADB 访问](#item-3) ⭐️ 8.0/10
4. [Ruff v0.16.0 将默认规则从 59 条扩展至 413 条](#item-4) ⭐️ 8.0/10
5. [梁文锋因言论外泄暂停 DeepSeek 融资](#item-5) ⭐️ 8.0/10

---

<a id="item-1"></a>
## [vLLM v0.26.0：支持 Inkling 模型并优化 DeepSeek-V4](https://github.com/vllm-project/vllm/releases/tag/v0.26.0) ⭐️ 8.0/10

vLLM v0.26.0 新增对 Inkling 模型系列的支持，并对 DeepSeek-V4 进行了跨多个硬件供应商的显著性能优化。此外，还引入了通过 head\_dtype 实现的 fp32 lm\_head 功能、按 KV 缓存组选择的灵活注意力后端，以及成熟的分层二级存储 KV 卸载。 此次发布强化了 vLLM 作为领先 LLM 推理引擎的地位，支持了像 Inkling 这样的新兴开源权重模型，并为 DeepSeek-V4 的生产部署提供了关键优化。新功能还提升了模型准确性和部署灵活性，惠及更广泛的 AI 社区。 此版本包含来自 212 位贡献者的 411 次提交，关键技术新增包括 Inkling 的 Hopper FA4 相对注意力、DeepSeek-V4 专用路由内核（端到端 TPOT 提升 2.94%）以及 ModelOpt NVFP4 量化。KV 卸载与分层存储已通过指标和对象存储二级层趋于成熟，Rust 前端现在支持多模态视频和音频。

github · khluu · 7月25日 10:38

**背景**: vLLM 是一个开源、高吞吐量的 LLM 推理引擎，针对 GPU 加速进行了优化。Inkling 模型系列由 Thinking Machines Lab 于 2026 年 7 月发布，是一个面向开发者定制化的开源权重多模态模型。DeepSeek-V4 是 DeepSeek 大语言模型的最新版本，需要高效的推理优化以支持生产环境部署。NVFP4 是一种由 NVIDIA ModelOpt 支持的量化格式，可减少内存并提高吞吐量。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://thinkingmachines.ai/news/introducing-inkling/">Inkling: Our Open-Weights Model - Thinking Machines Lab</a></li>
<li><a href="https://arunksingh16.medium.com/nvidia-nvfp4-quantization-blackwell-and-the-path-to-production-inference-12407e14e084">NVIDIA NVFP4: Quantization, Blackwell, and the Path to Production Inference | by Arun Kumar Singh | Jul, 2026 | Medium</a></li>

</ul>
</details>

**标签**: `#vLLM`, `#LLM inference`, `#release notes`, `#GPU optimization`, `#AI infrastructure`

---

<a id="item-2"></a>
## [开放权重 AI 的 Kubernetes 时刻：标准化在即](https://tobi.knaup.me/2026-07-25-open-weight-ai-is-having-its-kubernetes-moment/) ⭐️ 8.0/10

一篇文章指出，开放权重 AI 模型正成为人工智能部署的标准，类似于 Kubernetes 成为容器编排的标准。 这一趋势可能减少供应商锁定，通过提供通用的开放基础设施层推动 AI 的广泛采用，类似于 Kubernetes 使云原生开发民主化。 开放权重模型仅发布训练后的参数，不一定包含训练数据或代码，引发了关于真正开放性的讨论。与 Kubernetes 的类比突显了标准化、社区驱动的 AI 堆栈的潜力。

hackernews · tknaup · 7月25日 14:49 · [社区讨论](https://news.ycombinator.com/item?id=49048034)

**背景**: 开放权重 AI 指预训练参数公开发布的模型，允许他人微调或部署。与完全开源 AI 不同，训练数据和代码可能仍为专有。Kubernetes 作为开源容器编排平台，通过实现可移植性和可扩展性成为行业标准。文章认为开放权重模型同样可能成为 AI 部署的默认选择。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://en.wikipedia.org/wiki/Open-weight_artificial_intelligence">Open-weight artificial intelligence</a></li>
<li><a href="https://news.google.com/stories/CAAqNggKIjBDQklTSGpvSmMzUnZjbmt0TXpZd1NoRUtEd2pfNjZ2T0VSR2liV2lIdGlSTjN5Z0FQAQ?hl=en-IN&amp;gl=IN&amp;ceid=IN:en">Google News - Thinking Machines Lab releases open - weight AI model...</a></li>
<li><a href="https://openai.com/index/introducing-gpt-oss/">Introducing gpt-oss | OpenAI</a></li>

</ul>
</details>

**社区讨论**: 评论者讨论了按原产国禁止模型的不可行性，质疑了 AI 定价的波动性（“令牌经济学”），并展望了公司协作共享开放模型的未来，类似于它们对 Linux 的贡献。

**标签**: `#open-source`, `#AI`, `#Kubernetes`, `#model-weight`, `#community`

---

<a id="item-3"></a>
## [安卓可能限制设备上的 ADB 访问](https://kitsumed.github.io/blog/posts/android-may-soon-restrict-on-device-adb/) ⭐️ 8.0/10

据报道，谷歌正在考虑限制设备上的 Android 调试桥（ADB）访问，这意味着开发者可能需要使用 USB 连接或满足额外的身份验证要求才能进行无线调试。 这一变化可能会显著影响安卓开发者的工作流程，因为无线 ADB 是一种无需物理 USB 连接即可调试和测试应用的便捷工具。 该限制针对的是需要同时开启开发者选项和远程 ADB 的攻击向量，社区认为这只影响到极少数用户。

hackernews · shscs911 · 7月25日 06:57 · [社区讨论](https://news.ycombinator.com/item?id=49045159)

**背景**: Android 调试桥（ADB）是一个多功能的命令行工具，允许开发者安装应用、访问 Unix shell、查看日志和执行调试。设备上的 ADB（即无线调试）使用 mDNS 通过网络连接，无需 USB 数据线。虽然 ADB 对开发至关重要，但如果攻击者获得了对已启用 ADB 设备的远程访问权限，也会带来安全风险。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://en.wikipedia.org/wiki/Android_Debug_Bridge">Android Debug Bridge - Wikipedia</a></li>
<li><a href="https://developer.android.com/tools/adb">Android Debug Bridge (adb) | Android Studio | Android Developers</a></li>

</ul>
</details>

**社区讨论**: 社区评论显示意见分歧：一些用户认为考虑到攻击概率很低，安全变更没有必要；而另一些人则认为这是限制开发者自由的又一步。一位评论者预测未来的限制将迫使开发者付费或交出身份，其他人则指出可能会出现变通方法来保持 ADB 的可访问性。

**标签**: `#Android`, `#ADB`, `#Security`, `#Developer Tools`, `#Google`

---

<a id="item-4"></a>
## [Ruff v0.16.0 将默认规则从 59 条扩展至 413 条](https://simonwillison.net/2026/Jul/25/ruff/#atom-everything) ⭐️ 8.0/10

Ruff v0.16.0 于 2026 年 7 月 23 日发布，将默认 lint 规则从 59 条增加到 413 条。此更改导致许多 CI 管道因默认启用新检查而失败。 此更新对 Python 生态系统影响重大，因为 Ruff 被广泛用于代码检查。未固定 Ruff 版本的项目可能遇到 CI 失败，但新规则能够捕获以前遗漏的严重问题，如语法错误和运行时错误。 自 v0.1.0 以来，Ruff 的规则总数从 708 条增加到 968 条。新默认规则包括语法错误（例如 load-before-global-declaration）和运行时错误（例如 yield-in-init）的检查，并提供详细说明，可供 AI 编码代理自动修复问题。

rss · Simon Willison · 7月25日 22:44

**背景**: Ruff 是一个用 Rust 编写的极快 Python 代码检查器和格式化工具。它可以替代 Flake8、isort 和 pyupgrade 等工具，运行速度比前辈快 10-100 倍。Ruff 背后的公司 Astral 最近被 OpenAI 收购。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://docs.astral.sh/ruff/linter/">The Ruff Linter | Ruff - Astral</a></li>
<li><a href="https://astral.sh/">Astral : High-performance Python tooling</a></li>
<li><a href="https://github.com/astral-sh/ruff">GitHub - astral-sh/ruff: An extremely fast Python linter and ... ruff · PyPI Ruff - Astral Ruff: Complete Guide to Python&#x27;s Fastest Linter | pydevtools GitHub - sartcod/ruff: An extremely fast Python linter and ... Ruff: A Modern Python Linter for Error-Free and Maintainable ...</a></li>

</ul>
</details>

**标签**: `#Python`, `#Linting`, `#Ruff`, `#Astral`, `#Software Update`

---

<a id="item-5"></a>
## [梁文锋因言论外泄暂停 DeepSeek 融资](https://www.bloomberg.com/news/articles/2026-07-25/deepseek-said-to-tell-backers-of-funding-pause-after-viral-posts) ⭐️ 8.0/10

DeepSeek 暂停了下一轮融资（原计划至少 100 亿元人民币），原因是创始人梁文锋的内部言论被泄露到网上，促使公司重新评估信息披露流程。 这一暂停表明主要 AI 公司对内部沟通的敏感度提高，可能影响中国 AI 投资的节奏，因为 DeepSeek 是一家获得重要支持的关键参与者。 暂停是暂时的；DeepSeek 可能稍后重启谈判，并最早于 2026 年内准备 IPO。其首轮融资筹集了 70 亿美元，投资者包括腾讯和宁德时代。

telegram · zaihuapd · 7月26日 01:17

**背景**: DeepSeek 是一家专注于大语言模型的中国 AI 公司。它于 2026 年 6 月完成了首轮外部融资，筹集 70 亿美元，估值数千亿元。此次泄露事件导致内部流程重新评估。

**标签**: `#AI`, `#DeepSeek`, `#funding`, `#leak`, `#industry news`

---
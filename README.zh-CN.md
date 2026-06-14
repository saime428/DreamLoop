# DreamLoop

[English](README.md) | [中文](README.zh-CN.md)

[![CI](https://github.com/saime428/DreamLoop/actions/workflows/ci.yml/badge.svg)](https://github.com/saime428/DreamLoop/actions/workflows/ci.yml)

![DreamLoop dashboard screenshot](docs/assets/dashboard-screenshot.png)

**梦会重复说话，DreamLoop 帮你在本地听见。**

- 完全本地优先。梦境数据默认不离开你的机器。
- 支持 Ollama 零成本运行；需要云模型时再显式配置 DeepSeek、OpenAI 或 Custom OpenAI-compatible。
- CLI 优先、易 fork，适合开发者和 Obsidian 式知识工作流。
- 解梦更重视情绪、现实处境、多种可验证解释，而不是只给一两句玄学摘要。

```bash
git clone https://github.com/saime428/DreamLoop.git
cd DreamLoop
uv sync --extra dev
uv run dreamloop init
uv run dreamloop web
```

DreamLoop 是一个面向梦境记录爱好者、开发者和知识工作者的本地优先 AI 梦境日志。它不是云端日记应用，而是一个可以检查、扩展、fork 的个人工具。

## 快速开始

### 5 分钟体验，不需要 AI

```bash
pipx install dreamloop
dreamloop init
dreamloop demo
dreamloop web
```

预期结果：

```text
DreamLoop 会写入 3 条本地示例梦境、mock 分析和本地视觉记忆卡片。
Dashboard、Patterns、Gallery 会立刻有内容可看。
这个 demo 不需要云模型，也不会上传梦境。
```

### 从源码运行

```bash
git clone https://github.com/saime428/DreamLoop.git
cd DreamLoop
uv sync --extra dev
uv run dreamloop init
uv run dreamloop add "我梦见海底有一扇蓝色的门。"
uv run dreamloop web
```

预期结果：

```text
DreamLoop 把梦境写入 .dreamloop/dreamloop.sqlite3。
本地 Dashboard 在 http://127.0.0.1:8765 启动。
未配置模型时，AI 分析会保持 pending，不影响记录和浏览。
```

如果你不确定本机环境是否就绪，可以运行：

```bash
dreamloop doctor
```

它会检查数据目录、SQLite、AI provider、Ollama 连接和密钥配置状态，但不会打印任何密钥。

## 为什么做它

很多梦境类 App 把 AI 分析做成订阅功能，也默认把非常私密的文本送进云端。DreamLoop 的方向相反：数据先在本地落地，AI 是可替换层，用户明确选择后才使用云模型。

默认推荐路径是 Ollama，本机即可零成本分析。DeepSeek、OpenAI 和 Custom OpenAI-compatible 端点都是可选增强，适合想要更强模型或自建网关的人。

## 六页闭环

DreamLoop v0.1 的产品逻辑是一个完整闭环：

- Dashboard 总览：作为首页和 README 截图位，展示 AI 洞察、热力图、统计摘要和最近梦境。
- Log 录入：高频输入页，先写梦境，也可补充醒来感受、现实关联和个人联想，再点击 AI 分析。
- Detail 分析：查看梦境原文、详细解梦、现实问题、自我验证问题、原始 JSON，并能给每条解释打反馈。
- Patterns 规律：可点击梦境日历、符号趋势、主题趋势和高共鸣主题，图表能跳回 Log 过滤记录。
- Gallery 记忆：v0.1 先展示本地视觉卡片；真实图像生成是 opt-in 路线，不默认调用付费 API。
- Settings 信任托底：配置模型提供方、查看本地数据目录、确认密钥不回显，并阅读隐私审计说明。

## 无 AI 模式也能用

DreamLoop 的核心能力不依赖云模型：

- 你可以记录、浏览、删除梦境。
- 可以导入日历、同步天气、查看基础统计。
- 可以运行 `dreamloop demo` 体验完整页面状态。
- AI 只在你配置 provider 并明确触发分析时运行。

## 隐私承诺

- 梦境文本存储在 `.dreamloop/dreamloop.sqlite3`。
- `.dreamloop/` 会自动写入 `.gitignore`，避免误提交私密数据。
- 默认不会上传梦境。
- Ollama 路径保持本机分析。
- DeepSeek/OpenAI/Custom 只有在你显式配置后才会使用。
- API Key 写入 `.dreamloop/secrets.env`，不会进入源码、README、测试或页面 HTML。

## AI Provider

可用命令：

```bash
dreamloop ai status
dreamloop ai use ollama --model qwen3:8b
dreamloop ai use deepseek --model deepseek-v4-flash
dreamloop ai use openai --model gpt-4.1-mini
dreamloop ai use custom --model local-model --base-url http://localhost:1234/v1
dreamloop ai test
```

Provider 说明：

- `ollama`：本地优先，默认 `http://localhost:11434/v1`，推荐零成本路径。
- `deepseek`：可选云模型，默认 `deepseek-v4-flash`。
- `openai`：可选 OpenAI 云模型。
- `custom`：任意 OpenAI-compatible `/v1` 端点，包括本地网关。
- `none`：只记录和浏览，不做 AI 分析。

## 常见排查

- 页面没有分析：先运行 `dreamloop doctor`，确认 provider 是否 ready。
- Ollama 不可用：确认已启动 Ollama，并执行 `ollama pull qwen3:8b`。
- 不想用云：选择 `dreamloop ai use ollama --model qwen3:8b` 或 `dreamloop ai use none`。
- 页面没内容：运行 `dreamloop demo` 添加本地示例数据。
- 需要给别人看：运行 `dreamloop web` 后打开 `http://127.0.0.1:8765`。

## CLI 与 Obsidian 路线

DreamLoop 保持 CLI 优先：

```text
$ dreamloop add "A door opened under the sea."
saved locally -> .dreamloop/dreamloop.sqlite3
analysis -> pending
```

Obsidian 路线图：

- v0.2：Markdown export，带 frontmatter 和分析摘要。
- v0.3：Obsidian vault sync。
- v0.4：社区插件，支持捕获、双链和本地 Dashboard 启动。

## 本地数据模型

```text
.dreamloop/
  dreamloop.sqlite3
  config.json
  secrets.env
  chroma/
  exports/
  imports/
```

SQLite 保存梦境、分析结果、用户反馈、日历事件和天气摘要。ChromaDB 是可选增强，用于后续更强的相似梦境和聚类能力。

## 路线图

### v0.1

- CLI 和轻量 Web 六页闭环。
- SQLite 本地存储。
- Ollama 优先的 provider 设置。
- 可选 DeepSeek/OpenAI/Custom 结构化分析。
- 可选输入预设和更长的现实关联解梦报告。
- 可点击热力图、符号趋势、主题趋势、详情页分析。
- Gallery 最小视觉记忆闭环。
- 真实截图资产、CI、CHANGELOG 和公开发布包装。

### v0.1.1

- 修复 Dashboard 首屏撑爆。
- 增加 `dreamloop doctor` 和 `dreamloop demo`。
- 增加解梦解释反馈：有共鸣、不准、不确定。
- Patterns 展示高共鸣主题。
- Settings 增加隐私审计说明。

### v0.2

- Markdown/Obsidian 导出。
- CLI GIF/cast 传播资产。
- ChromaDB 聚类与 recurring theme insight。
- 备份和恢复流程。

### v0.3+

- Obsidian vault sync。
- Obsidian community plugin。
- 本地保存的 opt-in 梦境插画。
- 原生桌面壳或更顺手的本地启动器。

## 贡献

这个项目刻意保持小而可 fork。适合贡献的方向：

- 改进本地模型 prompt
- 补充 `.ics` fixture
- 打磨 Dashboard 可访问性
- 扩展 Markdown/Obsidian 导出
- 制作终端演示资产

运行测试：

```bash
uv run --extra dev pytest
```

构建：

```bash
uv build
```

## License

MIT

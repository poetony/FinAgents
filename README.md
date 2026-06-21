# FinAgent

<div align="center">

[![License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/Version-1.0.0-green.svg)](./VERSION)

**Multi-Agent LLM-Powered Financial Analysis Framework**

**基于大语言模型的多智能体金融分析框架**

</div>

---

https://github.com/your-org/FinAgent

## Table of Contents / 目录

- [English](#english)
  - [Quick Start](#quick-start)
  - [Supported LLM Providers](#supported-llm-providers)
  - [Features](#features)
  - [Architecture](#architecture)
  - [Configuration](#configuration)
  - [Contributing](#contributing)
  - [License](#license)
  - [Disclaimer](#disclaimer)
- [简体中文](#简体中文)
  - [快速开始](#快速开始)
  - [大模型支持](#大模型支持)
  - [功能特性](#功能特性)
  - [系统架构](#系统架构)
  - [配置说明](#配置说明)
  - [贡献指南](#贡献指南)
  - [许可证](#许可证)
  - [免责声明](#免责声明)
- [Acknowledgments / 致谢](#acknowledgments--致谢)

---

## English

FinAgent is a multi-agent stock analysis framework powered by large language models. Multiple specialized agents — market analyst, fundamentals analyst, news analyst, and risk manager — collaborate through structured debate to produce comprehensive financial analysis reports.

Based on [TradingAgents](https://github.com/TauricResearch/TradingAgents) by Tauric Research and [TradingAgents-CN](https://github.com/hsliuping/TradingAgents-CN).

### Quick Start

```bash
# 1. Install
git clone https://github.com/your-org/FinAgent.git
cd FinAgent
pip install -e .

# 2. Configure your LLM API key (interactive wizard)
python scripts/setup_llm.py

# 3. Start the app
python -m tradingagents
```

Or configure manually:

```bash
cp .env.example .env
# Edit .env — set one LLM API key (DeepSeek recommended for beginners)
# DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

### Supported LLM Providers

| Provider | Config Key | Notes |
|----------|-----------|-------|
| **DeepSeek** | `DEEPSEEK_API_KEY` | Recommended — cheap, great quality, excellent for Chinese markets |
| **OpenAI** | `OPENAI_API_KEY` | GPT-4o / GPT-4o-mini |
| **Alibaba Tongyi** | `DASHSCOPE_API_KEY` | Qwen models, stable access in China |
| **Google Gemini** | `GOOGLE_API_KEY` | Strong free tier available |
| **Anthropic Claude** | `ANTHROPIC_API_KEY` | Top-tier reasoning and analysis |
| **OpenRouter** | `OPENROUTER_API_KEY` | 200+ models with a single API key |
| **SiliconFlow** | `SILICONFLOW_API_KEY` | Chinese provider with many open-source models |
| **Ollama (local)** | None needed | Free, offline, run models locally |

Run `python scripts/setup_llm.py` for interactive setup.

### Features

- **Multi-Agent Collaboration** — Market analyst, fundamentals analyst, news analyst, and risk manager work in parallel, then debate to reach consensus
- **Multi-Market Support** — A-shares, Hong Kong stocks, and US stocks
- **Pluggable LLM Backends** — OpenAI, DeepSeek, DashScope, Google Gemini, Anthropic Claude, OpenRouter, Ollama, and custom endpoints
- **Flexible Data Sources** — AKShare (free, recommended), Tushare, FinnHub, BaoStock
- **Report Export** — Markdown, Word, and PDF formats
- **Web UI** — Vue 3 + FastAPI management interface
- **Batch Analysis** — Analyze multiple stocks simultaneously

### Architecture

```
User Request
    │
    ├── Market Analyst       (technical indicators, price trends)
    ├── Fundamentals Analyst  (PE, PB, ROE, financial health)
    ├── News Analyst          (market sentiment, news impact)
    └── Social Media Analyst  (retail sentiment, social buzz)
            │
            ▼
    Risk Manager (challenges assumptions, stress-tests scenarios)
            │
            ▼
    Portfolio Manager (allocates weights, scores the thesis)
            │
            ▼
    Final Report
```

All agents operate independently in parallel, then enter structured multi-round debate moderated by the Risk Manager before producing a final recommendation.

### Configuration

See `.env.example` for all options. Minimum requirement: set **one** LLM API key.

For database-backed features (progress tracking, caching, user management), configure PostgreSQL:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DATABASE=tradingagents
```

### Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Create a Pull Request

See [CONTRIBUTORS.md](CONTRIBUTORS.md) for the full list of contributors.

### License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

Based on [TradingAgents](https://github.com/TauricResearch/TradingAgents) (Apache 2.0) and [TradingAgents-CN](https://github.com/hsliuping/TradingAgents-CN).

### Disclaimer

This framework is for **research and educational purposes only**. It does not constitute investment advice. AI model predictions involve inherent uncertainty. Investment involves risk — decisions should be made cautiously.

---

## 简体中文

FinAgent 是一个基于大语言模型的多智能体股票分析框架。多个专业智能体——市场分析师、基本面分析师、新闻分析师、风险管理师——通过结构化辩论协作，产出全面的金融分析报告。

项目基于 Tauric Research 的 [TradingAgents](https://github.com/TauricResearch/TradingAgents) 和 [TradingAgents-CN](https://github.com/hsliuping/TradingAgents-CN) 深度开发。

### 快速开始

```bash
# 1. 安装
git clone https://github.com/your-org/FinAgent.git
cd FinAgent
pip install -e .

# 2. 配置大模型 API 密钥（交互式向导）
python scripts/setup_llm.py

# 3. 启动
python -m tradingagents
```

或手动配置：

```bash
cp .env.example .env
# 编辑 .env，设置一个大模型 API Key（推荐 DeepSeek）
# DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

### 大模型支持

| 提供商 | 配置项 | 说明 |
|--------|--------|------|
| **DeepSeek** | `DEEPSEEK_API_KEY` | 推荐 — 性价比极高，中文能力强 |
| **OpenAI** | `OPENAI_API_KEY` | GPT-4o / GPT-4o-mini |
| **阿里百炼** | `DASHSCOPE_API_KEY` | 通义千问系列，国内访问稳定 |
| **Google Gemini** | `GOOGLE_API_KEY` | 免费额度慷慨 |
| **Anthropic Claude** | `ANTHROPIC_API_KEY` | 推理分析能力顶尖 |
| **OpenRouter** | `OPENROUTER_API_KEY` | 一个 Key 访问 200+ 模型 |
| **硅基流动** | `SILICONFLOW_API_KEY` | 国产开源模型聚合 |
| **Ollama (本地)** | 无需密钥 | 免费、离线、本地运行 |

运行 `python scripts/setup_llm.py` 进入交互式配置向导。

### 功能特性

- **多智能体协作** — 市场分析师、基本面分析师、新闻分析师和风险管理师并行工作，经多轮辩论达成共识
- **多市场支持** — 覆盖A股、港股、美股
- **大模型可插拔** — 支持 OpenAI、DeepSeek、通义千问、Gemini、Claude、OpenRouter、Ollama 及自定义接口
- **数据源灵活** — AKShare（免费推荐）、Tushare、FinnHub、BaoStock
- **报告导出** — 支持 Markdown、Word、PDF 多格式导出
- **Web 管理界面** — Vue 3 + FastAPI 架构
- **批量分析** — 支持多只股票同时分析

### 系统架构

```
用户请求
    │
    ├── 市场分析师       (技术指标、价格趋势)
    ├── 基本面分析师     (PE、PB、ROE、财务健康度)
    ├── 新闻分析师       (市场情绪、新闻影响)
    └── 社交媒体分析师   (散户情绪、舆情热度)
            │
            ▼
    风险管理师 (质疑假设、压力测试)
            │
            ▼
    投资组合经理 (权重分配、综合评分)
            │
            ▼
    最终分析报告
```

所有智能体并行独立分析，然后在风险管理师的协调下进行多轮结构化辩论，最终产出一致性建议。

### 配置说明

查看 `.env.example` 获取全部配置项。最低要求：设置**一个**大模型 API Key。

如需数据库支持（进度追踪、缓存、用户管理），请配置 PostgreSQL：

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DATABASE=tradingagents
```

### 贡献指南

欢迎各种形式的贡献！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

查看 [CONTRIBUTORS.md](CONTRIBUTORS.md) 获取完整贡献者名单。

### 许可证

本项目采用 **MIT 许可证** — 详见 [LICENSE](LICENSE)。

基于 [TradingAgents](https://github.com/TauricResearch/TradingAgents)（Apache 2.0）和 [TradingAgents-CN](https://github.com/hsliuping/TradingAgents-CN)。

### 免责声明

本框架仅供**研究和教育用途**，不构成任何投资建议。AI 模型的预测存在不确定性。投资有风险，决策需谨慎。

---

## Acknowledgments / 致谢

Special thanks to [Tauric Research](https://github.com/TauricResearch) for creating the original [TradingAgents](https://github.com/TauricResearch/TradingAgents) framework and releasing it as open source. Their pioneering work in multi-agent financial analysis made this project possible.

感谢 [TradingAgents-CN](https://github.com/hsliuping/TradingAgents-CN) 项目在中文市场和国产大模型适配方面的重要贡献。

---

<div align="center">

**If you find FinAgent useful, please give it a Star!**

**如果觉得有用，请给个 Star！**

⭐ [Star this repo](https://github.com/your-org/FinAgent) | 📖 [Documentation](./docs/) | 🤝 [Contributing](./CONTRIBUTORS.md)

</div>

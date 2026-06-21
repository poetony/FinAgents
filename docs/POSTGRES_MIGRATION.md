# PostgreSQL 迁移指南

## 概述

本项目已支持使用 PostgreSQL 替代 MongoDB 作为主数据库。迁移后，数据存储在 PostgreSQL 的 JSONB 表中，保持与原有 MongoDB 接口的兼容性。

## 配置步骤

### 1. 环境变量配置

在 `.env` 中已配置：

```
POSTGRES_ENABLED=true
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=CUEBer@3947
POSTGRES_DATABASE=tradingagents
```

或使用连接字符串：

```
POSTGRES_CONNECTION_STRING=postgresql://postgres:password@localhost:5432/tradingagents
```

### 2. 初始化数据库

首次运行前执行：

```bash
python scripts/init_postgres.py
```

脚本会自动：
- 创建 `tradingagents` 数据库（若不存在）
- 创建所需的 JSONB 表结构

### 3. 大模型 API Key 配置

在 `.env` 中配置至少一个 LLM 提供商的 API Key：

- **DeepSeek**（推荐）：`DEEPSEEK_API_KEY=your_key`
- **阿里百炼**：`DASHSCOPE_API_KEY=your_key`
- **OpenAI**：`OPENAI_API_KEY=your_key`

也可在 Web 界面「设置 -> 大模型厂家」中配置。

## 表结构说明

数据存储在 `pg_doc_<collection_name>` 表中，每表包含：
- `id`：主键（对应文档 `_id`）
- `data`：JSONB 类型，存储完整文档
- `created_at` / `updated_at`：时间戳

## 切换回 MongoDB

如需恢复使用 MongoDB，在 `.env` 中设置：

```
POSTGRES_ENABLED=false
MONGODB_ENABLED=true
```

## 注意事项

- Redis 仍用于缓存，需单独配置
- 首次迁移时，MongoDB 中的历史数据需手动迁移（如有需要可编写迁移脚本）

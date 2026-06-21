# Single - 单股分析独立应用

单股分析功能已完整迁移至本目录，包含前后端及配置，可独立运行。

## 目录结构

```
Single/
├── backend/           # 后端 (FastAPI)
│   ├── main.py        # 入口，复用父项目 app、tradingagents
│   └── __init__.py
├── src/               # 前端 (Vue 3 + Vite)
│   ├── App.vue
│   ├── main.js
│   └── styles.css
├── .env               # 专用配置（覆盖父项目）
├── run_backend.py     # 后端启动脚本
├── start.ps1          # 一键启动前后端
├── package.json
├── vite.config.js
└── README.md
```

## 依赖

- **Python**：复用父项目 `TradingAgents` 的虚拟环境
- **Node.js**：前端构建
- **PostgreSQL**：与父项目共用（通过父项目 .env 配置）

## 启动方式

### 方式一：一键启动

```powershell
cd Single
.\start.ps1
```

### 方式二：分别启动

```powershell
cd Single

# 1. 后端 (8301)
python run_backend.py

# 2. 前端 (8302) - 新开终端
npm install   # 首次需安装
npm run dev
```

### 访问

- 前端：http://localhost:8302
- 后端 API：http://localhost:8301

## 配置

- `Single/.env`：覆盖父项目配置，如 `PORT=8301`、`DEBUG=true`
- 数据库、Redis 等仍使用父项目 `TradingAgents/.env`

## 与主项目关系

- **代码复用**：backend 通过 `sys.path` 导入父项目 `app`、`tradingagents`
- **独立运行**：不依赖主项目 `python -m app.main`，在 Single 目录下即可启动
- **主项目**：已移除 Single 模式，单股分析请使用本目录

## 启动命令汇总

```powershell
cd d:\soft\TradingAgents\Single
python run_backend.py          # 后端 8301
npm run dev                    # 前端 8302（新终端）
```

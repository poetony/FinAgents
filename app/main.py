"""
TradingAgents-CN FastAPI Backend
主应用程序入口

参考: D:\dev\TradingAgents-CN-main\app\main.py
"""

# 最先加载 .env，确保 database 等模块能读取到环境变量
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    # 若 Stock_analysis 项目存在，加载其 .env（覆盖 TRADINGAGENTS_RESULTS_DIR 等，使报告存到 Stock_analysis/results）
    _stock_analysis_env = Path(__file__).resolve().parent.parent.parent / "Stock_analysis" / ".env"
    if _stock_analysis_env.exists():
        load_dotenv(_stock_analysis_env, override=True)
except ImportError:
    pass

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from app.core.config import settings
from app.core.database import init_database, close_database


def get_version() -> str:
    """从 VERSION 文件读取版本号"""
    try:
        version_file = Path(__file__).parent.parent / "VERSION"
        if version_file.exists():
            return version_file.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return "1.0.0"


def _register_routers(app: FastAPI) -> None:
    """注册路由（参考 TradingAgents-CN-main 结构，缺失模块时跳过）"""
    router_specs = [
        ("health", "/api", ["health"]),
        ("auth_db", "/api/auth", ["authentication"]),
        ("analysis", "/api/analysis", ["analysis"]),
        ("reports", "", ["reports"]),
        ("screening", "/api/screening", ["screening"]),
        ("queue", "/api/queue", ["queue"]),
        ("favorites", "/api", ["favorites"]),
        ("stocks", "/api", ["stocks"]),
        ("multi_market_stocks", "/api", ["multi-market"]),
        ("stock_data", "", ["stock-data"]),
        ("stock_sync", "", ["stock-sync"]),
        ("tags", "/api", ["tags"]),
        ("config", "/api", ["config"]),
        ("model_capabilities", "", ["model-capabilities"]),
        ("usage_statistics", "", ["usage-statistics"]),
        ("database", "/api/system", ["database"]),
        ("cache", "", ["cache"]),
        ("operation_logs", "/api/system", ["operation_logs"]),
        ("logs", "/api/system", ["logs"]),
        ("system_config", "/api/system", ["system"]),
        ("notifications", "/api", ["notifications"]),
        ("websocket_notifications", "/api", ["websocket"]),
        ("scheduler", "", ["scheduler"]),
        ("sse", "/api/stream", ["streaming"]),
        ("sync", "", ["sync"]),
        ("multi_source_sync", "", ["multi-source-sync"]),
        ("paper", "/api", ["paper"]),
        ("tushare_init", "/api", ["tushare-init"]),
        ("akshare_init", "/api", ["akshare-init"]),
        ("baostock_init", "/api", ["baostock-init"]),
        ("historical_data", "", ["historical-data"]),
        ("multi_period_sync", "", ["multi-period-sync"]),
        ("financial_data", "", ["financial-data"]),
        ("news_data", "", ["news-data"]),
        ("social_media", "", ["social-media"]),
        ("internal_messages", "", ["internal-messages"]),
        ("license", "", ["license"]),
        ("api_stubs", "", ["stubs"]),
    ]
    logger = logging.getLogger("app.main")
    for module_name, prefix, tags in router_specs:
        try:
            mod = __import__(f"app.routers.{module_name}", fromlist=["router"])
            router = getattr(mod, "router", None)
            if router:
                app.include_router(router, prefix=prefix, tags=tags)
                logger.info(f"  Registered: {module_name}")
        except Exception as e:
            logger.debug(f"  Skipped {module_name}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger = logging.getLogger("app.main")

    # 日志配置
    try:
        from app.core.logging_config import setup_logging
        setup_logging()
    except ImportError:
        logging.basicConfig(level=logging.INFO)

    # Redis 集成：若 REDIS_ENABLED 且连接失败，自动尝试启动 Docker 容器
    try:
        from app.utils.redis_launcher import ensure_redis_available
        ensure_redis_available()
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Redis 启动器: {e}")

    # 启动配置验证
    try:
        from app.core.startup_validator import validate_startup_config
        validate_startup_config()
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"配置验证跳过: {e}")

    # 初始化数据库
    try:
        init_database()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database init: {e}")

    # 确保 database_manager 在分析流程前已初始化（UnifiedNewsAnalyzer 依赖 get_db_client）
    try:
        from tradingagents.config.database_manager import get_database_manager
        dm = get_database_manager()
        dm._detect_databases()
        logger.info("DatabaseManager initialized for analysis flow")
    except Exception as e:
        logger.warning(f"DatabaseManager init: {e}")

    # 配置桥接
    try:
        from app.core.config_bridge import bridge_config_to_env
        bridge_config_to_env()
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"配置桥接失败: {e}")

    # 配置摘要
    logger.info("=" * 70)
    logger.info("TradingAgents-CN Configuration Summary")
    logger.info("=" * 70)
    logger.info(f"Environment: {'Production' if settings.is_production else 'Development'}")
    logger.info(f"PostgreSQL: localhost (POSTGRES_ENABLED from .env)")
    logger.info(f"Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}")
    logger.info("=" * 70)
    logger.info("TradingAgents FastAPI backend started")

    try:
        yield
    finally:
        try:
            from app.services.user_service import user_service
            user_service.close()
        except Exception:
            pass
        close_database()
        logger.info("TradingAgents FastAPI backend stopped")


# 创建 FastAPI 应用
app = FastAPI(
    title="TradingAgents-CN API",
    description="股票分析与批量队列系统 API",
    version=get_version(),
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# TrustedHost 中间件（生产环境）
if not settings.DEBUG:
    try:
        from fastapi.middleware.trustedhost import TrustedHostMiddleware
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
    except Exception:
        pass

# CORS 中间件
# 注意：allow_credentials=True 时不能使用 allow_origins=["*"]，需明确指定源
# Single 前端 8302 必须显式加入，否则 CORS 预检失败
_cors_origins = settings.ALLOWED_ORIGINS
if _cors_origins == ["*"] or "*" in _cors_origins:
    _cors_origins = [
        "http://localhost:8302",
        "http://127.0.0.1:8302",
        "http://localhost:8301",
        "http://127.0.0.1:8301",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 操作日志中间件
try:
    from app.middleware.operation_log_middleware import OperationLogMiddleware
    app.add_middleware(OperationLogMiddleware)
except ImportError:
    pass

# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    if request.url.path in ["/health", "/api/health", "/favicon.ico"] or request.url.path.startswith("/static"):
        return await call_next(request)
    webapi_logger = logging.getLogger("webapi")
    webapi_logger.info(f"🔄 {request.method} {request.url.path} - 开始处理")
    response = await call_next(request)
    process_time = time.time() - start_time
    status_emoji = "✅" if response.status_code < 400 else "❌"
    webapi_logger.info(f"{status_emoji} {request.method} {request.url.path} - 状态: {response.status_code} - 耗时: {process_time:.3f}s")
    return response

# RequestID 中间件
try:
    from app.middleware.request_id import RequestIDMiddleware
    app.add_middleware(RequestIDMiddleware)
except ImportError:
    pass

# 占位 API 中间件：在路由之前拦截，确保 workflows/templates 和 model-capabilities/recommend 不再 404/405
from starlette.middleware.base import BaseHTTPMiddleware


class _StubApiMiddleware(BaseHTTPMiddleware):
    """占位 API 中间件：在路由之前拦截，返回空数据，避免 404/500 控制台报错（无登录/轻量模式）"""
    async def dispatch(self, request: Request, call_next):
        path = request.url.path.rstrip("/") or "/"
        method = request.method
        from app.core.response import ok

        # 404 占位
        if path == "/api/workflows/templates" and method == "GET":
            return JSONResponse(content=ok(data=[]))
        if path == "/api/model-capabilities/recommend" and method in ("GET", "POST"):
            return JSONResponse(content=ok(data={
                "quick_model": "qwen-plus", "deep_model": "qwen-max",
                "quick_model_info": {"capability_level": 2, "suitable_roles": [], "features": []},
                "deep_model_info": {"capability_level": 4, "suitable_roles": [], "features": []},
                "reason": "使用默认模型配置",
            }))
        if path == "/api/license/status" and method == "GET":
            return JSONResponse(content=ok(data={
                "plan": "free", "isPro": False, "isTrial": False, "isExpired": False,
                "isExpiringSoon": False, "daysRemaining": None, "isOffline": False,
            }))
        if path == "/api/notifications/unread_count" and method == "GET":
            return JSONResponse(content=ok(data={"count": 0}))
        if path == "/api/analysis/tasks" and method == "GET":
            return JSONResponse(content=ok(data={"tasks": [], "total": 0}))
        if path == "/api/news-data/latest" and method == "GET":
            return JSONResponse(content=ok(data=[]))

        # 500 占位（favorites/paper/sync 在 anonymous 下可能因 DB 失败）
        if path == "/api/favorites" and method == "GET":
            return JSONResponse(content=ok(data=[]))
        if path == "/api/paper/account" and method == "GET":
            return JSONResponse(content=ok(data={
                "user_id": "anonymous",
                "cash": {"CNY": 1000000, "HKD": 1000000, "USD": 100000},
                "positions": [], "realized_pnl": {},
            }))
        if path == "/api/sync/multi-source/status" and method == "GET":
            return JSONResponse(content=ok(data={
                "status": "idle", "last_sync": None, "sources": [],
            }))

        return await call_next(request)


app.add_middleware(_StubApiMiddleware)

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Internal server error occurred",
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )

# 占位接口（在 _register_routers 之前注册，优先匹配，供无登录/轻量模式使用）
from app.routers.auth_db import get_current_user
from app.core.response import ok
from fastapi import Depends
from pydantic import BaseModel

class _RecommendBody(BaseModel):
    research_depth: str = "标准"

@app.get("/api/license/status", include_in_schema=False)
async def _stub_license_status(force_refresh: bool = False, user: dict = Depends(get_current_user)):
    return ok(data={"plan": "free", "isPro": False, "isTrial": False, "isExpired": False, "isExpiringSoon": False, "daysRemaining": None, "isOffline": False})

@app.get("/api/notifications/unread_count", include_in_schema=False)
async def _stub_unread_count(user: dict = Depends(get_current_user)):
    return ok(data={"count": 0})

@app.get("/api/workflows/templates", include_in_schema=False)
async def _stub_workflow_templates(user: dict = Depends(get_current_user)):
    return ok(data=[])

@app.get("/api/analysis/tasks", include_in_schema=False)
async def _stub_analysis_tasks(offset: int = 0, limit: int = 20, user: dict = Depends(get_current_user)):
    return ok(data={"tasks": [], "total": 0})

@app.get("/api/news-data/latest", include_in_schema=False)
async def _stub_news_latest(limit: int = 10, hours_back: int = 24, user: dict = Depends(get_current_user)):
    return ok(data=[])

@app.post("/api/model-capabilities/recommend", include_in_schema=False)
async def _stub_model_recommend(body: _RecommendBody, user: dict = Depends(get_current_user)):
    return ok(data={"quick_model": "qwen-plus", "deep_model": "qwen-max", "quick_model_info": {"capability_level": 2, "suitable_roles": [], "features": []}, "deep_model_info": {"capability_level": 4, "suitable_roles": [], "features": []}, "reason": "使用默认模型配置"})

# WebSocket 占位子应用：必须在 _register_routers 和 spa_fallback 之前挂载，确保优先匹配
import asyncio
from fastapi import WebSocket as _WS, Query as _Q

_ws_app = FastAPI()
@_ws_app.websocket("/notifications")
async def _ws_stub(websocket: _WS, token: str = _Q(default="anonymous")):
    await websocket.accept()
    try:
        await websocket.send_json({"type": "connected", "data": {"user_id": "anonymous" if token == "anonymous" else "user", "message": "WebSocket 连接成功"}})
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if data == "ping":
                    await websocket.send_json({"type": "heartbeat", "data": {}})
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat", "data": {}})
    except Exception:
        pass

app.mount("/api/ws", _ws_app)

# 注册路由
_register_routers(app)

# 前端静态文件（Single 单股分析已迁移至 Single/ 目录，独立运行）
_FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.exists():
    app.mount("/js", StaticFiles(directory=_FRONTEND_DIST / "js"), name="static_js")
    app.mount("/css", StaticFiles(directory=_FRONTEND_DIST / "css"), name="static_css")
    if (_FRONTEND_DIST / "assets").exists():
        app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="static_assets")

    @app.get("/", include_in_schema=False)
    async def root_html():
        """根路径返回前端页面"""
        return FileResponse(_FRONTEND_DIST / "index.html")

    @app.get("/manifest.json", include_in_schema=False)
    async def manifest():
        """PWA manifest"""
        return FileResponse(_FRONTEND_DIST / "manifest.json")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon_spa():
        """favicon（避免 404，需在 catch-all 之前注册）"""
        fp = _FRONTEND_DIST / "favicon.ico"
        if fp.exists():
            return FileResponse(fp)
        from fastapi.responses import Response
        return Response(status_code=204)

    @app.get("/{path:path}", include_in_schema=False)
    async def spa_fallback(path: str):
        """SPA 路由回退：非 API 路径返回 index.html"""
        if path.startswith("api") or path.startswith("docs") or path.startswith("redoc") or path.startswith("openapi"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")
        # 带扩展名的视为静态文件，返回 404 让浏览器正常显示
        if path and "." in path.split("/")[-1]:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(_FRONTEND_DIST / "index.html")
else:
    @app.get("/")
    async def root():
        """根路径（无前端时返回 API 信息）"""
        return {
            "name": "TradingAgents-CN API",
            "version": get_version(),
            "status": "running",
            "docs_url": "/docs" if settings.DEBUG else None,
        }


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """favicon（无前端时）"""
    if _FRONTEND_DIST.exists():
        fp = _FRONTEND_DIST / "favicon.ico"
        if fp.exists():
            return FileResponse(fp)
    from fastapi.responses import Response
    return Response(status_code=204)


@app.get("/health", include_in_schema=False)
async def health_root():
    """根路径健康检查（兼容部分前端直接请求 /health）"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
        reload_dirs=["app"] if settings.DEBUG else None,
        reload_excludes=["__pycache__", "*.pyc", "*.pyo", ".git", "*.log"] if settings.DEBUG else None,
    )

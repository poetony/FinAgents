"""
Single 单股分析 - 独立后端入口
在 Single 目录下运行，复用父项目 app 与 tradingagents
"""

import sys
from pathlib import Path

# 路径设置
_SINGLE_DIR = Path(__file__).resolve().parent.parent
_PARENT_DIR = _SINGLE_DIR.parent

# 添加父项目到 Python 路径
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

# 加载环境变量：先父项目 .env，再 Single .env（覆盖）
try:
    from dotenv import load_dotenv
    load_dotenv(_PARENT_DIR / ".env")
    _single_env = _SINGLE_DIR / ".env"
    if _single_env.exists():
        load_dotenv(_single_env, override=True)
except ImportError:
    pass

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import logging
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_database, close_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    logger = logging.getLogger("single.backend")
    # 确保 .env 在 worker 进程中加载（reload 子进程可能未继承）
    try:
        from dotenv import load_dotenv
        load_dotenv(_PARENT_DIR / ".env")
        if (_SINGLE_DIR / ".env").exists():
            load_dotenv(_SINGLE_DIR / ".env", override=True)
        import os
        if os.getenv("QUANTDB_URL"):
            logger.info("QUANTDB_URL loaded at lifespan")
    except Exception as e:
        logger.warning(f"lifespan dotenv: {e}")
    try:
        from app.core.logging_config import setup_logging
        setup_logging()
    except ImportError:
        logging.basicConfig(level=logging.INFO)

    try:
        init_database()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database init: {e}")

    logger.info("Single 单股分析后端启动")
    try:
        yield
    finally:
        close_database()
        logger.info("Single 单股分析后端停止")


app = FastAPI(
    title="Single 单股分析 API",
    description="单股分析精简后端",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS：前端 8302 必须显式加入
_CORS_ORIGINS = [
    "http://localhost:8302",
    "http://127.0.0.1:8302",
    "http://localhost:8301",
    "http://127.0.0.1:8301",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_SERVER_ERROR", "message": str(exc)}},
    )


# 注册路由：仅单股分析所需
from app.routers.auth_db import router as auth_router, get_current_user
from app.routers.analysis import router as analysis_router

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(analysis_router, prefix="/api/analysis", tags=["analysis"])


# 健康检查
@app.get("/health")
async def health():
    return {"status": "ok"}


# 调试：测试数据获取（验证 quantdb 在 API 上下文中可用）
@app.get("/api/debug/fetch-000536")
async def debug_fetch_data():
    """测试 000536 数据获取，用于排查 quantdb 在 API 进程中是否可用"""
    import os
    from tradingagents.dataflows.interface import get_china_stock_data_unified
    from datetime import datetime, timedelta
    qurl = os.getenv("QUANTDB_URL", "")
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    try:
        r = get_china_stock_data_unified("000536", start, end)
        ok = r and "❌" not in r and "获取失败" not in r
        return {"QUANTDB_URL_set": bool(qurl), "success": ok, "len": len(r) if r else 0, "preview": (r[:200] + "...") if r else None}
    except Exception as e:
        return {"QUANTDB_URL_set": bool(qurl), "success": False, "error": str(e)}


# 前端静态文件：开发时由 Vite 8302 提供，生产可挂载 dist
_FRONTEND_DIST = _SINGLE_DIR / "dist"
if _FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    async def root():
        return FileResponse(_FRONTEND_DIST / "index.html")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa_fallback(path: str):
        if path.startswith("api") or path.startswith("health"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")
        if path and "." in path.split("/")[-1]:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(_FRONTEND_DIST / "index.html")
else:
    @app.get("/", include_in_schema=False)
    async def root():
        return {"message": "Single 单股分析 API", "frontend": "http://localhost:8302", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    port = int(getattr(settings, "PORT", 8301))
    # 直接运行本文件时使用 __main__:app
    uvicorn.run(
        "__main__:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
    )

#!/usr/bin/env python3
"""
Single 单股分析 - 后端启动脚本
在 Single 目录下执行: python run_backend.py
"""
import sys
from pathlib import Path

SINGLE_DIR = Path(__file__).resolve().parent
PARENT_DIR = SINGLE_DIR.parent

# 添加父项目到路径
sys.path.insert(0, str(PARENT_DIR))
# 添加 Single 到路径（用于 backend 模块）
sys.path.insert(0, str(SINGLE_DIR))

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv(PARENT_DIR / ".env")
    if (SINGLE_DIR / ".env").exists():
        load_dotenv(SINGLE_DIR / ".env", override=True)
except ImportError:
    pass

import uvicorn

if __name__ == "__main__":
    from app.core.config import settings
    port = int(getattr(settings, "PORT", 8301))
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
    )

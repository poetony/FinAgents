#!/usr/bin/env python3
"""
分析流程环境变量加载
参考 TradingAgents-main：在数据获取时确保 os.getenv 能读到 API Key
解决后端全流程分析中「单独测试数据源正常、流程中取不到数据」的问题
"""
import os
from pathlib import Path


def ensure_analysis_env_loaded():
    """
    确保美股/新闻等 API Key 在分析流程中可用。
    在 uvicorn reload 子进程、ThreadPoolExecutor 线程等场景下，
    显式从已知路径加载 .env，避免 env 未继承导致 os.getenv 返回空。

    加载顺序：先加载通用/默认 env，最后加载 Stock_analysis/.env 以覆盖，
    保证 D:\\soft\\Stock_analysis\\.env 中的 API Key 生效。
    """
    try:
        _here = Path(__file__).resolve().parent
        _root = _here.parent.parent  # utils -> tradingagents -> TradingAgents
        _parent = _root.parent       # 父目录 d:/soft

        # 顺序：通用 -> TradingAgents -> Stock_analysis（最后加载以覆盖）
        candidates = [
            _parent / ".env",
            _root / ".env",
            _parent / "Stock_analysis" / ".env",
        ]
        from dotenv import load_dotenv
        for env_path in candidates:
            if env_path.exists():
                try:
                    load_dotenv(env_path, override=True)
                except Exception:
                    pass
    except Exception:
        pass


# 向后兼容：历史代码可能调用此名称，统一指向 ensure_analysis_env_loaded
def _ensure_us_stock_env_loaded():
    """Deprecated alias. Use ensure_analysis_env_loaded instead."""
    return ensure_analysis_env_loaded()

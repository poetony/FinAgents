#!/usr/bin/env python3
"""
QuantDB 数据提供器
从 quantdb.daily_bars 和 quantdb.securities 读取 A 股历史数据
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any

# 确保加载 .env（支持从不同工作目录启动）
def _ensure_env_loaded():
    if os.getenv("QUANTDB_URL") or os.getenv("QUANTDB_DATABASE"):
        return
    for base in [Path(__file__).resolve().parents[5], Path(__file__).resolve().parents[4], Path.cwd()]:
        env_file = base / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
                break
            except ImportError:
                pass
from urllib.parse import quote_plus
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def _get_quantdb_conn_str() -> str:
    """获取 quantdb 连接字符串"""
    _ensure_env_loaded()
    url = os.getenv("QUANTDB_URL")
    if url:
        return url
    host = os.getenv("QUANTDB_HOST", os.getenv("POSTGRES_HOST", "localhost"))
    port = os.getenv("QUANTDB_PORT", os.getenv("POSTGRES_PORT", "5432"))
    user = os.getenv("QUANTDB_USER", os.getenv("POSTGRES_USER", "postgres"))
    password = os.getenv("QUANTDB_PASSWORD", os.getenv("POSTGRES_PASSWORD", ""))
    database = os.getenv("QUANTDB_DATABASE", "quantdb")
    if password:
        pw = quote_plus(str(password))
        return f"postgresql://{user}:{pw}@{host}:{port}/{database}"
    return f"postgresql://{user}@{host}:{port}/{database}"


def _normalize_code(code: str) -> str:
    """标准化为 6 位代码"""
    s = str(code).strip()
    if "." in s:
        s = s.split(".")[0]
    return s.zfill(6) if len(s) <= 6 else s[-6:]


def get_stock_data(symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """
    从 quantdb.daily_bars 获取股票日线数据

    Args:
        symbol: 6 位股票代码（如 000536）
        start_date: 开始日期 YYYY-MM-DD
        end_date: 结束日期 YYYY-MM-DD

    Returns:
        DataFrame 含 date, open, high, low, close, volume，若无数据返回 None
    """
    try:
        import psycopg2

        code6 = _normalize_code(symbol)
        conn_str = _get_quantdb_conn_str()
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()

        # ts_code 可能是 000536 或 000536.SZ，两种都试
        for try_code in (code6, f"{code6}.SZ" if code6.startswith(("0", "3")) else f"{code6}.SH"):
            cur.execute(
                """
                SELECT ts_code, trade_date, open, high, low, close,
                       COALESCE(volume, 0)::bigint as volume,
                       COALESCE(amount, 0) as amount
                FROM daily_bars
                WHERE ts_code = %s
                  AND trade_date >= %s
                  AND trade_date <= %s
                ORDER BY trade_date ASC
                """,
                (try_code, start_date, end_date),
            )
            rows = cur.fetchall()
            if rows:
                break
        conn.close()

        if not rows:
            logger.warning(f"[QuantDB] 未找到 {symbol} 在 {start_date}~{end_date} 的数据")
            return None

        df = pd.DataFrame(
            rows,
            columns=["ts_code", "trade_date", "open", "high", "low", "close", "volume", "amount"],
        )
        # 统一 date 列格式 YYYY-MM-DD（兼容 date 或 YYYYMMDD 整数）
        td = df["trade_date"].astype(str).str.replace("-", "")
        df["date"] = pd.to_datetime(td, format="%Y%m%d", errors="coerce").dt.strftime("%Y-%m-%d")
        df["vol"] = df["volume"]
        logger.info(f"[QuantDB] 获取 {symbol} 数据 {len(df)} 条")
        return df

    except Exception as e:
        logger.error(f"[QuantDB] 获取 {symbol} 数据失败: {e}", exc_info=True)
        return None


def get_stock_info(symbol: str) -> Optional[Dict[str, Any]]:
    """
    从 quantdb.securities 获取股票基本信息

    Args:
        symbol: 6 位股票代码

    Returns:
        {"symbol": str, "name": str, "industry": str, ...} 或 None
    """
    try:
        import psycopg2

        code6 = _normalize_code(symbol)
        conn_str = _get_quantdb_conn_str()
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()

        for try_code in (code6, f"{code6}.SZ" if code6.startswith(("0", "3")) else f"{code6}.SH"):
            cur.execute(
                "SELECT ts_code, name, industry, list_date, market FROM securities WHERE ts_code = %s",
                (try_code,),
            )
            row = cur.fetchone()
            if row:
                break
        conn.close()

        if not row:
            logger.warning(f"[QuantDB] 未找到 {symbol} 的基本信息")
            return None

        return {
            "symbol": str(row[0]).split(".")[0] if "." in str(row[0]) else str(row[0]),
            "name": row[1] or f"股票{symbol}",
            "industry": row[2] or "未知",
            "list_date": str(row[3]) if row[3] else "",
            "exchange": "SZ" if code6.startswith(("0", "3")) else "SH",
        }

    except Exception as e:
        logger.error(f"[QuantDB] 获取 {symbol} 基本信息失败: {e}", exc_info=True)
        return None


def get_quantdb_provider():
    """获取 QuantDB 提供器（兼容 data_source_manager 调用风格）"""
    class QuantDBProvider:
        def get_stock_data(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
            return get_stock_data(symbol, start_date, end_date)

        def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
            return get_stock_info(symbol)

    return QuantDBProvider()

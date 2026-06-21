"""
Database status and connection checks, extracted from DatabaseService.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

import os
from app.core.database import get_redis_client, get_connection_context
from app.core.config import settings


def _get_postgres_status_sync() -> Dict[str, Any]:
    """同步获取 PostgreSQL 状态"""
    try:
        with get_connection_context() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
                cur.execute("SELECT version()")
                row = cur.fetchone()
                version = row.get("version", "Unknown") if row else "Unknown"
        return {
            "connected": True,
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", "5432")),
            "database": os.getenv("POSTGRES_DATABASE", "tradingagents"),
            "version": version,
            "connected_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", "5432")),
            "database": os.getenv("POSTGRES_DATABASE", "tradingagents"),
        }


async def get_postgres_status() -> Dict[str, Any]:
    """获取 PostgreSQL 状态"""
    import asyncio
    return await asyncio.to_thread(_get_postgres_status_sync)


async def get_redis_status() -> Dict[str, Any]:
    try:
        redis_client = get_redis_client()
        await redis_client.ping()
        info = await redis_client.info()
        return {
            "connected": True,
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
            "database": settings.REDIS_DB,
            "version": info.get("redis_version", "Unknown"),
            "uptime": info.get("uptime_in_seconds", 0),
            "memory_used": info.get("used_memory", 0),
            "memory_peak": info.get("used_memory_peak", 0),
            "connected_clients": info.get("connected_clients", 0),
            "total_commands": info.get("total_commands_processed", 0),
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
            "database": settings.REDIS_DB,
        }


async def get_database_status() -> Dict[str, Any]:
    postgres_status = await get_postgres_status()
    redis_status = await get_redis_status()
    return {"postgres": postgres_status, "redis": redis_status}


async def test_postgres_connection() -> Dict[str, Any]:
    try:
        import asyncio
        def _ping():
            with get_connection_context() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
        start = datetime.utcnow()
        await asyncio.to_thread(_ping)
        took_ms = (datetime.utcnow() - start).total_seconds() * 1000
        return {"success": True, "response_time_ms": round(took_ms, 2), "message": "PostgreSQL连接正常"}
    except Exception as e:
        return {"success": False, "error": str(e), "message": "PostgreSQL连接失败"}


async def test_redis_connection() -> Dict[str, Any]:
    try:
        redis_client = get_redis_client()
        start = datetime.utcnow()
        await redis_client.ping()
        took_ms = (datetime.utcnow() - start).total_seconds() * 1000
        return {"success": True, "response_time_ms": round(took_ms, 2), "message": "Redis连接正常"}
    except Exception as e:
        return {"success": False, "error": str(e), "message": "Redis连接失败"}


async def test_connections() -> Dict[str, Any]:
    postgres = await test_postgres_connection()
    redis = await test_redis_connection()
    return {"postgres": postgres, "redis": redis, "overall": postgres["success"] and redis["success"]}


# 兼容旧 API 名称
async def get_mongodb_status() -> Dict[str, Any]:
    """已废弃，请使用 get_postgres_status"""
    return await get_postgres_status()


async def test_mongodb_connection() -> Dict[str, Any]:
    """已废弃，请使用 test_postgres_connection"""
    return await test_postgres_connection()
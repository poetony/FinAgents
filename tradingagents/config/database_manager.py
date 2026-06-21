#!/usr/bin/env python3
"""
智能数据库管理器
仅使用 PostgreSQL（QuantDB / tradingagents），MongoDB 已完全移除
"""

import logging
import os
from typing import Dict, Any, Optional, Tuple

class DatabaseManager:
    """智能数据库管理器 - PostgreSQL 专用"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._load_env_config()

        self.postgres_available = False
        self.postgres_client = None
        self.redis_available = False
        self.redis_client = None

        self._detect_databases()
        self._initialize_connections()

        db_status = []
        if self.postgres_available:
            db_status.append("PostgreSQL")
        db_status.append(f"Redis: {self.redis_available}")
        self.logger.info(f"数据库管理器初始化完成 - {', '.join(db_status)}")

    def _load_env_config(self):
        """从.env文件加载配置"""
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            self.logger.info("python-dotenv未安装，直接读取环境变量")

        from .env_utils import parse_bool_env
        self.postgres_enabled = parse_bool_env("POSTGRES_ENABLED", False) or bool(os.getenv("POSTGRES_HOST"))
        self.redis_enabled = parse_bool_env("REDIS_ENABLED", False)

        self.db_config = {
            "database": os.getenv("POSTGRES_DATABASE", "tradingagents"),
        }

        self.redis_config = {
            "enabled": self.redis_enabled,
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": os.getenv("REDIS_PORT", "6379"),
            "password": os.getenv("REDIS_PASSWORD"),
            "db": int(os.getenv("REDIS_DB", "0")),
            "timeout": 2
        }

        self.logger.info(f"PostgreSQL 启用: {self.postgres_enabled}")
        self.logger.info(f"Redis 启用: {self.redis_enabled}")

    def _detect_postgres(self) -> Tuple[bool, str]:
        """检测 PostgreSQL 是否可用"""
        if not self.postgres_enabled:
            return False, "PostgreSQL未启用 (POSTGRES_ENABLED=false 且未设置 POSTGRES_HOST)"
        try:
            from app.core.database import _get_connection
            conn = _get_connection()
            conn.close()
            return True, "PostgreSQL连接成功"
        except ImportError as e:
            return False, f"psycopg2未安装: {e}"
        except Exception as e:
            return False, f"PostgreSQL连接失败: {str(e)}"

    def _detect_redis(self) -> Tuple[bool, str]:
        """检测Redis是否可用"""
        if not self.redis_enabled:
            return False, "Redis未启用 (REDIS_ENABLED=false)"
        try:
            import redis
            connect_kwargs = {
                "host": self.redis_config["host"],
                "port": int(self.redis_config["port"]),
                "db": self.redis_config["db"],
                "socket_timeout": self.redis_config["timeout"],
                "socket_connect_timeout": self.redis_config["timeout"]
            }
            if self.redis_config["password"]:
                connect_kwargs["password"] = self.redis_config["password"]
            client = redis.Redis(**connect_kwargs)
            client.ping()
            return True, "Redis连接成功"
        except ImportError:
            return False, "redis未安装"
        except Exception as e:
            return False, f"Redis连接失败: {str(e)}"

    def _detect_databases(self):
        """检测数据库可用性"""
        self.logger.info("开始检测数据库可用性...")

        postgres_available, postgres_msg = self._detect_postgres()
        self.postgres_available = postgres_available
        if postgres_available:
            self.logger.info(f"✅ PostgreSQL: {postgres_msg}")
        else:
            self.logger.info(f"❌ PostgreSQL: {postgres_msg}")

        redis_available, redis_msg = self._detect_redis()
        self.redis_available = redis_available
        if redis_available:
            self.logger.info(f"✅ Redis: {redis_msg}")
        else:
            self.logger.info(f"❌ Redis: {redis_msg}")

        self._update_config_based_on_detection()

    def _update_config_based_on_detection(self):
        """根据检测结果更新配置"""
        if self.redis_available:
            self.primary_backend = "redis"
        elif self.postgres_available:
            self.primary_backend = "postgres"
        else:
            self.primary_backend = "file"
        self.logger.info(f"主要缓存后端: {self.primary_backend}")

    def _initialize_connections(self):
        """初始化数据库连接"""
        if self.postgres_available:
            try:
                from app.core.database import get_postgres_client_compat
                self.postgres_client = get_postgres_client_compat()
                self.logger.info("PostgreSQL 客户端初始化成功")
            except Exception as e:
                self.logger.error(f"PostgreSQL 客户端初始化失败: {e}")
                self.postgres_available = False

        if self.redis_available:
            try:
                import redis
                connect_kwargs = {
                    "host": self.redis_config["host"],
                    "port": int(self.redis_config["port"]),
                    "db": self.redis_config["db"],
                    "socket_timeout": self.redis_config["timeout"]
                }
                if self.redis_config["password"]:
                    connect_kwargs["password"] = self.redis_config["password"]
                self.redis_client = redis.Redis(**connect_kwargs)
                self.logger.info("Redis客户端初始化成功")
            except Exception as e:
                self.logger.error(f"Redis客户端初始化失败: {e}")
                self.redis_available = False

    @property
    def mongodb_config(self) -> Dict[str, Any]:
        """兼容旧 API（app_adapter 等）：返回数据库配置，MongoDB 已移除"""
        return {"database": self.db_config.get("database", "tradingagents")}

    def get_db_client(self):
        """获取数据库客户端（PostgreSQL）"""
        if self.postgres_available and self.postgres_client:
            return self.postgres_client
        return None

    def get_db(self):
        """获取数据库实例"""
        if self.postgres_available and self.postgres_client:
            return self.postgres_client.tradingagents
        return None

    def get_mongodb_client(self):
        """兼容旧 API：返回 PostgreSQL 客户端（MongoDB 已移除）"""
        return self.get_db_client()

    def get_mongodb_db(self):
        """兼容旧 API：返回数据库实例"""
        return self.get_db()

    def get_redis_client(self):
        """获取Redis客户端"""
        if self.redis_available and self.redis_client:
            return self.redis_client
        return None

    def is_db_available(self) -> bool:
        """检查 PostgreSQL 数据库是否可用"""
        return self.postgres_available

    def is_mongodb_available(self) -> bool:
        """[已弃用] 请使用 is_db_available()"""
        return self.is_db_available()

    def is_redis_available(self) -> bool:
        """检查Redis是否可用"""
        return self.redis_available

    def is_database_available(self) -> bool:
        """检查是否有任何数据库可用"""
        return self.postgres_available or self.redis_available

    def get_cache_backend(self) -> str:
        """获取当前缓存后端"""
        return self.primary_backend

    def get_config(self) -> Dict[str, Any]:
        """获取配置信息"""
        return {
            "postgres": self.db_config,
            "redis": self.redis_config,
            "primary_backend": self.primary_backend,
            "postgres_available": self.postgres_available,
            "redis_available": self.redis_available,
            "cache": {
                "primary_backend": self.primary_backend,
                "fallback_enabled": True,
                "ttl_settings": {
                    "us_stock_data": 7200,
                    "us_news": 21600,
                    "us_fundamentals": 86400,
                    "china_stock_data": 3600,
                    "china_news": 14400,
                    "china_fundamentals": 43200,
                }
            }
        }

    def get_status_report(self) -> Dict[str, Any]:
        """获取状态报告"""
        return {
            "database_available": self.is_database_available(),
            "postgres": {
                "available": self.postgres_available,
                "database": self.db_config.get("database", "tradingagents"),
            },
            "redis": {
                "available": self.redis_available,
                "host": self.redis_config["host"],
                "port": self.redis_config["port"]
            },
            "cache_backend": self.get_cache_backend(),
            "fallback_enabled": True
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        stats = {
            "postgres_available": self.postgres_available,
            "redis_available": self.redis_available,
            "redis_keys": 0,
            "redis_memory": "N/A"
        }
        if self.redis_available and self.redis_client:
            try:
                info = self.redis_client.info()
                stats["redis_keys"] = self.redis_client.dbsize()
                stats["redis_memory"] = info.get("used_memory_human", "N/A")
            except Exception as e:
                self.logger.error(f"获取Redis统计失败: {e}")
        return stats

    def cache_clear_pattern(self, pattern: str) -> int:
        """清理匹配模式的缓存"""
        cleared_count = 0
        if self.redis_available and self.redis_client:
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    cleared_count += self.redis_client.delete(*keys)
            except Exception as e:
                self.logger.error(f"Redis缓存清理失败: {e}")
        return cleared_count


_database_manager = None

def get_database_manager() -> DatabaseManager:
    """获取全局数据库管理器实例"""
    global _database_manager
    if _database_manager is None:
        _database_manager = DatabaseManager()
    return _database_manager

def is_redis_available() -> bool:
    """检查Redis是否可用"""
    return get_database_manager().is_redis_available()

def get_cache_backend() -> str:
    """获取当前缓存后端"""
    return get_database_manager().get_cache_backend()

def get_db_client():
    """获取数据库客户端（PostgreSQL）"""
    return get_database_manager().get_db_client()


def get_db():
    """获取数据库实例（PostgreSQL）"""
    return get_database_manager().get_db()


def is_db_available() -> bool:
    """检查数据库是否可用（PostgreSQL）"""
    return get_database_manager().postgres_available


# 兼容旧 API（已弃用，请使用 get_db_client / get_db / is_db_available）
def get_mongodb_client():
    """[已弃用] 请使用 get_db_client()"""
    return get_db_client()


def is_mongodb_available() -> bool:
    """[已弃用] 请使用 is_db_available()"""
    return is_db_available()


def get_mongodb_db():
    """[已弃用] 请使用 get_db()"""
    return get_db()

def get_redis_client():
    """获取Redis客户端"""
    return get_database_manager().get_redis_client()

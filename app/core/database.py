#!/usr/bin/env python3
"""
PostgreSQL 数据库连接模块
提供类 MongoDB 的文档接口（find/find_one/insert_one 等）
使用 JSONB 存储文档数据，保持 schema 灵活性
"""

import asyncio
import os
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# PostgreSQL 连接配置
_POSTGRES_CONFIG = None


def _get_postgres_config() -> Dict[str, Any]:
    """获取 PostgreSQL 配置"""
    global _POSTGRES_CONFIG
    if _POSTGRES_CONFIG is not None:
        return _POSTGRES_CONFIG

    # 优先使用连接字符串
    conn_str = os.getenv("POSTGRES_CONNECTION_STRING")
    if conn_str:
        _POSTGRES_CONFIG = {
            "connection_string": conn_str,
            "host": "localhost",
            "port": 5432,
            "database": "tradingagents",
        }
        return _POSTGRES_CONFIG

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "")
    database = os.getenv("POSTGRES_DATABASE", "tradingagents")

    # 构建连接字符串（用于需要 DSN 的场景）
    from urllib.parse import quote_plus
    if password:
        encoded_password = quote_plus(str(password))
        conn_str = f"postgresql://{user}:{encoded_password}@{host}:{port}/{database}"
    else:
        conn_str = f"postgresql://{user}@{host}:{port}/{database}"

    _POSTGRES_CONFIG = {
        "connection_string": conn_str,
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
    }
    return _POSTGRES_CONFIG


def _ensure_database_exists():
    """确保目标数据库存在，若不存在则创建"""
    config = _get_postgres_config()
    dbname = config.get("database", "tradingagents")
    if "user" not in config:
        return
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        conn = psycopg2.connect(
            host=config.get("host", "localhost"),
            port=config.get("port", 5432),
            user=config.get("user", "postgres"),
            password=config.get("password", ""),
            dbname="postgres",
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (dbname,),
            )
            if cur.fetchone() is None:
                cur.execute(f'CREATE DATABASE "{dbname}"')
                logger.info(f"已创建数据库: {dbname}")
        conn.close()
    except Exception as e:
        logger.warning(f"创建数据库时出错（可能已存在）: {e}")


def _get_connection():
    """获取 PostgreSQL 连接"""
    import psycopg2
    from psycopg2.extras import RealDictCursor

    config = _get_postgres_config()
    if "user" in config and "password" in config:
        _ensure_database_exists()
        conn = psycopg2.connect(
            host=config.get("host", "localhost"),
            port=config.get("port", 5432),
            user=config.get("user", "postgres"),
            password=config.get("password", ""),
            dbname=config.get("database", "tradingagents"),
            cursor_factory=RealDictCursor,
            options="-c client_encoding=UTF8",
        )
    else:
        conn = psycopg2.connect(
            config["connection_string"],
            cursor_factory=RealDictCursor,
        )
    return conn


@contextmanager
def get_connection_context():
    """获取数据库连接上下文"""
    conn = _get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class _AsyncCursorIterator:
    """PostgresCursor 的异步迭代器包装，兼容 async for"""

    def __init__(self, cursor: "PostgresCursor"):
        self._cursor = cursor
        self._result = None
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._result is None:
            self._result = await self._cursor.to_list(length=None)
        if self._index >= len(self._result):
            raise StopAsyncIteration
        doc = self._result[self._index]
        self._index += 1
        return doc


class PostgresCursor:
    """MongoDB 风格的游标，支持 .sort().limit() 链式调用"""

    def __init__(
        self,
        collection: "PostgresCollectionProxy",
        filter_dict: Dict,
        projection: Optional[Dict] = None,
        sort: Optional[List[Tuple[str, int]]] = None,
        limit: Optional[int] = None,
    ):
        self.collection = collection
        self.filter_dict = filter_dict
        self.projection = projection
        self._sort = sort or []
        self._limit = limit

    def sort(self, key_or_list, direction: Optional[int] = None) -> "PostgresCursor":
        """链式 sort 调用"""
        if isinstance(key_or_list, (list, tuple)):
            self._sort = key_or_list
        else:
            self._sort = [(key_or_list, direction or 1)]
        return self

    def limit(self, n: int) -> "PostgresCursor":
        """链式 limit 调用"""
        self._limit = n
        return self

    async def to_list(self, length: Optional[int] = None) -> List[Dict]:
        """兼容 MongoDB Motor 游标：将迭代结果转为列表（异步，避免阻塞）"""
        result = await asyncio.to_thread(lambda: list(self))
        if length is not None and length >= 0:
            return result[:length]
        return result

    def __aiter__(self):
        """兼容 async for：支持 [x async for x in cursor]"""
        return _AsyncCursorIterator(self)

    def __iter__(self):
        with get_connection_context() as conn:
            with conn.cursor() as cur:
                where_sql, where_values = self.collection._filter_to_sql(self.filter_dict)
                order_parts = []
                for field, direction in self._sort:
                    direction_str = "DESC" if direction == -1 else "ASC"
                    order_parts.append(f"data->>'{field}' {direction_str}")
                order_sql = " ORDER BY " + ", ".join(order_parts) if order_parts else ""
                limit_sql = f" LIMIT {self._limit}" if self._limit else ""
                sql = f"""
                    SELECT data FROM pg_doc_{self.collection.table_name}
                    WHERE {where_sql}
                    {order_sql}
                    {limit_sql}
                """
                cur.execute(sql, where_values)
                for row in cur.fetchall():
                    if row and row.get("data"):
                        doc = row["data"] if isinstance(row["data"], dict) else json.loads(row["data"])
                        if self.projection and self.projection.get("_id", 0) == 0:
                            doc.pop("_id", None)
                        yield doc


class PostgresCollectionProxy:
    """
    MongoDB 风格的集合代理
    将 find_one, find 等操作转换为 PostgreSQL 查询
    使用 JSONB 存储文档
    """

    def __init__(self, table_name: str, db: "PostgresDBCompat"):
        self.table_name = table_name
        self.db = db

    def _filter_to_sql(self, filter_dict: Dict) -> Tuple[str, List]:
        """将 MongoDB 风格 filter 转换为 SQL WHERE 子句"""
        if not filter_dict:
            return "TRUE", []

        conditions = []
        values = []
        for i, (key, val) in enumerate(filter_dict.items()):
            if key == "_id":
                # ObjectId 或普通 id
                if isinstance(val, dict):
                    # $in, $eq 等操作符暂不处理
                    continue
                conditions.append("(data->>'id')::text = %s OR data->>'_id' = %s")
                values.extend([str(val), str(val)])
            elif isinstance(val, dict):
                # MongoDB 操作符
                for op, op_val in val.items():
                    if op == "$eq":
                        conditions.append(f"data->>%s = %s")
                        values.extend([key, str(op_val)])
                    elif op == "$in":
                        placeholders = ", ".join(["%s"] * len(op_val))
                        conditions.append(f"data->>%s IN ({placeholders})")
                        values.extend([key] + [str(v) for v in op_val])
                    elif op == "$lt":
                        conditions.append(f"data->>%s < %s")
                        values.extend([key, str(op_val)])
                    elif op == "$lte":
                        conditions.append(f"data->>%s <= %s")
                        values.extend([key, str(op_val)])
                    elif op == "$gt":
                        conditions.append(f"data->>%s > %s")
                        values.extend([key, str(op_val)])
                    elif op == "$gte":
                        conditions.append(f"data->>%s >= %s")
                        values.extend([key, str(op_val)])
                    elif op == "$ne":
                        conditions.append(f"data->>%s != %s")
                        values.extend([key, str(op_val)])
            else:
                # 简单相等（布尔值在 JSONB 中为 true/false 小写）
                if isinstance(val, bool):
                    val = "true" if val else "false"
                else:
                    val = str(val)
                conditions.append(f"data->>%s = %s")
                values.extend([key, val])

        if not conditions:
            return "TRUE", []
        return " AND ".join(conditions), values

    def find_one(
        self,
        filter_dict: Optional[Dict] = None,
        projection: Optional[Dict] = None,
        sort: Optional[List[Tuple[str, int]]] = None,
    ) -> Optional[Dict]:
        """查找单条文档"""
        filter_dict = filter_dict or {}
        with get_connection_context() as conn:
            with conn.cursor() as cur:
                where_sql, where_values = self._filter_to_sql(filter_dict)
                order_sql = ""
                if sort:
                    order_parts = []
                    for field, direction in sort:
                        direction_str = "DESC" if direction == -1 else "ASC"
                        order_parts.append(f"data->>'{field}' {direction_str}")
                    order_sql = " ORDER BY " + ", ".join(order_parts)
                sql = f"""
                    SELECT data FROM pg_doc_{self.table_name}
                    WHERE {where_sql}
                    {order_sql}
                    LIMIT 1
                """
                cur.execute(sql, where_values)
                row = cur.fetchone()
                if row and row.get("data"):
                    doc = row["data"] if isinstance(row["data"], dict) else json.loads(row["data"])
                    if projection and "_id" not in projection and projection.get("_id", 0) == 0:
                        doc.pop("_id", None)
                    return doc
                return None

    def find(
        self,
        filter_dict: Optional[Dict] = None,
        projection: Optional[Dict] = None,
        sort: Optional[List[Tuple[str, int]]] = None,
        limit: Optional[int] = None,
    ):
        """查找多条文档，返回游标风格对象（支持 .sort().limit() 链式调用）"""
        return PostgresCursor(self, filter_dict or {}, projection, sort, limit)

    def insert_one(self, document: Dict) -> Any:
        """插入单条文档"""
        import uuid
        doc_id = str(document.get("_id") or document.get("id") or uuid.uuid4())
        if "_id" not in document:
            document["_id"] = doc_id
        with get_connection_context() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO pg_doc_{self.table_name} (id, data)
                    VALUES (%s, %s)
                    ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data, updated_at = NOW()
                    """,
                    (doc_id, json.dumps(document, default=str)),
                )
        return type("InsertResult", (), {"inserted_id": doc_id})()

    def replace_one(self, filter_dict: Dict, document: Dict, upsert: bool = False) -> Any:
        """替换文档"""
        row_id = str(filter_dict.get("_id") or filter_dict.get("id") or "")
        if not row_id:
            existing = self.find_one(filter_dict)
            if existing:
                row_id = str(existing.get("_id") or existing.get("id"))
        if "_id" not in document and row_id:
            document["_id"] = row_id
        if row_id:
            with get_connection_context() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        UPDATE pg_doc_{self.table_name}
                        SET data = %s, updated_at = NOW()
                        WHERE id = %s
                        """,
                        (json.dumps(document, default=str), row_id),
                    )
                    if cur.rowcount > 0:
                        return type("UpdateResult", (), {"modified_count": 1})()
        if upsert:
            self.insert_one(document)
        return type("UpdateResult", (), {"modified_count": 1})()

    def update_one(self, filter_dict: Dict, update: Dict, upsert: bool = False) -> Any:
        """更新单条文档"""
        existing = self.find_one(filter_dict)
        if existing:
            doc = dict(existing)
            if "$set" in update:
                doc.update(update["$set"])
            self.replace_one(filter_dict, doc)
            return type("UpdateResult", (), {"modified_count": 1})()
        elif upsert:
            self.insert_one(update.get("$set", {}))
            return type("UpdateResult", (), {"modified_count": 0, "upserted_id": None})()
        return type("UpdateResult", (), {"modified_count": 0})()

    def update_many(self, filter_dict: Dict, update: Dict, upsert: bool = False) -> Any:
        """更新多条文档"""
        modified_count = 0
        cursor = self.find(filter_dict)
        for doc in cursor:
            existing = dict(doc)
            if "$set" in update:
                existing.update(update["$set"])
            self.replace_one({"_id": existing.get("_id"), "id": existing.get("id")}, existing)
            modified_count += 1
        return type("UpdateResult", (), {"modified_count": modified_count})()

    def delete_one(self, filter_dict: Dict) -> Any:
        """删除单条文档"""
        with get_connection_context() as conn:
            with conn.cursor() as cur:
                where_sql, where_values = self._filter_to_sql(filter_dict)
                cur.execute(
                    f"DELETE FROM pg_doc_{self.table_name} WHERE {where_sql}",
                    where_values,
                )
                return type("DeleteResult", (), {"deleted_count": cur.rowcount})()

    def delete_many(self, filter_dict: Dict) -> Any:
        """删除多条文档"""
        with get_connection_context() as conn:
            with conn.cursor() as cur:
                where_sql, where_values = self._filter_to_sql(filter_dict)
                cur.execute(
                    f"DELETE FROM pg_doc_{self.table_name} WHERE {where_sql}",
                    where_values,
                )
                return type("DeleteResult", (), {"deleted_count": cur.rowcount})()

    def create_index(self, keys: List[Tuple[str, int]], **kwargs) -> str:
        """创建索引（PostgreSQL 下为 no-op，已通过 GIN 索引支持 JSONB 查询）"""
        return "pg_index_placeholder"

    def count_documents(self, filter_dict: Optional[Dict] = None) -> int:
        """统计文档数量"""
        filter_dict = filter_dict or {}
        with get_connection_context() as conn:
            with conn.cursor() as cur:
                where_sql, where_values = self._filter_to_sql(filter_dict)
                cur.execute(
                    f"SELECT COUNT(*) as cnt FROM pg_doc_{self.table_name} WHERE {where_sql}",
                    where_values,
                )
                row = cur.fetchone()
                return row["cnt"] or 0

    async def bulk_write(self, operations: List, ordered: bool = True) -> Any:
        """批量写入（异步），兼容 pymongo UpdateOne/ReplaceOne"""
        return await asyncio.to_thread(self._bulk_write_sync, operations, ordered)

    def bulk_write_sync(self, operations: List, ordered: bool = True) -> Any:
        """批量写入（同步），供 save_news_data_sync 等同步调用方使用"""
        return self._bulk_write_sync(operations, ordered)

    def _bulk_write_sync(self, operations: List, ordered: bool = True) -> Any:
        """批量写入（同步实现）"""
        modified_count = 0
        upserted_count = 0
        upserted_ids = []
        for op in operations:
            # pymongo ReplaceOne 使用 _filter, _doc, _upsert；兼容 filter/replacement
            f = getattr(op, "_filter", None) or getattr(op, "filter", None)
            if f is None and isinstance(op, dict):
                f = op.get("filter", {})
            f = f or {}
            upsert = getattr(op, "_upsert", None)
            if upsert is None:
                upsert = getattr(op, "upsert", False) if not isinstance(op, dict) else op.get("upsert", False)
            doc = getattr(op, "_doc", None) or getattr(op, "replacement", None) or getattr(op, "update", None)
            if doc is None and isinstance(op, dict):
                doc = op.get("replacement", op.get("update", {}))
            doc = doc or {}
            # UpdateOne 的 _doc 含 $set 等操作符；ReplaceOne 的 _doc 为完整文档
            is_update = isinstance(doc, dict) and any(k.startswith("$") for k in doc.keys())
            if is_update:
                self.update_one(f, doc, upsert=upsert)
                modified_count += 1
            else:
                r = doc
                existing = self.find_one(f)
                if existing:
                    new_doc = dict(existing)
                    new_doc.update(r)
                    if "_id" not in new_doc:
                        new_doc["_id"] = existing.get("_id")
                    self.replace_one(f, new_doc)
                    modified_count += 1
                elif upsert:
                    new_doc = dict(r)
                    if "_id" not in new_doc:
                        import uuid
                        new_doc["_id"] = str(uuid.uuid4())[:24]
                    self.insert_one(new_doc)
                    upserted_count += 1
                    upserted_ids.append(new_doc["_id"])
        result = type("BulkWriteResult", (), {
            "modified_count": modified_count,
            "upserted_count": upserted_count,
            "upserted_ids": upserted_ids,
        })()
        return result


class PostgresDBCompat:
    """
    MongoDB 兼容的数据库对象
    提供 db.collection_name 和 db["collection_name"] 访问方式
    """

    def __init__(self):
        self._collections: Dict[str, PostgresCollectionProxy] = {}
        self._initialized = False

    def _ensure_init(self):
        if not self._initialized:
            _ensure_tables()
            self._initialized = True

    def __getattr__(self, name: str) -> PostgresCollectionProxy:
        if name.startswith("_"):
            raise AttributeError(name)
        self._ensure_init()
        if name not in self._collections:
            self._collections[name] = PostgresCollectionProxy(name, self)
        return self._collections[name]

    def __getitem__(self, name: str) -> PostgresCollectionProxy:
        return getattr(self, name)

    def list_collection_names(self) -> List[str]:
        """列出所有表（集合）名"""
        with get_connection_context() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public' AND tablename LIKE 'pg_doc_%'
                """)
                return [r["tablename"].replace("pg_doc_", "") for r in cur.fetchall()]

    def command(self, cmd: str, *args, **kwargs) -> Dict:
        """模拟 MongoDB command，用于 collStats 等"""
        if cmd == "collStats":
            coll_name = kwargs.get("collStats") or (args[0] if args else "")
            coll = getattr(self, coll_name)
            size = 0
            count = 0
            try:
                count = coll.count_documents({})
                table_name = f"pg_doc_{coll_name}"
                with get_connection_context() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT pg_total_relation_size(%s::regclass) as size", (table_name,))
                        row = cur.fetchone()
                        size = row["size"] if row else 0
            except Exception:
                pass
            return {
                "count": count,
                "size": size,
                "storageSize": size,
                "nindexes": 0,
                "totalIndexSize": 0,
            }
        return {}


# 全局数据库实例
_db_sync: Optional[PostgresDBCompat] = None


def get_mongo_db_sync() -> PostgresDBCompat:
    """获取同步数据库连接（PostgreSQL 兼容接口）"""
    global _db_sync
    if _db_sync is None:
        _db_sync = PostgresDBCompat()
        logger.info("✅ PostgreSQL 数据库连接已初始化")
    return _db_sync


def get_mongo_db():
    """获取异步数据库连接 - 当前仅支持同步，返回同步对象"""
    return get_mongo_db_sync()


def get_database():
    """获取数据库连接（兼容 historical_data_service、news_data_service 等）"""
    return get_mongo_db_sync()


def get_postgres_client_compat():
    """获取 PostgreSQL 客户端兼容对象（用于 database_manager 等）"""
    class PostgresClientCompat:
        """模拟 pymongo.MongoClient，提供 .tradingagents、get_database() 和 client['dbname']"""
        def __init__(self):
            self._db = get_mongo_db_sync()

        @property
        def tradingagents(self):
            return self._db

        def get_database(self, name: str):
            return self._db

        def __getitem__(self, name: str):
            """兼容 client['tradingagents'] 等调用"""
            return self._db

    return PostgresClientCompat()


def init_database():
    """初始化数据库（创建表结构）"""
    _ensure_tables()
    logger.info("✅ PostgreSQL 数据库初始化完成")


def init_db():
    """init_database 的别名，兼容旧代码"""
    init_database()


def close_database():
    """关闭数据库连接（PostgreSQL 无持久连接，为 no-op）"""
    pass


def close_db():
    """close_database 的别名"""
    close_database()


def get_redis_client():
    """获取 Redis 客户端（供 queue_service 等使用）"""
    try:
        from app.core.redis_client import get_redis
        return get_redis()
    except Exception:
        try:
            from tradingagents.config.database_manager import get_redis_client as _get
            return _get()
        except Exception:
            raise RuntimeError("Redis 未初始化，请检查 redis_client 或 database_manager")


def _ensure_tables():
    """确保所需表存在"""
    collections = [
        "users",
        "system_configs",
        "stock_basic_info",
        "stock_daily_quotes",
        "market_quotes",
        "stock_financial_data",
        "stock_news",
        "financial_data_cache",
        "datasource_groupings",
        "prompt_templates",
        "user_template_configs",
        "llm_providers",
        "cache",
        "stock_data",
        "news_data",
        "fundamentals_data",
        "social_media_messages",
        "token_usage",
        "operation_logs",
        "unified_analysis_tasks",
        "analysis_tasks",
        "analysis_reports",
        "database_backups",
    ]
    with get_connection_context() as conn:
        with conn.cursor() as cur:
            for coll in collections:
                table = f"pg_doc_{coll}"
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table} (
                        id TEXT PRIMARY KEY,
                        data JSONB NOT NULL DEFAULT '{{}}',
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
                # 创建 GIN 索引以加速 JSONB 查询
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table}_data_gin
                    ON {table} USING GIN (data)
                """)
    logger.info(f"✅ 已确保 {len(collections)} 个 PostgreSQL 表存在")

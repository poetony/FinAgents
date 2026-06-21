"""
Redis 启动器 - 后端启动时自动确保 Redis 可用
当 REDIS_ENABLED=true 且 Redis 连接失败时，尝试通过 Docker 启动 Redis 容器
"""

import os
import subprocess
import time
import logging

logger = logging.getLogger(__name__)

CONTAINER_NAME = "tradingagents-redis-local"
DEFAULT_PORT = 6380
DEFAULT_PASSWORD = "tradingagents123"


def _ensure_redis_container(port: int, password: str) -> bool:
    """
    确保 Redis 容器存在且运行中。
    若容器已存在但停止，则启动；若不存在则创建并启动。
    返回 True 表示容器已就绪，False 表示失败。
    """
    try:
        # 检查容器是否存在
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name={CONTAINER_NAME}", "--format", "{{.Names}} {{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return False
        out = (result.stdout or "").strip()
        if not out:
            # 容器不存在，创建
            logger.info(f"[Redis] 创建并启动容器 (端口 {port})...")
            run_result = subprocess.run(
                [
                    "docker", "run", "-d",
                    "--name", CONTAINER_NAME,
                    "-p", f"{port}:6379",
                    "redis:latest",
                    "redis-server", "--appendonly", "yes", "--requirepass", password,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if run_result.returncode != 0:
                logger.warning(f"[Redis] 创建容器失败: {run_result.stderr or run_result.stdout}")
                return False
            logger.info(f"[Redis] 容器已创建: localhost:{port}")
            return True
        if "Up" in out:
            logger.debug(f"[Redis] 容器已在运行: {CONTAINER_NAME}")
            return True
        # 容器存在但已停止，启动
        logger.info(f"[Redis] 启动已存在的容器...")
        start_result = subprocess.run(
            ["docker", "start", CONTAINER_NAME],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if start_result.returncode != 0:
            logger.warning(f"[Redis] 启动容器失败: {start_result.stderr}")
            return False
        logger.info(f"[Redis] 容器已启动: {CONTAINER_NAME}")
        return True
    except FileNotFoundError:
        logger.debug("[Redis] Docker 未安装或不在 PATH 中")
        return False
    except subprocess.TimeoutExpired:
        logger.warning("[Redis] Docker 命令超时")
        return False
    except Exception as e:
        logger.warning(f"[Redis] 启动容器异常: {e}")
        return False


def _check_redis_connection(host: str, port: int, password: str) -> bool:
    """检测 Redis 是否可连接"""
    try:
        import redis
        client = redis.Redis(
            host=host,
            port=int(port),
            password=password or None,
            db=0,
            socket_timeout=2,
            socket_connect_timeout=2,
        )
        client.ping()
        return True
    except Exception:
        return False


def ensure_redis_available() -> bool:
    """
    确保 Redis 可用。若 REDIS_ENABLED 且连接失败，尝试启动 Docker 容器后重试。
    返回 True 表示 Redis 可用，False 表示不可用（将降级到文件缓存）。
    """
    if not os.getenv("REDIS_ENABLED", "").lower() in ("true", "1", "yes"):
        return False
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", str(DEFAULT_PORT)))
    password = os.getenv("REDIS_PASSWORD", DEFAULT_PASSWORD)
    # 先检测是否已可连接
    if _check_redis_connection(host, port, password):
        logger.info(f"[Redis] 已连接: {host}:{port}")
        return True
    # 尝试启动 Docker 容器（仅 localhost 时）
    if host in ("localhost", "127.0.0.1"):
        if _ensure_redis_container(port, password):
            time.sleep(1.5)  # 等待 Redis 就绪
            if _check_redis_connection(host, port, password):
                logger.info(f"[Redis] 启动后连接成功: {host}:{port}")
                return True
    logger.debug(f"[Redis] 不可用，将使用文件缓存降级")
    return False

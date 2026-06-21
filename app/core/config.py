#!/usr/bin/env python3
"""
应用配置模块
从 .env 和环境变量加载配置
"""

import os
from typing import Optional
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0

    # 分析配置
    MARKET_ANALYST_LOOKBACK_DAYS: int = 365

    # JWT 认证
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # PostgreSQL（当为 true 时，UserService 等使用 PostgreSQL）
    POSTGRES_ENABLED: bool = False

    # CORS / 安全（与参考项目兼容）
    ALLOWED_ORIGINS: list = Field(default_factory=lambda: ["*"])
    ALLOWED_HOSTS: list = Field(default_factory=lambda: ["*"])

    # 代理配置
    HTTP_PROXY: str = ""
    HTTPS_PROXY: str = ""
    NO_PROXY: str = ""

    # 时区（供 timezone 模块使用）
    TIMEZONE: str = "Asia/Shanghai"

    # 单股分析精简模式：仅提供单股分析页面，访问 8301 直接进入单股分析界面
    SINGLE_MODE: bool = True

    @property
    def is_production(self) -> bool:
        return not self.DEBUG

    @property
    def REDIS_URL(self) -> str:
        """构建 Redis 连接 URL"""
        if self.REDIS_PASSWORD:
            pw = quote_plus(self.REDIS_PASSWORD)
            return f"redis://:{pw}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例"""
    return settings

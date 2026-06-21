from fastapi import APIRouter, Depends, HTTPException, status
from typing import Any, Dict
import re
import logging

from app.core.config import settings
from app.routers.auth_db import get_current_user

router = APIRouter()
logger = logging.getLogger("webapi")

SENSITIVE_KEYS = {
    "POSTGRES_PASSWORD",
    "MONGODB_PASSWORD",  # 已废弃，兼容旧配置
    "REDIS_PASSWORD",
    "JWT_SECRET",
    "CSRF_SECRET",
    "STOCK_DATA_API_KEY",
    "REFRESH_TOKEN_EXPIRE_DAYS",  # not sensitive itself, but keep for completeness
}

MASK = "***"


def _mask_value(key: str, value: Any) -> Any:
    if value is None:
        return None
    if key in SENSITIVE_KEYS:
        return MASK
    # Mask URLs that may contain credentials
    if key in {"REDIS_URL", "POSTGRES_CONNECTION_STRING"} and isinstance(value, str):
        v = value
        # redis://:pass@host:port/db
        v = re.sub(r"(redis://:)[^@/]+@", r"\1***@", v)
        # postgresql://user:pass@host:port/db
        v = re.sub(r"(postgresql://[^:/?#]+):([^@/]+)@", r"\1:***@", v)
        return v
    return value


def _build_summary() -> Dict[str, Any]:
    raw = settings.model_dump()
    # Attach derived URLs
    raw["REDIS_URL"] = settings.REDIS_URL

    summary: Dict[str, Any] = {}
    for k, v in raw.items():
        summary[k] = _mask_value(k, v)
    return summary


@router.get("/config/summary", tags=["system"], summary="配置概要（已屏蔽敏感项，需管理员）")
async def get_config_summary(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """
    返回当前生效的设置概要。敏感字段将以 *** 掩码显示。
    访问控制：需管理员身份。
    """
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return {"settings": _build_summary()}


@router.get("/config/validate", tags=["system"], summary="验证配置完整性")
async def validate_config():
    """
    验证系统配置的完整性和有效性。
    返回验证结果，包括缺少的配置项和无效的配置。

    验证内容：
    1. 环境变量配置（.env 文件）
    2. 数据库中存储的配置（大模型、数据源等，PostgreSQL）

    注意：此接口会先从数据库重载配置到环境变量，然后再验证。
    """
    from app.core.startup_validator import StartupValidator
    from app.core.config_bridge import bridge_config_to_env
    from app.services.config_service import config_service

    try:
        # 🔧 步骤1: 重载配置 - 从数据库读取配置并桥接到环境变量
        try:
            bridge_config_to_env()
            logger.info("✅ 配置已从数据库重载到环境变量")
        except Exception as e:
            logger.warning(f"⚠️  配置重载失败: {e}，将验证 .env 文件中的配置")

        # 🔍 步骤2: 验证环境变量配置
        validator = StartupValidator()
        env_result = validator.validate()

        # 🔍 步骤3: 验证数据库中的配置（厂家/数据源，PostgreSQL）
        db_validation = {
            "llm_providers": [],
            "data_source_configs": [],
            "warnings": []
        }

        try:
            from app.utils.api_key_utils import (
                is_valid_api_key,
                get_env_api_key_for_provider
            )

            # 🔥 修改：直接从数据库读取原始数据，避免使用 get_llm_providers() 返回的已修改数据
            # get_llm_providers() 会将环境变量的 Key 赋值给 provider.api_key，导致无法区分来源
            from app.core.database import get_mongo_db_sync
            from app.models.config import LLMProvider

            db = get_mongo_db_sync()
            providers_collection = db.llm_providers

            # 查询所有厂家配置（原始数据，PostgreSQL）
            providers_data = list(providers_collection.find())
            llm_providers = [LLMProvider(**data) for data in providers_data]

            logger.info(f"🔍 获取到 {len(llm_providers)} 个大模型厂家")

            for provider in llm_providers:
                # 只验证已启用的厂家
                if not provider.is_active:
                    continue

                validation_item = {
                    "name": provider.name,
                    "display_name": provider.display_name,
                    "is_active": provider.is_active,
                    "has_api_key": False,
                    "status": "未配置",
                    "source": None,
                    "mongodb_configured": False,  # 兼容前端字段名，实际为 PostgreSQL
                    "env_configured": False
                }
                db_key_valid = is_valid_api_key(provider.api_key)
                validation_item["mongodb_configured"] = db_key_valid

                # 检查环境变量中的 API Key 是否有效
                env_key = get_env_api_key_for_provider(provider.name)
                env_key_valid = env_key is not None
                validation_item["env_configured"] = env_key_valid

                if db_key_valid:
                    validation_item["has_api_key"] = True
                    validation_item["status"] = "已配置"
                    validation_item["source"] = "database"
                elif env_key_valid:
                    validation_item["has_api_key"] = True
                    validation_item["status"] = "已配置（环境变量）"
                    validation_item["source"] = "environment"
                    db_validation["warnings"].append(
                        f"大模型厂家 {provider.display_name} 使用环境变量配置，建议在数据库中配置以便统一管理"
                    )
                else:
                    validation_item["status"] = "未配置"
                    db_validation["warnings"].append(
                        f"大模型厂家 {provider.display_name} 已启用但未配置有效的 API Key（数据库和环境变量中都未找到）"
                    )
                db_validation["llm_providers"].append(validation_item)

            # 验证数据源配置
            from app.utils.api_key_utils import (
                is_valid_api_key,
                get_env_api_key_for_datasource
            )

            system_config = await config_service.get_system_config()
            if system_config and system_config.data_source_configs:
                logger.info(f"🔍 获取到 {len(system_config.data_source_configs)} 个数据源配置")

                for ds_config in system_config.data_source_configs:
                    # 只验证已启用的数据源
                    if not ds_config.enabled:
                        continue

                    validation_item = {
                        "name": ds_config.name,
                        "type": ds_config.type,
                        "enabled": ds_config.enabled,
                        "has_api_key": False,
                        "status": "未配置",
                        "source": None,
                        "mongodb_configured": False,  # 兼容前端，实际为 PostgreSQL
                        "env_configured": False
                    }

                    # 某些数据源不需要 API Key（如 AKShare）
                    if ds_config.type in ["akshare", "yahoo"]:
                        validation_item["has_api_key"] = True
                        validation_item["status"] = "已配置（无需密钥）"
                        validation_item["source"] = "builtin"
                        validation_item["mongodb_configured"] = True
                        validation_item["env_configured"] = True
                    else:
                        # 检查数据库中的 API Key 是否有效
                        db_key_valid = is_valid_api_key(ds_config.api_key)
                        validation_item["mongodb_configured"] = db_key_valid

                        # 检查环境变量中的 API Key 是否有效
                        ds_type = ds_config.type.value if hasattr(ds_config.type, 'value') else ds_config.type
                        env_key = get_env_api_key_for_datasource(ds_type)
                        env_key_valid = env_key is not None
                        validation_item["env_configured"] = env_key_valid

                        if db_key_valid:
                            validation_item["has_api_key"] = True
                            validation_item["status"] = "已配置"
                            validation_item["source"] = "database"
                        elif env_key_valid:
                            validation_item["has_api_key"] = True
                            validation_item["status"] = "已配置（环境变量）"
                            validation_item["source"] = "environment"
                            db_validation["warnings"].append(
                                f"数据源 {ds_config.name} 使用环境变量配置，建议在数据库中配置以便统一管理"
                            )
                        else:
                            validation_item["status"] = "未配置"
                            db_validation["warnings"].append(
                                f"数据源 {ds_config.name} 已启用但未配置有效的 API Key（数据库和环境变量中都未找到）"
                            )
                    db_validation["data_source_configs"].append(validation_item)

        except Exception as e:
            logger.error(f"验证数据库配置失败: {e}", exc_info=True)
            db_validation["warnings"].append(f"数据库配置验证失败: {str(e)}")

        logger.info(f"🔍 数据库验证结果: {len(db_validation['llm_providers'])} 个大模型厂家, {len(db_validation['data_source_configs'])} 个数据源, {len(db_validation['warnings'])} 个警告")

        # 数据库配置警告不影响总体验证结果
        # 只有环境变量中的必需配置缺失或无效时才显示红色错误
        overall_success = env_result.success

        return {
            "success": True,
            "data": {
                # 环境变量验证结果
                "env_validation": {
                    "success": env_result.success,
                    "missing_required": [
                        {"key": config.key, "description": config.description}
                        for config in env_result.missing_required
                    ],
                    "missing_recommended": [
                        {"key": config.key, "description": config.description}
                        for config in env_result.missing_recommended
                    ],
                    "invalid_configs": [
                        {"key": config.key, "error": config.description}
                        for config in env_result.invalid_configs
                    ],
                    "warnings": env_result.warnings
                },
                # 数据库配置验证结果（PostgreSQL，保留 key 兼容前端）
                "mongodb_validation": db_validation,
                # 总体验证结果（只考虑必需配置）
                "success": overall_success
            },
            "message": "配置验证完成"
        }
    except Exception as e:
        logger.error(f"配置验证失败: {e}", exc_info=True)
        return {
            "success": False,
            "data": None,
            "message": f"配置验证失败: {str(e)}"
        }

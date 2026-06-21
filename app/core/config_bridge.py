"""
配置桥接模块
将统一配置系统的配置桥接到环境变量，供 TradingAgents 核心库使用
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("app.config_bridge")


def bridge_config_to_env():
    """
    将统一配置桥接到环境变量

    这个函数会：
    1. 从数据库读取大模型厂家配置（API 密钥、超时、温度等）
    2. 将配置写入环境变量
    3. 将默认模型写入环境变量
    4. 将数据源配置写入环境变量（API 密钥、超时、重试等）
    5. 将系统运行时配置写入环境变量

    这样 TradingAgents 核心库就能通过环境变量读取到用户配置的数据
    """
    try:
        from app.core.unified_config import unified_config
        from app.services.config_service import config_service

        logger.info("🔧 开始桥接配置到环境变量...")
        bridged_count = 0

        # 1. 桥接大模型配置（基础 API 密钥）
        # 从 PostgreSQL 读取；失败则用 JSON 后备
        use_fallback_llm = True
        try:
            from app.core.database import get_mongo_db_sync
            from app.models.config import LLMProvider

            db = get_mongo_db_sync()
            providers_collection = db.llm_providers
            providers_data = list(providers_collection.find({}))
            providers = [LLMProvider(**data) for data in providers_data]

            logger.info(f"  📊 从 PostgreSQL 读取到 {len(providers)} 个厂家配置")
            use_fallback_llm = False
            for provider in providers:
                if not provider.is_active:
                    continue
                env_key = f"{provider.name.upper()}_API_KEY"
                existing_env_value = os.getenv(env_key)
                if existing_env_value and not existing_env_value.startswith("your_"):
                    logger.info(f"  ✓ 使用 .env 文件中的 {env_key} (长度: {len(existing_env_value)})")
                    bridged_count += 1
                elif provider.api_key and not provider.api_key.startswith("your_"):
                    os.environ[env_key] = provider.api_key
                    logger.info(f"  ✓ 使用 PostgreSQL 厂家配置的 {env_key} (长度: {len(provider.api_key)})")
                    bridged_count += 1
        except Exception as e:
            logger.warning(f"⚠️  从 PostgreSQL 读取厂家配置失败: {e}，使用 JSON 后备")

        if use_fallback_llm:
            # 后备方案：从 JSON 文件读取
            llm_configs = unified_config.get_llm_configs()
            for llm_config in llm_configs:
                # provider 现在是字符串类型，不再是枚举
                env_key = f"{llm_config.provider.upper()}_API_KEY"
                existing_env_value = os.getenv(env_key)

                # 检查环境变量是否已存在且有效（不是占位符）
                if existing_env_value and not existing_env_value.startswith("your_"):
                    logger.info(f"  ✓ 使用 .env 文件中的 {env_key} (长度: {len(existing_env_value)})")
                    bridged_count += 1
                elif llm_config.enabled and llm_config.api_key:
                    # 只有当环境变量不存在或为占位符时，才使用数据库配置
                    if not llm_config.api_key.startswith("your_"):
                        os.environ[env_key] = llm_config.api_key
                        logger.info(f"  ✓ 使用 JSON 文件中的 {env_key} (长度: {len(llm_config.api_key)})")
                        bridged_count += 1
                    else:
                        logger.warning(f"  ⚠️  {env_key} 在 .env 和 JSON 文件中都是占位符，跳过")
                else:
                    logger.debug(f"  ⏭️  {env_key} 未配置")

        # 2. 桥接默认模型配置
        default_model = unified_config.get_default_model()
        if default_model:
            os.environ['TRADINGAGENTS_DEFAULT_MODEL'] = default_model
            logger.info(f"  ✓ 桥接默认模型: {default_model}")
            bridged_count += 1

        quick_model = unified_config.get_quick_analysis_model()
        if quick_model:
            os.environ['TRADINGAGENTS_QUICK_MODEL'] = quick_model
            logger.info(f"  ✓ 桥接快速分析模型: {quick_model}")
            bridged_count += 1

        deep_model = unified_config.get_deep_analysis_model()
        if deep_model:
            os.environ['TRADINGAGENTS_DEEP_MODEL'] = deep_model
            logger.info(f"  ✓ 桥接深度分析模型: {deep_model}")
            bridged_count += 1

        # 3. 桥接数据源配置（基础 API 密钥）
        try:
            from app.core.database import get_mongo_db_sync
            from app.models.config import SystemConfig

            db = get_mongo_db_sync()
            config_collection = db.system_configs
            config_data = config_collection.find_one(
                {"is_active": True},
                sort=[("version", -1)]
            )

            if config_data and config_data.get('data_source_configs'):
                system_config = SystemConfig(**config_data)
                data_source_configs = system_config.data_source_configs
                logger.info(f"  📊 从 PostgreSQL 读取到 {len(data_source_configs)} 个数据源配置")
            else:
                data_source_configs = unified_config.get_data_source_configs()
        except Exception as e:
            logger.warning(f"⚠️  从 PostgreSQL 读取数据源配置失败: {e}，使用 JSON 后备")
            data_source_configs = unified_config.get_data_source_configs()

        for ds_config in data_source_configs:
            if ds_config.enabled and ds_config.api_key:
                # Tushare Token
                # 🔥 优先级：数据库配置 > .env 文件（用户在 Web 后台修改后立即生效）
                if ds_config.type.value == 'tushare':
                    existing_token = os.getenv('TUSHARE_TOKEN')

                    # 优先使用数据库配置
                    if ds_config.api_key and not ds_config.api_key.startswith("your_"):
                        os.environ['TUSHARE_TOKEN'] = ds_config.api_key
                        logger.info(f"  ✓ 使用数据库中的 TUSHARE_TOKEN (长度: {len(ds_config.api_key)})")
                        if existing_token and existing_token != ds_config.api_key:
                            logger.info(f"  ℹ️  已覆盖 .env 文件中的 TUSHARE_TOKEN")
                    # 降级到 .env 文件配置
                    elif existing_token and not existing_token.startswith("your_"):
                        logger.info(f"  ✓ 使用 .env 文件中的 TUSHARE_TOKEN (长度: {len(existing_token)})")
                        logger.info(f"  ℹ️  数据库中未配置有效的 TUSHARE_TOKEN，使用 .env 降级方案")
                    else:
                        logger.warning(f"  ⚠️  TUSHARE_TOKEN 在数据库和 .env 中都未配置有效值")
                        continue
                    bridged_count += 1

                # FinnHub API Key
                # 🔥 优先级：数据库配置 > .env 文件
                elif ds_config.type.value == 'finnhub':
                    existing_key = os.getenv('FINNHUB_API_KEY')

                    # 优先使用数据库配置
                    if ds_config.api_key and not ds_config.api_key.startswith("your_"):
                        os.environ['FINNHUB_API_KEY'] = ds_config.api_key
                        logger.info(f"  ✓ 使用数据库中的 FINNHUB_API_KEY (长度: {len(ds_config.api_key)})")
                        if existing_key and existing_key != ds_config.api_key:
                            logger.info(f"  ℹ️  已覆盖 .env 文件中的 FINNHUB_API_KEY")
                    # 降级到 .env 文件配置
                    elif existing_key and not existing_key.startswith("your_"):
                        logger.info(f"  ✓ 使用 .env 文件中的 FINNHUB_API_KEY (长度: {len(existing_key)})")
                        logger.info(f"  ℹ️  数据库中未配置有效的 FINNHUB_API_KEY，使用 .env 降级方案")
                    else:
                        logger.warning(f"  ⚠️  FINNHUB_API_KEY 在数据库和 .env 中都未配置有效值")
                        continue
                    bridged_count += 1

        # 4. 桥接数据源细节配置（超时、重试、缓存等）
        bridged_count += _bridge_datasource_details(data_source_configs)

        # 5. 桥接系统运行时配置
        bridged_count += _bridge_system_settings()

        # 6. 同步定价配置到 tradingagents 的 config/pricing.json
        # 注意：这里需要从数据库读取配置，因为文件中的配置没有定价信息
        # 使用异步方式同步定价配置
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # 在异步上下文中，创建后台任务
            task = loop.create_task(_sync_pricing_config_from_db())
            task.add_done_callback(_handle_sync_task_result)
            logger.info("🔄 定价配置同步任务已创建（后台执行）")
        except RuntimeError:
            # 不在异步上下文中，使用 asyncio.run
            asyncio.run(_sync_pricing_config_from_db())

        logger.info(f"✅ 配置桥接完成，共桥接 {bridged_count} 项配置")
        return True

    except Exception as e:
        logger.error(f"❌ 配置桥接失败: {e}", exc_info=True)
        logger.warning("⚠️  TradingAgents 将使用 .env 文件中的配置")
        return False


def _bridge_datasource_details(data_source_configs) -> int:
    """
    桥接数据源细节配置到环境变量

    Args:
        data_source_configs: 数据源配置列表

    Returns:
        int: 桥接的配置项数量
    """
    bridged_count = 0

    for ds_config in data_source_configs:
        if not ds_config.enabled:
            continue

        # 注意：字段名是 type 而不是 source_type
        source_type = ds_config.type.value.upper()

        # 超时时间
        if ds_config.timeout:
            env_key = f"{source_type}_TIMEOUT"
            os.environ[env_key] = str(ds_config.timeout)
            logger.debug(f"  ✓ 桥接 {env_key}: {ds_config.timeout}")
            bridged_count += 1

        # 速率限制
        if ds_config.rate_limit:
            env_key = f"{source_type}_RATE_LIMIT"
            os.environ[env_key] = str(ds_config.rate_limit / 60.0)  # 转换为每秒请求数
            logger.debug(f"  ✓ 桥接 {env_key}: {ds_config.rate_limit / 60.0}")
            bridged_count += 1

        # 最大重试次数（从 config_params 中获取）
        if ds_config.config_params and 'max_retries' in ds_config.config_params:
            env_key = f"{source_type}_MAX_RETRIES"
            os.environ[env_key] = str(ds_config.config_params['max_retries'])
            logger.debug(f"  ✓ 桥接 {env_key}: {ds_config.config_params['max_retries']}")
            bridged_count += 1

        # 缓存 TTL（从 config_params 中获取）
        if ds_config.config_params and 'cache_ttl' in ds_config.config_params:
            env_key = f"{source_type}_CACHE_TTL"
            os.environ[env_key] = str(ds_config.config_params['cache_ttl'])
            logger.debug(f"  ✓ 桥接 {env_key}: {ds_config.config_params['cache_ttl']}")
            bridged_count += 1

        # 是否启用缓存（从 config_params 中获取）
        if ds_config.config_params and 'cache_enabled' in ds_config.config_params:
            env_key = f"{source_type}_CACHE_ENABLED"
            os.environ[env_key] = str(ds_config.config_params['cache_enabled']).lower()
            logger.debug(f"  ✓ 桥接 {env_key}: {ds_config.config_params['cache_enabled']}")
            bridged_count += 1

    if bridged_count > 0:
        logger.info(f"  ✓ 桥接数据源细节配置: {bridged_count} 项")

    return bridged_count


def _bridge_system_settings() -> int:
    """
    桥接系统运行时配置到环境变量

    Returns:
        int: 桥接的配置项数量
    """
    try:
        try:
            from app.core.database import get_mongo_db_sync
            db = get_mongo_db_sync()
            config_doc = db.system_configs.find_one({"is_active": True})
        except Exception as e:
            logger.debug(f"  ⚠️  无法从 PostgreSQL 获取系统设置: {e}")
            return 0

        if not config_doc or 'system_settings' not in config_doc:
            logger.debug("  ⚠️  系统设置为空，跳过桥接")
            return 0

        system_settings = config_doc['system_settings']

        if not system_settings:
            logger.debug("  ⚠️  系统设置为空，跳过桥接")
            return 0

        logger.debug(f"  📋 获取到 {len(system_settings)} 个系统设置")
        bridged_count = 0

        # TradingAgents 运行时配置
        ta_settings = {
            'ta_hk_min_request_interval_seconds': 'TA_HK_MIN_REQUEST_INTERVAL_SECONDS',
            'ta_hk_timeout_seconds': 'TA_HK_TIMEOUT_SECONDS',
            'ta_hk_max_retries': 'TA_HK_MAX_RETRIES',
            'ta_hk_rate_limit_wait_seconds': 'TA_HK_RATE_LIMIT_WAIT_SECONDS',
            'ta_hk_cache_ttl_seconds': 'TA_HK_CACHE_TTL_SECONDS',
            'ta_use_app_cache': 'TA_USE_APP_CACHE',
        }

        # Token 使用统计配置
        token_tracking_settings = {
            'enable_cost_tracking': 'ENABLE_COST_TRACKING',
            'auto_save_usage': 'AUTO_SAVE_USAGE',
        }

        for setting_key, env_key in ta_settings.items():
            # 检查 .env 文件中是否已经设置了该环境变量
            env_value = os.getenv(env_key)
            if env_value is not None:
                # .env 文件中已设置，优先使用 .env 的值
                logger.info(f"  ✓ 使用 .env 文件中的 {env_key}: {env_value}")
                bridged_count += 1
            elif setting_key in system_settings:
                # .env 文件中未设置，使用数据库中的值
                value = system_settings[setting_key]
                os.environ[env_key] = str(value).lower() if isinstance(value, bool) else str(value)
                logger.info(f"  ✓ 桥接 {env_key}: {value}")
                bridged_count += 1
            else:
                logger.debug(f"  ⚠️  配置键 {setting_key} 不存在于系统设置中")

        # 桥接 Token 使用统计配置
        for setting_key, env_key in token_tracking_settings.items():
            if setting_key in system_settings:
                value = system_settings[setting_key]
                os.environ[env_key] = str(value).lower() if isinstance(value, bool) else str(value)
                logger.info(f"  ✓ 桥接 {env_key}: {value}")
                bridged_count += 1
            else:
                logger.debug(f"  ⚠️  配置键 {setting_key} 不存在于系统设置中")

        # 时区配置
        if 'app_timezone' in system_settings:
            os.environ['APP_TIMEZONE'] = system_settings['app_timezone']
            logger.debug(f"  ✓ 桥接 APP_TIMEZONE: {system_settings['app_timezone']}")
            bridged_count += 1

        # 货币偏好
        if 'currency_preference' in system_settings:
            os.environ['CURRENCY_PREFERENCE'] = system_settings['currency_preference']
            logger.debug(f"  ✓ 桥接 CURRENCY_PREFERENCE: {system_settings['currency_preference']}")
            bridged_count += 1

        if bridged_count > 0:
            logger.info(f"  ✓ 桥接系统运行时配置: {bridged_count} 项")

        # 同步到文件系统（供 unified_config 使用）
        try:
            print(f"🔄 [config_bridge] 准备同步系统设置到文件系统")
            print(f"🔄 [config_bridge] system_settings 包含 {len(system_settings)} 项")

            # 检查关键字段
            if "quick_analysis_model" in system_settings:
                print(f"  ✓ [config_bridge] 包含 quick_analysis_model: {system_settings['quick_analysis_model']}")
            else:
                print(f"  ⚠️  [config_bridge] 不包含 quick_analysis_model")

            if "deep_analysis_model" in system_settings:
                print(f"  ✓ [config_bridge] 包含 deep_analysis_model: {system_settings['deep_analysis_model']}")
            else:
                print(f"  ⚠️  [config_bridge] 不包含 deep_analysis_model")

            from app.core.unified_config import unified_config
            result = unified_config.save_system_settings(system_settings)

            if result:
                logger.info(f"  ✓ 系统设置已同步到文件系统")
                print(f"✅ [config_bridge] 系统设置同步成功")
            else:
                logger.warning(f"  ⚠️  系统设置同步返回 False")
                print(f"⚠️  [config_bridge] 系统设置同步返回 False")
        except Exception as e:
            logger.warning(f"  ⚠️  同步系统设置到文件系统失败: {e}")
            print(f"❌ [config_bridge] 同步系统设置到文件系统失败: {e}")
            import traceback
            print(traceback.format_exc())

        return bridged_count

    except Exception as e:
        logger.warning(f"  ⚠️  桥接系统设置失败: {e}")
        return 0


def get_bridged_api_key(provider: str) -> Optional[str]:
    """
    获取桥接的 API 密钥
    
    Args:
        provider: 提供商名称 (如: openai, deepseek, dashscope)
    
    Returns:
        API 密钥，如果不存在返回 None
    """
    env_key = f"{provider.upper()}_API_KEY"
    return os.environ.get(env_key)


def get_bridged_model(model_type: str = "default") -> Optional[str]:
    """
    获取桥接的模型名称
    
    Args:
        model_type: 模型类型 (default, quick, deep)
    
    Returns:
        模型名称，如果不存在返回 None
    """
    if model_type == "quick":
        return os.environ.get('TRADINGAGENTS_QUICK_MODEL')
    elif model_type == "deep":
        return os.environ.get('TRADINGAGENTS_DEEP_MODEL')
    else:
        return os.environ.get('TRADINGAGENTS_DEFAULT_MODEL')


def clear_bridged_config():
    """
    清除桥接的配置

    用于测试或重新加载配置
    """
    keys_to_clear = [
        # 模型配置
        'TRADINGAGENTS_DEFAULT_MODEL',
        'TRADINGAGENTS_QUICK_MODEL',
        'TRADINGAGENTS_DEEP_MODEL',
        # 数据源 API 密钥
        'TUSHARE_TOKEN',
        'FINNHUB_API_KEY',
        # 系统配置
        'APP_TIMEZONE',
        'CURRENCY_PREFERENCE',
    ]

    # 清除所有可能的 API 密钥
    providers = ['OPENAI', 'ANTHROPIC', 'GOOGLE', 'DEEPSEEK', 'DASHSCOPE', 'QIANFAN']
    for provider in providers:
        keys_to_clear.append(f'{provider}_API_KEY')

    # 清除数据源细节配置
    data_sources = ['TUSHARE', 'AKSHARE', 'FINNHUB']
    for ds in data_sources:
        keys_to_clear.extend([
            f'{ds}_TIMEOUT',
            f'{ds}_RATE_LIMIT',
            f'{ds}_MAX_RETRIES',
            f'{ds}_CACHE_TTL',
            f'{ds}_CACHE_ENABLED',
        ])

    # 清除 TradingAgents 运行时配置
    ta_runtime_keys = [
        'TA_HK_MIN_REQUEST_INTERVAL_SECONDS',
        'TA_HK_TIMEOUT_SECONDS',
        'TA_HK_MAX_RETRIES',
        'TA_HK_RATE_LIMIT_WAIT_SECONDS',
        'TA_HK_CACHE_TTL_SECONDS',
        'TA_USE_APP_CACHE',
    ]
    keys_to_clear.extend(ta_runtime_keys)

    for key in keys_to_clear:
        if key in os.environ:
            del os.environ[key]
            logger.debug(f"  清除环境变量: {key}")

    logger.info("✅ 已清除所有桥接的配置")


def reload_bridged_config():
    """
    重新加载桥接的配置

    用于配置更新后重新桥接
    """
    logger.info("🔄 重新加载配置桥接...")
    clear_bridged_config()
    return bridge_config_to_env()


def _sync_pricing_config(llm_configs):
    """
    同步定价配置到 tradingagents 的 config/pricing.json

    Args:
        llm_configs: LLM 配置列表
    """
    try:
        # 获取项目根目录的 config 目录
        project_root = Path(__file__).parent.parent.parent
        config_dir = project_root / "config"
        config_dir.mkdir(exist_ok=True)

        pricing_file = config_dir / "pricing.json"

        # 构建定价配置列表
        pricing_configs = []
        for llm_config in llm_configs:
            if llm_config.enabled:
                pricing_config = {
                    # provider 现在是字符串类型，不再是枚举
                    "provider": llm_config.provider,
                    "model_name": llm_config.model_name,
                    "input_price_per_1k": llm_config.input_price_per_1k or 0.0,
                    "output_price_per_1k": llm_config.output_price_per_1k or 0.0,
                    "currency": llm_config.currency or "CNY"
                }
                pricing_configs.append(pricing_config)

        # 保存到文件
        with open(pricing_file, 'w', encoding='utf-8') as f:
            json.dump(pricing_configs, f, ensure_ascii=False, indent=2)

        logger.info(f"  ✓ 同步定价配置到 {pricing_file}: {len(pricing_configs)} 个模型")

    except Exception as e:
        logger.warning(f"  ⚠️  同步定价配置失败: {e}")


def sync_pricing_config_now():
    """
    立即同步定价配置（用于配置更新后实时同步）

    注意：这个函数会在后台异步执行同步操作
    """
    import asyncio

    try:
        # 如果在异步上下文中，创建后台任务
        try:
            loop = asyncio.get_running_loop()
            # 在异步上下文中，创建一个后台任务（不等待完成）
            task = loop.create_task(_sync_pricing_config_from_db())
            # 添加回调来记录错误
            task.add_done_callback(_handle_sync_task_result)
            logger.info("🔄 定价配置同步任务已创建（后台执行）")
            return True
        except RuntimeError:
            # 不在异步上下文中，使用 asyncio.run
            asyncio.run(_sync_pricing_config_from_db())
            return True
    except Exception as e:
        logger.error(f"❌ 立即同步定价配置失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def _handle_sync_task_result(task):
    """处理同步任务的结果"""
    try:
        task.result()
    except Exception as e:
        logger.error(f"❌ 定价配置同步任务执行失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def _sync_pricing_config_from_db():
    """
    从 PostgreSQL 同步定价配置
    """
    try:
        from app.core.database import get_mongo_db_sync

        db = get_mongo_db_sync()

        # 获取最新的激活配置（PostgreSQL 兼容接口为同步）
        config = db.system_configs.find_one(
            {'is_active': True},
            sort=[('version', -1)]
        )

        if not config:
            logger.warning("⚠️  未找到激活的配置")
            return

        # 获取项目根目录的 config 目录
        project_root = Path(__file__).parent.parent.parent
        config_dir = project_root / "config"
        config_dir.mkdir(exist_ok=True)

        pricing_file = config_dir / "pricing.json"

        # 构建定价配置列表
        pricing_configs = []
        for llm_config in config.get('llm_configs', []):
            if llm_config.get('enabled', False):
                # 从数据库读取的是字典，直接使用字符串 provider
                provider = llm_config.get('provider')

                # 如果 provider 是枚举类型，转换为字符串
                if hasattr(provider, 'value'):
                    provider = provider.value

                pricing_config = {
                    "provider": provider,
                    "model_name": llm_config.get('model_name'),
                    "input_price_per_1k": llm_config.get('input_price_per_1k') or 0.0,
                    "output_price_per_1k": llm_config.get('output_price_per_1k') or 0.0,
                    "currency": llm_config.get('currency') or "CNY"
                }
                pricing_configs.append(pricing_config)

        # 保存到文件
        with open(pricing_file, 'w', encoding='utf-8') as f:
            json.dump(pricing_configs, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ 同步定价配置到 {pricing_file}: {len(pricing_configs)} 个模型")

    except Exception as e:
        logger.error(f"❌ 从数据库同步定价配置失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


# 导出函数
__all__ = [
    'bridge_config_to_env',
    'get_bridged_api_key',
    'get_bridged_model',
    'clear_bridged_config',
    'reload_bridged_config',
    'sync_pricing_config_now',
]


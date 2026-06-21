"""
模型能力分级常量

定义默认模型配置、分析深度要求、聚合渠道等。
"""
from enum import Enum
from typing import Dict, Any, List


# ==================== 枚举定义 ====================

class ModelRole(str, Enum):
    """模型适用角色"""
    QUICK_ANALYSIS = "quick_analysis"
    DEEP_ANALYSIS = "deep_analysis"
    BOTH = "both"


class ModelFeature(str, Enum):
    """模型特性"""
    TOOL_CALLING = "tool_calling"
    LONG_CONTEXT = "long_context"
    REASONING = "reasoning"
    VISION = "vision"
    FAST_RESPONSE = "fast_response"
    COST_EFFECTIVE = "cost_effective"


# ==================== 分析深度要求 ====================

ANALYSIS_DEPTH_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
    "快速": {
        "min_capability": 1,
        "quick_model_min": 1,
        "deep_model_min": 1,
        "required_features": [ModelFeature.TOOL_CALLING],
        "description": "适合快速分析和简单任务",
    },
    "基础": {
        "min_capability": 1,
        "quick_model_min": 1,
        "deep_model_min": 2,
        "required_features": [ModelFeature.TOOL_CALLING],
        "description": "基础分析，平衡速度与质量",
    },
    "标准": {
        "min_capability": 2,
        "quick_model_min": 1,
        "deep_model_min": 2,
        "required_features": [ModelFeature.TOOL_CALLING],
        "description": "标准分析，推荐配置",
    },
    "深度": {
        "min_capability": 3,
        "quick_model_min": 2,
        "deep_model_min": 3,
        "required_features": [ModelFeature.TOOL_CALLING, ModelFeature.REASONING],
        "description": "深度分析，多轮辩论",
    },
    "全面": {
        "min_capability": 4,
        "quick_model_min": 2,
        "deep_model_min": 4,
        "required_features": [ModelFeature.TOOL_CALLING, ModelFeature.REASONING],
        "description": "全面分析，最高质量",
    },
}


# ==================== 能力等级描述 ====================

CAPABILITY_DESCRIPTIONS: Dict[int, str] = {
    1: "⚡ 基础级 - 适合快速分析和简单任务",
    2: "📊 标准级 - 适合基础和标准分析",
    3: "🎯 高级 - 适合标准和深度分析",
    4: "🔥 专业级 - 适合深度和全面分析",
    5: "👑 旗舰级 - 适合所有级别，最强推理能力",
}


# ==================== 默认模型能力配置 ====================

DEFAULT_MODEL_CAPABILITIES: Dict[str, Dict[str, Any]] = {
    # 阿里百炼
    "qwen-turbo": {
        "capability_level": 1,
        "suitable_roles": [ModelRole.BOTH],
        "features": [ModelFeature.TOOL_CALLING, ModelFeature.FAST_RESPONSE, ModelFeature.COST_EFFECTIVE],
        "recommended_depths": ["快速", "基础", "标准"],
        "performance_metrics": {"speed": 5, "cost": 5, "quality": 2},
        "description": "阿里百炼轻量模型，快速响应",
    },
    "qwen-plus": {
        "capability_level": 2,
        "suitable_roles": [ModelRole.BOTH],
        "features": [ModelFeature.TOOL_CALLING, ModelFeature.REASONING],
        "recommended_depths": ["基础", "标准", "深度"],
        "performance_metrics": {"speed": 4, "cost": 4, "quality": 3},
        "description": "阿里百炼标准模型",
    },
    "qwen-max": {
        "capability_level": 4,
        "suitable_roles": [ModelRole.DEEP_ANALYSIS, ModelRole.BOTH],
        "features": [ModelFeature.TOOL_CALLING, ModelFeature.REASONING, ModelFeature.LONG_CONTEXT],
        "recommended_depths": ["标准", "深度", "全面"],
        "performance_metrics": {"speed": 3, "cost": 2, "quality": 5},
        "description": "阿里百炼旗舰模型，强推理能力",
    },
    "qwen3-max": {
        "capability_level": 4,
        "suitable_roles": [ModelRole.DEEP_ANALYSIS, ModelRole.BOTH],
        "features": [ModelFeature.TOOL_CALLING, ModelFeature.REASONING, ModelFeature.LONG_CONTEXT],
        "recommended_depths": ["标准", "深度", "全面"],
        "performance_metrics": {"speed": 3, "cost": 2, "quality": 5},
        "description": "通义千问3 Max",
    },
    # OpenAI
    "gpt-3.5-turbo": {
        "capability_level": 1,
        "suitable_roles": [ModelRole.BOTH],
        "features": [ModelFeature.TOOL_CALLING, ModelFeature.FAST_RESPONSE],
        "recommended_depths": ["快速", "基础", "标准"],
        "performance_metrics": {"speed": 5, "cost": 4, "quality": 2},
        "description": "OpenAI 轻量模型",
    },
    "gpt-4": {
        "capability_level": 3,
        "suitable_roles": [ModelRole.DEEP_ANALYSIS, ModelRole.BOTH],
        "features": [ModelFeature.TOOL_CALLING, ModelFeature.REASONING],
        "recommended_depths": ["标准", "深度", "全面"],
        "performance_metrics": {"speed": 3, "cost": 2, "quality": 4},
        "description": "OpenAI GPT-4",
    },
    "gpt-4o-mini": {
        "capability_level": 2,
        "suitable_roles": [ModelRole.BOTH],
        "features": [ModelFeature.TOOL_CALLING, ModelFeature.FAST_RESPONSE],
        "recommended_depths": ["快速", "基础", "标准"],
        "performance_metrics": {"speed": 5, "cost": 4, "quality": 3},
        "description": "OpenAI GPT-4o Mini",
    },
    # DeepSeek
    "deepseek-chat": {
        "capability_level": 3,
        "suitable_roles": [ModelRole.DEEP_ANALYSIS, ModelRole.BOTH],
        "features": [ModelFeature.TOOL_CALLING, ModelFeature.REASONING],
        "recommended_depths": ["标准", "深度", "全面"],
        "performance_metrics": {"speed": 4, "cost": 5, "quality": 4},
        "description": "DeepSeek 推理模型",
    },
    # 智谱
    "glm-3-turbo": {
        "capability_level": 1,
        "suitable_roles": [ModelRole.BOTH],
        "features": [ModelFeature.TOOL_CALLING, ModelFeature.FAST_RESPONSE],
        "recommended_depths": ["快速", "基础", "标准"],
        "performance_metrics": {"speed": 5, "cost": 5, "quality": 2},
        "description": "智谱 GLM-3 Turbo",
    },
    "glm-4": {
        "capability_level": 3,
        "suitable_roles": [ModelRole.DEEP_ANALYSIS, ModelRole.BOTH],
        "features": [ModelFeature.TOOL_CALLING, ModelFeature.REASONING],
        "recommended_depths": ["标准", "深度", "全面"],
        "performance_metrics": {"speed": 4, "cost": 4, "quality": 4},
        "description": "智谱 GLM-4",
    },
    # 硅基流动
    "stepfun-ai/Step-3.5-Flash": {
        "capability_level": 2,
        "suitable_roles": [ModelRole.BOTH],
        "features": [ModelFeature.TOOL_CALLING, ModelFeature.FAST_RESPONSE],
        "recommended_depths": ["快速", "基础", "标准"],
        "performance_metrics": {"speed": 5, "cost": 5, "quality": 3},
        "description": "硅基流动 Step-3.5-Flash，快速响应",
    },
    "deepseek-ai/DeepSeek-V3.2": {
        "capability_level": 4,
        "suitable_roles": [ModelRole.DEEP_ANALYSIS, ModelRole.BOTH],
        "features": [ModelFeature.TOOL_CALLING, ModelFeature.REASONING, ModelFeature.LONG_CONTEXT],
        "recommended_depths": ["标准", "深度", "全面"],
        "performance_metrics": {"speed": 3, "cost": 3, "quality": 5},
        "description": "硅基流动 DeepSeek-V3.2，旗舰全能",
    },
    "Pro/deepseek-ai/DeepSeek-V3.2-Exp": {
        "capability_level": 4,
        "suitable_roles": [ModelRole.DEEP_ANALYSIS, ModelRole.BOTH],
        "features": [ModelFeature.TOOL_CALLING, ModelFeature.REASONING, ModelFeature.LONG_CONTEXT],
        "recommended_depths": ["标准", "深度", "全面"],
        "performance_metrics": {"speed": 3, "cost": 3, "quality": 5},
        "description": "硅基流动 DeepSeek-V3.2 Pro 版",
    },
}


# ==================== 聚合渠道配置 ====================

AGGREGATOR_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "302ai": {
        "display_name": "302.AI",
        "description": "302.AI 聚合平台",
        "default_base_url": "https://api.302.ai/v1",
        "model_name_format": "{provider}/{model}",
    },
    "openrouter": {
        "display_name": "OpenRouter",
        "description": "OpenRouter 多模型网关",
        "default_base_url": "https://openrouter.ai/api/v1",
        "model_name_format": "{provider}/{model}",
    },
    "oneapi": {
        "display_name": "One API",
        "description": "One API 统一接口",
        "default_base_url": "http://localhost:3000/v1",
        "model_name_format": "{model}",
    },
    "newapi": {
        "display_name": "New API",
        "description": "New API 聚合",
        "default_base_url": "https://api.newapi.dev/v1",
        "model_name_format": "{provider}/{model}",
    },
}


# ==================== 徽章辅助函数 ====================

def get_model_capability_badge(level: int) -> str:
    """获取能力等级徽章"""
    badges = {1: "⚡基础", 2: "📊标准", 3: "🎯高级", 4: "🔥专业", 5: "👑旗舰"}
    return badges.get(level, f"L{level}")


def get_role_badge(role: ModelRole) -> str:
    """获取角色徽章"""
    badges = {
        ModelRole.QUICK_ANALYSIS: "⚡快速分析",
        ModelRole.DEEP_ANALYSIS: "🧠深度推理",
        ModelRole.BOTH: "🔄通用",
    }
    return badges.get(role, str(role))


def get_feature_badge(feature: ModelFeature) -> str:
    """获取特性徽章"""
    badges = {
        ModelFeature.TOOL_CALLING: "🔧工具调用",
        ModelFeature.LONG_CONTEXT: "📜长上下文",
        ModelFeature.REASONING: "💡强推理",
        ModelFeature.VISION: "👁️视觉",
        ModelFeature.FAST_RESPONSE: "⚡快速响应",
        ModelFeature.COST_EFFECTIVE: "💰高性价比",
    }
    return badges.get(feature, str(feature))

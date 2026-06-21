"""
API 占位接口 - 当主模块加载失败时提供降级响应
用于无登录/轻量模式下减少 404 错误
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.routers.auth_db import get_current_user
from app.core.response import ok

router = APIRouter(prefix="/api", tags=["stubs"])


@router.get("/notifications/unread_count")
async def stub_unread_count(user: dict = Depends(get_current_user)):
    """占位：未读通知数（主 notifications 模块不可用时）"""
    return ok(data={"count": 0})


@router.get("/workflows/templates")
async def stub_workflow_templates(user: dict = Depends(get_current_user)):
    """占位：工作流模板列表"""
    return ok(data=[])


class RecommendRequest(BaseModel):
    research_depth: str = "标准"


@router.post("/model-capabilities/recommend")
async def stub_model_recommend(
    request: RecommendRequest,
    user: dict = Depends(get_current_user)
):
    """占位：模型推荐（主 model-capabilities 不可用时返回默认）"""
    return ok(data={
        "quick_model": "qwen-plus",
        "deep_model": "qwen-max",
        "quick_model_info": {"capability_level": 2, "suitable_roles": [], "features": []},
        "deep_model_info": {"capability_level": 4, "suitable_roles": [], "features": []},
        "reason": "使用默认模型配置",
    })

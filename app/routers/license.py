"""
授权/许可证 API - 占位接口（无登录模式下返回默认状态）
"""
from fastapi import APIRouter, Depends

from app.routers.auth_db import get_current_user
from app.core.response import ok

router = APIRouter(prefix="/api/license", tags=["license"])


@router.get("/status")
async def get_license_status(
    force_refresh: bool = False,
    user: dict = Depends(get_current_user)
):
    """获取授权状态（占位：始终返回初级学员）"""
    return ok(data={
        "plan": "free",
        "isPro": False,
        "isTrial": False,
        "isExpired": False,
        "isExpiringSoon": False,
        "daysRemaining": None,
        "isOffline": False,
    })

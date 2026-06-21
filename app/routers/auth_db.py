"""
认证 - 无登录模式
仅提供 get_current_user 供其他路由使用，/me 供前端检查状态。
"""

from typing import Optional, Any

from fastapi import APIRouter, Depends, Header

router = APIRouter()

_DEFAULT_USER = {
    "id": "anonymous",
    "username": "anonymous",
    "email": "anonymous@local",
    "name": "anonymous",
    "is_admin": True,
    "roles": ["admin"],
    "preferences": {},
}


async def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    """获取当前用户（始终返回默认用户）"""
    return _DEFAULT_USER


@router.get("/me", summary="获取当前用户")
async def get_me(current_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """前端检查登录状态，始终返回默认用户"""
    return {"success": True, "data": current_user, "message": "ok"}


@router.post("/login", summary="登录（占位，始终成功）")
async def login() -> dict[str, Any]:
    """前端可能调用，直接返回成功"""
    return {"success": True, "data": {"user": _DEFAULT_USER, "token": "anonymous"}, "message": "ok"}

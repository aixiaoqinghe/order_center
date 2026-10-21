from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import Response, ErrorResponse
from app.schemas.user import (
    UserCreate,
    UserLogin, 
    UserLoginOut,
    UserOut,
    UserRegisterOut,
)
from app.services import user_service

router = APIRouter(prefix="/api/user", tags=["user"])

@router.post(
    "/register",
    response_model=Response[UserRegisterOut],
    responses={
        400: {"model": ErrorResponse, "description": "用户名已存在 / 参数校验失败"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"},
    },
)
def register(data: UserCreate, db: Session = Depends(get_db)):
    """用户注册

    校验用户名唯一性，Argon2id 哈希密码后写入用户表。

    400 错误场景：
    - user_name 已存在
    - user_name / user_password 长度不满足要求（参数校验失败）
    """
    user = user_service.create_user(db, data)
    return Response(msg="success registered", data=user)

@router.post(
    "/login",
    response_model=Response[UserLoginOut],
    responses={
        400: {"model": ErrorResponse, "description": "用户不存在 / 密码错误"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"},
    },
)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """用户登录

    校验用户名存在 + Argon2id 密码哈希比对，成功返回用户信息（user_id + user_name）。

    400 错误场景：
    - 用户不存在
    - 密码错误
    - user_name / user_password 缺失（参数校验失败）

    注意：日志侧不区分用户不存在 vs 密码错误，避免用户名枚举；但返回给前端的 msg 会区分。
    """
    user = user_service.login(db, data)
    return Response(msg="success login", data=user)

@router.get(
    "/info",
    response_model=Response[UserOut],
    responses={
        400: {"model": ErrorResponse, "description": "用户不存在 / 参数校验失败"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"},
    },
)
def info(
    user_id: int = Query(..., description="用户ID，必填", gt=0),
    db: Session = Depends(get_db),
):
    """查询用户信息

    根据 user_id 查询用户基本信息（不含 user_password）。

    400 错误场景：
    - user_id 未传 / <= 0（参数校验失败）
    - 用户不存在
    """
    user = user_service.get_user_by_id(db, user_id)
    return Response(msg="success", data=user)
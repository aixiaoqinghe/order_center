from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import Response, ErrorResponse
from app.schemas.user import (
    LoginUserInfo,
    UserCreate,
    UserLogin, 
    UserLoginOut,
    UserOut,
    UserRegisterOut,
)
from app.services import user_service
from app.utils.deps import bearer_scheme, get_current_user
from app.utils.security import create_access_token

from app.models.user import User

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
    token = create_access_token(user.user_id)
    return Response(
        msg="登录成功",
        data=UserLoginOut(
            token=token,
            user=LoginUserInfo.model_validate(user),
        ),
    )

@router.get(
    "/info",
    response_model=Response[UserOut],
    responses={
        401: {"model": ErrorResponse, "description": "token 缺失 / 无效 / 已过期"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"},
    },
    dependencies=[Depends(bearer_scheme)],
)
def info(
    current_user: User = Depends(get_current_user),
):
    """查询当前登录用户信息

    从 token 解析用户身份，返回该用户基本信息（不含 user_password）。

    401 场景：
    - 缺失 Authorization 头
    - token 签名非法 / 已过期
    - token 中的用户不存在（被删）
    """
    return Response(msg="success", data=current_user)
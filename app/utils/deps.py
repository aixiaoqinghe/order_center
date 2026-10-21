from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.services.user_service import get_user_by_id
from app.utils.exceptions import TokenInvalidError, UserNotFoundError

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
        db: Session = Depends(get_db),
):
    if credentials is None:
        raise TokenInvalidError("缺失认证凭证")
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        raise TokenInvalidError("token 无效或已过期")

    user_id = payload.get("sub")
    if user_id is None:
        raise TokenInvalidError("token 缺少 sub")
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        raise TokenInvalidError("token sub 非法")

    try:
        user = get_user_by_id(db, uid)
    except UserNotFoundError:
        raise TokenInvalidError("用户不存在或已被删除")
    return user
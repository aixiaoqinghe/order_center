from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate, UserLogin
from app.utils.exceptions import (
    PasswordError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.utils.security import hash_password, verify_password

def get_user_by_name(db: Session, name: str) -> User | None:
    """按用户名查用户，查不到返回None"""
    return db.query(User).filter(User.user_name == name).first()

def get_user_by_id(db: Session, user_id: int) -> User | None:
    """按 id 查用户，查不到返回 None"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        raise UserNotFoundError
    return user

def create_user(db: Session, data: UserCreate) -> User:
    """注册：查重 -> 哈希 -> 写库 -> commit"""
    # 1.查重
    if get_user_by_name(db, data.user_name) is not None:
        raise UserAlreadyExistsError(f"用户名已存在:{data.user_name}")

    # 2.哈希密码（明文只在内存里存这一下）
    user = User(
        user_name=data.user_name,
        user_password=hash_password(data.user_password),
        user_nickname=data.user_nickname,
        user_phonenumber=data.user_phonenumber,
    )

    # 3.写库
    try:
        db.add(user)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(user) # 拿回自增 user_id 和 DB 默认值
    return user

def login(db: Session, data: UserLogin) -> User:
    """登录：查用户 -> 校验密码 -> 返回"""
    user = get_user_by_name(db, data.user_name)
    if user is None:
        raise PasswordError("用户名或密码错误")

    if not verify_password(data.user_password, user.user_password):
        raise PasswordError("用户名或密码错误")
    
    return user
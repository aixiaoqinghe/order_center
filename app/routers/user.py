from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import Response
from app.schemas.user import (
    UserCreate,
    UserLogin, 
    UserLoginOut,
    UserOut,
    UserRegisterOut,
)
from app.services import user_service

router = APIRouter(prefix="/api/user", tags=["user"])

@router.post("/register", response_model=Response[UserRegisterOut])
def register(data: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    user = user_service.create_user(db, data)
    return Response(msg="success registered", data=user)

@router.post("/login", response_model=Response[UserLoginOut])
def login(data: UserLogin, db: Session = Depends(get_db)):
    """用户登录"""
    user = user_service.login(db, data)
    return Response(msg="success login", data=user)

@router.get("/info", response_model=Response[UserOut])
def info(user_id:int, db: Session = Depends(get_db)):
    """查询用户信息"""
    user = user_service.get_user_by_id(db, user_id)
    return Response(msg="success", data=user)

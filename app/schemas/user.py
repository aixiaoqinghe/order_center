from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, ConfigDict, Field, field_serializer

class UserCreate(BaseModel):
    """注册入参:只收前端该传的字段"""
    user_name: str = Field(..., min_length=4, max_length=20, description="用户名")
    user_password: str = Field(..., min_length=6, max_length=20, description="明文密码")
    user_nickname: str | None = Field(None, max_length=50, description="昵称")
    user_phonenumber: str | None = Field(None, max_length=11, description="手机号")

class UserLogin(BaseModel):
    """登录入参"""
    user_name: str = Field(..., max_length=20)
    user_password: str = Field(..., max_length=20)

class UserRegisterOut(BaseModel):
    """注册返回 data"""
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    user_name: str
    user_createtime: datetime

class UserLoginOut(BaseModel):
    """登录返回 data"""
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    user_name: str

# 东八区时区(固定偏移)
CST = timezone(timedelta(hours=8))

class UserOut(BaseModel):
    """返回出参:绝对不含 user_password"""
    # from_attributes 让 Pydantic 能直接吃 ORM 对象
    model_config = ConfigDict(from_attributes = True)
    user_id: int
    user_name: str
    user_nickname: str | None = None
    user_createtime: datetime
    user_phonenumber: str | None = None

    # 自定义序列化:把 UTC 时间转成东八区的 "YYYY-MM-DD HH:mm:ss"
    @field_serializer("user_createtime")
    def serialize_createtime(self, dt: datetime) -> str:
        # 从 ORM 拿的 dt 是 UTC 时间，转成东八区再格式化
        return dt.astimezone(CST).strftime("%Y-%m-%d %H:%M:%S")


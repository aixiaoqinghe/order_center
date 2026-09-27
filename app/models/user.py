from datetime import datetime, timezone
from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class User(Base):
    """用户表 ORM 模型，对应 docs/schema.sql 的 user 表"""
    __tablename__ = "user"

    user_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="用户id,主键"
    )

    user_name: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, comment="用户名"
    )
    # 存的是 Argon2id 哈希后的串，所以给100长度
    user_password: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="用户密码(Argon2id哈希)"
    )
    user_nickname: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="用户昵称"
    )
    # 强制 UTC: 默认值用 Python 侧生成，避免 DB 时区不一致
    user_createtime: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda:datetime.now(timezone.utc),
        comment="创建时间(UTC)",
    )
    user_phonenumber: Mapped[str | None] = mapped_column(
        String(11), nullable=True, comment="手机号"
    )

    def __repr__(self) -> str:
        return f"<User id={self.user_id} name={self.user_name}>"
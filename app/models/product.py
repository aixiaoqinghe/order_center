# app/models/product.py
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Product(Base):
    """商品表 ORM 模型，对应 docs/schema.sql 的 product 表"""

    __tablename__ = "product"

    product_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="商品id,主键"
    )
    product_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="商品名称"
    )
    product_createtime: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="创建时间(UTC)",
    )
    product_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="商品类别"
    )
    # 价格用 Numeric，不用 float，避免精度误差
    product_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="商品价格"
    )

    def __repr__(self) -> str:
        return f"<Product id={self.product_id} name={self.product_name}>"
from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

class Inventory(Base):
    """库存表 ORM 模型，对应 docs/schema.sql 的 inventory 表"""

    __tablename__ = "inventory"

    # product_id 既是主键，也是指向 product 的外键（schema.sql 里没显式写 FK，按主键处理）
    product_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, comment="商品id,主键"
    )
    total_stock: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="总库存"
    )
    locked_stock: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="锁定库存"
    )

    def __repr__(self) -> str:
        return f"<Inventory pid={self.product_id} total={self.total_stock} locked={self.locked_stock}>"
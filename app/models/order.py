from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Integer, Numeric, String, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

class Order(Base):
    """订单表 ORM 模型，对应 docs/schema.sql 的 order 表"""

    __tablename__ = "order"

    order_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="订单id,主键"
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True, comment="用户id"
    )
    order_total_num: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="下单总数量"
    )
    order_total_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="订单总金额"
    )
    order_createtime: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="下单时间(UTC)",
    )
    # onupdate: 每次 UPDATE 时自动刷新这个字段
    order_updatetime: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="状态变更时间(UTC)",
    )
    order_status: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, comment="订单状态:0待支付 1已支付 2已完成 3已取消"
    )
    order_cancel_reason: Mapped[str | None] = mapped_column(
        String(256), nullable=True, comment="取消原因"
    )
    def __repr__(self) -> str:
        return f"<Order id={self.order_id} user={self.user_id} status={self.order_status}>"

class OrderItem(Base):
    """订单明细表 ORM 模型，对应 docs/schema.sql 的 order_item 表"""

    __tablename__ = "order_item"

    # 联合主键：order_id + product_id
    order_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, comment="订单id"
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, index=True, comment="商品id"
    )
    order_item_num: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="下单件数"
    )
    # 下单时的快照金额
    order_item_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="下单时的金额"
    )
    order_item_subtotal: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="下单小计"
    )
    product_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="下单时商品名"
    )

    def __repr__(self) -> str:
        return f"<OrderItem order={self.order_id} product={self.product_id} num={self.order_item_num}>"
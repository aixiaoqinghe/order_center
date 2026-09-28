from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ===== 入参 =====

class OrderItemCreate(BaseModel):
    """创建订单入参里的 items 每项"""
    product_id: int
    order_item_num: int = Field(..., ge=1, le=100)

class OrderCreate(BaseModel):
    """创建订单入参"""
    user_id: int
    items: list[OrderItemCreate]

# ===== 出参 =====

class OrderItemOut(BaseModel):
    """items[] 出参(创建/详情共用) """
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    order_item_num: int
    order_item_amount: Decimal
    order_item_subtotal: Decimal

class OrderCreateOut(BaseModel):
    """创建订单出参(含 user_id, 含 items)"""
    model_config = ConfigDict(from_attributes=True)

    order_id: int
    user_id: int
    order_total_num: int
    order_createtime: datetime
    order_total_amount: Decimal
    order_status: int
    order_cancel_reason: str | None = None
    items: list[OrderItemOut]

class OrderDetailOut(BaseModel):
    """订单详情出参(不含 user_id, 含 items )"""
    model_config = ConfigDict(from_attributes=True)

    order_id: int
    order_total_num: int
    order_createtime: datetime
    order_total_amount: Decimal
    order_status: int
    order_cancel_reason: str | None = None
    items: list[OrderItemOut]

class OrderListItem(BaseModel):
    """列表每项(不含 items,不含 user_id)"""
    model_config = ConfigDict(from_attributes=True)

    order_id: int
    order_total_num: int
    order_total_amount: Decimal
    order_createtime: datetime
    order_status: int
    order_cancel_reason: str | None = None

class OrderListData(BaseModel):
    """列表包装"""
    user_id: int
    list: list[OrderListItem]
    total: int
    page: int
    size: int


class OrderCancelOut(BaseModel):
    """取消出参"""
    model_config = ConfigDict(from_attributes=True)

    order_id: int
    order_status: int
    order_cancel_reason: str | None = None

class OrderCancelIn(BaseModel):
    """取消订单入参（body）"""
    user_id: int
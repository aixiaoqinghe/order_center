from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

class ProductCreate(BaseModel):
    """创建商品入参"""
    product_name: str = Field(..., min_length=4, max_length=20)
    product_type: str | None = Field(None, min_length=2, max_length=20)
    product_amount: Decimal = Field(..., ge=0, le=1000000)
    total_stock: int = Field(..., ge=0, le=1000000)


class ProductListItem(BaseModel):
    """商品列表里的单项"""
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    product_type: str | None = None
    product_amount: Decimal

class ProductDetailOut(BaseModel):
    """商品详情出参"""
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    product_createtime: datetime
    product_type: str | None = None
    product_amount: Decimal
    available_stock: int     # 计算字段，service层算好传进来

class ProductCreateOut(BaseModel):
    """创建商品返回"""
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    product_amount: Decimal
    total_stock: int

class ProductListData(BaseModel):
    """商品列表分页包装"""
    list: list[ProductListItem]
    total: int
    page: int
    size: int
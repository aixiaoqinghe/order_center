from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import Response, ErrorResponse
from app.schemas.product import (
    ProductCreate,
    ProductCreateOut,
    ProductDetailOut,
    ProductListData,
)
from app.services import product_service

router = APIRouter(prefix="/api/product", tags=["product"])

@router.get(
    "/list",
    response_model=Response[ProductListData],
    responses={
        500: {"model": ErrorResponse, "description": "服务器内部错误"},
    },
)
def list_products(
    page: int = Query(1, ge=1, le=100, description="页码，从 1 开始，上限 100"),
    size: int = Query(30, ge=10, le=50, description="每页数量，10-50"),
    db: Session = Depends(get_db),
):
    """分页查询商品列表

    按 product_id 升序分页返回商品基本信息，返回结构含 list + total + page + size。

    注意：列表返回的是 ProductListItem（不含库存），查商品详情（/api/product/{product_id}）
    会额外返回 available_stock（可售库存）。
    """
    data = product_service.product_page_list(db, page, size)
    return Response(msg="success found", data=data)

@router.get(
    "/{product_id}",
    response_model=Response[ProductDetailOut],
    responses={
        400: {"model": ErrorResponse, "description": "商品不存在 / 库存记录不存在"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"},
    },
)
def get_product(
    product_id: int = Path(..., gt=0, description="商品ID，必填"),
    db: Session = Depends(get_db),
):
    """查询商品详情

    跨 product + inventory 表拼接，返回商品基本信息 + 可售库存（total_stock - locked_stock）。

    400 错误场景：
    - 商品不存在
    - 库存记录不存在（商品存在但 inventory 行缺失）
    - product_id <= 0（参数校验失败）
    """
    data = product_service.product_detail(db, product_id)
    return Response(msg="success found", data=data)

@router.post(
    "/create",
    response_model=Response[ProductCreateOut],
    responses={
        500: {"model": ErrorResponse, "description": "服务器内部错误"},
    },
)
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    """创建商品

    同时写 product 和 inventory 两张表，同一事务提交：
    - product：基本信息（name / type / amount）
    - inventory：total_stock 取请求值，locked_stock 初始为 0

    参数校验失败（字段违反长度/数值约束）会返回 422。
    """
    result = product_service.create_product(db, data)
    return Response(msg="success created", data=result)
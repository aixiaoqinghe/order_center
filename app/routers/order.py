from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import Response
from app.schemas.order import (
    OrderCancelIn,
    OrderCancelOut,
    OrderCreate,
    OrderCreateOut,
    OrderDetailOut,
    OrderListData,
)
from app.services import order_service

from fastapi import Depends
from app.redis_client import get_redis

router = APIRouter(prefix="/api/order", tags=["order"])

@router.post("/create",response_model=Response[OrderCreateOut])
async def create_order(data: OrderCreate, db: Session = Depends(get_db), redis=Depends(get_redis)):
    """创建订单"""
    result = await order_service.create_order(db, redis, data.user_id, data)
    return Response(msg="success created", data=result)

@router.get("/detail/{order_id}", response_model=Response[OrderDetailOut])
def get_order_detail(
    order_id: int,
    user_id: int = Query(..., description="用户ID"),
    db: Session = Depends(get_db),
):
    """订单详情"""
    result = order_service.get_order_detail(db, order_id, user_id)
    return Response(msg="success found", data=result)

@router.get("/list", response_model=Response[OrderListData])
def get_order_list(
    user_id: int = Query(..., description="用户ID"),
    page: int = Query(1, ge=1, le=100, description="页码"),
    size: int = Query(30, ge=10, le=50, description="每页数量"),
    db: Session = Depends(get_db),
):
    """订单列表"""
    result = order_service.get_order_list(db, user_id, page, size)
    return Response(msg="success found", data=result)

@router.post("/cancel/{order_id}", response_model=Response[OrderCancelOut])
def cancel_order(
    order_id: int,
    data: OrderCancelIn,
    db: Session = Depends(get_db)
):
    """取消订单"""
    result = order_service.cancel_order(db, order_id, data.user_id)
    return Response(msg="success canceled", data=result)
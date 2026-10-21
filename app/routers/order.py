from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import Response, ErrorResponse
from app.schemas.order import (
    OrderCancelOut,
    OrderCreate,
    OrderCreateOut,
    OrderDetailOut,
    OrderListData,
    OrderPayOut,
)
from app.services import order_service

from fastapi import Depends
from app.redis_client import get_redis

from app.utils.deps import get_current_user, bearer_scheme
from app.models.user import User   

router = APIRouter(prefix="/api/order", tags=["order"], dependencies=[Depends(bearer_scheme)])

@router.post(
    "/create",
    response_model=Response[OrderCreateOut],
    responses={
        400: {"model": ErrorResponse, "description": "业务错误：商品不存在/库存不足/分布式锁抢不到"},
        401: {"model": ErrorResponse, "description": "token 缺失 / 无效 / 已过期"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"},
    },
)
async def create_order(
    data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis=Depends(get_redis),
):
    """创建订单

    从 token 解析当前用户身份（忽略 body 中的 user_id，以 token 为准）。
    根据用户提交的商品列表创建订单，接口异步化，DB 操作为同步调用（通过线程池隔离阻塞，不阻塞事件循环）。

    执行步骤：
    - 同一 product_id 的商品合并、数量累加
    - 升序 product_id 加 Redis 分布式锁（防死锁）
    - 库存校验 → 预扣 locked_stock → flush 拿 order_id → 发 MQ
    - commit 后查完整订单返回
    - 最后发 MQ 设置超时自动关单

    400 错误场景：
    - 商品不存在
    - 库存不足（total_stock - locked_stock < 下单数量）
    - 分布式锁抢不到（并发冲突）

    返回完整订单对象，含订单项明细。
    """
    result = await order_service.create_order(db, redis, current_user.user_id, data)
    return Response(msg="success created", data=result)

@router.get(
    "/detail/{order_id}",
    response_model=Response[OrderDetailOut],
    responses={
        400: {"model": ErrorResponse, "description": "订单不存在"},
        401: {"model": ErrorResponse, "description": "token 缺失 / 无效 / 已过期"},
        403: {"model": ErrorResponse, "description": "无权访问该订单"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"},
    },
)
def get_order_detail(
    order_id: int = Path(..., gt=0, description="订单ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询订单详情

    从 token 解析当前用户身份，返回订单基本信息与订单项明细。
    订单不存在返回业务错误；非本人订单返回 403。
    """
    result = order_service.get_order_detail(db, current_user.user_id, order_id)
    return Response(msg="success found", data=result)

@router.get(
    "/list",
    response_model=Response[OrderListData],
    responses={
        401: {"model": ErrorResponse, "description": "token 缺失 / 无效 / 已过期"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"},
    },
)
def get_order_list(
    page: int = Query(1, ge=1, description="页码，从1开始"),
    size: int = Query(10, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询当前登录用户订单列表

    从 token 解析当前用户身份，分页返回该用户订单列表。
    """
    result = order_service.get_order_list(db, current_user.user_id, page, size)
    return Response(msg="success found", data=result)

@router.post(
    "/cancel/{order_id}",
    response_model=Response[OrderCancelOut],
    responses={
        400: {"model": ErrorResponse, "description": "订单不存在/状态不允许取消/库存记录不存在"},
        401: {"model": ErrorResponse, "description": "token 缺失 / 无效 / 已过期"},
        403: {"model": ErrorResponse, "description": "无权操作该订单"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"},
    },
)
def cancel_order(
    order_id: int = Path(..., gt=0, description="订单ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """取消订单

    从 token 解析当前用户身份。仅待支付订单可取消，取消后释放锁定库存。
    订单不存在、订单状态不允许取消时返回业务错误；非本人订单返回 403。
    """
    result = order_service.cancel_order(db, current_user.user_id, order_id)
    return Response(msg="success canceled", data=result)

@router.post(
    "/pay/{order_id}",
    response_model=Response[OrderPayOut],
    responses={
        400: {"model": ErrorResponse, "description": "订单不存在/状态不允许支付"},
        401: {"model": ErrorResponse, "description": "token 缺失 / 无效 / 已过期"},
        403: {"model": ErrorResponse, "description": "无权支付该订单"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"},
    },
)
def pay_order(
    order_id: int = Path(..., gt=0, description="订单ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """支付订单

    从 token 解析当前用户身份。仅待支付订单可支付，非本人订单返回 403。
    """
    data = order_service.pay_order(db, current_user.user_id, order_id)
    return Response(code=200, msg="success paid", data=data)
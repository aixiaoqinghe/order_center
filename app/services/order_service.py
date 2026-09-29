from decimal import Decimal
import asyncio

from sqlalchemy.orm import Session
import logging

from app.models.inventory import Inventory
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User
from app.schemas.order import OrderCreate
from app.utils.exceptions import (
    InventoryNotFoundError,
    OrderForbiddenError,
    OrderNotFoundError,
    OrderStatusError,
    ProductNotFoundError,
    StockNotEnoughError,
    UserNotFoundError,
    LockAcquireFailedError,
)

from collections import defaultdict
from app.utils.lock import acquire, release

logger = logging.getLogger(__name__)

def _do_critical_section(db, merged: dict, user_id: int) -> dict:
    """同步临界区:库存校验+加锁+建单+commit,丢线程池跑不阻塞事件循环"""
    total_num = 0
    total_amount = 0
    item_snapshots = []

    for pid, m in merged.items():
        inventory = db.query(Inventory).filter_by(product_id=pid).first()
        if inventory is None:
            raise InventoryNotFoundError()
        if inventory.total_stock - inventory.locked_stock < m["order_item_num"]:
            raise StockNotEnoughError()

        inventory.locked_stock += m["order_item_num"]

        subtotal = m["order_item_amount"] * m["order_item_num"]

        item_snapshots.append({
            "product_id": m["product_id"],
            "product_name": m["product_name"],
            "order_item_num": m["order_item_num"],
            "order_item_amount": m["order_item_amount"],
            "order_item_subtotal": subtotal,
        })
        total_num += m["order_item_num"]
        total_amount += subtotal

    order = Order(
        user_id=user_id,
        order_status=0,
        order_total_num=total_num,
        order_total_amount=total_amount,
    )
    db.add(order)
    db.flush()

    for snap in item_snapshots:
        db.add(OrderItem(order_id=order.order_id, **snap))

    db.commit()
    db.refresh(order)

    items = db.query(OrderItem).filter(OrderItem.order_id == order.order_id).all()

    return {
        "order_id": order.order_id,
        "user_id": order.user_id,
        "order_total_num": order.order_total_num,
        "order_total_amount": order.order_total_amount,
        "order_createtime": order.order_createtime,
        "order_status": order.order_status,
        "order_cancel_reason": order.order_cancel_reason,
        "items": [
            {
                "product_id": it.product_id,
                "product_name": it.product_name,
                "order_item_num": it.order_item_num,
                "order_item_amount": it.order_item_amount,
                "order_item_subtotal": it.order_item_subtotal,
            }
            for it in items
        ],
    }

async def create_order(db, redis, user_id, data):
    # 同一 product_id 只保留一条，数量累加，防重复提交把自己锁挡死 / order_item 撞主键
    merged = {}
    for item in data.items:
        product = db.query(Product).filter_by(product_id=item.product_id).first()
        if product is None:
            raise ProductNotFoundError()

        if item.product_id not in merged:
            merged[item.product_id] = {
                "product_id": item.product_id,
                "product_name": product.product_name,
                "order_item_num": 0,
                "order_item_amount": product.product_amount,    # 单价
            }
        merged[item.product_id]["order_item_num"] += item.order_item_num

    # 升序 product_id + 加锁
    product_ids = sorted(merged.keys())

    held_locks = {}
    try:
        for pid in product_ids:
            value = await acquire(redis, pid)
            if value is None:
                raise LockAcquireFailedError()
            held_locks[pid] = value

        # 临界区:同步db操作丢线程池,不阻塞事件循环,让其他请求能及时抢锁
        result = await asyncio.to_thread(_do_critical_section, db, merged, user_id)

        return result

    except Exception:
        db.rollback()
        raise

    finally:
        # 逆序释放
        for pid in reversed(list(held_locks.keys())):
            try:
                await release(redis, pid, held_locks[pid])
            except Exception:
                # 释放锁的异常是warn不raise:因为锁有 TTL,即使锁释放失败，60s后Redis回自动清理掉
                logger.warning(f"release lock failed: product_id={pid}")

def get_order_detail(db: Session, order_id: int, user_id: int) -> dict:
    """订单详情:查 order -> 校验归属 -> 查 items"""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if order is None:
        raise OrderNotFoundError(f"订单不存在:{order_id}")

    if order.user_id != user_id:
        raise OrderForbiddenError("无权查看该订单")

    items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()

    return {
        "order_id": order.order_id,
        "order_total_num": order.order_total_num,
        "order_createtime": order.order_createtime,
        "order_total_amount": order.order_total_amount,
        "order_status": order.order_status,
        "order_cancel_reason": order.order_cancel_reason,
        "items": [
            {
                "product_id": it.product_id,
                "product_name": it.product_name,
                "order_item_num": it.order_item_num,
                "order_item_amount": it.order_item_amount,
                "order_item_subtotal": it.order_item_subtotal,
            }
            for it in items
        ],
    }

def get_order_list(db: Session, user_id: int, page: int, size: int) -> dict:
    """订单列表：分页查该 user 的订单"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        raise UserNotFoundError(f"用户不存在:{user_id}")

    total = db.query(Order).filter(Order.user_id == user_id).count()
    offset = (page - 1) * size
    orders = (
        db.query(Order)
        .filter(Order.user_id == user_id)
        .order_by(Order.order_id.desc())
        .offset(offset)
        .limit(size)
        .all()
    )

    return {
        "user_id": user_id,
        "list": [
            {
                "order_id": o.order_id,
                "order_total_num": o.order_total_num,
                "order_total_amount": o.order_total_amount,
                "order_createtime": o.order_createtime,
                "order_status": o.order_status,
                "order_cancel_reason": o.order_cancel_reason,
            }
            for o in orders
        ],
        "total": total,
        "page": page,
        "size": size,
    }

def cancel_order(db: Session, user_id: int,order_id: int) -> dict:
    """取消订单：校验状态 -> 回滚库存(locked -= n) -> 改 status/reason"""
    try:
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if order is None:
            raise OrderNotFoundError(f"订单不存在:{order_id}")

        if order.user_id != user_id:
            raise OrderForbiddenError("无权取消该订单")
        
        if order.order_status != 0:
            raise OrderStatusError(f"订单当前状态不允许取消:{order.order_status}")

        # 回滚库存: locked -= n (简化版，total 先不动)
        items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        for it in items:
            inventory = db.query(Inventory).filter(Inventory.product_id == it.product_id).first()

            if inventory is None:
                raise InventoryNotFoundError(f"库存记录不存在: {it.product_id}")
            inventory.locked_stock -= it.order_item_num
        # 改状态
        order.order_status = 3
        order.order_cancel_reason = "用户取消订单"

        db.commit()
        db.refresh(order)

    except Exception:
        db.rollback()
        raise

    return {
        "order_id": order.order_id,
        "order_status": order.order_status,
        "order_cancel_reason": order.order_cancel_reason,
    }
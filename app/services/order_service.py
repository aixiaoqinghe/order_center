from decimal import Decimal
import asyncio

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
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
    ConsumeStockError
)

from collections import defaultdict
from app.utils.lock import acquire, release

from app.mq_client import publish_order_created, publish_order_timeout
from app.config import settings

logger = logging.getLogger(__name__)

async def _do_critical_section(db, merged: dict, user_id: int) -> dict:
    """临界区:同步DB操作丢线程池 → flush拿到order_id → 发MQ → 再commit, 全程不阻塞事件循环"""

    def _db_flush():
        """阶段1:库存校验 + 建单 + flush(拿到 order_id, 但不 commit)"""
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

        mq_items = [
            {
                "product_id": pid,
                "order_item_num": m["order_item_num"],
                "order_item_amount": str(m["order_item_amount"]),
            }
            for pid, m in merged.items()
        ]
        return order.order_id, mq_items

    order_id, mq_items = await asyncio.to_thread(_db_flush)

    await publish_order_created(order_id, user_id, mq_items)

    def _db_commit():
        """阶段2:commit + refresh + 返回完整订单数据"""
        db.commit()
        order = db.query(Order).filter(Order.order_id == order_id).first()
        db.refresh(order)
        items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        return order, items

    order, items = await asyncio.to_thread(_db_commit)

    await publish_order_timeout(order_id)

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

        result = await _do_critical_section(db, merged, user_id)

        logger.info("下单成功: order_id=%s, user_id=%s", result["order_id"], user_id)
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

def get_order_detail(db: Session, user_id: int, order_id: int) -> dict:
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

def cancel_order(db: Session, user_id: int, order_id: int) -> dict:
    """取消订单：校验状态 -> FOR UPDATE 锁行看 locked 真实值 -> 回滚库存 -> 改 status/reason"""
    try:
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if order is None:
            raise OrderNotFoundError(f"订单不存在:{order_id}")

        if order.user_id != user_id:
            raise OrderForbiddenError("无权取消该订单")

        if order.order_status != 0:
            raise OrderStatusError(f"订单当前状态不允许取消:{order.order_status}")

        items = (
            db.query(OrderItem)
            .filter(OrderItem.order_id == order_id)
            .order_by(OrderItem.product_id.asc())
            .all()
        )

        for it in items:
            row = db.execute(
                text(
                    "SELECT total_stock, locked_stock FROM inventory "
                    "WHERE product_id = :pid FOR UPDATE"
                ),
                {"pid": it.product_id},
            ).fetchone()

            if row is None:
                raise InventoryNotFoundError(f"库存记录不存在: {it.product_id}")

            locked = row[1]
            if locked >= it.order_item_num:
                db.execute(
                    text(
                        "UPDATE inventory SET total_stock = total_stock + :n, "
                        "locked_stock = locked_stock - :n "
                        "WHERE product_id = :pid"
                    ),
                    {"n": it.order_item_num, "pid": it.product_id},
                )
            else:
                db.execute(
                    text(
                        "UPDATE inventory SET total_stock = total_stock + :n "
                        "WHERE product_id = :pid"
                    ),
                    {"n": it.order_item_num, "pid": it.product_id},
                )

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

async def consume_order(db, redis, order_id: int, items: list):
    """消费者扣库存 + 幂等(三层 Redis setnx + DB 唯一约束 + 查 consumer_idempotent 状态判断)"""

    # 1. 第一层幂等：Redis 幂等：抢 key, 抢不到说明已处理
    key = f"idem:order:{order_id}"
    ok = await redis.set(key, "1", nx=True, ex=settings.IDEMPOTENT_TTL_SECONDS)
    if not ok:
        logger.warning(f"[幂等拦截] Redis hit, order_id={order_id}")
        return       # key已存在,已处理，正常返回(调用方 ack)

    # 2. 第三层幂等：查 consumer_idempotent 状态判断
    # 位置: setnx 之后、插入 consumer_idempotent 之前
    # 目的: 防"处理中崩溃"留下的半成品(status=0) 和 "失败残留" (status=2)
    row = db.execute(
        text("SELECT consume_status FROM consumer_idempotent WHERE order_id = :oid"),
        {"oid": order_id}
    ).fetchone()

    need_insert = True    # 是否需要插 consumer_idempotent
    if row is not None:
        status = row[0]
        if status == 1:
            # 已成功处理，直接return 
            return
        # status == 0 或 2: 半成品/失败，继续往下处理，但不用再插了
        need_insert = False

    # 3. 第二层幂等：DB 幂等：插占位记录(单独事务 commit, 失败残留 status=0)
    if need_insert:
        try:
            db.execute(text(
                "INSERT INTO consumer_idempotent(order_id, consume_status, result_msg)"
                "VALUES (:oid, 0, :msg)"
            ), {"oid": order_id, "msg": "正在处理该消息中"})
            db.commit()
        except IntegrityError:
            # 主键冲突：说明这条记录已存在(可能 Redis 失效导致第一层没拦住)
            # catch 后跳过插入，直接往下扣库存
            db.rollback()
            logger.warning(f"[幂等拦截] DB hit, order_id={order_id}")
            return    # 已处理，正常返回

    # 3. 每个 item 原子扣库存
    for item in items:
        pid = item["product_id"]
        n = item["order_item_num"]
        result = db.execute(text(
            "UPDATE inventory SET total_stock = total_stock - :n, "
            "locked_stock = locked_stock - :n "
            "WHERE product_id = :pid AND locked_stock >= :n"
        ), {"n": n, "pid": pid})
        if result.rowcount == 0:
            raise ConsumeStockError(f"扣库存失败: product_id={pid}, n={n}")

    # 4.更新幂等记录为成功
    # 更新 status=1(成功),不管是need_insert=True 还是 False,最终都要更新成1
    db.execute(text(
        "UPDATE consumer_idempotent SET consume_status = 1, result_msg = :msg "
        "WHERE order_id = :oid"
    ), {"msg": "该消息已经处理成功", "oid": order_id})
    db.commit()

async def consume_order_timeout(db, order_id: int):
    """
    Day9: 超时关单消费逻辑
    - status = 0 待支付 -> 关单 + 回滚库存
    - status != 0 -> 直接返回(幂等：状态已流转，不再关)
    - 订单不存在 -> 直接返回
    - 回滚分两种：consumer_idempotent.status=1 说明消费者扣过，只回 total；
      否则完整回滚 total + locked。FOR UPDATE 锁行防竞态，升序 product_id 防死锁
    """
    logger.info("[consume_order_timeout] 开始处理 order_id=%s", order_id)
    order = db.execute(
        text("SELECT order_status FROM `order` WHERE order_id = :oid"),
        {"oid": order_id}
    ).fetchone()

    if order is None:
        logger.info("[consume_order_timeout] order_id=%s 不存在，跳过", order_id)
        return

    status = order[0]
    logger.info("[consume_order_timeout] order_id=%s 当前 status=%s", order_id, status)
    if status != 0:
        logger.info("[consume_order_timeout] order_id=%s 已流转(status=%s)，跳过", order_id, status)
        return

    row = db.execute(
        text("SELECT consume_status FROM consumer_idempotent WHERE order_id = :oid"),
        {"oid": order_id}
    ).fetchone()
    consumer_done = row is not None and row[0] == 1

    items = db.execute(
        text(
            "SELECT product_id, order_item_num FROM order_item "
            "WHERE order_id = :oid ORDER BY product_id ASC"
        ),
        {"oid": order_id}
    ).fetchall()

    logger.info("[consume_order_timeout] order_id=%s consumer_done=%s, %d 件商品需回滚", order_id, consumer_done, len(items))
    for item in items:
        pid, n = item[0], item[1]

        db.execute(
            text("SELECT * FROM inventory WHERE product_id = :pid FOR UPDATE"),
            {"pid": pid},
        )

        if consumer_done:
            db.execute(
                text("UPDATE inventory SET total_stock = total_stock + :n WHERE product_id = :pid"),
                {"n": n, "pid": pid},
            )
        else:
            result = db.execute(
                text(
                    "UPDATE inventory SET total_stock = total_stock + :n, "
                    "locked_stock = locked_stock - :n "
                    "WHERE product_id = :pid AND locked_stock >= :n"
                ),
                {"n": n, "pid": pid},
            )
            if result.rowcount == 0:
                raise ConsumeStockError(f"超时回滚库存失败: product_id={pid}")

    db.execute(
        text(
            "UPDATE `order` SET order_status = 3, "
            "order_cancel_reason = :reason WHERE order_id = :oid"
        ),
        {"oid": order_id, "reason": "超时未支付"}
    )
    db.commit()
    logger.info("[consume_order_timeout] order_id=%s 关单完成，status=3", order_id)


def pay_order(db: Session, user_id: int, order_id: int) -> dict:
    """模拟支付: 归属校验 → 仅待支付订单可支付 → 改状态为已支付"""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if order is None:
        raise OrderNotFoundError()

    if order.user_id != user_id:
        raise OrderForbiddenError("无权支付该订单")

    if order.order_status != 0:
        raise OrderStatusError("该订单状态不可支付")

    order.order_status = 1
    db.commit()
    return {"order_id": order.order_id, "order_status": order.order_status}
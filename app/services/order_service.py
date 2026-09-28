from decimal import Decimal

from sqlalchemy.orm import Session

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
)

def create_order(db: Session, data: OrderCreate) -> dict:
    """创建订单(无并发版):校验 -> 扣 locked -> 写 order + order_item"""
    try:
        # 1.校验 user
        user = db.query(User).filter(User.user_id == data.user_id).first()
        if user is None:
            raise UserNotFoundError(f"用户不存在:{data.user_id}")
        # 2.遍历 items: 查商品、查库存、校验、扣 locked、记快照
        item_snapshots = []
        total_num = 0
        total_amount = Decimal("0.00")
        for item in data.items:
            product = db.query(Product).filter(Product.product_id == item.product_id).first()
            if product is None:
                raise ProductNotFoundError(f"商品不存在:{item.product_id}")
            inventory = db.query(Inventory).filter(Inventory.product_id == item.product_id).first()
            if inventory is None:
                raise StockNotEnoughError(f"商品无库存记录:{item.product_id}")
            available = inventory.total_stock - inventory.locked_stock
            if available < item.order_item_num:
                raise StockNotEnoughError(
                    f"商品库存不足:{item.product_id}, 可售={available}, 需要={item.order_item_num}"
                )
            # 扣锁库存
            inventory.locked_stock += item.order_item_num
            # 快照
            subtotal = product.product_amount * item.order_item_num
            item_snapshots.append({
                "product_id": product.product_id,
                "product_name": product.product_name,
                "order_item_num": item.order_item_num,
                "order_item_amount": product.product_amount,
                "order_item_subtotal": subtotal
            })
            total_num += item.order_item_num
            total_amount += subtotal
        # 3.写 order
        order = Order(
            user_id=data.user_id,
            order_total_num=total_num,
            order_total_amount=total_amount,
            order_status=0
        )
        db.add(order)
        db.flush()    # 拿 order_id
        # 4.写 order_item
        for snap in item_snapshots:
            db.add(OrderItem(order_id=order.order_id, **snap))
        db.commit()
        db.refresh(order)

    except Exception:
        db.rollback()
        raise
        # 5.拼返回 dict
    return {
        "order_id": order.order_id,
        "user_id": order.user_id,
        "order_total_num": order.order_total_num,
        "order_createtime": order.order_createtime,
        "order_total_amount": order.order_total_amount,
        "order_status": order.order_status,
        "order_cancel_reason": order.order_cancel_reason,
        "items": item_snapshots,
    }

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
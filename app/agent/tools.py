from langchain_core.tools import tool
from app.database import SessionLocal
from app.models.order import Order, OrderItem
from app.models.inventory import Inventory

# 注: Day6 工具直接查 ORM，不校验 user_id；Day7 接路由时升级为带 user_id 调 order_service
# get_logistics 项目无物流表，返回固定文案，不瞎编。

@tool
def get_order_info(order_id: int) -> str:
    """
        根据订单 ID 查询订单状态、金额、创建时间。
        当用户询问订单进度、是否发货、金额是否正确时使用。
        参数 order_id 是订单编号 (整数)。
    """
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            return f"未找到订单 {order_id}"
        items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        item_desc = ";".join(
            f"{it.product_name} x{it.order_item_num}" for it in items
        ) if items else "无明细"
        return (
            f"订单{order_id}: 状态={order.order_status}, "
            f"金额={order.order_total_amount}, "
            f"创建时间={order.order_createtime}, "
            f"明细: {item_desc}"
        )
    finally:
        db.close()

@tool
def get_inventory(product_id: int) -> str:
    """
        根据商品 ID 查询当前可用库存数量。当用户询问某商品还有没有货、库存多少时使用。
        参数 product_id 是商品 ID (整数)。
    """
    db = SessionLocal()
    try:
        inv = db.query(Inventory).filter(Inventory.product_id == product_id).first()
        if not inv:
            return f"未找到商品 {product_id} 的库存信息"
        available = inv.total_stock - inv.locked_stock
        return f"商品{product_id}: 可用库存 {available} 件"
    finally:
        db.close()

@tool
def get_logistics(order_id: int) -> str:
    """
        根据订单 ID 查询物流状态。
        当用户询问货到哪了、什么时候能到时使用。
        参数 order_id 是订单编号 (整数)。
    """
    return "当前系统暂不支持物流查询，请查看订单状态或联系客服。"
from langchain_core.tools import tool
from app.database import SessionLocal
from app.models.inventory import Inventory
from typing import Annotated 
from langgraph.prebuilt import InjectedState 
from app.agent.state import ConsultState
from app.services import order_service
from app.services.product_service import product_detail 
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma 

# 注: Day6 工具直接查 ORM，不校验 user_id；Day7 接路由时升级为带 user_id 调 order_service
# get_logistics 项目无物流表，返回固定文案，不瞎编。

ORDER_STATUS_MAP = {
    0: "待支付",
    1: "已支付",
    2: "已完成",
    3: "已取消",
}

# 模块级初始化一次，不要每次调用重建 (重建会重新加载模型 + 读索引，很慢)
_embedding = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",
    encode_kwargs={"normalize_embeddings": True},
    model_kwargs={"local_files_only": True},
)
_vectorstore = Chroma(
    persist_directory="data/chroma",
    embedding_function=_embedding,
)

@tool
def get_order_info(order_id: int, state: Annotated[ConsultState, InjectedState]) -> str:
    """
        根据订单 ID 查询订单状态、金额、创建时间。
        当用户询问订单进度、是否发货、金额是否正确时使用。
        参数 order_id 是订单编号 (整数)。
    """
    user_id = state["user_id"]
    db = SessionLocal()
    try:
        detail = order_service.get_order_detail(db, user_id, order_id)
        status_text = ORDER_STATUS_MAP.get(detail["order_status"], f"未知状态({detail['order_status']})")
        items = detail.get("items", [])
        item_desc = ";".join(
            f"{it['product_name']} x{it['order_item_num']}" for it in items 
        ) if items else "无明细"
        return (
            f"订单{order_id}: 状态={status_text}, "
            f"金额={detail['order_total_amount']}, "
            f"创建时间={detail['order_createtime']}, "
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

@tool
def get_orders_item(state: Annotated[ConsultState, InjectedState]) -> str:
    """
        查询当前用户的最近订单列表。
        当用户问"我的订单"、"我买了什么"、"最近的单子"时使用，不需要提供订单号。
    """
    user_id = state["user_id"]
    db = SessionLocal()
    try:
        result = order_service.get_order_list(db, user_id, page=1, size=5)
        orders = result.get("list", [])
        if not orders:
            return "您还没有订单。"
        lines = []
        for o in orders:
            lines.append(
                f"订单{o['order_id']}: 状态={ORDER_STATUS_MAP.get(o['order_status'], o['order_status'])}, 金额={o['order_total_amount']}"
            )
        return "您最近的订单:\n" + "\n".join(lines)
    finally:
        db.close()

@tool
def get_product_detail(product_id: int) -> str:
    """
        根据商品 ID 查询商品价格、类型等基本信息。
        当用户询问某商品多少钱、是什么类型时使用。
        参数 product_id 是商品 ID (整数)。
    """
    db = SessionLocal()
    try:
        info = product_detail(db, product_id)
        return (
            f"商品{info['product_name']}: 类型={info['product_type']},"
            f"价格={info['product_amount']}, 可用库存={info['available_stock']}件"
        )
    finally:
        db.close()

@tool
def search_faq(query: str) -> str:
    """
        检索客服常见问题知识库。
        当用户询问平台规则、系统功能、FAQ类问题时使用，例如:
        "订单状态有哪些"、"怎么取消订单"、"下单规则是什么"、
        "支付说明"、"库存不够怎么办"、"超时不支付会怎样"、
        "用户登录时效多久"、"商品信息包含什么"。
        不要用于查询具体某个订单或某个商品的实时数据。
        参数 query 是用户问题或关键词。
    """
    results = _vectorstore.similarity_search(query, k=3)
    if not results:
        return "知识库中没有找到相关内容，请建议用户联系人工客服。"
    return "\n\n".join(f"{r.page_content}" for r in results)
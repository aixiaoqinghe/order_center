import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

load_dotenv()

# 注: DeepSeek 思考模式下 tool_choice 不能设 required/ 指定函数名,
# 默认 auto 可用; 工具调用多轮时还需回传 reasoning_content (今天单轮不涉及)。

@tool
def get_order_info(order_id: str) -> str:
    """
    根据订单号查询订单状态、金额、创建时间。当用户询问订单进度、是否发货、金额是否正确时使用。参数 order_id 是订单编号，格式如 ORD123。
    """
    fake_orders = {
        "ORD123": "订单ORD123: 状态已支付，金额199.5元，创建时间2026-10-20",
    }
    return fake_orders.get(order_id, f"未找到订单: {order_id}")

@tool
def get_inventory(product_name: str) -> str:
    """
        根据商品名称查询当前库存数量。当用户询问某商品还有没有货、库存多少时使用。
        参数 product_name 是商品名称, 如 '机械键盘'。
    """
    fake_inventory = {"机械键盘": "库存 37 件"}
    return fake_inventory.get(product_name, f"未找到商品 {product_name} 的库存记录")

@tool
def get_logistics(order_id: str) -> str:
    """
        根据订单号查询物流状态和预计到达时间。当用户询问货到哪了、什么时候能到时使用。
        参数 order_id 是订单编号, 格式如 ORD123。
    """
    fake_logistics = {
        "ORD123": "物流单号 SF123456, 已揽收, 预计明天送达",
    }
    return fake_logistics.get(order_id, f"未找到订单 {order_id} 的物流信息")

llm = ChatOpenAI(
    model=os.getenv("LLM_MODEL"),
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL"),
    timeout=int(os.getenv("LLM_TIMEOUT_READ", "30")),
    use_responses_api=False,
)

# 绑定工具，不传 tool_choice (默认 auto)
llm_with_tools = llm.bind_tools([get_order_info, get_inventory, get_logistics])

resp = llm_with_tools.invoke("订单ORD123到哪了")
print(f"content: {resp.content}")
print(f"tool_calls: {resp.tool_calls}")
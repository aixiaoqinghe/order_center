from sqlalchemy.orm import Session

from app.models.order import Order
from app.utils.exceptions import OrderNotFoundError, LLMCallError 
from app.utils.llm_client import chat

import logging

logger = logging.getLogger(__name__)

# order_status -> 兜底话术(大模型失败时用)
_STATUS_ANSWER = {
    0: "当前订单尚未支付，您可确认订单后进行支付",
    1: "当前订单已经支付成功，正在为您安排物流事项，预计后天送达",
    2: "当前订单已经完成，是否需要售后处理",
    3: "当前订单已经取消，是否需要为您推荐相关好物",
}

# order_status -> 中文状态名(v2)
_STATUS_NAME = {
    0: "待支付",
    1: "已支付",
    2: "已完成",
    3: "已取消"
}

_SYSTEM_PROMPT = """
    你是一个电商客服，只能根据提供的订单信息回答用户问题。
    不许编造订单信息里没有的内容
    如果说用户的问题和订单无关，回答用户"抱歉，暂时无法为您回答该问题"
    用自然、口语化的客服语气回答，
    像真人对话，不要罗列字段，
    不要输出订单号等内部编号，
    回答简洁，长度限制在300字内。
"""

async def consult_order(db: Session, order_id: int, question: str) -> dict:
    """AI 咨询(v3: 调大模型，失败降级返回兜底话术)"""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if order is None:
        raise OrderNotFoundError()

    status_name = _STATUS_NAME.get(order.order_status, "未知")

    # 基础信息：订单状态必给
    info_lines = [f"- 订单状态:{status_name}"]
    # 只有已取消 (status=3) 才给取消原因
    if order.order_status == 3:
        cancel_reason = order.order_cancel_reason or "无"
        info_lines.append(f"- 取消原因: {cancel_reason}")

    user_prompt = f"""
        当前订单消息:
        {chr(10).join(info_lines)}
        用户问题: {question}
    """

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        answer = await chat(messages)
    except LLMCallError:
        # 降级: 大模型失败，按订单状态返回兜底话术
        logger.warning("LLM调用失败，降级返回兜底话术，order_id=%s", order.order_id)
        answer = _STATUS_ANSWER.get(
            order.order_status,
            "抱歉，当前咨询繁忙，请稍后重试",
        )

    return {"order_id": order.order_id, "answer": answer}
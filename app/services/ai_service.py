from sqlalchemy.orm import Session

from app.models.order import Order
from app.utils.exceptions import OrderNotFoundError

# order_status -> 占位话术(v1 不调大模型，写死)
_STATUS_ANSWER = {
    0: "当前订单尚未支付，您可确认订单后进行支付",
    1: "当前订单已经支付成功，正在为您安排物流事项，预计后天送达",
    2: "当前订单已经完成，是否需要售后处理",
    3: "当前订单已经取消，是否需要为你推荐相关好物",
}

def consult_order(db: Session, order_id: int, question: str) -> dict:
    """AI 咨询(v1 骨架: 查订单，按状态返回占位话术，不调大模型)"""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if order is None:
        raise OrderNotFoundError()

    answer = _STATUS_ANSWER.get(
        order.order_status,
        "抱歉，暂时无法为您解答该订单的问题",
    )
    return {"order_id": order.order_id, "answer": answer}
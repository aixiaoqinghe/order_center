from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.ai import ConsultResponse
from app.schemas.common import ErrorResponse, Response
from app.services import ai_service
from app.utils.deps import get_current_user, bearer_scheme

import asyncio 
from app.agent.agent import build_consult_agent 
from app.agent.state import ConsultState

consult_agent = build_consult_agent()     # 模块级构建一次，不要每次请求重建

router = APIRouter(prefix="/api/order", tags=["AI咨询"], dependencies=[Depends(bearer_scheme)])

@router.post(
    "/consult/{order_id}",
    response_model=Response[ConsultResponse],
    responses={
        400: {"model": ErrorResponse, "description": "订单不存在"},
        401: {"model": ErrorResponse, "description": "token 缺失 / 无效 / 已过期"},
        403: {"model": ErrorResponse, "description": "无权咨询该订单"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"},
    },
)
async def consult_order(
    order_id: int = Path(..., gt=0, description="订单ID"),
    question: str = Query(..., min_length=1, max_length=500, description="咨询问题"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """订单 AI 咨询

    从 token 解析当前用户身份。调大模型对订单进行咨询解读。
    非本人订单返回 403；订单不存在返回业务错误；
    大模型调用失败时降级返回兜底文案（不抛异常）。
    """
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                consult_agent.invoke,
                {
                    "messages": [("user", f"当前订单ID: {order_id}。用户问题: {question}")],
                    "user_id": current_user.user_id
                },
                {"configurable": {"thread_id": f"{current_user.user_id}_{order_id}"}},
            ),
            timeout=15.0,
        )
        answer = result["messages"][-1].content
        if not answer or len(answer.strip()) < 3:
            raise ValueError("Agent 返回内容过短")
        return Response(code=200, msg="success consulted", data={"order_id": order_id, "answer": answer})
    except Exception:
        # 降级走旧 ai_service
        data = await ai_service.consult_order(db, current_user.user_id, order_id, question)
        return Response(code=200, msg="success consulted (fallback)", data=data)
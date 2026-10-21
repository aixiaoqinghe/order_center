from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.ai import ConsultResponse
from app.schemas.common import ErrorResponse, Response
from app.services import ai_service

router = APIRouter(prefix="/api/order", tags=["AI咨询"])

@router.post(
    "/consult/{order_id}",
    response_model=Response[ConsultResponse],
    responses={
        400: {"model": ErrorResponse, "description": "订单不存在"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"},
    },
)
async def consult_order(
    order_id: int = Path(..., gt=0, description="订单ID"),
    question: str = Query(..., min_length=1, max_length=500, description="咨询问题"),
    db: Session = Depends(get_db),
):
    """订单 AI 咨询

    调大模型对订单进行咨询解读。订单不存在返回业务错误；
    大模型调用失败时降级返回兜底文案（不抛异常）。
    """
    data = await ai_service.consult_order(db, order_id, question)
    return Response(code=200, msg="success consulted", data=data)
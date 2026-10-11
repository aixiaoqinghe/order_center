from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.ai import ConsultRequest, ConsultResponse
from app.schemas.common import Response
from app.services import ai_service

router = APIRouter(prefix="/api/order", tags=["AI咨询"])

@router.post("/consult/{order_id}", response_model=Response[ConsultResponse])
async def consult_order(
    order_id: int,
    body: ConsultRequest,
    db: Session = Depends(get_db),
):
    """AI 咨询接口: 真实调大模型 (v2)"""
    data = await ai_service.consult_order(db, order_id, body.question)
    return Response(code=200, msg="success consulted", data=data)
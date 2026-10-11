from pydantic import BaseModel, Field

class ConsultRequest(BaseModel):
    """AI 咨询请求体"""
    question: str = Field(..., min_length=1, max_length=500, description="咨询问题")

class ConsultResponse(BaseModel):
    """AI 咨询响应数据"""
    order_id: int = Field(..., description="订单ID")
    answer: str = Field(..., description="AI 回答")
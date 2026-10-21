from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from app.database import engine

from app.routers import user as user_router
from app.routers import product as product_router
from app.routers import order as order_router
from app.routers import ai
from app.schemas.common import ErrorResponse, Response
from app.utils.exceptions import (
    InventoryNotFoundError,
    LockAcquireFailedError,
    OrderForbiddenError,
    OrderNotFoundError,
    OrderStatusError,
    PasswordError,
    ProductNotFoundError,
    StockNotEnoughError,
    TokenInvalidError,
    UserAlreadyExistsError,
    UserNotFoundError,
)

from app.utils.logger import setup_logging
import logging

setup_logging()
logger = logging.getLogger(__name__)

class HealthOut(BaseModel):
    db: str

app = FastAPI(title="Order Center", version="0.1.0")

app.include_router(user_router.router)
app.include_router(product_router.router)
app.include_router(order_router.router)
app.include_router(ai.router)

@app.get(
    "/health",
    response_model=Response[HealthOut],
    responses={
        503: {"model": ErrorResponse, "description": "数据库不可用"},
    },
)
def health():
    """健康检查

    检查服务与数据库连通性。数据库不通返回 503，其余返回 200。
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return JSONResponse(
            status_code=200,
            content={"code": 200, "msg": "health ok", "data": {"db": "ok"}},
        )
    except Exception:
        logger.exception("health check db failed")
        return JSONResponse(
            status_code=503,
            content={"code": 503, "msg": "db unavailable", "data": None},
        )

@app.exception_handler(UserAlreadyExistsError)
@app.exception_handler(UserNotFoundError)
@app.exception_handler(PasswordError)
@app.exception_handler(ProductNotFoundError)
@app.exception_handler(InventoryNotFoundError)
@app.exception_handler(StockNotEnoughError)
@app.exception_handler(OrderNotFoundError)
@app.exception_handler(OrderStatusError)
@app.exception_handler(LockAcquireFailedError)
async def business_error_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc), "data": None})

@app.exception_handler(OrderForbiddenError)
async def forbidden_handler(request: Request, exc: OrderForbiddenError):
    return JSONResponse(status_code=403, content={"code": 403, "msg": str(exc), "data": None})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """参数校验失败: 返回全部错误, msg 一句总结, data 放明细"""
    errors = [
        {
            "field": ".".join(str(x) for x in err["loc"]),
            "msg": err["msg"],
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=400,
        content={"code": 400, "msg": "参数校验失败", "data": errors},
    )

@app.exception_handler(TokenInvalidError)
async def token_invalid_handler(request: Request, exc: TokenInvalidError):
    logger.warning("认证失败: %s %s", request.method, request.url.path)
    return JSONResponse(status_code=401, content={"code": 401, "msg": "认证失败，请重新登录", "data": None})

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """ 兜底: 未捕获异常统一 500 + 记日志 """
    logger.exception(
        "未捕获异常 method=%s path=%s", 
        request.method, request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={"code": 500, "msg": "服务器内部错误", "data": None},
    )
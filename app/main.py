from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.database import engine

from app.routers import user as user_router
from app.routers import product as product_router
from app.routers import order as order_router
from app.routers import ai
from app.utils.exceptions import (
    InventoryNotFoundError,
    LockAcquireFailedError,
    OrderForbiddenError,
    OrderNotFoundError,
    OrderStatusError,
    PasswordError,
    ProductNotFoundError,
    StockNotEnoughError,
    UserAlreadyExistsError,
    UserNotFoundError,
)

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Order Center", version="0.1.0")

app.include_router(user_router.router)
app.include_router(product_router.router)
app.include_router(order_router.router)
app.include_router(ai.router)

@app.get("/health")
def health():
    """健康检查：验证服务和 MySQL 连接"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "db": "unavailable", "detail": str(e)}
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
    """参数校验失败: 统一 {code, msg, data} 格式，只取第一条错误"""
    first = exc.errors()[0]
    # loc 形如 ("body", "question"), 取最后一个字段名
    field = first["loc"][-1]
    msg = f"参数校验失败: {field}: {first['msg']}"
    return JSONResponse(
        status_code=400,
        content={"code": 400, "msg": msg, "data": None},
    )

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
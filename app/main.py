from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.database import engine

from app.routers import user as user_router
from app.routers import product as product_router
from app.utils.exceptions import (
    PasswordError,
    ProductNotFoundError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.routers import product as product_router

app = FastAPI(title="Order Center", version="0.1.0")

app.include_router(product_router.router)
app.include_router(user_router.router)

@app.get("/health")
def health():
    """健康检查：验证服务和 MySQL 连接"""
    try:
        # 拿一个连接执行 SELECT 1, 验证 DB 可用
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    except Exception as e:
        # DB 不可用,返回503(服务不可用),不是500(服务器内部错误)
        return JSONResponse(
            status_code = 503,
            content = {"status": "error", "db": "unavailable", "detail": str(e)}
        )

# 注册 router
app.include_router(user_router.router)

# 全局异常处理器：业务异常都转400
@app.exception_handler(UserAlreadyExistsError)
@app.exception_handler(UserNotFoundError)
@app.exception_handler(PasswordError)
@app.exception_handler(ProductNotFoundError)
async def business_error_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=400, content={"code": 400, "msg": str(exc), "data": None})
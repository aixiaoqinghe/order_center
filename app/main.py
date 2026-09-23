from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.database import engine

app = FastAPI(title="Order Center", version="0.1.0")

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
import redis.asyncio as redis
from app.config import settings

# 模块级单例连接池，全局共享
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD or None,
    db=0,
    decode_responses=True,       # 存 value 读出来是 str 不是 bytes,锁的 value 比对要用
)

async def get_redis():
    """FastAPI 依赖: router 用 Depends(get_redis) 拿到连接，再传给 service """
    return redis_client
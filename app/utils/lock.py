import uuid
from redis.asyncio import Redis

# Lua 脚本:只有 value 匹配才删除,保证“比对+删除”原子性
# 防止:比对通过后、删除前锁过期，此时删掉的是别人的锁
_RELEASE_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
else
    return 0
end
"""

async  def acquire(redis: Redis, product_id: int, ttl: int = 60) -> str | None:
    """
    获取单个 product_id 的分布式锁
    成功返回 value (释放时要用),失败返回 None
    """
    key = f"lock:product:{product_id}"
    value = str(uuid.uuid4())
    # NX: 只有 key 不存在才设成功; PX: ttl 毫秒后自动过期，防死锁
    ok = await redis.set(key, value, nx=True, px=ttl * 1000)
    return value if ok else None

async def release(redis: Redis, product_id: int, value: str) -> bool:
    """
    释放锁。只有 value 匹配才删除，防止删掉别人的锁。
    返回 True 表示删成功, False 表示锁已不属于自己(比如已过期被别人拿到)
    """
    key = f"lock:product:{product_id}"
    result = await redis.eval(_RELEASE_SCRIPT, 1, key, value)
    return result == 1
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
import aio_pika
from app.database import SessionLocal
from app.mq_client import get_connection, TIMEOUT_QUEUE
from app.services.order_service import consume_order_timeout
from app.utils.exceptions import ConsumeStockError
from consumer import send_to_dlx


async def main():
    conn = await get_connection()
    channel = await conn.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await channel.declare_queue(TIMEOUT_QUEUE, durable=True)

    print("[consumer_timeout] 启动，等待超时关单消息...")

    async for message in queue.iterator():
        db = SessionLocal()
        try:
            body = json.loads(message.body)
            order_id = body["order_id"]
            print(f"[consumer_timeout] 收到消息 order_id={order_id}")
            await consume_order_timeout(db, order_id)
            print(f"[consumer_timeout] 处理完成 order_id={order_id}")
            await message.ack()
        except ConsumeStockError as e:
            print(f"[consumer_timeout] 业务失败: {e}")
            await send_to_dlx(message, str(e), "business", order_id)
            await message.ack()
        except Exception as e:
            print(f"[consumer_timeout] 异常: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            await send_to_dlx(message, str(e), "temp", order_id)
            await message.ack()
        finally:
            db.close()


if __name__ == "__main__":
    asyncio.run(main())
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

    async for message in queue.iterator():
        db = SessionLocal()
        try:
            body = json.loads(message.body)
            order_id = body["order_id"]
            await consume_order_timeout(db, order_id)
            # 成功
            await message.ack()
        except ConsumeStockError as e:
            await send_to_dlx(message, str(e), "business")
            # 业务失败 -> 进死信
            await message.ack()
        except Exception as e:
            await send_to_dlx(message, str(e), "temp")
            # 临时故障 -> 直接死信
            await message.ack()
        finally:
            db.close()


if __name__ == "__main__":
    asyncio.run(main())
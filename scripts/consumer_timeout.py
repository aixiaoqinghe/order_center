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
from app.utils.logger import setup_logging
import logging
from consumer import send_to_dlx

setup_logging("consumer_timeout.log")
logger = logging.getLogger(__name__)


async def main():
    conn = await get_connection()
    channel = await conn.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await channel.declare_queue(TIMEOUT_QUEUE, durable=True)

    logger.info("启动，等待超时关单消息...")

    async for message in queue.iterator():
        db = SessionLocal()
        try:
            body = json.loads(message.body)
            order_id = body["order_id"]
            logger.info(f"收到消息 order_id={order_id}")
            await consume_order_timeout(db, order_id)
            logger.info(f"处理完成 order_id={order_id}")
            await message.ack()
        except ConsumeStockError as e:
            logger.error(f"业务失败: {e}", exc_info=True)
            await send_to_dlx(message, str(e), "business", order_id)
            await message.ack()
        except Exception as e:
            logger.error(f"异常: {type(e).__name__}: {e}", exc_info=True)
            await send_to_dlx(message, str(e), "temp", order_id)
            await message.ack()
        finally:
            db.close()


if __name__ == "__main__":
    asyncio.run(main())
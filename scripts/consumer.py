"""
Day8 MQ 消费者
用法: python scripts/consumer.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.redis_client import redis_client
from app.database import SessionLocal
from app.services import order_service
from app.config import settings

import asyncio
import json
from app.mq_client import get_connection, QUEUE_NAME
import aio_pika
from sqlalchemy import text
from app.mq_client import get_connection, get_mq, QUEUE_NAME
from app.database import SessionLocal
from app.redis_client import redis_client
from app.services import order_service
from app.utils.exceptions import ConsumeStockError
from app.utils.logger import setup_logging
import logging

setup_logging("consumer.log")
logger = logging.getLogger(__name__)

async def send_to_dlx(message, exc, nack_type, order_id):
    """发到死信队列 + 写 dlx_msg 表"""
    # 发死信队列
    exchange = await get_mq()
    await exchange.publish(
        aio_pika.Message(
            body = message.body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json",
        ),
        routing_key="order.dlx",
    )

    # 写表(新开 session)
    db = SessionLocal()
    try:
        db.execute(text(
            "INSERT INTO dlx_msg (order_id, msg_content, nack_reason, nack_type)"
            "VALUES (:oid, :content, :reason, :type)"
        ),{
            "oid": order_id,
            "content": str(message.body),
            "reason": str(exc),
            "type": nack_type,
        })
        db.commit()
    finally:
        db.close()

async def handle(message):
    """消费单条消息"""
    db = SessionLocal()
    try:
        body = json.loads(message.body)
        order_id = body["order_id"]
        items = body["items"]

        await order_service.consume_order(db, redis_client, order_id, items)
        await message.ack()
    
    except ConsumeStockError as e:
        # 业务失败 -> 直接死信,不重试
        logger.warning(f"业务失败，进死信: {e}")
        db.rollback()
        await send_to_dlx(message, e, "业务失败", order_id)
        await message.ack()

    except Exception as e:
        # 临时故障 -> 重试
        db.rollback()
        headers = message.headers or {}
        count = int(headers.get("x-retry-count", 0))

        if count >= settings.MQ_RETRY_MAX:
            # 重试超限 -> 死信
            await send_to_dlx(message, e, "临时故障", order_id)
        else:
            # 重发到延迟队列
            exchange = await get_mq()
            await exchange.publish(
                aio_pika.Message(
                    body=message.body,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    content_type="application/json",
                    headers={"x-retry-count": count + 1},
                ),
                routing_key="order.retry",
            )
        await message.ack()
    finally:
        db.close()

async def main():
    connection = await get_connection()
    channel = await connection.channel()     # 消费者自己的 channel

    queue = await channel.declare_queue(QUEUE_NAME, durable=True)

    logger.info("启动，等待消息...")
    async with queue.iterator() as it:
        async for message in it:
            await handle(message)

if __name__ == "__main__":
    asyncio.run(main())
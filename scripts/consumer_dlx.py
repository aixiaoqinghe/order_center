import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aiofiles
import asyncio
import json
import logging
from datetime import datetime

from sqlalchemy import text

from app.database import SessionLocal
from app.mq_client import get_connection, DLX_QUEUE_NAME
from app.utils.logger import setup_logging
from app.config import settings

setup_logging("consumer_dlx.log")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
ALERT_FILE = os.path.join(BASE_DIR, settings.ALERT_LOG_PATH)

async def write_alert_file(line: str) -> None:
    try:
        async with aiofiles.open(ALERT_FILE, "a", encoding="utf-8") as f:
            await f.write(line)
    except Exception as e:
        logger.error("写告警文件失败: %s", e)

async def handle_dlx_message(db, body):
    """处理一条死信，任何异常不抛"""
    order_id = body.get("order_id")

    # 查 dlx_msg 拿原因和 msg_id
    row = db.execute(
        text(
            "SELECT msg_id, nack_reason, nack_type FROM dlx_msg "
            "WHERE order_id = :oid AND msg_status = 0 "
            "ORDER BY msg_createtime DESC LIMIT 1"
        ),
        {"oid": order_id}
    ).fetchone()

    if row is None:
        # 查不到: 告警 + 不标价
        logger.warning(f"[DLX] order_id={order_id} 查不到 dlx_msg 记录")
        return

    msg_id, nack_reason, nack_type = row

    # 日志 WARNING + 控制台
    logger.warning(
        f"[DLX] order_id={order_id} msg_id={msg_id} "
        f"nack_type={nack_type} reason={nack_reason}"
    )

    # 写告警文件
    line = (
        f"[{datetime.now().isoformat()}] order_id={order_id} "
        f"nack_type={nack_type} reason={nack_reason}\n"
    )
    await write_alert_file(line)

    # 标记已处理
    try:
        db.execute(
            text("UPDATE dlx_msg SET msg_status = 1 WHERE msg_id = :mid"),
            {"mid": msg_id}
        )
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"标记 dlx_msg 失败: order_id={order_id} err={e}")

async def main():
    conn = await get_connection()
    channel = await conn.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await channel.declare_queue(DLX_QUEUE_NAME, durable=True)

    async for message in queue.iterator():
        db = SessionLocal()
        try:
            body = json.loads(message.body)
            await handle_dlx_message(db, body)
        except Exception as e:
            # 兜底: 任何异常只记日志，不抛
            logger.error(f"死信消费异常:{e}")
        finally:
            db.close()
            # 无论成功失败都 ACK (消息已记录在 dlx_msg 表，队列不背存储)
            await message.ack()

if __name__ == "__main__":
    asyncio.run(main())
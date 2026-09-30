"""
Day 7 重复消费模拟脚本
对用一个 order_id 重复发送 MQ 消息，用于 Day 8消费者幂等测试
用法: python scripts/mq_dup_test.py
"""
import asyncio
import sys

sys.path.insert(0, ".")
from app.mq_client import publish_order_created, close_mq

ORDER_ID = 627
USER_ID = 1
ITEMS = [
    {"product_id": 4, "order_item_num": 3, "order_item_amount": "200.00"}
]
SEND_TIMES = 2   # 发几次

async def main():
    for i in range(SEND_TIMES):
        await publish_order_created(ORDER_ID, USER_ID, ITEMS)
        print(f"已发送第 {i + 1} 条, order_id={ORDER_ID}")
    print(f"共发送 {SEND_TIMES} 条重复消息")
    await close_mq()

if __name__ == "__main__":
    asyncio.run(main())
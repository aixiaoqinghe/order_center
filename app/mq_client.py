import json
import aio_pika
from app.config import settings

# 模块级单例: 连接/信道/交换机
_connection = None
_channel = None
_exchange = None

EXCHANGE_NAME = "order.exchange"
QUEUE_NAME = "order.create.queue"
ROUTING_KEY = "order.create"

async def get_mq():
    """懒加载单例：首次调用建连接，断了重建。返回 exchange。"""
    global _connection, _channel, _exchange

    # 无连接或连接已关闭 -> 重建
    if _connection is None or _connection.is_closed:
        _connection = await aio_pika.connect_robust(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            login=settings.RABBITMQ_LOGIN,
            password=settings.RABBITMQ_PASSWORD,
            virtualhost=settings.RABBITMQ_VHOST,
        )
        _channel = await _connection.channel()

        # 声明 topic 交换机m durable 持久化
        _exchange = await _channel.declare_exchange(
            EXCHANGE_NAME,
            aio_pika.ExchangeType.TOPIC,
            durable=True
        )
        # 声明队列, durable 持久化
        queue = await _channel.declare_queue(QUEUE_NAME, durable=True)
        # 绑定: routing_key 匹配 order.create 的消息进这个队列
        await queue.bind(_exchange, routing_key=ROUTING_KEY)

    return _exchange

async def publish_order_created(order_id: int, user_id: int, items: list):
    """发送订单创建消息(持久化)"""
    exchange = await get_mq()
    body = {
        "order_id": order_id,
        "user_id": user_id,
        "items": items,         # [{product_id, order_item_num, order_item_amount}]
    }
    message = aio_pika.Message(
        body=json.dumps(body).encode(),
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,   # 消息持久化
        content_type="application/json"
    )
    await exchange.publish(message, routing_key=ROUTING_KEY)


async def close_mq():
    """关闭 MQ 连接，脚本退出前调用"""
    global _connection, _channel, _exchange
    if _connection and not _connection.is_closed:
        await _connection.close()
    _connection = _channel = _exchange = None
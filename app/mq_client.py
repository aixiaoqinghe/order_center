import json
import aio_pika
from app.config import settings

# 模块级单例: 连接/信道/交换机
_connection = None
_channel = None
_exchange = None

EXCHANGE_NAME = "order.exchange"
QUEUE_NAME = "order.create.queue"
RETRY_QUEUE_NAME = "order.retry.queue"
DLX_QUEUE_NAME = "order.dlx.queue"
ROUTING_KEY = "order.create"
RETRY_ROUTING_KEY = "order.retry"
DLX_ROUTING_KEY = "order.dlx"

# 超时关单队列
TIMEOUT_DELAY_QUEUE = "order.timeout.delay.queue"
TIMEOUT_QUEUE = "order.timeout.queue"
TIMEOUT_DELAY_ROUTING_KEY = "order.timeout.delay"
TIMEOUT_ROUTING_KEY = "order.timeout"

async def get_connection():
    """懒加载单例: 只负责 connection, 断了重建"""
    global _connection, _channel, _exchange

    if _connection is None or _connection.is_closed:
        _connection = await aio_pika.connect_robust(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            login=settings.RABBITMQ_LOGIN,
            password=settings.RABBITMQ_PASSWORD,
            virtualhost=settings.RABBITMQ_VHOST,
        )
        # connection 重建 -> channel/exchange 置 None,下次 get_mq 自然重建
        _channel = None
        _exchange  =None

    return _connection

async def get_mq():
    """生产者用: 拿 connection -> 建 channel/exchange, 返回 exchange"""
    global _channel, _exchange

    connection = await get_connection()

    if _channel is None or _channel.is_closed:
        _channel = await connection.channel()

        # 声明 topic 交换机，durable 持久化
        _exchange = await _channel.declare_exchange(
            EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
        )

        # 声明队列, durable 持久化
        queue = await _channel.declare_queue(QUEUE_NAME, durable=True)

        # 绑定: routing_key 匹配 order.create 的消息进这个队列
        await queue.bind(_exchange, routing_key=ROUTING_KEY)

        # 延迟队列：消息 TTL 5s, 过期后按 dead-letter 配置回主队列
        retry_queue = await _channel.declare_queue(
            RETRY_QUEUE_NAME,
            durable=True,
            arguments={
                "x-message-ttl": 5000,                             # 5s
                "x-dead-letter-exchange": EXCHANGE_NAME,           # 过期后回到主 exchange
                "x-dead-letter-routing-key": ROUTING_KEY,          # 路由键变回 order.create
            },
        )
        # 延迟队列绑定: routing_key = order.retry 的消息进它
        await retry_queue.bind(_exchange, routing_key=RETRY_ROUTING_KEY)

        # 死信队列
        dlx_queue = await _channel.declare_queue(DLX_QUEUE_NAME, durable=True)
        await dlx_queue.bind(_exchange, routing_key=DLX_ROUTING_KEY)

        # 超时关单队列(15min TTL)
        await _declare_timeout_queues(_channel, _exchange)

    return _exchange


async def _declare_timeout_queues(channel, exchange):
    """超时关单：延迟队列15min TTL -> 过期回到主exchange -> 消费队列接住"""

    delay_queue = await channel.declare_queue(
        TIMEOUT_DELAY_QUEUE,
        durable=True,
        arguments={
            "x-message-ttl": 900000,
            "x-dead-letter-exchange": EXCHANGE_NAME,
            "x-dead-letter-routing-key": TIMEOUT_ROUTING_KEY,
        },
    )
    await delay_queue.bind(exchange, routing_key=TIMEOUT_DELAY_ROUTING_KEY)

    timeout_queue = await channel.declare_queue(TIMEOUT_QUEUE, durable=True)
    await timeout_queue.bind(exchange, routing_key=TIMEOUT_ROUTING_KEY)


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

# 发超时消息：在 create_order commit 后调用
async def publish_order_timeout(order_id: int):
    """发超时关单消息到延迟队列"""
    mq = await get_mq()
    await mq.publish(
        aio_pika.Message(
            body=json.dumps({"order_id": order_id}).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,   # 消息持久化
        ),
        routing_key=TIMEOUT_DELAY_ROUTING_KEY,
    )


async def close_mq():
    """关闭 MQ 连接，脚本退出前调用"""
    global _connection, _channel, _exchange
    if _connection and not _connection.is_closed:
        await _connection.close()
    _connection = _channel = _exchange = None
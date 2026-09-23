### 创建订单流程
```mermaid
sequenceDiagram
    autonumber
    participant U as 用户
    participant API as 订单接口
    participant R as Redis锁
    participant DB as MySQL
    participant MQ as RabbitMQ
    participant C as 消费者

    U->>API: 点击"下单" (user_id + items)
    API->>R: 加锁 (key = product_id)
    R-->>API: 加锁成功

    API->>DB: 查库存
    DB-->>API: 返回库存结果

    alt 库存充足
        API->>DB: 锁库存 (locked_stock += n)
        DB-->>API: 锁库存成功

        API->>DB: 写订单 (order + order_item)
        DB-->>API: 订单写入成功

        API->>MQ: 发送消息 (order_id, user_id, items)
        API->>R: 释放锁
        R-->>API: 释放成功
        API-->>U: 订单创建成功, 请付款 (order_status=0)

        MQ->>C: 投递消息
        C->>DB: 扣库存 (total_stock -= n, locked_stock -= n)
        alt 扣减成功
            C->>MQ: ACK
        else 扣减失败
            C->>MQ: NACK
            Note over C,MQ: 重试 3 次, 间隔 5 秒
            MQ->>C: 重新投递
            Note over C,MQ: 重试超限 → 进入死信队列
        end
    else 库存不足
        API->>R: 释放锁
        R-->>API: 释放成功
        API-->>U: 库存不足, 下单失败
    end
```

### 消费者重试与死信流程

```mermaid
sequenceDiagram
    autonumber
    participant MQ
    participant C as 消费者
    participant RQ as 重试延迟队列
    participant DLQ as 死信队列
    participant DB
    participant Alert as 告警

    MQ->>C: 投递消息

    alt 消费成功
        C->>MQ: ACK
    else 消费失败 - 临时故障且未超3次
        C->>C: 读 x-retry-count
        C->>RQ: 发消息 (x-retry-count+1)
        Note right of RQ: 5秒后重新投递到原队列
    else 消费失败 - 临时故障超3次 or 业务失败
        C->>MQ: nack(requeue=false)
        MQ->>DLQ: 消息进入死信
        DLQ->>DB: 记录死信表
        DLQ->>Alert: 告警
    end
```

### 说明

**锁**
- 锁的 key：`product_id`（按商品粒度锁，不同商品互不影响）
- 锁的持有范围：加锁 → 查库存 → 锁库存 → 写订单 → 发MQ → 释放锁
- 锁的释放时机：发完 MQ 即释放，不等消费者

**MQ 消息内容**
- order_id：消费者定位订单
- user_id：日志追踪
- items：商品列表，每项含 product_id、order_item_num、order_item_amount

**消费者**
- 只做一件事：扣减库存（total_stock -= n, locked_stock -= n）
- 不改订单状态、不写物流（这些属于付款流程）

**重试策略**
- 重试 3 次，间隔 5 秒
- 超限 → 死信队列

**库存不足分支**
- 释放锁 → 返回用户"库存不足"，订单不创建
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
        alt 正常返回 (含扣减未生效只告警)
            C->>MQ: ACK
        else 临时故障 (DB/Redis 异常、消息体解析失败)
            C->>MQ: 重新 publish 到 order.retry (x-retry-count+1)
            Note over C,MQ: 5 秒后回主队列, 最多 3 次, 超限则发 order.dlx 并写 dlx_msg 表
            C->>MQ: ACK 原消息
        end
    else 库存不足
        API->>R: 释放锁
        R-->>API: 释放成功
        API-->>U: 库存不足, 下单失败
    end
```

### 关单与库存回滚流程（手动取消 / 超时自动取消）

关单和 MQ 消费者对同一订单**通过订单行锁（FOR UPDATE）串行化**，不可能同时跑。

```mermaid
sequenceDiagram
    autonumber
    participant Cancel as 关单逻辑
    participant DB as MySQL
    participant MQC as MQ消费者

    Note over Cancel: 触发关单 (手动取消 / 15min超时)
    Cancel->>DB: SELECT order_status ... FOR UPDATE (锁订单行并读状态)
    DB-->>Cancel: 拿到锁, 返回 order_status
    Note over Cancel: 手动取消用 ORM with_for_update(), 超时关单用原生 SQL, 都只锁一行

    alt 订单已流转 (order_status != 0)
        Cancel-->>Cancel: 超时关单直接 return, 手动取消抛 OrderStatusError(400)
    else 订单仍待支付 (order_status = 0)
        Cancel->>DB: 查 consumer_idempotent.consume_status
        DB-->>Cancel: 返回 (不存在 / 0 / 1)
        Note right of Cancel: 2 为设计预留值, 当前代码无写入路径

        alt consume_status = 1 (MQ 已消费)
            Cancel->>DB: UPDATE inventory SET total_stock += n
            Note right of DB: MQ 扣过 total -= n, 回滚就是 += n
        else consume_status != 1 (MQ 未消费)
            Cancel->>DB: UPDATE inventory SET locked_stock -= n
            Note right of DB: 下单只动了 locked += n, total 没被动过
        end

        Cancel->>DB: UPDATE order SET order_status = 3, order_cancel_reason = ...
        Cancel->>DB: commit, 释放订单行锁
    end

    rect rgb(230, 245, 255)
        Note over MQC,DB: MQ 后到 (关单已提交 status=3, 直接拿到订单锁)
        MQC->>DB: 插占位 consume_status=0 并单独 commit
        Note over MQC,DB: 这次 commit 会释放此前所有行锁, 订单锁必须在它之后拿
        MQC->>DB: SELECT order_status ... FOR UPDATE (读到 3)
        Note right of MQC: 订单已关, 无需再扣库存
        MQC->>DB: UPDATE consumer_idempotent SET consume_status = 1, result_msg = 跳过扣库存
        MQC-->>MQC: 正常 ACK, 不重投
    end
```

**关单库存回滚规则**
- 先拿订单行锁 `FOR UPDATE`，锁覆盖「判断 → 改库存 → 改订单状态」全过程，与 MQ 消费者串行化
- 再按 `product_id` 升序拿 `inventory` 行锁，与下单/扣库存顺序一致，防死锁
- 查 `consumer_idempotent.consume_status` 判断 MQ 状态（订单级可靠信号，与扣库存在同一事务提交）；运行时只会出现 0 处理中 / 1 已处理(扣减成功或跳过扣库存)，记录不存在时也视为未消费。`2 失败` 是 `schema.sql` 注释保留的设计预留值，当前代码没有任何写入 2 的路径；`consume_order` 第三层是「`==1` 才 return」，读到任何非 1 值仍会继续处理
- `consume_status = 1`（MQ 已扣过）→ 只补回 `total_stock += n`
- `consume_status != 1`（含 0 / 不存在，以及历史残留的 2）→ 只释放 `locked_stock -= n`
- 两条分支由 `if consumer_done / else` 天然互斥；订单行锁的作用是让判断与回滚期间 MQ 插不进来，保证读到的 `consume_status` 是已提交的最终值
- 注：`consume_status=1` 也被「订单不存在 / 已取消，跳过扣库存」两个分支复用。这两类订单已不是待支付状态，不会再触发关单回滚，所以不影响上面的流程；但信号语义不纯，属明确保留的边界（见 README「已知缺陷」）

**为什么 MQ 未消费时不补 total_stock？**
下单只动了 `locked_stock += n`，`total_stock` 一分没动。MQ 未消费意味着 total 从来没被减过，关单补 total 就是凭空捏造的回滚。

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

    alt 消费成功 (含扣减未生效只告警、订单已取消跳过扣库存)
        C->>MQ: ACK
    else 临时故障且未超 3 次
        C->>C: 读 x-retry-count
        C->>RQ: 发消息 (x-retry-count+1)
        Note right of RQ: 5 秒后 dead-letter 回主队列
        C->>MQ: ACK 原消息
    else 临时故障超 3 次
        C->>DLQ: 主动 publish 到 order.dlx
        C->>DB: 写 dlx_msg 表
        Note over DLQ,Alert: 死信消费者 consumer_dlx.py 消费后写日志与告警文件
        C->>MQ: ACK 原消息
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
- 执行顺序：Redis `SET NX EX` 抢幂等 key → 查 `consume_status` 决定是否插占位 → 插占位 `consume_status=0` 并**单独 commit** → 拿订单行锁 `FOR UPDATE`（必须在这次 commit 之后，否则锁会被释放）
- 主要职责：扣减库存（`total_stock -= n, locked_stock -= n`），按 `product_id` 升序；UPDATE 影响 0 行只打 warning、不抛错
- 拿锁后查 `order_status`，已关单（=3）或订单不存在则跳过扣库存，置 `consume_status=1` + `result_msg` 并正常返回
- 扣库存与置 `consume_status=1` 在同一事务同一次 commit
- 不改订单状态、不写物流（这些属于付款流程）

**重试策略**
- 只对临时故障（DB/Redis 异常、消息体解析失败）重试：ACK 原消息 + 重新 publish 一条带 `x-retry-count` 的新消息到 `order.retry.queue`（TTL 5s，dead-letter 回 `order.create`），最多 3 次
- 超限 → 主动 publish 到 `order.dlx` 并写 `dlx_msg` 表
- 代码里没有 `basic_nack`；`ConsumeStockError` 的「业务失败直接进死信」分支已成死代码（全仓无 `raise`），`rowcount=0` 现在只打 warning、置 `consume_status=1` 并正常 ACK

**库存不足分支**
- 释放锁 → 返回用户"库存不足"，订单不创建
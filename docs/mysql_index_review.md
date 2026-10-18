# MySQL 索引复盘

## 一、查询 SQL 清单

> 范围：`app/routers/`、`app/services/`、`scripts/` 中所有 SELECT 查询
> 统计标准：ORM `.query()` / `.filter()` / `.filter_by()`、裸 SQL `text()`
> `app/routers/` 无直接查询（全调 service 层），`app/main.py` 不在范围内

---

### 1.1 ORM 查询（SQLAlchemy 链式调用 —— .query()）

#### app/services/user_service.py

| # | 行号 | 用途 | ORM 语句 | 等价 SQL |
|---|------|------|----------|----------|
| 1 | :14 | 按用户名查用户 | `db.query(User).filter(User.user_name == name).first()` | `SELECT * FROM user WHERE user_name = ? LIMIT 1` |
| 2 | :18 | 按 user_id 查用户 | `db.query(User).filter(User.user_id == user_id).first()` | `SELECT * FROM user WHERE user_id = ? LIMIT 1` |

#### app/services/product_service.py

| # | 行号 | 用途 | ORM 语句 | 等价 SQL |
|---|------|------|----------|----------|
| 3 | :11 | 按 product_id 查商品 | `db.query(Product).filter(Product.product_id == product_id).first()` | `SELECT * FROM product WHERE product_id = ? LIMIT 1` |
| 4 | :14 | 按 product_id 查库存 | `db.query(Inventory).filter(Inventory.product_id == product_id).first()` | `SELECT * FROM inventory WHERE product_id = ? LIMIT 1` |
| 5 | :66 | 商品总数（分页用） | `db.query(Product).count()` | `SELECT COUNT(*) FROM product` |
| 6 | :69-73 | 商品分页列表 | `db.query(Product).order_by(Product.product_id).offset(offset).limit(size).all()` | `SELECT * FROM product ORDER BY product_id ASC LIMIT ? OFFSET ?` |

#### app/services/order_service.py

| # | 行号 | 用途 | ORM 语句 | 等价 SQL |
|---|------|------|----------|----------|
| 7 | :43 | 创建订单时查库存 | `db.query(Inventory).filter_by(product_id=pid).first()` | `SELECT * FROM inventory WHERE product_id = ? LIMIT 1` |
| 8 | :92 | 按 order_id 查订单详情 | `db.query(Order).filter(Order.order_id == order_id).first()` | `SELECT * FROM \`order\` WHERE order_id = ? LIMIT 1` |
| 9 | :94 | 查订单的所有商品项 | `db.query(OrderItem).filter(OrderItem.order_id == order_id).all()` | `SELECT * FROM order_item WHERE order_id = ?` |
| 10 | :125 | 支付时按 product_id 查商品 | `db.query(Product).filter_by(product_id=item.product_id).first()` | `SELECT * FROM product WHERE product_id = ? LIMIT 1` |
| 11 | :168 | 按 order_id 查订单（支付回调） | `db.query(Order).filter(Order.order_id == order_id).first()` | `SELECT * FROM \`order\` WHERE order_id = ? LIMIT 1` |
| 12 | :175 | 查订单商品项（支付回调） | `db.query(OrderItem).filter(OrderItem.order_id == order_id).all()` | `SELECT * FROM order_item WHERE order_id = ?` |
| 13 | :198 | 查 user（订单列表分页前校验） | `db.query(User).filter(User.user_id == user_id).first()` | `SELECT * FROM user WHERE user_id = ? LIMIT 1` |
| 14 | :202 | 订单总数（分页用） | `db.query(Order).filter(Order.user_id == user_id).count()` | `SELECT COUNT(*) FROM \`order\` WHERE user_id = ?` |
| 15 | :204-209 | 订单分页列表 | `db.query(Order).filter(Order.user_id == user_id).order_by(Order.order_id.desc()).offset(offset).limit(size).all()` | `SELECT * FROM \`order\` WHERE user_id = ? ORDER BY order_id DESC LIMIT ? OFFSET ?` |
| 16 | :234 | 取消订单时查订单 | `db.query(Order).filter(Order.order_id == order_id).first()` | `SELECT * FROM \`order\` WHERE order_id = ? LIMIT 1` |
| 17 | :243-248 | 取消订单时查商品项（升序防死锁） | `db.query(OrderItem).filter(OrderItem.order_id == order_id).order_by(OrderItem.product_id.asc()).all()` | `SELECT * FROM order_item WHERE order_id = ? ORDER BY product_id ASC` |
| 18 | :438 | 手动关单时查订单 | `db.query(Order).filter(Order.order_id == order_id).first()` | `SELECT * FROM \`order\` WHERE order_id = ? LIMIT 1` |

#### app/services/ai_service.py

| # | 行号 | 用途 | ORM 语句 | 等价 SQL |
|---|------|------|----------|----------|
| 19 | :39 | AI 咨询时按 order_id 查订单 | `db.query(Order).filter(Order.order_id == order_id).first()` | `SELECT * FROM \`order\` WHERE order_id = ? LIMIT 1` |

---

### 1.2 原生 SQL —— 裸 text() 查询

#### app/services/order_service.py

| # | 行号 | 用途 | 完整 SQL |
|---|------|------|----------|
| 20 | :251-257 | 取消订单 — 查库存并**行锁** | `SELECT total_stock, locked_stock FROM inventory WHERE product_id = :pid FOR UPDATE` |
| 21 | :311-314 | 消费者幂等 — 查 consumer_idempotent 状态 | `SELECT consume_status FROM consumer_idempotent WHERE order_id = :oid` |
| 22 | :370-373 | 超时关单 — 查订单状态 | `SELECT order_status FROM \`order\` WHERE order_id = :oid` |
| 23 | :385-388 | 超时关单 — 查消费者幂等记录 | `SELECT consume_status FROM consumer_idempotent WHERE order_id = :oid` |
| 24 | :391-397 | 超时关单 — 查订单商品项（升序防死锁） | `SELECT product_id, order_item_num FROM order_item WHERE order_id = :oid ORDER BY product_id ASC` |
| 25 | :403-406 | 超时关单 — 查库存并**行锁** | `SELECT * FROM inventory WHERE product_id = :pid FOR UPDATE` |

#### scripts/consumer_dlx.py

| # | 行号 | 用途 | 完整 SQL |
|---|------|------|----------|
| 26 | :40-47 | 死信处理 — 查 dlx_msg 记录 | `SELECT msg_id, nack_reason, nack_type FROM dlx_msg WHERE order_id = :oid AND msg_status = 0 ORDER BY msg_createtime DESC LIMIT 1` |

#### scripts/load_test.py

| # | 行号 | 用途 | 完整 SQL |
|---|------|------|----------|
| 27 | :64-65 | 压测脚本 — 查库存 | `SELECT total_stock, locked_stock FROM inventory WHERE product_id=:p` |


## 二、EXPLAIN 结果
| 序号 | type | key | rows | Extra | 表总行数 | rows判断 | 
| ---- | -----| --- | ---- | ---- | -------- | -------- |
| 1 | const | uk_user_name | 1 | null | 10 | 精准 | 
| 2 | const | primary | 1 | null | 10 | 精准 | 
| 3 | const | primary | 1 | null | 5 | 精准 | 
| 4 | const | primary | 1 | null | 5 | 精准 | 
| 5 | index | primary | 2 | Using index | 5 | 精准 | 
| 6 | index | primary | 2 | null | 5 | 精准 | 
| 7 | const | primary | 1 | null | 5 | 精准 | 
| 8 | const | primary | 1 | null | 672 | 精准 | 
| 9 | ref | primary | 1 | null | 676 | 精准 | 
| 10 | const | primary | 1 | null | 5 | 精准 | 
| 11 | const | primary | 1 | null | 672 | 精准 | 
| 12 | ref | primary | 1 | null | 676 | 精准 | 
| 13 | const | primary | 1 | null | 10 | 精准 | 
| 14 | ref | idx_user_id | 665 | Using index | 672 | 接近全表(索引无效)|
| 15 | index | primary | 4 | Using where; Backward index scan | 672 | 远小于表 | 
| 16 | const | primary | 1 | null | 672 | 精准 | 
| 17 | ref | primary | 1 | null | 676 | 精准 | 
| 18 | const | primary | 1 | null | 672 | 精准 | 
| 19 | const | primary | 1 | null | 672 | 精准 | 
| 20 | const | primary | 1 | null | 5 | 精准 | 
| 21 | 我这个 consumer_idempotent 这个表里面是没有内容的，所以这个explain结果也是为空的 | 
| 22 | const | primary | 1 | null | 672 | 精准 | 
| 23 | 和第21点原因相同，这个 consumer_idempotent 这个表里面没有内容，相应的 explain 结果也是为空的
| 24 | ref | primary | 1 | null | 676 | 精准 |
| 25 | const | primary | 1 | null | 5 | 精准 | 
| 26 | all | null | 6 | Using where; Using filesort | 6 | 全表 |
| 27 | const | primary | 1 | null | 5 | 精准 |  


## 三、索引失效判断
#14: idx_user_id 存在且被用上 (key 非空)，但 rows=665≈表672，索引选择性差，过滤效果接近全表，实际无效。
证据: EXPLAIN rows≈665, 表总数 672.
#26: dlx_msg 无 order_id 索引，type=ALL 全表扫 + Using filesort(额外排序),表当前6行影响小，数据增长后是性能点。证据:type=ALL\key=NULL\Extra=Using filesort。
#21/#23: 表空，EXPLAIN 提示 no matching row in const table,说明 order_id 走 const 访问(主键/唯一索引等值查)，当前无数据不影响判断，索引存在且有效。
#9/#12/#17/#24: order_item 联合主键(order_id, product_id), where order_id 命中最左前缀，key=primary\rows=1,走索引正确，非问题。
#15：分页倒扫走主键索引，type=index、rows=4<<672，非失效，可接受。

#5/#6：表小，COUNT/分页走主键索引扫描（type=index），rows 2≪表 5，非失效。

其余查询（#1-4、7-8、10-13、16、18-20、22、25、27）：均走主键/唯一索引等值查，type=const/ref、rows=1，无失效。


## 三-2、索引设计与落地

### 设计
| 问题 | 索引设计 | 动作 | 理由 |
|---|---|---|---|
| #14/#15 | order 表 (user_id, order_id) | 新建联合索引，删单列 idx_user_id | 等值列 user_id 在前、排序列 order_id 在后；COUNT 覆盖索引，列表免 filesort；联合索引最左覆盖单列，单列冗余删除 |
| #26 | dlx_msg 表 (order_id, msg_status, msg_createtime) | 新建 | 两个等值列在前、排序列在后，免 filesort |

### 改造前后 EXPLAIN 对比
| 序号 | type | key | rows | Extra | 表总行数 | rows判断 | 阶段 | 数据说明 |
|---|---|---|---|---|---|---|---|---|
| 14 | ref | idx_user_id | 665 | Using index | 672 | 接近全表 | 改造前 | — |
| 15 | index | primary | 4 | Using where; Backward index scan | 672 | 远小于表 | 改造前 | — |
| 26 | all | null | 6 | Using where; Using filesort | 6 | 全表 | 改造前 | — |
| 14 | ref | idx_user_order | 665 | Using index | 672 | 接近全表 | 改造后 | 覆盖索引 |
| 15(订单集中user) | index | PRIMARY | 4 | Using where; Backward index scan | 672 | 远小于表 | 改造后 | 600单user，优化器选主键 |
| 15(订单少user) | ref | idx_user_order | 1 | Backward index scan | 672 | 精准 | 改造后 | 走联合索引，免filesort |
| 26 | ref | idx_order_status_time | 1 | Backward index scan | 6 | 精准 | 改造后 | filesort消除 |


### 说明
- #14 rows 未降属正常：该 user_id 下约 600 行，COUNT 需数这些行，索引作用在覆盖（Using index）而非减行
- #15 在订单集中的 user_id 下优化器选 PRIMARY 倒扫，订单少的 user_id 下走 idx_user_order 免 filesort，索引有效
- #26 ALL→ref、filesort 消除


## 四、慢查询与优化

### 4.1 慢查询记录（改造前/问题场景）

| # | SQL | Query_time | Lock_time | Rows_examined | 说明 |
|---|---|---|---|---|---|
| 1 | UPDATE inventory SET total_stock=50, locked_stock=0 WHERE product_id=1 | 50.418525 s | 50.417928s | 0 | 压测重置库存，等锁 |
| 2 | 同上（另一连接） | 50.519611s | 50.518854s | 0 | 同上 |

### 4.2 现象分析
- Query_time ≈ Lock_time，耗时全在等锁，非 SQL 本身慢
- Rows_examined=0，未扫到行，一直在等 inventory 行锁释放

### 4.3 根因
- load_test.py 并发开 30 个连接，事务未 commit/rollback，持有 inventory product_id=1 行锁
- 服务/消费者进程异常退出或未停干净，连接残留，事务挂起
- 查证：information_schema.innodb_trx 30 条 RUNNING，同一时刻开始，thread_id 连续

### 4.4 处理
- KILL 挂起连接（thread_id 57、65-93），innodb_trx 清零
- 停 load_test.py 进程

### 4.5 死信链路补测
- RabbitMQ order.dlx.queue 积压 9 条，consumer_dlx.py 启动后立即消费
- dlx_msg 跑前 6 条、跑后 6 条：consumer_dlx.py 只有 SELECT + UPDATE，无 INSERT，不增加记录属正常（插入死信记录在 consumer.py）
- dlx_msg 6 条全 msg_status=1，故 #26 查询 msg_status=0 查不到，返回空、极快、不进慢日志

### 4.6 #26 有数据场景补测
- 手动插入 msg_status=0 测试数据，跑 #26 查询
- 结果：0.006 秒，EXPLAIN key=idx_order_status_time，无 Using filesort
- 结论：改造后 #26 有数据也不慢

### 4.7 优化方向（面试点，基于本项目实际）

1. **Query_time ≈ Lock_time 是锁等待信号**
   本次两条 UPDATE 的 Query_time≈Lock_time、Rows_examined=0，说明慢在等锁不是 SQL。
   判读：Query_time≈Lock_time → 等锁；Query_time≫Lock_time → 扫数据多。看到慢 SQL 先拆因，别上来加索引。

2. **长事务占锁成因（本项目实际遇到）**
   load_test.py 并发开连接后未 commit/rollback，进程异常退出/未停干净，事务挂起占 inventory 行锁。
   查证：information_schema.innodb_trx 30 条 RUNNING，同一时刻开始，thread_id 连续。
   代码层面：异常路径没 rollback、连接没关。

3. **查长事务、KILL、innodb_lock_wait_timeout 防护**
   查：information_schema.innodb_trx，trx_started 早的就是长事务。
   解：KILL thread_id，杀完查 innodb_trx 清零才算解。
   防：innodb_lock_wait_timeout 别调大，修事务逻辑；业务层捕获 Lock wait timeout 重试。

4. **压测脚本也要管事务和连接（本项目实际踩到）**
   load_test.py 连接/事务没及时释放，留下 30 个长事务占锁，后续查询全等锁。
   压测脚本不是生产代码，但数据库共享，脚本泄漏连接一样会制造慢查询。

5. **慢查询日志是线上定位第一手证据**
   本次开 slow_query_log=ON、long_query_time=1，抓到 50 秒锁等待。
   看三字段：Query_time（总耗时）、Lock_time（锁等待）、Rows_examined（扫描行数，对比返回行数看索引是否失效）。
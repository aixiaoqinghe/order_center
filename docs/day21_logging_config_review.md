## 改造前 vs 改造后对照表：

| 项 | 改造前 | 改造后 |
|---|---|---|
| 日志 format | `%(asctime)s %(levelname)s %(name)s: %(message)s`（无行号） | `... %(name)s [%(lineno)d]: %(message)s`（加行号） |
| 毫秒格式 | 时间戳毫秒前无逗号 | 覆盖 `Formatter.formatTime`，输出 `11:37:08,977` |
| 落文件 | 无，只控制台 | 控制台 + `logs/app.log` 单文件 |
| consumer_dlx | 自己 basicConfig，格式不一 | 调 `setup_logging("consumer_dlx.log")`，格式统一 |
| httpx 噪音 | INFO 噪音 | `httpx` logger 降 WARNING |
| consumer 脚本（3 个） | 各自 basicConfig / print，格式不一 | 统一调 `setup_logging("consumer.log")` / `setup_logging("consumer_timeout.log")` / `setup_logging("consumer_dlx.log")`，全用 logger |
| order_service print（6处）+ 成功路径无 INFO | `consume_order_timeout` 里 print（6处），`create_order` 成功路径无日志 | print→logger.info，成功路径加 `logger.info("下单成功: order_id=%s, user_id=%s")` |


## 配置

| 项 | 改造前（硬编码） | 改造后（Settings 字段，默认值沿用） |
|---|---|---|
| DB 连接池 | `pool_size=10, max_overflow=20, pool_recycle=3600, echo=False` | `DB_POOL_SIZE=10` / `DB_MAX_OVERFLOW=20` / `DB_POOL_RECYCLE=3600` / `DB_ECHO=False` |
| MQ TTL | `5000` / `900000` | `MQ_RETRY_TTL_MS=5000` / `MQ_ORDER_TIMEOUT_MS=900000` |
| 锁 TTL | `60` | `REDIS_LOCK_TTL=60` |
| 幂等 TTL | `7200` | `IDEMPOTENT_TTL_SECONDS=7200` |
| 重试上限 | `3` | `MQ_RETRY_MAX=3` |
| 日志级别 | `logging.INFO` 占位 | `getattr(logging, settings.LOG_LEVEL)` |
| 告警路径 | `logs/dlx_alerts.log` | `ALERT_LOG_PATH` |
| API 端口 | `8000`（load_test/test_flow_e2e） | `settings.API_PORT` |


## 验证记录（2026-10-20 实跑）

### 启动日志（uvicorn app.main:app --host 0.0.0.0 --port 8000）

```
INFO:     Started server process [19716]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

Settings 全部字段从 .env 正常加载，无缺失/类型转换报错。

### load_test（--concurrency 3 --stock 2）

```
==================================================
并发数:3  库存:2
成功单数:1  失败单数:2
  系统繁忙: 2
最终 total_stock:2  locked_stock:1
==================================================
>>> 🟢 正常: 成功(1) ≤ 库存(2)  锁生效
```

### logs/app.log 下单 INFO

```
2026-10-20 11:36:26,387 INFO app.services.order_service [152]: 下单成功: order_id=686 user_id=1
2026-10-20 11:37:08,977 INFO app.services.order_service [152]: 下单成功: order_id=687 user_id=1
```

### grep 对账：三个文件 print 全部清零

```
grep -rn "print(" app/services/order_service.py
→ No matches found

grep -rn "print(" scripts/consumer.py
→ No matches found

grep -rn "print(" scripts/consumer_timeout.py
→ No matches found
```

### 改造后 user/product 日志示例

```
2026-10-20 10:42:28,182 INFO app.services.user_service [52]: 用户注册成功: user_id=11 user_name=test_log_001
2026-10-20 10:42:56,793 WARNING app.services.user_service [32]: 注册失败，用户名已存在: user_name=test_log_001
2026-10-20 10:42:58,886 INFO app.services.user_service [66]: 用户登录成功: user_id=11
2026-10-20 10:43:00,309 WARNING app.services.user_service [59]: 登录失败: user_name=no_such_user
2026-10-20 10:43:01,388 WARNING app.services.product_service [16]: 查询商品失败，商品不存在: product_id=99999
```


## 已知问题/遗留（留 Day23）：

 - 锁失败路径无日志（留 Day23）
 - uvicorn 自身日志格式与 app 日志不同（未做）
 - 测试文件注释里 --port 8000 保留（非配置项）
 - 幂等语义：进程内单次、跨进程独立
 - root.handlers.clear() 前提：root 无第三方 handler
 - 登录失败日志已合并，接口仍区分异常
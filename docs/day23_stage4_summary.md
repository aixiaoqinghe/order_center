## 改造前 vs 改造后总表 (Day15-23)
| Day | 改造项 | 改造前 | 改造后 | 
| --- | ------ | ------ | ----- |
| 15-17 | MySQL 索引 | ① order 表 idx_user_id 单列：rows=665(表672)，选择性差；② dlx_msg 无索引，type=ALL 全表扫 + Using filesort | ① order 建联合索引 idx_user_order(user_id, order_id)，删单列 idx_user_id，COUNT 覆盖 + 列表免 filesort；② dlx_msg 建联合索引 idx_order_status_time(order_id, msg_status, msg_createtime)，ALL→ref，filesort 消除 |
| 15-17 | 慢查询 | 压测脚本事务泄漏导致 UPDATE inventory 等锁 50s（Query_time≈Lock_time，Rows_examined=0，30 条长事务占 inventory 行锁） | KILL 挂起 thread_id，innodb_trx 清零；结论：慢查询要先拆因，Query_time≈Lock_time 是锁等待信号，别上来加索引 |
| 18 | 全局异常处理 | 12 类自定义异常散落、handler 返回体风格不一、未知异常走 FastAPI 默认 500 裸抛格式、ConsumeStockError/LLMCallError 漏 handler | 建 4 个异常 handler（business 覆盖 9 类业务错→400、forbidden→403、validation→400、unhandled→500 兜底），12 类全部明确归属；ConsumeStockError/LLMCallError 不走 business，归 unhandled 兜底→500；500 兜底统一 {code,msg,data} 并记 ERROR+堆栈+method+path（无敏感信息） |
| 19 | 统一返回体 | 12 个业务接口已统一 {code,msg,data}，但 /health 成功返回 {"status":"ok","db":"ok"}、失败返回 {"status":"error",...} | /health 也统一：成功 {code:200,msg:"health ok",data:{"db":"ok"} }，失败 {code:503,msg:"db unavailable",data:null} + HTTP 503 |
| 20 | 参数校验 | validation_exception_handler 只取第一条错误 msg、data=null，字段名只取 loc[-1] | msg 固定"参数校验失败"、data=[全部错误 {field,msg}]、字段路径全拼（body.items.0.order_item_num） |
| 21 | 日志系统 | consumer 各自 basicConfig / print、order_service 6 处 print、httpx INFO 噪音、无行号无毫秒无落文件 | 统一 setup_logging：控制台+logs/app.log、行号 %(lineno)d、毫秒逗号分隔、httpx 降 WARNING、3 个 consumer 脚本全改 logger、print 清零 |
| 21 | 配置解耦 | DB 池 pool_size=10/max_overflow=20/pool_recycle=3600/echo=False、MQ TTL 5000/900000、锁 TTL 60、幂等 7200、重试上限 3、API 端口 8000、日志级别 INFO、告警路径 logs/dlx_alerts.log 全部硬编码散落各处 | 全收进 Settings 类（Pydantic BaseSettings），.env 可配；Day21 新入 Settings 共 12 项：LOG_LEVEL、DB_POOL_SIZE、DB_MAX_OVERFLOW、DB_POOL_RECYCLE、DB_ECHO、API_PORT、REDIS_LOCK_TTL、IDEMPOTENT_TTL_SECONDS、MQ_RETRY_TTL_MS、MQ_ORDER_TIMEOUT_MS、MQ_RETRY_MAX、ALERT_LOG_PATH（注：DB_HOST/REDIS_HOST/RABBITMQ_HOST 等连接基础配置 Day21 之前已在 Settings，JWT_* 三项 Day23 新入） |
| 22 | Swagger 文档 | title/version 有，description 全空，接口无多行 docstring，参数无 description/约束，无错误响应声明 | 项目 description 补写，12 接口多行 docstring，Query/Path 加 description + gt/ge/minLength 约束，responses 按实际异常声明 400/403/500/503，新增 ErrorResponse 通用模型 |
| 22 | 入参行为变更 | cancel 用 body OrderCancelIn(user_id:int)、consult 用 body ConsultRequest(question:str)，与 detail/list 的 Query 直传风格不统一 | cancel body→Query(gt=0) 传 user_id；consult body→Query(min_length=1,max_length=500) 传 question；OrderCancelIn/ConsultRequest 保留但路由不再引用 |
| 23 | JWT 鉴权 | 无 token 机制，前端直接传 user_id 参数可冒充任意用户；order 路由和 ai 路由裸奔；detail/cancel 归属校验靠前端传 user_id（可绕过）、pay/consult 无归属校验 | 新增 security.py（jose JWT 签发/校验）+ deps.py（HTTPBearer + get_current_user）；user/info、order 全路由(create/detail/list/cancel/pay)、ai/consult 共 7 接口加鉴权；detail/cancel 的 user_id Query 参数彻底删除，改从 token 取（归属校验逻辑原有，只换 user_id 来源）；pay/consult 新增归属校验返回 403 |
| 23 | 登录出参 | 登录 data 是扁平用户信息（user_id + user_name） | data 改为嵌套结构 {token: str, user: {user_id, user_name} }，token 含 sub(user_id) + exp(JWT_EXPIRE_MINUTES 从 .env 读) |
| 23 | create_order 越权 | OrderCreate body 含 user_id 字段，前端可传任意值冒充他人下单 | OrderCreate body 只保留 items 列表，user_id 从 token 解析的 current_user.user_id 取，完全消除越权入口 |
| 23 | 死信写文件阻塞 | consumer_dlx.py 用同步 f.write() 写 dlx_alerts.log，阻塞 asyncio 事件循环 | 新增 write_alert_file 协程，用 aiofiles.open + await f.write() 异步写，事件循环零阻塞 |


## 展开版面试话术

### 全局异常
 - 前：12 类异常散落、handler 返回体不一、500 裸抛、ConsumeStockError/LLMCallError 没归属
 - 改：4 个 handler、12 类全部明确归属、500 兜底统一返回体、记堆栈+method+path 不记敏感
 - 为什么：前端一种错误结构；排查靠堆栈；不泄露内部

### 统一返回体
 - 前：/health 是 {status,db}，和其他接口 {code,msg,data} 不一致
 - 改：/health 也统一，失败 503 + data:null
 - 为什么：全项目一种结构，前端不用逐接口适配

### 参数校验
 - 前：只取第一条错误、data:null、字段名只有 loc[-1]
 - 改：返回全部错误 data:[ {field,msg} ]、field 用 loc 全拼
 - 为什么：前端一次看全、嵌套字段能定位

### 日志系统
 - 前：consumer 各自 basicConfig/print、order_service 6 处 print、httpx 噪音、无行号无毫秒无落文件
 - 改：统一 setup_logging（控制台+文件+行号+毫秒）、httpx 降 WARNING、consumer 全改 logger
 - 为什么：排查靠统一日志，不靠猜

### 配置解耦
 - 前：DB 池/MQ TTL/锁 TTL/幂等 TTL/重试上限/端口/日志级别/告警路径全硬编码
 - 改：全进 Settings（Pydantic BaseSettings），.env 可配
 - 为什么：换环境不改代码

### 鉴权
 - 前：无 token、前端传 user_id 可冒充、pay/consult 无归属校验
 - 改：JWT 签发/校验、7 接口鉴权、归属校验 403、create_order 从 token 取 user_id
 - 为什么：身份从 token 取，不信前端传参
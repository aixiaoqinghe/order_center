## 异常清单

| 类名 | 触发点 (文件:行) | 归属handler | 返回码 |
|------|-----------------|-------------|--------|
| UserAlreadyExistsError | user_service.py:27 | business_error_handler(现状=目标) | 400 |
| UserNotFoundError | user_service.py:20, order_service.py:200 | business_error_handler(现状=目标) | 400 |
| PasswordError | user_service.py:52, user_service.py:55 | business_error_handler(现状=目标) | 400 |
| ProductNotFoundError | product_service.py:13, order_service.py:127 | business_error_handler(现状=目标) | 400 |
| InventoryNotFoundError | order_service.py:45, order_service.py:261 | business_error_handler(现状=目标) | 400 |
| StockNotEnoughError | order_service.py:47 | business_error_handler(现状=目标) | 400 |
| OrderNotFoundError | order_service.py:170, order_service.py:236, order_service.py:440, ai_service.py:41 | business_error_handler(现状=目标) | 400 |
| OrderForbiddenError | order_service.py:173, order_service.py:239 | forbidden_handler(现状=目标) | 403 |
| OrderStatusError | order_service.py:242, order_service.py:442 | business_error_handler(现状=目标) | 400 |
| LockAcquireFailedError | order_service.py:146 | business_error_handler(现状=目标) | 400 |
| ConsumeStockError | order_service.py:350, order_service.py:423 | 500兜底 | 500 |
| LLMCallError | llm_client.py:37, llm_client.py:39, llm_client.py:41, llm_client.py:48 | 无(被 ai_service 降级吞掉) | 不产生（被 ai_service 降级吞掉，正常走 200 返回兜底话术）|


## 改造前后对比
| 项 | 改造前 | 改造后 | 
| ------ | ------ | ------ |
| 自定义异常类覆盖 | 12 类中 10 类有 handler，ConsumeStockError/LLMCallError 漏网 | 12 类全部明确归属（ConsumeStockError 500 兜底；LLMCallError 被 ai_service 吞，不冒 handler） |
| 500 兜底 | 无，未知异常走 FastAPI 默认 500，格式不统一 | 有 Exception 兜底，统一 {code:500,msg,data}，记日志 | 
| ConsumeStockError 默认 msg | 裸 pass，无默认 msg | 有默认 msg"消费者扣库存失败(影响0行)" |
| handler 返回体统一 | 3 个 handler 已是 {code,msg,data}（现状就统一）| 4 个 handler 全统一（含新 500 兜底） |
| 日志 | 500 无日志 | 500 记 ERROR + 堆栈 + method + path，无敏感信息 |
| /health 503 | 非统一格式 | 未改，留 Day19 |

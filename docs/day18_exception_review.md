## 异常清单

> 行号已按 2026-11-19 修复后的 `order_service.py`（475 行）重标。`ConsumeStockError` 已停用：全仓无 `raise`，仅保留异常类定义与 `consumer*.py` 的 catch 兼容。

| 类名 | 触发点 (文件:行) | 归属handler | 返回码 |
|------|-----------------|-------------|--------|
| UserAlreadyExistsError | user_service.py:33 | business_error_handler(现状=目标) | 400 |
| UserNotFoundError | user_service.py:24, user_service.py:60, order_service.py:202 | business_error_handler(现状=目标) | 400 |
| PasswordError | user_service.py:64 | business_error_handler(现状=目标) | 400 |
| ProductNotFoundError | product_service.py:17, order_service.py:128 | business_error_handler(现状=目标) | 400 |
| InventoryNotFoundError | order_service.py:46, order_service.py:277, product_service.py:21 | business_error_handler(现状=目标) | 400 |
| StockNotEnoughError | order_service.py:48 | business_error_handler(现状=目标) | 400 |
| OrderNotFoundError | order_service.py:172, order_service.py:244, order_service.py:465, ai_service.py:41 | business_error_handler(现状=目标) | 400 |
| OrderForbiddenError | order_service.py:175, order_service.py:247, order_service.py:468, ai_service.py:44 | forbidden_handler(现状=目标) | 403 |
| OrderStatusError | order_service.py:250, order_service.py:471 | business_error_handler(现状=目标) | 400 |
| LockAcquireFailedError | order_service.py:147 | business_error_handler(现状=目标) | 400 |
| ConsumeStockError | 已废弃（无触发点） | 曾归 500 兜底 | 不再产生 |
| LLMCallError | llm_client.py:37, llm_client.py:39, llm_client.py:41, llm_client.py:48 | 无(被 ai_service 降级吞掉) | 不产生（被 ai_service 降级吞掉，正常走 200 返回兜底话术）|


## 改造前后对比
> 下表是 Day18 当时的改造记录，`ConsumeStockError` 相关表述属历史时点，现行已停用。
| 项 | 改造前 | 改造后 | 
| ------ | ------ | ------ |
| 自定义异常类覆盖 | 12 类中 10 类有 handler，ConsumeStockError/LLMCallError 漏网 | 12 类全部明确归属（ConsumeStockError 500 兜底；LLMCallError 被 ai_service 吞，不冒 handler） |
| 500 兜底 | 无，未知异常走 FastAPI 默认 500，格式不统一 | 有 Exception 兜底，统一 {code:500,msg,data}，记日志 | 
| ConsumeStockError 默认 msg | 裸 pass，无默认 msg | 有默认 msg"消费者扣库存失败(影响0行)" |
| handler 返回体统一 | 3 个 handler 已是 {code,msg,data}（现状就统一）| 4 个 handler 全统一（含新 500 兜底） |
| 日志 | 500 无日志 | 500 记 ERROR + 堆栈 + method + path，无敏感信息 |
| /health 503 | 非统一格式 | 未改，留 Day19 |

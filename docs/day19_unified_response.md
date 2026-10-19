## 接口出参清单

| 接口 | 成功返回体 | 异常路径返回体 | 是否统一{code, msg, data} |
| ------ | ------ | ------ | ------ |
| POST /api/user/register | {"code": 200, "msg": "success registered", "data": ...} | {"code": 400, "msg": "用户名已存在:xxx", "data": None} | 是 |
| POST /api/user/login | {"code": 200, "msg": "success login", "data": ...} | {"code": 400, "msg": "用户名或密码错误", "data": None} | 是 |
| GET /api/user/info | {"code": 200, "msg": "success", "data": ...} | {"code": 400, "msg": "用户不存在", "data": None} | 是 |
| GET /api/product/list | {"code": 200, "msg": "success found", "data": ...} | — | 是 |
| GET /api/product/{product_id} | {"code": 200, "msg": "success found", "data": ...} | {"code": 400, "msg": "商品不存在:xxx", "data": None} | 是 |
| POST /api/product/create | {"code": 200, "msg": "success created", "data": ...} | — | 是 |
| POST /api/order/create | {"code": 200, "msg": "success created", "data": ...} | ① {"code": 400, "msg": "商品不存在", "data": None} ② {"code": 400, "msg": "库存记录不存在", "data": None} ③ {"code": 400, "msg": "库存不足", "data": None} ④ {"code": 400, "msg": "系统繁忙，稍后重试", "data": None} | 是 |
| GET /api/order/detail/{order_id} | {"code": 200, "msg": "success found", "data": ...} | ① {"code": 400, "msg": "订单不存在:xxx", "data": None} ② {"code": 403, "msg": "无权查看该订单", "data": None} | 是 |
| GET /api/order/list | {"code": 200, "msg": "success found", "data": ...} | {"code": 400, "msg": "用户不存在:xxx", "data": None} | 是 |
| POST /api/order/cancel/{order_id} | {"code": 200, "msg": "success canceled", "data": ...} | ① {"code": 400, "msg": "订单不存在:xxx", "data": None} ② {"code": 403, "msg": "无权取消该订单", "data": None} ③ {"code": 400, "msg": "订单当前状态不允许取消:xxx", "data": None} ④ {"code": 400, "msg": "库存记录不存在:xxx", "data": None} | 是 |
| POST /api/order/pay/{order_id} | {"code": 200, "msg": "success paid", "data": ...} | ① {"code": 400, "msg": "订单不存在", "data": None} ② {"code": 400, "msg": "该订单状态不可支付", "data": None} | 是 |
| POST /api/order/consult/{order_id} | {"code": 200, "msg": "success consulted", "data": ...} | {"code": 400, "msg": "订单不存在", "data": None} | 是 |
| GET /health | {code:200,msg:"health ok",data:{"db":"ok"} }| {code:503,msg:"db unavailable",data:null}(HTTP 503) | 是 |

> 脚注：标记为 "—" 的接口（product/list、product/create）无业务异常抛出，参数校验失败和 500 兜底统一见下方"通用异常说明"。

---

## 通用异常说明（所有接口都有，不再逐行重复）

| 类型 | 触发条件 | 返回体 |
| ---- | -------- | ------ |
| 参数校验失败 | Pydantic Schema 校验不通过（body / query / path 参数格式错误） | {"code": 400, "msg": "参数校验失败", "data": [{"field": "字段路径", "msg": "错误原因"}, ...]} |
| 兜底 500 | 任何未被 handler 捕获的异常（比如 ConsumeStockError、数据库连接异常等） | {"code": 500, "msg": "服务器内部错误", "data": None} |

> 脚注：field路径格式
 - body 参数 -> body.user_name、body.items.0.product_id (嵌套数组用索引)
 - path 参数 -> path.order_id
 - query 参数 -> query.page
---

## 已确认无问题

1. 403不统一(语义正确)
2. msg风格不统一(结构统一即可)
3. OrderForbiddenError msg 靠传参(没问题)


## 改造前后对比
| 项 | 改造前 | 改造后 | 
| --- | --- | --- |
| 12 个业务接口出参 | 已统一 {code,msg,data}(核过) |  不变，确认全统一 |
| /health 成功 | {"status":"ok","db":"ok"} | {code:200,msg:"health ok",data:{"db":"ok"} } |
| /health 失败 | {"status":"error",...} + 503 | {code:503,msg:"db unavailable",data:null} + HTTP 503 |
| 异常路径 | 走 4 个 handler，统一(Day18 已做) | 不变 | 
| 成功路径漏网 | 无(12接口全统一) | 无 |


## 验证记录
- 成功路径：HTTP 200 + body 符合
- 失败路径：临时修改/health中的"SELECT 1"，造 DB 不通，HTTP 503 + body 符合 + 日志 ERROR 无敏感信息 + 代码已还原
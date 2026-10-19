## 接口入参清单
| 接口 | 入参来源 | 校验规则 | 校验失败信息 |
|------|---------|---------|-------------|
| POST /api/user/register | body | UserCreate: user_name str 长度4-20, user_password str 长度6-20, user_nickname str 长度最大50(可选), user_phonenumber str 长度最大11(可选)| 走 validation_exception_handler → msg:"参数校验失败", data:[{field, msg}] |
| POST /api/user/login | body | UserLogin: user_name 长度最大20, user_password 长度最大20 | 走 validation_exception_handler → msg:"参数校验失败", data:[{field, msg}] |
| GET /api/user/info | query | user_id: int | 走 validation_exception_handler → msg:"参数校验失败", data:[{field, msg}] |
| GET /api/product/list | query | page int=Query(1, ge=1, le=100), size int=Query(30, ge=10, le=50)| 走 validation_exception_handler → msg:"参数校验失败", data:[{field, msg}] |
| GET /api/product/{product_id} | path | product_id: int | 走 validation_exception_handler → msg:"参数校验失败", data:[{field, msg}] |
| POST /api/product/create | body | ProductCreate: product_name str 长度4-20, product_type str 长度2-20(可选), product_amount decimal 0-1000000, total_stock int 0-1000000 | 走 validation_exception_handler → msg:"参数校验失败", data:[{field, msg}] |
| POST /api/order/create | body | OrderCreate: user_id int, items list[OrderItemCreate(每项: product_id int, order_item_num int 1-100)] | 走 validation_exception_handler → msg:"参数校验失败", data:[{field, msg}] |
| GET /api/order/detail/{order_id} | path, query | order_id: int, user_id: int(必填) | 走 validation_exception_handler → msg:"参数校验失败", data:[{field, msg}] |
| GET /api/order/list | query | user_id: int(必填), page int=Query(1, ge=1, le=100), size int=Query(30, ge=10, le=50) | 走 validation_exception_handler → msg:"参数校验失败", data:[{field, msg}] |
| POST /api/order/cancel/{order_id} | path, body | order_id: int, OrderCancelIn: user_id int | 走 validation_exception_handler → msg:"参数校验失败", data:[{field, msg}] |
| POST /api/order/pay/{order_id} | path | order_id: int | 走 validation_exception_handler → msg:"参数校验失败", data:[{field, msg}] |
| POST /api/order/consult/{order_id} | path, body | order_id: int, ConsultRequest: question str 长度1-500 | 走 validation_exception_handler → msg:"参数校验失败", data:[{field, msg}] |
| GET /health | 无入参 | - | - |

## 已知问题（仅记录）
1. user/info、order/detail、order/cancel 依赖前端传 user_id 做权限比对，缺 token 鉴权，存在越权风险
2. consult 无归属校验（快照 known_issues 第 8 条）


## 改造前后对比
| 项 | 改造前 | 改造后 |
| --- | --- | --- |
| 校验失败 msg | "参数校验失败: {field}:{msg}"(只第一条) | "参数校验失败"(一句总结) |
| 校验失败 data | null | [{"field": "...", "msg": "..."}, ...] (全部错误) |
| 字段名 | 只取 loc[-1] (第一条的字段) | 全拼点连接，嵌套可定位 (body.items.0.order_item_num) |
| 接口入参校验 | 12接口均有 pydantic/Query 校验 (核过) | 不变，确认无漏 |
| 已知问题 | 越权风险、consult无校验 (不归Day20) | 记录，未修 | 
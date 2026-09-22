# 订单系统接口文档

## 1.用户注册
- **路径**:/api/user/register
- **方法**: POST
- **入参**:
  | 字段 | 类型 | 必填 | 校验规则 |
  | --- | --- | --- | --- |
  | user_name | string | 是 | 4-20位 |
  | user_password | string | 是 | 6-20位 |
  | phonenumber | string | 否 | 11位数字 | 
  | user_nickname | string | 否 | 4-20位 |
- **出参数**:
  ```
    json
    {"code": 200, 
    "msg": "success registered", 
    "data": {
        "user_id": 1,
        "user_name": test_001,
        "user_createtime": "(当时时间)"
        } 
    }
  ```
- **错误码**
  | 码 | 含义 | 
  | --- | --- |
  | 400 | 用户名已存在/密码格式错误 |
  | 500 | 数据库错误 | 
- **备注**
  无

  ## 2.用户登录
- **路径**:/api/user/login
- **方法**: POST
- **入参**:
  | 字段 | 类型 | 必填 | 校验规则 |
  | --- | --- | --- | --- |
  | user_name | string | 是 | 4-20位 |
  | user_password | string | 是 | 6-20位 |
- **出参数**:
  ```
    json
    {"code": 200, 
    "msg": "success login", 
    "data": {
        "user_id": 1,
        "user_name": test_001
        } 
    }
  ```
- **错误码**
  | 码 | 含义 | 
  | --- | --- |
  | 400 | 用户名/密码错误 |
  | 500 | 数据库错误 | 
- **备注**
  无

  ## 3.用户查询自己信息
- **路径**:/api/user/info
- **方法**: GET
- **入参**:
  | 字段 | 类型 | 必填 | 校验规则 |
  | --- | --- | --- | --- |
  | user_id | int | 是 | 用户ID,数字 |
- **出参数**:
  ```
    json
    {"code": 200, 
    "msg": "success found", 
    "data": {
        "user_id": 1,
        "user_name": test_001,
        "user_password": 123456,
        "user_nickname": "用户1",
        "user_phonenumber": "13800000000",
        "user_createtime": "(当时时间)"
        } 
    }
  ```
- **错误码**
  | 码 | 含义 | 
  | --- | --- |
  | 400 | 用户名/密码错误 |
  | 500 | 数据库错误 | 
- **备注**
  无

## 4.商品列表浏览
- **路径**:/api/product/list
- **方法**: GET
- **入参**:
  | 字段 | 类型 | 必填 | 校验规则 |
  | --- | --- | --- | --- |
  | page | int | 是 | 1-100 |
  | size | int | 是 | 10-50 |
- **出参数**:
  ```
    json
    {
      "code": 200, 
      "msg": "success found", 
      "data":{
          "list": [
            {"product_id": 1, "product_name": "商品1", "product_type": "电子产品", "product_amount": 99.9}, 
            {"product_id": 2, "product_name": "商品2", "product_type": "生活用品", "product_amount": 88.8}
          ],
          "total": 1000,
          "page": 1,        // 当前页码
          "size": 30        // 每页数量
        } 
      }
  ```
- **错误码**
  | 码 | 含义 | 
  | --- | --- |
  | 400 | 商品ID不存在 |
- **备注**
  无

## 5.商品详情
- **路径**:/api/product/{product_id}
- **方法**: GET
- **入参**:
  | 字段 | 类型 | 必填 | 校验规则 |
  | --- | --- | --- | --- |
  | product_id | int | 是 | 商品ID,数字 |
- **出参数**:
  ```
    json
    {"code": 200, 
    "msg": "success found", 
    "data": {
        "product_id": 1,
        "product_name": "商品1",
        "product_createtime": "(当时时间)",
        "product_type": "电子产品",
        "product_amount": 99.9,
        "available_stock": 20
        } 
    }
  ```
- **错误码**
  | 码 | 含义 | 
  | --- | --- |
  | 400 | 商品ID不存在 |
- **备注**
  无

## 6.创建商品
- **路径**:/api/product/create
- **方法**: POST
- **入参**:
  | 字段 | 类型 | 必填 | 校验规则 |
  | --- | --- | --- | --- |
  | product_name | string | 是 | 4-20位 |
  | product_type | string | 否 | 6-20位 |
  | product_amount | float | 是 | 0-1000000 |
- **出参数**:
  ```
    json
    {"code": 200, 
    "msg": "success created", 
    "data": {
        "product_id": 200,
        "product_name": "商品200",
        "product_amount": 99.9
        } 
    }
  ```
- **错误码**
  | 码 | 含义 | 
  | --- | --- |
  | 500 | 数据库错误 | 
- **备注**
  无

  ## 7.创建订单
- **路径**:/api/order/create
- **方法**: POST
- **入参**:
  | 字段 | 类型 | 必填 | 校验规则 |
  | --- | --- | --- | --- |
  | user_id | int | 是 | 用户ID,数字 |
  | items | array | 是 | 订单商品列表 |
  | items[].product_id | int | 是 | 商品ID，数字 |
  | items[].order_item_num | int | 是 | 购买数量，1-100 |
- **出参数**:
  ```
    json
    {"code": 200, 
    "msg": "success created", 
    "data": {
        "order_id": 1,
        "user_id": 1,
        "order_total_num": 3,
        "order_createtime": "(当时时间)",
        "order_total_amount": 299.7,
        "order_status": 0,
        "order_cancel_reason": "",
        "items": [
          {"product_id": 1, "product_name": "商品1", "order_item_num": 2, "order_item_amount": 99.9, "order_item_subtotal": 199.8},
          {"product_id": 2, "product_name": "商品2", "order_item_num": 1, "order_item_amount": 99.9, "order_item_subtotal": 99.9}
        ]
        } 
    }
  ```
- **错误码**
  | 码 | 含义 | 
  | --- | --- |
  | 400 | 商品ID不存在/用户ID不存在 |
- **备注**
  无

## 8.订单详情页里查询单个订单
- **路径**:/api/order/detail/{order_id}
- **方法**: GET
- **入参**:
  | 字段 | 类型 | 必填 | 校验规则 |
  | --- | --- | --- | --- |
  | order_id | int | 是 | 订单ID,数字 |
  | user_id | int | 是 | 用户ID,数字 |
- **出参数**:
  ```
    json
    {"code": 200, 
    "msg": "success found", 
    "data": {
        "order_id": 1,
        "order_total_num": 1,
        "order_createtime": "(当时时间)",
        "order_total_amount": 99.9,
        "order_status": 0,     // 0待支付
        "order_cancel_reason": "",
        "items": [
          {"product_id": 1, "product_name": "商品1", "order_item_num": 2, "order_item_amount": 99.9, "order_item_subtotal": 199.8},
          {"product_id": 2, "product_name": "商品2", "order_item_num": 1, "order_item_amount": 99.9, "order_item_subtotal": 99.9}
        ]
        } 
    }
  ```
- **错误码**
  | 码 | 含义 | 
  | --- | --- |
  | 400 | 订单ID不存在 |
  | 403 | 无权查看该订单 |
- **备注**
  无

## 9.订单列表查询
- **路径**:/api/order/list
- **方法**: GET
- **入参**:
  | 字段 | 类型 | 必填 | 校验规则 |
  | --- | --- | --- | --- |
  | user_id | int | 是 | 用户ID,数字 |
  | page | int | 是 | 1-100 |
  | size | int | 是 | 10-50 |
- **出参数**:
  ```
    json
    {"code": 200, 
    "msg": "success found", 
    "data": {
        "user_id": 1,
        "list": [
            {"order_id": 1, "order_total_num": 1, "order_total_amount": 99.9, "order_createtime": "(当时时间)", "order_status": 0, "order_cancel_reason": ""}, 
            {"order_id": 2, "order_total_num": 2, "order_total_amount": 199.8, "order_createtime": "(当时时间)", "order_status": 0, "order_cancel_reason": ""}
          ],
        "total": 100,
        "page": 1,        // 当前页码
        "size": 30        // 每页数量
        } 
    }
  ```
- **错误码**
  | 码 | 含义 | 
  | --- | --- |
  | 400 | 用户ID不存在 |
- **备注**
  无

## 10.取消订单
- **路径**:/api/order/cancel/{order_id}
- **方法**: POST
- **入参**:
  | 字段 | 类型 | 必填 | 校验规则 |
  | --- | --- | --- | --- |
  | order_id | int | 是 | 订单ID,数字 |
- **出参数**:
  ```
    json
    {"code": 200, 
    "msg": "success canceled", 
    "data": {
        "order_id": 1,
        "order_status": 3,
        "order_cancel_reason": "用户取消订单"
        } 
    }
  ```
- **错误码**
  | 码 | 含义 | 
  | --- | --- |
  | 400 | 订单ID不存在 |
- **备注**
  无


## 11.模拟支付
- **路径**:/api/order/pay/{order_id}
- **方法**: POST
- **入参**:
  | 字段 | 类型 | 必填 | 校验规则 |
  | --- | --- | --- | --- |
  | order_id | int | 是 | 订单ID,数字 |
- **出参数**:
  ```
    json
    {"code": 200, 
    "msg": "success paid", 
    "data": {
        "order_id": 1,
        "order_status": 1
        } 
    }
  ```
- **错误码**
  | 码 | 含义 | 
  | --- | --- |
  | 400 | 订单ID不存在 |
- **备注**
  无


## 12.AI咨询
- **路径**:/api/order/consult/{order_id}
- **方法**: POST
- **入参**:
  | 字段 | 类型 | 必填 | 校验规则 |
  | --- | --- | --- | --- |
  | order_id | int | 是 | 订单ID,数字 |
  | question | string | 是 | 咨询问题 |
- **出参数**:
  ```
    json
    {"code": 200, 
    "msg": "success consulted", 
    "data": {
        "order_id": 1,
        "answer": "您的订单已支付，预计明天送达"
        } 
    }
  ```
- **错误码**
  | 码 | 含义 | 
  | --- | --- |
  | 400 | 订单ID不存在 |
- **备注**
  无
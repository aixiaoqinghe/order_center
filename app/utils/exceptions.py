class UserAlreadyExistsError(Exception):
    def __init__(self, msg: str = "注册时用户名已存在"):
        super().__init__(msg)

class UserNotFoundError(Exception):
    def __init__(self, msg: str = "用户不存在"):
        super().__init__(msg)

class PasswordError(Exception):
    def __init__(self, msg: str = "登录密码错误"):
        super().__init__(msg)

class ProductNotFoundError(Exception):
    def __init__(self, msg: str = "商品不存在"):
        super().__init__(msg)

class OrderNotFoundError(Exception):
    def __init__(self, msg: str = "订单不存在"):
        super().__init__(msg)

class OrderForbiddenError(Exception):
    def __init__(self, msg: str = "无权访问该订单"):
        super().__init__(msg)

class StockNotEnoughError(Exception):
    def __init__(self, msg: str = "库存不足"):
        super().__init__(msg)

class OrderStatusError(Exception):
    def __init__(self, msg: str = "订单状态不允许该操作"):
        super().__init__(msg)

class InventoryNotFoundError(Exception):
    def __init__(self, msg: str = "库存记录不存在"):
        super().__init__(msg)

class LockAcquireFailedError(Exception):
    def __init__(self, msg: str = "系统繁忙，稍后重试"):
        super().__init__(msg)

class ConsumeStockError(Exception):
    """消费者扣库存失败：库存不足或商品不存在(UPDATE 影响 0 行)"""
    def __init__(self, msg: str = "消费者扣库存失败(影响0行)"):
        super().__init__(msg)

class LLMCallError(Exception):
    """大模型调用失败"""
    def __init__(self, msg: str = "大模型调用失败"):
        self.msg = msg
        super().__init__(msg)

class TokenInvalidError(Exception):
    """token 无效、格式错误或已过期"""
    def __init__(self, msg: str = "token 无效或已过期"):
        super().__init__(msg)
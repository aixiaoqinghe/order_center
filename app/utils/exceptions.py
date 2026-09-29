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
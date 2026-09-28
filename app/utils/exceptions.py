class UserAlreadyExistsError(Exception):
    """注册时用户名已存在"""

class UserNotFoundError(Exception):
    """用户不存在"""

class PasswordError(Exception):
    """登录密码错误"""

class ProductNotFoundError(Exception):
    """商品不存在"""

class OrderNotFoundError(Exception):
    """订单不存在"""


class OrderForbiddenError(Exception):
    """无权访问该订单"""


class StockNotEnoughError(Exception):
    """库存不足"""


class OrderStatusError(Exception):
    """订单状态不允许该操作"""

class InventoryNotFoundError(Exception):
    """库存记录不存在"""
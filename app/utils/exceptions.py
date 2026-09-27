class UserAlreadyExistsError(Exception):
    """注册时用户名已存在"""

class UserNotFoundError(Exception):
    """用户不存在"""

class PasswordError(Exception):
    """登录密码错误"""

class ProductNotFoundError(Exception):
    """商品不存在"""
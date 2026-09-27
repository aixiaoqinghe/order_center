from passlib.context import CryptContext

# Argon2id 上下文;deprecated="auto"表示将来换算法时旧哈希仍可校验
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(plain: str) -> str:
    """明文密码 -> Argon2id 哈希串"""
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    """校验明文与哈希是否匹配"""
    return pwd_context.verify(plain, hashed)
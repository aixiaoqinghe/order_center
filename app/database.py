# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# 1. 创建 engine（全局一个，带连接池）
engine = create_engine(
    settings.database_url,
    pool_size=10,          # 连接池常驻连接数
    max_overflow=20,       # 峰值可临时增加的连接数（总数上限 = pool_size + max_overflow）
    pool_pre_ping=True,    # 每次取连接前先 ping 一下，防止拿到失效连接
    pool_recycle=3600,     # 连接超过 1 小时回收，防止 MySQL 主动断开
    echo=False,            # True 会打印所有 SQL，调试用，生产关
)

# 2. session 工厂：每次调用产生一个新 session
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,      # 手动提交，避免误提交
    autoflush=False,       # 手动 flush，避免意外触发 SQL
)

# 3. ORM 模型的基类
Base = declarative_base()


# 4. 依赖注入用：给每个请求一个 session，请求结束自动关闭
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
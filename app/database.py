# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# 1. 创建 engine（全局一个，带连接池）
engine = create_engine(
    settings.database_url,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=settings.DB_POOL_RECYCLE,
    echo=settings.DB_ECHO,
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
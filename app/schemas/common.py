from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class Response(BaseModel, Generic[T]):
    """统一响应包装：{code, msg, data}"""

    code: int = 200
    msg: str
    data: T | None = None

import httpx

from app.config import settings
from app.utils.exceptions import LLMCallError

_client: httpx.AsyncClient | None = None

def get_llm_client() -> httpx.AsyncClient:
    """懒加载单例 httpx.AsyncClient """
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=settings.LLM_BASE_URL,
            timeout=httpx.Timeout(
                connect=settings.LLM_TIMEOUT_CONNECT,
                read=settings.LLM_TIMEOUT_READ,
                write=settings.LLM_TIMEOUT_WRITE,
                pool=settings.LLM_TIMEOUT_POOL,
            ),
            headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
        )
    return _client

async def chat(messages: list[dict]) -> str:
    """调大模型，返回 answer 字符串；所有失败统一转 LLMCallError"""
    client = get_llm_client()
    try:
        resp = await client.post(
            "/chat/completions",
            json={
                "model": settings.LLM_MODEL,
                "messages": messages,
            },
        )
        resp.raise_for_status()
    except httpx.TimeoutException as e:
        raise LLMCallError(f"大模型调用超时:{e}")
    except httpx.HTTPStatusError as e:
        raise LLMCallError(f"大模型返回错误状态:{e.response.status_code}")
    except httpx.RequestError as e:
        raise LLMCallError(f"大模型请求失败:{e}")

    data = resp.json()
    # 解析 DeepSeek 返回
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMCallError(f"大模型返回结构异常:{e}")

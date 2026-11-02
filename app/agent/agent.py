import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from app.agent.state import ConsultState
from app.agent.tools import get_order_info, get_inventory, get_logistics, get_orders_item, get_product_detail, search_faq
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import ToolErrorMiddleware
from langchain.agents.middleware.types import ToolCallRequest
from langgraph.checkpoint.redis import RedisSaver 

load_dotenv()


def build_consult_agent():
    llm = ChatOpenAI(
        model=os.getenv("LLM_MODEL"),
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
        timeout=int(os.getenv("LLM_TIMEOUT_READ", "30")),
        use_responses_api=False,
    )

    ttl_config = {"default_ttl": 1440, "refresh_on_read": True}
    checkpointer = RedisSaver(
        redis_url="redis://localhost:6380",
        ttl=ttl_config,
    )
    checkpointer.setup()

    return create_agent(
        llm,
        [get_order_info, get_inventory, get_logistics, get_orders_item, get_product_detail, search_faq],
        state_schema=ConsultState,
        system_prompt="你是订单系统的智能客服。根据工具返回的信息回答用户问题，不要编造信息。",
        checkpointer=checkpointer,
        middleware=[ToolErrorMiddleware(on_tool_error)],
    )

def on_tool_error(exc: Exception, request: ToolCallRequest) -> str:
    return f"工具 {request.tool_call['name']} 执行失败: {type(exc).__name__}。请告知用户暂时无法查询。"
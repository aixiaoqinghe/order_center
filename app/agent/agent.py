import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from app.agent.state import ConsultState
from app.agent.tools import get_order_info, get_inventory, get_logistics
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import ToolErrorMiddleware
from langchain.agents.middleware.types import ToolCallRequest

load_dotenv()


def build_consult_agent():
    llm = ChatOpenAI(
        model=os.getenv("LLM_MODEL"),
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
        timeout=int(os.getenv("LLM_TIMEOUT_READ", "30")),
        use_responses_api=False,
    )
    return create_agent(
        llm,
        [get_order_info, get_inventory, get_logistics],
        state_schema=ConsultState,
        system_prompt="你是订单客服。根据工具返回的信息回答用户问题。不要编造信息。",
        checkpointer=InMemorySaver(),
        middleware=[ToolErrorMiddleware(on_tool_error)],
    )

def on_tool_error(exc: Exception, request: ToolCallRequest) -> str:
    return f"工具 {request.tool_call['name']} 执行失败: {type(exc).__name__}。请告知用户暂时无法查询。"
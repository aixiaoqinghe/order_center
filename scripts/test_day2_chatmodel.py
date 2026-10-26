import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# 从 .env 读
llm = ChatOpenAI(
    model = os.getenv("LLM_MODEL"),
    api_key = os.getenv("LLM_API_KEY"),
    base_url = os.getenv("LLM_BASE_URL"),
    timeout = int(os.getenv("LLM_TIMEOUT_READ", "30")),
    use_responses_api = False,     # 显示设，避免路由猜错
)

resp = llm.invoke("你好")
print(resp.content)
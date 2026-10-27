import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

load_dotenv()

# 注: Deepseek 思考模式不支持 tool_choice, with_structured_output 会 400
# 故改用 PydanticOutputParser 走 Prompt 约束 + 本地解析, 绕开 tool_choice 依赖。

# 定义抽取目标
class OrderInfo(BaseModel):
    order_id: str = Field(description="订单编号")
    status: str = Field(description="订单状态, 如未支付、已支付、已完成、已取消")
    amount: float = Field(description="订单金额")

llm = ChatOpenAI(
    model=os.getenv("LLM_MODEL"),
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL"),
    timeout=int(os.getenv("LLM_TIMEOUT_READ", "30")),
    use_responses_api=False,
)

text = "订单ORD123已支付，金额199.5元，等待发货。"

# PydanticOutputParser : Prompt 约束格式 + 本地解析
parser = PydanticOutputParser(pydantic_object=OrderInfo)
prompt = ChatPromptTemplate.from_messages([
    ("system", "从文本中抽取订单信息.。 \n{format_instructions}"),
    ("human", "{text}"),
]).partial(format_instructions=parser.get_format_instructions())

chain = prompt | llm | parser 
result = chain.invoke({"text": text})
print(f"成功: {result}")
print(f"类型: {type(result)}")
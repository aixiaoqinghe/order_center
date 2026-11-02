from app.agent.agent import build_consult_agent 
from langchain_core.messages import HumanMessage

agent = build_consult_agent()

# 5-10 个测试问题，覆盖不同类型
questions = [
    ("订单状态有哪些", "faq"),           # 应调 search_fag 
    ("怎么取消订单", "faq"),             # 应调 search_faq
    ("库存不足怎么办", "faq"),           # 应调 search_faq
    ("我的订单", "list"),               # 应调 get_orders_item
    ("订单666什么状态", "order"),        # 应调 get_order_info
    ("订单99999什么状态", "notfound"),   # 应调 get_order_info, 返回未找到
    ("商品5多少钱", "product"),          # 应调 get_product_detail
    ("订单666到哪了", "logistics"),      # 应调 get_logistics, 返回暂不支持 
]

for i, (q, kind) in enumerate(questions, 1):
    config = {"configurable": {"thread_id": f"eval_{i}"}, "recursion_limit": 7}
    result = agent.invoke(
        {"messages": [HumanMessage(content=f"当前订单ID: 666。用户问题: {q}")], "user_id": 1},
        config,
    )
    answer = result["messages"][-1].content
    # 看它调了哪些工具
    tools_called = []
    for msg in result["messages"]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            tools_called.extend(tc["name"] for tc in msg.tool_calls)
    print(f"=== {i}. {q} [预期: {kind}] ===")
    print(f"调用工具: {tools_called or '无'}")
    print(f"回答: {answer}")
    print()
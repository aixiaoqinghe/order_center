from app.agent.agent import build_consult_agent

agent = build_consult_agent()
config = {"configurable": {"thread_id": "test_day10_error"}, "recursion_limit": 7}

# 查一个不存在的订单，get_order_info 会抛 OrderNotFoundError (或类似)
result = agent.invoke(
    {"messages": [("user", "当前订单ID: 999999。这个订单什么状态?")], "user_id": 1},
    config,
)
print(result["messages"][-1].content)
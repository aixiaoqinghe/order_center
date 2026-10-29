from app.agent.agent import build_consult_agent

# 构建 agent (已挂 InMemorySaver)
agent = build_consult_agent()

# 同一个 thread_id = 同一个对话线程
config = {"configurable": {"thread_id": "test_user_1_order_666"}}

print("=== 第一轮: 问订单 ===")
r1 = agent.invoke(
    {"messages": [("user", "当前订单ID: 666。订单到哪了?")], "user_id": 1},
    config,
)
print(r1["messages"][-1].content)

print("\n=== 第二轮: 追问 (不重复订单号) ===")
r2 = agent.invoke(
    {"messages": [("user", "我刚才问的是哪个订单?")], "user_id": 1},
    config,
)
print(r2["messages"][-1].content)

print("\n=== 第三轮: 换 thread_id (应该失忆) ===")
other_config = {"configurable": {"thread_id": "test_user_1_order_999"}}
r3 = agent.invoke(
    {"messages": [("user", "我刚才问的是哪个订单?")], "user_id": 1},
    other_config
)
print(r3["messages"][-1].content)
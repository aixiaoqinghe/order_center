from app.agent.tools import search_faq

# 测三个不同类型的问题
for q in ["订单状态有哪些", "怎么取消订单", "库存不足怎么办"]:
    print(f"=== 问: {q} ===")
    print(search_faq.invoke({"query": q}))
    print()
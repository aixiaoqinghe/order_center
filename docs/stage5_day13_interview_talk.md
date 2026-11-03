# 阶段5 面试话术

## 1. 项目背景（一句话）
订单系统需要 AI 客服，原来采取的方式是用ORM查询数据库中的订单状态 (已取消时带取消原因)，拼接进 prompt 里面，然后使用 llm 来回答用户问题，但是使用 llm 弊端就是问题类型不固定，固定路径覆盖不全。

## 2. 我做了什么（核心，3-5 句）
- 把客服从单纯的只能查数据库固定内容，拼接成prompt回答的llm，升级为根据用户的问题，动态调用不同的工具tools，来回答用户问题。
- 封装了哪些工具：
    - get_order_info：根据订单ID查订单信息。
    - get_inventory：根据商品ID查询库存信息
    - get_logistics：根据订单ID查询物流状态，项目无物流表，返回固定文案不瞎编。
    - get_orders_item：根据用户ID查询用户最近订单列表
    - get_product_detail：根据商品ID查询商品详情
    - search_faq：从 Chroma 知识库检索 FAQ。

- 加了什么能力：
    - RAG: 从 Chroma 检索相关 FAQ，交给 LLM 组织回答。
    - 记忆: Redis 存对话历史，按 thread_id 隔离，TTL 24小时。 
    - 降级: 当工具使用失败时，调用我们原先的 llm 来回答用户问题。
- 用了什么框架：
    - LangChain: 用于封装工具、调用 llm 等。
    - LangGraph: 用于构建 Agent，管理状态、调用工具等。
    - create_agent 是 LangChain 1.x 的入口，底层跑 LangGraph 循环。


## 3. 架构（能画图、能口述）
用户问题 + 历史记忆 → LLM 决定调哪个工具 (可能是查订单、
查库存、查FAQ) → 执行工具 → 结果塞回 LLM → LLM 决定还要不要再调 → 最终回答 → 返回


## 4. 踩过的坑（挑 3-5 个你印象最深的）
1. DeepSeek 思考模式不支持 tool_choice:
    with_structured_output 走 function_calling 会 400，改用 PydanticOutputParser 绕开 (Day3)
2. create_react_agent 已弃用: LangChain 1.x 迁到 create_agent (Day5)
3. max_iterations 是旧版 AgentExecutor 参数: create_agent 用 recursion_limit (Day10)
4. 工具描述决定模型调不调用: 描述写功能 / 参数格式 / 适用场景，模型才不混 (Day4)
5. InjectedState 解决工具拿不到 user_id: 模型看不到，工具内部拿 (Day7)
6. asyncio.to_thread 包 Agent 执行不阻塞 event loop (Day7)
7. ToolErrorMiddleware 转述工具异常: Agent 不崩，用户看到人话 (Day10)
8. sentence-transformers 6.2.0 + bge-small-zh 报 Unrecognized processing class: 降到 5.7.0 + local_files_only = True 解决 (Day11)
9. from_conn_string 是 @contextmanager: Web 服务单例常驻不能用 with，改直接 RedisSaver(...) 构造 (Day12)
10. InMemorySaver 重启丢记忆: 换 Redis Stack + RedisSaver，TTL 24h (Day12)


## 5. 技术选型（为什么这么选）
- 为什么用 Agent 不用固定 Workflow：
    问题类型不固定，固定路径覆盖不全
- 为什么用 LangChain：
    生态成熟、工具 / Agent 封装现成、create_agent 直接跑 ReAct 循环
- 为什么用 Chroma / bge-small-zh：
    本地零配置、中文优化、512维轻量、不用 API key
- 为什么用 Redis 存记忆：
    项目已有 Redis、TTL 可控、跨请求持久化

## 6. 项目局限（诚实说，不吹）
- Agent 局限: 
    没有多 Agent 协作、没有正式评估指标 (只有8个问题的轻评估)、没有 Human-in-the-loop、没有 LangSmith tracing
- 订单系统 known_issues:
    锁冲突不重试、同步 DB + 异步外壳、扣库存不幂等、支付无并发控制等

## 7. 3 分钟口述版
  我这个订单系统原来有个 AI 客服，流程是固定的: 查订单状态、拼进 prompt、调一次大模型。问题在于用户问题类型不固定————有人问订单、有人问库存、有人问退货规则，固定路径覆盖不全。

  阶段5 我把它升级成了 Tool-Calling Agent。用 LangChain 的 create_agent(底层跑 LangGraph 循环)，封装了6个工具：查订单、查库存、查物流、查最近订单列表、查商品详情、查 FAQ。用户问什么，模型自己决定调哪个工具、调几次。

  加了三个能力: RAG，FAQ 存 Chroma，search_faq 检索相关条目交给模型组织；记忆，Redis 存对话历史，按 user_id order_id 隔离，TTL 24小时，多轮追问不丢上下文；降级，Agent 硬异常、超时、返回空，都退回原来的旧客服，保证可用。

  踩过的坑里印象最深的是: DeepSeek 思考模式不支持 tool_choice，with_structured_output 会400，改用 PydanticOutputParser 绕开；还有 create_react_agent 弃用，迁到 create_agent；以及 InjectedState 让工具偷偷拿到 user_id，模型看不到。

  局限我也清楚: 没有多 Agent 协作、没有正式评估指标、没有 Human-in-the-loop。这些是下一步方向。

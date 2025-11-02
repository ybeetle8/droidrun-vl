# LangGraph 快速开始

## 安装

项目使用 `uv` 包管理工具。

### 使用 uv 安装 LangGraph

```bash
# 安装 LangGraph 和相关依赖
uv pip install langgraph langchain langchain-core langchain-openai typing-extensions
```

### 已安装的包

执行上述命令后，会自动安装以下包：

- `langgraph` (1.0.2) - 核心框架
- `langchain` (1.0.3) - LangChain 核心
- `langchain-core` (1.0.2) - 核心组件
- `langchain-openai` (1.0.1) - OpenAI 兼容接口
- `langgraph-checkpoint` (3.0.0) - 检查点系统
- `langgraph-prebuilt` (1.0.2) - 预构建组件
- `langsmith` (0.4.38) - 监控和追踪

## 运行演示

### 1. LangGraph 版本（推荐）

```bash
uv run test/test_tools_lg.py
```

### 2. LlamaIndex 版本（对比）

```bash
uv run test/test_tools.py
```

## 关键特性对比

| 特性 | test_tools.py<br>(LlamaIndex) | test_tools_lg.py<br>(LangGraph) |
|------|-------------------------------|--------------------------------|
| 状态管理 | 手动 Context.store | TypedDict 类型安全 |
| 流程控制 | 线性执行 | 图结构 + 条件路由 |
| 检查点 | ❌ 无 | ✅ 自动保存/恢复 |
| 可视化 | ❌ 无 | ✅ ASCII 流程图 |
| 重试机制 | 手动实现 | 内置支持 |
| 人机交互 | ❌ 无 | ✅ interrupt_before |

## 代码结构对比

### LlamaIndex 版本（简化）

```python
# 线性执行
async def main_async():
    adb_tools = AdbTools(use_tcp=True)

    # 阶段1：分析
    analysis = analyze_screen_phase1(...)

    # 阶段2：生成代码
    result = await generate_and_execute_code_phase2(...)

    # 阶段3：验证
    if result:
        save_verification_screenshot(adb_tools)
```

### LangGraph 版本（结构化）

```python
# 构建状态图
workflow = StateGraph(AndroidAgentState)

# 添加节点
workflow.add_node("capture", capture_screen_node)
workflow.add_node("analyze", analyze_screen_node)
workflow.add_node("generate_code", generate_code_node)
workflow.add_node("execute", execute_code_node)
workflow.add_node("verify", verify_result_node)

# 条件路由（支持重试和分支）
workflow.add_conditional_edges(
    "generate_code",
    route_next_action,
    {
        "execute": "execute",
        "generate_code": "generate_code",  # 重试
        END: END
    }
)

# 编译并执行
app = workflow.compile(checkpointer=memory)
final_state = await app.ainvoke(initial_state, config)
```

## LangGraph 核心概念

### 1. 状态（State）

使用 TypedDict 定义类型安全的状态：

```python
class AndroidAgentState(TypedDict):
    messages: Annotated[list, add_messages]  # 自动累积
    screenshot: bytes | None
    ui_state: dict | None
    next_action: Literal["analyze", "execute", "end"] | None
```

### 2. 节点（Node）

每个节点是一个异步函数，接收状态并返回更新：

```python
async def analyze_screen_node(
    state: AndroidAgentState,
    config: dict
) -> AndroidAgentState:
    """分析屏幕"""
    llm = config["configurable"]["llm"]

    # 调用 LLM
    result = await llm.ainvoke(...)

    # 返回更新的状态
    return {
        **state,
        "analysis_result": result,
        "next_action": "generate_code"
    }
```

### 3. 边（Edge）

定义节点之间的连接：

```python
# 固定边
workflow.add_edge(START, "capture")

# 条件边（动态路由）
workflow.add_conditional_edges(
    "analyze",
    route_next_action,  # 路由函数
    {
        "generate_code": "generate_code",
        END: END
    }
)
```

### 4. 检查点（Checkpoint）

自动保存每个节点后的状态：

```python
# 添加内存检查点
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# 带线程ID执行（用于恢复）
config = {
    "configurable": {
        "thread_id": "demo_001"
    }
}

# 自动保存每步
await app.ainvoke(initial_state, config)

# 可以从检查点恢复
state = await app.aget_state(config)
```

## 高级特性

### 1. 人机交互

在敏感操作前暂停，等待人工确认：

```python
app = workflow.compile(
    checkpointer=memory,
    interrupt_before=["execute"]  # 执行前暂停
)

# 第一次执行：运行到 execute 前暂停
await app.ainvoke(state, config)

# 人工审核后继续
await app.ainvoke(None, config)  # 从检查点继续
```

### 2. 流式输出

逐步获取每个节点的输出：

```python
async for event in app.astream(initial_state, config):
    node_name = list(event.keys())[0]
    node_state = event[node_name]
    print(f"节点 {node_name} 完成")
```

### 3. 可视化

查看工作流结构：

```python
# ASCII 图
print(app.get_graph().draw_ascii())

# Mermaid 图（可在 Markdown 中渲染）
print(app.get_graph().draw_mermaid())

# PNG 图（需要 graphviz）
app.get_graph().draw_png("workflow.png")
```

### 4. 并行执行

同时运行多个节点：

```python
# 定义并行节点
workflow.add_node("task1", task1_node)
workflow.add_node("task2", task2_node)
workflow.add_node("merge", merge_node)

# 从起点到两个任务
workflow.add_edge(START, "task1")
workflow.add_edge(START, "task2")

# 两个任务都完成后到 merge
workflow.add_edge("task1", "merge")
workflow.add_edge("task2", "merge")
```

## 调试技巧

### 1. 查看每步状态

```python
# 获取当前状态
state = await app.aget_state(config)
print(f"当前节点: {state.next}")
print(f"状态值: {state.values}")
```

### 2. 查看执行历史

```python
# 获取所有检查点
checkpoints = await app.aget_state_history(config)

async for checkpoint in checkpoints:
    print(f"步骤: {checkpoint.metadata}")
    print(f"状态: {checkpoint.values}")
```

### 3. 时间旅行（回到历史状态）

```python
# 获取特定检查点
checkpoint = await app.aget_state(config, checkpoint_id="...")

# 从该检查点继续
await app.ainvoke(None, config)
```

## 性能优化

### 1. 选择合适的 Checkpointer

```python
# 内存（开发/测试）
from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()

# SQLite（生产）
from langgraph.checkpoint.sqlite import SqliteSaver
checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

# PostgreSQL（大规模）
from langgraph.checkpoint.postgres import PostgresSaver
checkpointer = PostgresSaver.from_conn_string("postgresql://...")
```

### 2. 控制检查点频率

```python
# 只在关键节点保存
app = workflow.compile(
    checkpointer=memory,
    checkpoint_at=["analyze", "execute"]  # 只在这些节点保存
)
```

## 监控和追踪

### 使用 LangSmith

LangGraph 原生集成 LangSmith 云端监控：

```bash
# 设置环境变量
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=your_api_key
export LANGCHAIN_PROJECT=droidrun

# 运行时自动上传追踪数据
uv run test/test_tools_lg.py
```

在 [smith.langchain.com](https://smith.langchain.com) 可以看到：
- 每个节点的输入/输出
- LLM 调用详情
- 耗时分析
- 错误追踪

## 常见问题

### Q1: 为什么代码量更多？

A: LangGraph 用更多的结构换来了：
- 更清晰的架构
- 更强的类型安全
- 更多的功能（检查点、可视化等）
- 更好的可维护性

### Q2: 什么时候用 LangGraph 而不是 LlamaIndex？

A: 如果你：
- 主要做 Agent 编排（不需要 RAG）
- 需要复杂的流程控制
- 需要暂停/恢复
- 需要人工审核
- 需要可视化和监控

那就选 LangGraph！

### Q3: 能同时用 LangGraph 和 LlamaIndex 吗？

A: 可以！
- LlamaIndex 负责 RAG（文档检索）
- LangGraph 负责工作流编排

```python
# 在 LangGraph 节点中使用 LlamaIndex
async def rag_search_node(state, config):
    query_engine = state["query_engine"]  # LlamaIndex
    result = query_engine.query(state["query"])

    return {
        **state,
        "search_result": result
    }
```

## 下一步

1. **运行演示**：`uv run test/test_tools_lg.py`
2. **查看对比文档**：[LangGraph vs LlamaIndex 对比.md](./LangGraph%20vs%20LlamaIndex%20对比.md)
3. **探索高级特性**：人机交互、并行执行、监控
4. **考虑迁移 DroidRun**：用 LangGraph 重构核心代理

## 参考资源

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [LangGraph GitHub](https://github.com/langchain-ai/langgraph)
- [LangSmith 监控平台](https://smith.langchain.com)
- [LangChain 文档](https://python.langchain.com/)

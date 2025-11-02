# LangGraph vs LlamaIndex 工作流对比

## 概述

本文档对比了 `test/test_tools.py`（LlamaIndex 版本）和 `test/test_tools_lg.py`（LangGraph 版本）的实现差异，展示 LangGraph 在 Agent 工作流编排方面的优势。

## 核心差异对比

### 1. 架构设计

| 特性 | LlamaIndex | LangGraph |
|------|------------|-----------|
| 核心抽象 | Workflow + Events | StateGraph + Nodes |
| 状态管理 | Context.store (字典) | TypedDict (类型安全) |
| 流程控制 | 事件驱动 | 图结构 + 条件路由 |
| 可视化 | ❌ 无 | ✅ 自动生成流程图 |

### 2. 状态管理

#### LlamaIndex (test_tools.py)
```python
# 状态分散在各处，需要手动管理
class SimpleContext:
    def __init__(self):
        self.store = SimpleStore()

# 手动 get/set
await ctx.store.set("ui_state", state["a11y_tree"])
state = await ctx.store.get("ui_state", default=None)
```

#### LangGraph (test_tools_lg.py)
```python
# 类型安全的状态定义
class AndroidAgentState(TypedDict):
    messages: Annotated[list, add_messages]  # 自动累积
    screenshot: bytes | None
    ui_state: dict | None
    analysis_result: str | None
    # ... 完整的类型定义

# 状态自动传递和更新
return {
    **state,
    "analysis_result": full_response,
    "next_action": "generate_code"
}
```

**优势：**
- ✅ 类型检查：IDE 自动补全和类型提示
- ✅ 自动合并：消息历史自动累积
- ✅ 清晰结构：一眼看出所有状态字段

### 3. 流程编排

#### LlamaIndex (test_tools.py)
```python
# 线性执行，缺乏灵活性
async def main_async():
    # 1. 初始化
    adb_tools = AdbTools(use_tcp=USE_TCP)

    # 2. 第一阶段
    analysis_result = analyze_screen_phase1(...)

    # 3. 第二阶段
    result = await generate_and_execute_code_phase2(...)

    # 4. 验证
    if result:
        save_verification_screenshot(adb_tools)
```

#### LangGraph (test_tools_lg.py)
```python
# 图结构，支持条件路由和重试
workflow = StateGraph(AndroidAgentState)

# 添加节点
workflow.add_node("capture", capture_screen_node)
workflow.add_node("analyze", analyze_screen_node)
workflow.add_node("generate_code", generate_code_node)
workflow.add_node("execute", execute_code_node)
workflow.add_node("verify", verify_result_node)

# 条件路由
workflow.add_conditional_edges(
    "generate_code",
    route_next_action,
    {
        "execute": "execute",
        "generate_code": "generate_code",  # 支持重试！
        END: END
    }
)
```

**优势：**
- ✅ 灵活路由：基于状态动态决定下一步
- ✅ 重试机制：内置支持（见代码生成失败重试）
- ✅ 并行执行：可以轻松添加并行节点
- ✅ 可视化：`app.get_graph().draw_ascii()` 打印流程图

### 4. 检查点（Checkpoint）系统

#### LlamaIndex (test_tools.py)
```python
# ❌ 无内置检查点支持
# 需要手动保存/恢复状态
```

#### LangGraph (test_tools_lg.py)
```python
# ✅ 内置检查点支持
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

config = {
    "configurable": {
        "thread_id": "android_agent_demo_001"  # 唯一标识
    }
}

# 自动保存每个节点后的状态
final_state = await app.ainvoke(initial_state, config)

# 可以从任意检查点恢复！
```

**优势：**
- ✅ 自动保存：每个节点执行后自动保存状态
- ✅ 暂停/恢复：可以暂停工作流，稍后继续
- ✅ 时间旅行：可以回到任意历史状态
- ✅ 调试友好：出错时可以从检查点重新开始

### 5. 人机交互（Human-in-the-Loop）

#### LlamaIndex (test_tools.py)
```python
# ❌ 无内置支持
# 需要手动实现中断逻辑
```

#### LangGraph (test_tools_lg.py)
```python
# ✅ 原生支持人工干预
workflow.add_node("human_review", human_review_node)

# 可以在任意节点设置中断点
app = workflow.compile(
    checkpointer=memory,
    interrupt_before=["execute"]  # 执行前暂停，等待人工确认
)

# 执行到 execute 节点前会暂停
# 人工审核后可以继续
await app.ainvoke(state, config)
```

**优势：**
- ✅ 内置中断：可以在任意节点暂停
- ✅ 人工审核：适用于敏感操作
- ✅ 灵活控制：可以修改状态后继续

### 6. 调试和监控

#### LlamaIndex (test_tools.py)
```python
# 调试依赖 print 语句
print("🔍 第一阶段：屏幕分析")
print("-" * 100)
```

#### LangGraph (test_tools_lg.py)
```python
# 可视化流程图
print(app.get_graph().draw_ascii())

# 输出示例：
#     +-----------+
#     |  __start__|
#     +-----------+
#           *
#           *
#           *
#     +-----------+
#     |  capture  |
#     +-----------+
#           *
#           *
#           *
#     +-----------+
#     |  analyze  |
#     +-----------+
# ...

# 每个节点的输入/输出都可追踪
# 支持集成 LangSmith 进行深度监控
```

**优势：**
- ✅ 可视化：自动生成流程图
- ✅ 日志追踪：每个节点的输入输出都可追踪
- ✅ 性能分析：可以分析每个节点的耗时
- ✅ 远程监控：集成 LangSmith 云端监控

### 7. 错误处理和重试

#### LlamaIndex (test_tools.py)
```python
# 手动实现重试逻辑
try:
    result = await generate_and_execute_code_phase2(...)
except Exception as e:
    # 需要手动处理
    print(f"错误: {e}")
```

#### LangGraph (test_tools_lg.py)
```python
# 基于状态的重试
async def generate_code_node(state: AndroidAgentState, config: dict):
    code = extract_code_from_markdown(full_response)

    if not code:
        retry_count = state.get("retry_count", 0) + 1
        if retry_count < 3:
            return {
                **state,
                "retry_count": retry_count,
                "next_action": "generate_code"  # 自动重试！
            }

# 路由器自动处理重试
workflow.add_conditional_edges(
    "generate_code",
    route_next_action,
    {
        "generate_code": "generate_code",  # 循环重试
        "execute": "execute",
        END: END
    }
)
```

**优势：**
- ✅ 声明式重试：在状态和路由中定义
- ✅ 灵活控制：可以基于任意条件重试
- ✅ 避免死循环：可以设置最大重试次数

## 代码量对比

| 指标 | LlamaIndex | LangGraph |
|------|------------|-----------|
| 总行数 | 435 | 680 |
| 核心逻辑 | 300+ | 400+ |
| 样板代码 | 少 | 多（但更清晰） |

**注意：** LangGraph 代码量更多，但换来了：
- 更清晰的结构
- 更强的类型安全
- 更好的可维护性
- 更多的功能（检查点、可视化等）

## 性能对比

| 指标 | LlamaIndex | LangGraph |
|------|------------|-----------|
| 启动开销 | 低 | 中等 |
| 运行时开销 | 低 | 低（检查点有轻微开销） |
| 内存占用 | 低 | 中等（需要存储状态历史） |

## 适用场景

### 选择 LlamaIndex Workflow 当：
- ✅ 简单的线性流程
- ✅ 不需要检查点和恢复
- ✅ 项目已经使用 LlamaIndex 的 RAG 功能
- ✅ 追求最小依赖

### 选择 LangGraph 当：
- ✅ 复杂的多分支流程
- ✅ 需要条件路由和重试
- ✅ 需要暂停/恢复功能
- ✅ 需要人工审核环节
- ✅ 团队协作，需要可视化流程
- ✅ 专注于 Agent 编排（不需要 RAG）

## 迁移建议

如果你的项目符合以下情况，建议迁移到 LangGraph：

1. **主要使用 Workflow，不使用 LlamaIndex 的 RAG 功能**
   - DroidRun 就是这种情况！

2. **需要更复杂的流程控制**
   - 例如：根据执行结果选择不同路径

3. **需要调试和监控**
   - LangGraph 的可视化和追踪功能更强

4. **多人协作**
   - 图结构比事件驱动更容易理解

## 安装和运行

### 安装 LangGraph
```bash
pip install -r requirements_langgraph.txt
```

### 运行演示
```bash
# LlamaIndex 版本
python test/test_tools.py

# LangGraph 版本
python test/test_tools_lg.py
```

## LangGraph 核心优势总结

### 🎯 最重要的 5 个优势

1. **状态图架构** - 清晰、可视化、易于理解
2. **内置检查点** - 自动保存/恢复，支持暂停
3. **条件路由** - 灵活的流程控制，支持重试和分支
4. **类型安全** - TypedDict 提供完整的类型检查
5. **人机交互** - 原生支持人工审核和干预

### 📊 何时值得迁移

如果你的答案是"是"，强烈建议迁移：

- [ ] 主要使用 Workflow，不用 RAG？
- [ ] 需要复杂的流程控制？
- [ ] 需要暂停/恢复功能？
- [ ] 团队协作需要可视化？
- [ ] 需要人工审核环节？

### ⚠️ 注意事项

1. **学习曲线**：LangGraph 的概念（图、节点、边）需要时间理解
2. **依赖增加**：需要安装 LangChain 全家桶
3. **代码重构**：需要重新组织代码结构

## 示例：可视化流程图

运行 `test_tools_lg.py` 时会自动打印流程图：

```
     +-----------+
     |  __start__|
     +-----------+
           *
           *
           *
     +-----------+
     |  capture  |
     +-----------+
           *
           *
           *
     +-----------+
     |  analyze  |
     +-----------+
           *
           *
           *
  +----------------+
  | generate_code  |
  +----------------+
      ***     ***
    **          **
  **              **
+----------+    +----------+
| execute  |    |  __end__ |
+----------+    +----------+
    *
    *
    *
+----------+
|  verify  |
+----------+
    *
    *
    *
+----------+
| __end__  |
+----------+
```

这种可视化在复杂工作流中非常有用！

## 总结

对于 DroidRun 这样的 Agent 控制项目：

- **当前**：使用 LlamaIndex Workflow，但只用了它的工作流功能
- **建议**：迁移到 LangGraph，因为：
  1. 不需要 LlamaIndex 的 RAG 核心能力
  2. LangGraph 更适合 Agent 编排
  3. 获得更好的调试、监控和人机交互能力

**迁移成本**：中等（1-2 天重构核心代理逻辑）
**迁移收益**：高（更清晰的架构，更强的功能）

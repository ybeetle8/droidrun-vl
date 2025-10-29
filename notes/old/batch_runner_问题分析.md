# simple_example.py 显存爆炸问题分析

## 问题描述

运行 `simple_example.py` 时 Ollama 显存爆炸，但使用 CLI 命令 `uv run droidrun --provider Ollama --model qwen3-coder:30b --base_url http://localhost:11434` 运行正常。

## 根本原因：reasoning 参数默认值差异

**关键差异：CLI 和 SDK 的 `reasoning` 参数默认值不同**

### CLI 运行方式
```bash
uv run droidrun --provider Ollama --model qwen3-coder:30b --base_url http://localhost:11434 "打开闲鱼"
```

在 `droidrun/cli/main.py:247-248`：
```python
@click.option(
    "--reasoning", is_flag=True, help="Enable planning with reasoning", default=False
)
```

**CLI 默认 `reasoning=False`** - 只使用一个 LLM 实例

### simple_example.py 原代码
```python
agent = DroidAgent(
    goal="打开闲鱼",
    llm=llm,
    tools=tools,
    max_steps=15,
    vision=False,
    # ❌ 没有指定 reasoning，使用默认值
)
```

查看 `droidrun/agent/droid/droid_agent.py:72`：
```python
def __init__(
    self,
    goal: str,
    llm: LLM,
    tools: Tools,
    personas: List[AgentPersona] = [DEFAULT],
    max_steps: int = 15,
    timeout: int = 1000,
    vision: bool = False,
    reasoning: bool = False,  # SDK 默认也是 False，但可能被意外设置为 True
    ...
)
```

## 为什么会导致显存爆炸？

当 `reasoning=True` 时（在 `droid_agent.py:156-171`）：

```python
if self.reasoning:
    logger.info("📝 Initializing Planner Agent...")
    self.planner_agent = PlannerAgent(
        goal=goal,
        llm=llm,  # ⚠️ PlannerAgent 也会使用 LLM
        vision=vision,
        ...
    )
    self.max_codeact_steps = 5

    if self.reflection:
        self.reflector = Reflector(llm=llm, debug=debug)  # ⚠️ Reflector 也会使用 LLM
```

**多个组件同时使用 30B 模型：**
1. **DroidAgent** - 协调层（可能持有 LLM 引用）
2. **PlannerAgent** - 规划层（使用 LLM 进行任务分解）
3. **CodeActAgent** - 执行层（使用 LLM 执行具体操作）
4. **Reflector**（如果启用）- 反思层（使用 LLM 进行反思）

**结果：** 多个 qwen3-coder:30B 实例同时加载 → 显存爆炸！

## 解决方案

### 方案 1：显式禁用 reasoning（推荐）

```python
agent = DroidAgent(
    goal="打开闲鱼",
    llm=llm,
    tools=tools,
    max_steps=15,
    vision=False,
    reasoning=False,  # ✅ 显式禁用 reasoning
    reflection=False, # ✅ 显式禁用 reflection
)
```

### 方案 2：使用更小的模型

如果确实需要 reasoning 功能：
```python
llm = load_llm(
    provider_name="Ollama",
    model="qwen2.5:7b",  # ✅ 使用 7B 模型而不是 30B
    base_url="http://localhost:11434",
    temperature=0.2
)

agent = DroidAgent(
    goal="打开闲鱼",
    llm=llm,
    tools=tools,
    max_steps=15,
    vision=False,
    reasoning=True,   # 7B 模型可以承受多实例
    reflection=False,
)
```

### 方案 3：完全对齐 CLI 配置

```python
agent = DroidAgent(
    goal="打开闲鱼",
    llm=llm,
    tools=tools,
    max_steps=15,
    timeout=1000,
    vision=False,
    reasoning=False,
    reflection=False,
    debug=False,
)
```

## 修正后的 simple_example.py

```python
"""
最简单的 DroidRun 示例：打开闲鱼
"""

import asyncio
from droidrun.agent.droid import DroidAgent
from droidrun.agent.utils.llm_picker import load_llm
from droidrun.tools import AdbTools


async def main():
    # 1. 初始化 LLM（使用本地 Ollama）
    llm = load_llm(
        provider_name="Ollama",
        model="qwen3-coder:30b",
        base_url="http://localhost:11434",
        temperature=0.2
    )

    # 2. 初始化 Android 设备工具
    tools = AdbTools()

    # 3. 创建 DroidAgent 执行任务
    agent = DroidAgent(
        goal="打开闲鱼",
        llm=llm,
        tools=tools,
        max_steps=15,
        vision=False,
        reasoning=False,  # ✅ 关键：禁用 reasoning 避免多实例
        reflection=False, # ✅ 禁用 reflection
    )

    # 4. 执行任务
    result = await agent.run()

    # 5. 打印结果
    print(f"执行成功: {result.get('success')}")
    if result.get('output'):
        print(f"输出: {result['output']}")


if __name__ == "__main__":
    asyncio.run(main())
```

## 经验教训

1. **CLI 和 SDK 参数默认值可能不同** - 务必检查文档和源码
2. **大模型 + reasoning 模式 = 多实例** - 显存消耗成倍增加
3. **简单任务不需要 reasoning** - "打开闲鱼" 这类任务直接用 CodeActAgent 即可
4. **显式优于隐式** - 关键参数最好显式指定，避免依赖默认值
5. **参考 CLI 实现** - CLI 的参数配置通常是经过优化的最佳实践

## 性能对比

| 模式 | LLM 实例数 | 30B 模型显存需求 | 适用场景 |
|------|-----------|-----------------|----------|
| reasoning=False | 1 | ~20-30GB | 简单任务、单步操作 |
| reasoning=True | 2-3 | ~60-90GB | 复杂任务、多步规划 |
| reasoning=True + reflection=True | 3-4 | ~90-120GB | 极复杂任务 |

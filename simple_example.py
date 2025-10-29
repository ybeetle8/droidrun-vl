"""
最简单的 DroidRun 示例：打开闲鱼
"""

import asyncio
from droidrun.agent.droid import DroidAgent
from droidrun.agent.utils.llm_picker import load_llm
from droidrun.tools import AdbTools


async def main():
    # 1. 初始化 LLM（使用本地 Ollama）
    print("=== load_llm 参数 ===")
    llm_kwargs = {
        "provider_name": "Ollama",
        "model": "qwen3-coder:30b",
        "base_url": "http://localhost:11434",
        "temperature": 0.2,
        "context_window": 8192,  # 限制 KV cache 大小（从 262144 降到 8192）
        "request_timeout": 300.0,
    }
    print(llm_kwargs)

    llm = load_llm(**llm_kwargs)
    print(f"LLM 实例: {type(llm)}")
    print(f"LLM metadata: {llm.metadata}")

    # 2. 初始化 Android 设备工具
    tools = AdbTools()

    # 3. 创建 DroidAgent 执行任务
    print("\n=== DroidAgent 参数 ===")
    agent_kwargs = {
        "goal": "打开闲鱼",
        "llm": llm,
        "tools": tools,
        "max_steps": 15,
        "timeout": 1000,
        "vision": False,
        "reasoning": False,
        "reflection": False,
        "debug": False,
        "enable_tracing": False,
        "save_trajectories": "none",
    }
    print({k: v for k, v in agent_kwargs.items() if k not in ["llm", "tools"]})

    agent = DroidAgent(**agent_kwargs)

    # 4. 执行任务（使用 stream_events 避免内存堆积）
    handler = agent.run()

    # 消费事件流
    async for event in handler.stream_events():
        print(f"事件: {type(event).__name__}")

    result = await handler

    # 5. 打印结果
    print(f"执行成功: {result.get('success')}")
    if result.get('output'):
        print(f"输出: {result['output']}")


if __name__ == "__main__":
    asyncio.run(main())

"""
工具调用演示
演示 LLM 与工具结合的两阶段流程：
1. 第一阶段：屏幕分析，提取商品信息（流式输出）
2. 第二阶段：LLM 生成点击代码并执行，验证结果
"""
import os
import sys
import json
import inspect
from pathlib import Path
from typing import Dict, Callable, Any

# 设置控制台编码为 UTF-8
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# 设置环境变量
os.environ["OPENAI_API_KEY"] = "sk-Kd92LE2pud8bVtZE23B47248Bc064006Af400cB6770c8577"

from droidrun.tools.adb import AdbTools
from droidrun.tools.tools import describe_tools
from droidrun.agent.utils.llm_picker import load_llm
from droidrun.agent.utils.executer import SimpleCodeExecutor
from llama_index.core.base.llms.types import ChatMessage, MessageRole, TextBlock, ImageBlock
from llama_index.core.workflow import Context
import asyncio


def parse_tool_descriptions(tool_list: Dict[str, Callable]) -> str:
    """
    将工具字典转换为 LLM 可读的 markdown 格式描述

    Args:
        tool_list: 工具函数字典 {"tool_name": function, ...}

    Returns:
        str: markdown 格式的工具描述
    """
    tool_descriptions = []

    for tool in tool_list.values():
        tool_name = tool.__name__
        tool_signature = inspect.signature(tool)
        tool_docstring = tool.__doc__ or "No description available."
        formatted_signature = f"def {tool_name}{tool_signature}:\n    \"\"\"{tool_docstring}\"\"\"\n..."
        tool_descriptions.append(formatted_signature)

    return "\n\n".join(tool_descriptions)


def analyze_screen_phase1(screenshot_bytes: bytes, state_data: dict, llm, extra_params: dict = None):
    """
    第一阶段：使用大模型分析屏幕，提取商品信息

    Args:
        screenshot_bytes: 截图字节数据
        state_data: UI状态JSON数据
        llm: 大模型实例
        extra_params: 额外的生成参数

    Returns:
        str: 分析结果
    """
    print("\n" + "=" * 100)
    print("🔍 第一阶段：屏幕分析")
    print("=" * 100)

    if extra_params is None:
        extra_params = {}

    # 构建提示词
    state_json_str = json.dumps(state_data, ensure_ascii=False, indent=2)

    prompt = f"""请分析这个Android屏幕截图和UI状态信息，提取商品列表。

**分析要求：**
1. 找出屏幕上的所有商品
2. 一定是要出现在屏幕上的,遮住过多的不要,防止后面点错
3. 对于每个商品，提取以下信息：
   - 商品标题
   - 商品价格
   - 商品 UI元素的 index （用于点击）
   - UI元素的坐标 (bounds)
4. 按照商品在屏幕上出现的顺序列出

**输出格式（JSON）：**
```json
{{
  "products": [
    {{
      "title": "商品标题",
      "price": "商品价格",
      "index": 数字,
      "bounds": [x1, y1, x2, y2]
    }}
  ]
}}
```

下面是UI状态的JSON数据：
```json
{state_json_str}
```"""

    # 构建消息
    content_blocks = [
        TextBlock(text=prompt),
        ImageBlock(image=screenshot_bytes)
    ]

    message = ChatMessage(
        role=MessageRole.USER,
        content=content_blocks,
    )

    # 调用大模型（流式输出）
    response_stream = llm.stream_chat([message], **extra_params)

    print("\n🤖 分析结果（流式输出）:\n")
    print("-" * 100)

    full_response = ""
    for chunk in response_stream:
        content = chunk.delta
        if content:
            print(content, end="", flush=True)
            full_response += content

    print()
    print("-" * 100)

    return full_response


async def generate_and_execute_code_phase2(
    analysis_result: str,
    tool_list: Dict[str, Callable],
    tool_descriptions: str,
    adb_tools: AdbTools,
    llm,
    extra_params: dict = None
):
    """
    第二阶段：让 LLM 生成点击代码并执行

    Args:
        analysis_result: 第一阶段的分析结果
        tool_list: 工具函数字典
        tool_descriptions: 工具描述文档
        adb_tools: AdbTools 实例
        llm: 大模型实例
        extra_params: 额外的生成参数

    Returns:
        dict: 执行结果
    """
    print("\n" + "=" * 100)
    print("🔧 第二阶段：生成并执行点击代码")
    print("=" * 100)

    if extra_params is None:
        extra_params = {}

    # 构建系统提示
    system_prompt = f"""你是一个 Android 自动化助手。你可以通过编写 Python 代码来控制设备。

## 可用工具：

{tool_descriptions}

## 代码要求：
1. 代码必须用 ```python ... ``` 包裹
2. 只使用上面列出的工具函数
3. 代码要简洁清晰
4. 执行完操作后要输出结果说明

## 示例：
```python
# 点击第一个商品
result = tap_by_index(5)
print(f"点击结果: {{result}}")
```
"""

    # 构建用户提示
    user_prompt = f"""基于以下屏幕分析结果，请生成代码来点击第一个商品。

## 屏幕分析结果：
{analysis_result}

## 任务：
请编写 Python 代码，点击第一个商品，并输出点击结果。
"""

    # 构建消息
    messages = [
        ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
        ChatMessage(role=MessageRole.USER, content=user_prompt)
    ]

    # 调用大模型（流式输出）
    print("\n🤖 LLM 响应（流式输出）:\n")
    print("-" * 100)

    response_stream = llm.stream_chat(messages, **extra_params)

    full_response = ""
    for chunk in response_stream:
        content = chunk.delta
        if content:
            print(content, end="", flush=True)
            full_response += content

    print()
    print("-" * 100)

    # 提取代码
    code = extract_code_from_markdown(full_response)

    if not code:
        print("\n❌ 未找到可执行的代码块")
        return None

    print(f"\n📝 提取的代码:\n")
    print("```python")
    print(code)
    print("```")

    # 执行代码
    print("\n⚙️  执行代码...\n")

    # 创建 Context（简化版）
    class SimpleContext:
        def __init__(self):
            self.store = SimpleStore()

        def write_event_to_stream(self, event):
            """写入事件到流（简化实现，仅用于演示）"""
            # 在演示中，我们只是忽略事件，不做实际处理
            pass

    class SimpleStore:
        def __init__(self):
            self._data = {}

        async def get(self, key, default=None):
            return self._data.get(key, default)

        async def set(self, key, value):
            self._data[key] = value

    ctx = SimpleContext()

    # 获取当前 UI 状态并存储到 context
    state = adb_tools.get_state()
    await ctx.store.set("ui_state", state["a11y_tree"])

    # 初始化代码执行器
    executor = SimpleCodeExecutor(
        loop=asyncio.get_event_loop(),
        locals={},
        globals={},
        tools=tool_list,
        tools_instance=adb_tools
    )

    # 执行代码
    result = await executor.execute(ctx, code)

    print("📊 执行结果:")
    print("-" * 100)
    print(result['output'])
    print("-" * 100)

    return result


def extract_code_from_markdown(text: str) -> str:
    """
    从 markdown 格式的文本中提取 Python 代码块

    Args:
        text: 包含代码块的文本

    Returns:
        str: 提取的代码，如果没有找到返回空字符串
    """
    import re

    # 匹配 ```python ... ``` 或 ``` ... ```
    patterns = [
        r'```python\s*\n(.*?)```',
        r'```\s*\n(.*?)```'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            # 返回第一个代码块
            return matches[0].strip()

    return ""


def save_verification_screenshot(adb_tools: AdbTools, output_dir: str = "test/analysis_output"):
    """
    保存验证截图

    Args:
        adb_tools: AdbTools 实例
        output_dir: 输出目录
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    print("\n📸 保存验证截图...")
    _, screenshot_bytes = adb_tools.take_screenshot(hide_overlay=True)

    screenshot_file = output_path / f"verification_{timestamp}.png"
    with open(screenshot_file, "wb") as f:
        f.write(screenshot_bytes)

    print(f"✅ 验证截图已保存: {screenshot_file}")


async def main_async():
    """主函数（异步版本）"""
    print("=" * 100)
    print("🎯 工具调用演示：两阶段流程")
    print("=" * 100)
    print()

    # 配置参数
    API_BASE = "http://192.168.18.9:8080/v1"
    MODEL = "/models"
    USE_TCP = True

    # LLM 生成参数
    MAX_TOKENS = 4048
    VLLM_EXTRA_PARAMS = {
        "frequency_penalty": 0.05,
        "presence_penalty": 0.05,
    }

    try:
        # 1. 初始化 ADB 工具
        print("📱 正在连接Android设备...")
        adb_tools = AdbTools(use_tcp=USE_TCP)
        print(f"✅ 已连接到设备: {adb_tools.device.serial}")

        # 2. 获取截图和UI状态
        print("\n📸 正在截取屏幕...")
        _, screenshot_bytes = adb_tools.take_screenshot(hide_overlay=True)
        print(f"✅ 截图完成，大小: {len(screenshot_bytes)} 字节")

        print("\n🔍 正在获取UI状态信息...")
        state_data = adb_tools.get_state()
        print(f"✅ UI状态获取完成")

        # 3. 初始化大模型
        print("\n🤖 正在连接大模型...")
        llm = load_llm(
            provider_name="OpenAILike",
            model=MODEL,
            api_base=API_BASE,
            api_key=os.environ["OPENAI_API_KEY"],
            temperature=0.0,
            request_timeout=60.0,
            max_tokens=MAX_TOKENS,
        )
        print("✅ 大模型连接成功")

        # 4. 第一阶段：屏幕分析
        analysis_result = analyze_screen_phase1(
            screenshot_bytes,
            state_data,
            llm,
            VLLM_EXTRA_PARAMS
        )

        # 5. 准备工具列表和描述
        print("\n🔧 准备工具列表...")
        tool_list = describe_tools(adb_tools, exclude_tools=[])
        # 只保留演示需要的工具
        demo_tools = {
            "tap_by_index": tool_list["tap_by_index"],
            "swipe": tool_list["swipe"],
            "input_text": tool_list["input_text"],
        }
        tool_descriptions = parse_tool_descriptions(demo_tools)
        print("✅ 工具准备完成")

        # 6. 第二阶段：生成并执行代码
        result = await generate_and_execute_code_phase2(
            analysis_result,
            demo_tools,
            tool_descriptions,
            adb_tools,
            llm,
            VLLM_EXTRA_PARAMS
        )

        # 7. 验证结果：等待页面加载后截图
        if result:
            print("\n⏳ 等待 2 秒让页面加载...")
            import time
            time.sleep(2)

            save_verification_screenshot(adb_tools)

        print("\n" + "=" * 100)
        print("✅ 演示完成！")
        print("=" * 100)

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """主函数"""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()

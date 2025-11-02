"""
LangGraph 节点函数定义
"""
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Literal
from io import StringIO
import sys

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END

from droidrun.tools.adb import AdbTools
from .state import AndroidAgentState
from ..utils.helpers import parse_tool_descriptions, extract_json_from_text, extract_code_from_markdown


async def capture_screen_node(state: AndroidAgentState, config: RunnableConfig) -> AndroidAgentState:
    """
    节点1: 捕获屏幕截图和 UI 状态
    """
    print("\n" + "=" * 100)
    print("📱 节点1: 捕获屏幕")
    print("=" * 100)

    # 从 config 获取工具
    tools = config["configurable"]["tools"]

    # 创建 AdbTools 实例用于截图
    adb_tools = AdbTools(use_tcp=True)

    print("📸 正在截取屏幕...")
    _, screenshot_bytes = adb_tools.take_screenshot(hide_overlay=True)
    print(f"✅ 截图完成，大小: {len(screenshot_bytes)} 字节")

    print("🔍 正在获取UI状态信息...")
    ui_state = adb_tools.get_state()
    print(f"✅ UI状态获取完成")

    # 生成工具描述
    tool_descriptions = parse_tool_descriptions(tools)

    return {
        **state,
        "screenshot": screenshot_bytes,
        "ui_state": ui_state,
        "tool_descriptions": tool_descriptions,
        "next_action": "analyze"
    }


async def analyze_screen_node(state: AndroidAgentState, config: RunnableConfig) -> AndroidAgentState:
    """
    节点2: 分析屏幕内容
    """
    print("\n" + "=" * 100)
    print("🔍 节点2: 屏幕分析")
    print("=" * 100)

    llm: ChatOpenAI = config["configurable"]["llm"]

    state_json_str = json.dumps(state["ui_state"], ensure_ascii=False, indent=2)

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

    messages = [
        HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{__import__('base64').b64encode(state['screenshot']).decode()}"
                    }
                }
            ]
        )
    ]

    print("\n🤖 分析结果（流式输出）:\n")
    print("-" * 100)

    full_response = ""
    async for chunk in llm.astream(messages):
        content = chunk.content
        if content:
            print(content, end="", flush=True)
            full_response += content

    print()
    print("-" * 100)

    products = extract_json_from_text(full_response)

    return {
        **state,
        "messages": state["messages"] + [HumanMessage(content=prompt), AIMessage(content=full_response)],
        "analysis_result": full_response,
        "extracted_products": products.get("products", []) if products else [],
        "next_action": "generate_code"
    }


async def generate_code_node(state: AndroidAgentState, config: RunnableConfig) -> AndroidAgentState:
    """
    节点3: 生成执行代码
    """
    print("\n" + "=" * 100)
    print("🔧 节点3: 生成执行代码")
    print("=" * 100)

    llm: ChatOpenAI = config["configurable"]["llm"]
    tool_descriptions = state["tool_descriptions"]

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

    user_prompt = f"""基于以下屏幕分析结果，请生成代码来点击第一个商品。

## 屏幕分析结果：
{state["analysis_result"]}

## 任务：
请编写 Python 代码，点击第一个商品，并输出点击结果。
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]

    print("\n🤖 LLM 响应（流式输出）:\n")
    print("-" * 100)

    full_response = ""
    async for chunk in llm.astream(messages):
        content = chunk.content
        if content:
            print(content, end="", flush=True)
            full_response += content

    print()
    print("-" * 100)

    code = extract_code_from_markdown(full_response)

    if not code:
        print("\n❌ 未找到可执行的代码块")
        retry_count = state.get("retry_count", 0) + 1
        if retry_count < 3:
            return {
                **state,
                "retry_count": retry_count,
                "next_action": "generate_code"
            }
        else:
            return {
                **state,
                "next_action": "end"
            }

    print(f"\n📝 提取的代码:\n")
    print("```python")
    print(code)
    print("```")

    return {
        **state,
        "messages": state["messages"] + [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt), AIMessage(content=full_response)],
        "generated_code": code,
        "retry_count": 0,
        "next_action": "execute"
    }


async def execute_code_node(state: AndroidAgentState, config: RunnableConfig) -> AndroidAgentState:
    """
    节点4: 执行生成的代码
    """
    print("\n" + "=" * 100)
    print("⚙️  节点4: 执行代码")
    print("=" * 100)

    code = state["generated_code"]
    tools = config["configurable"]["tools"]

    exec_globals = {tool_name: tool for tool_name, tool in tools.items()}
    exec_locals = {}

    print("\n执行中...\n")

    try:
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        exec(code, exec_globals, exec_locals)

        output = captured_output.getvalue()
        sys.stdout = old_stdout

        print("📊 执行结果:")
        print("-" * 100)
        print(output)
        print("-" * 100)

        result = {
            "success": True,
            "output": output,
            "error": None
        }

    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()

        print("❌ 执行错误:")
        print("-" * 100)
        print(error_msg)
        print("-" * 100)

        result = {
            "success": False,
            "output": None,
            "error": error_msg
        }

    return {
        **state,
        "execution_result": result,
        "next_action": "verify" if result["success"] else "end"
    }


async def verify_result_node(state: AndroidAgentState) -> AndroidAgentState:
    """
    节点5: 验证执行结果
    """
    print("\n" + "=" * 100)
    print("✅ 节点5: 验证结果")
    print("=" * 100)

    print("\n⏳ 等待 2 秒让页面加载...")
    await asyncio.sleep(2)

    output_dir = Path("test/analysis_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("\n📸 保存验证截图...")
    adb_tools = AdbTools(use_tcp=True)
    _, screenshot_bytes = adb_tools.take_screenshot(hide_overlay=True)

    screenshot_file = output_dir / f"verification_lg_{timestamp}.png"
    with open(screenshot_file, "wb") as f:
        f.write(screenshot_bytes)

    print(f"✅ 验证截图已保存: {screenshot_file}")

    return {
        **state,
        "next_action": "end"
    }


def route_next_action(state: AndroidAgentState) -> Literal["analyze", "generate_code", "execute", "verify", "__end__"]:
    """
    条件路由函数
    """
    next_action = state.get("next_action")

    if next_action == "analyze":
        return "analyze"
    elif next_action == "generate_code":
        return "generate_code"
    elif next_action == "execute":
        return "execute"
    elif next_action == "verify":
        return "verify"
    else:
        return END

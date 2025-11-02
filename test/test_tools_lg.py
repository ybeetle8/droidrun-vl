"""
LangGraph 版本工具调用演示
展示 LangGraph 相比 llama_index 的优势：
1. 状态图管理 - 清晰的状态流转
2. 内置检查点 - 自动保存中间状态，支持暂停/恢复
3. 条件路由 - 灵活的流程控制
4. 更好的调试 - 可视化执行流程
5. 人机交互 - 支持中断和人工干预
"""
import os
import sys
import json
import inspect
import asyncio
from pathlib import Path
from typing import Dict, Callable, Any, Annotated, Literal
from datetime import datetime

# 设置控制台编码为 UTF-8
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# 设置环境变量
os.environ["OPENAI_API_KEY"] = "sk-"

# LangGraph 核心导入
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict

# LangChain 导入（LangGraph 基于 LangChain）
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.runnables import RunnableConfig

# DroidRun 导入
from droidrun.tools.adb import AdbTools
from droidrun.tools.tools import describe_tools


# ============================================================================
# 状态定义 - LangGraph 的核心优势：类型安全的状态管理
# ============================================================================

class AndroidAgentState(TypedDict):
    """
    Agent 状态定义

    LangGraph 优势：
    - 类型安全：TypedDict 提供类型检查
    - 自动合并：messages 使用 add_messages 自动累积历史
    - 检查点友好：所有状态可序列化，支持保存/恢复
    """
    # 消息历史（自动累积）
    messages: Annotated[list, add_messages]

    # 设备相关
    screenshot: bytes | None
    ui_state: dict | None

    # 分析结果
    analysis_result: str | None
    extracted_products: list[dict] | None

    # 执行相关
    generated_code: str | None
    execution_result: dict | None

    # 工具描述（可序列化的字符串，而不是函数对象）
    tool_descriptions: str | None

    # 控制流
    next_action: Literal["analyze", "generate_code", "execute", "verify", "end"] | None
    retry_count: int


# ============================================================================
# 工具函数
# ============================================================================

def parse_tool_descriptions(tool_list: Dict[str, Callable]) -> str:
    """将工具字典转换为 LLM 可读的 markdown 格式描述"""
    tool_descriptions = []

    for tool in tool_list.values():
        tool_name = tool.__name__
        tool_signature = inspect.signature(tool)
        tool_docstring = tool.__doc__ or "No description available."
        formatted_signature = f"def {tool_name}{tool_signature}:\n    \"\"\"{tool_docstring}\"\"\"\n..."
        tool_descriptions.append(formatted_signature)

    return "\n\n".join(tool_descriptions)


def extract_json_from_text(text: str) -> dict | None:
    """从文本中提取 JSON 数据"""
    import re

    # 尝试匹配 ```json ... ``` 或 ```{ ... }```
    patterns = [
        r'```json\s*\n(.*?)```',
        r'```\s*\n(\{.*?\})```',
        r'\{.*?\}'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError:
                continue

    return None


def extract_code_from_markdown(text: str) -> str:
    """从 markdown 格式的文本中提取 Python 代码块"""
    import re

    patterns = [
        r'```python\s*\n(.*?)```',
        r'```\s*\n(.*?)```'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            return matches[0].strip()

    return ""


# ============================================================================
# 节点函数 - LangGraph 的工作流节点
# ============================================================================

async def capture_screen_node(state: AndroidAgentState, config: RunnableConfig) -> AndroidAgentState:
    """
    节点1: 捕获屏幕截图和 UI 状态

    LangGraph 优势：
    - 每个节点是独立的函数，易于测试
    - 状态自动传递和更新
    - 可以在任意节点设置检查点
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

    # 生成工具描述（工具本身已经在 config 中）
    tool_descriptions = parse_tool_descriptions(tools)

    # 更新状态（只存可序列化的数据）
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

    LangGraph 优势：
    - config 参数可以传递 LLM 等外部配置
    - 消息历史自动管理
    - 支持流式输出
    """
    print("\n" + "=" * 100)
    print("🔍 节点2: 屏幕分析")
    print("=" * 100)

    # 获取 LLM
    llm: ChatOpenAI = config["configurable"]["llm"]

    # 构建提示词
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

    # 构建消息（LangGraph 使用标准的 LangChain 消息格式）
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

    # LangGraph 优势：原生支持流式输出
    full_response = ""
    async for chunk in llm.astream(messages):
        content = chunk.content
        if content:
            print(content, end="", flush=True)
            full_response += content

    print()
    print("-" * 100)

    # 提取产品信息
    products = extract_json_from_text(full_response)

    # 更新状态
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

    LangGraph 优势：
    - 可以基于之前的消息历史继续对话
    - 支持条件分支（如果生成失败可以重试）
    """
    print("\n" + "=" * 100)
    print("🔧 节点3: 生成执行代码")
    print("=" * 100)

    llm: ChatOpenAI = config["configurable"]["llm"]

    # 从状态获取工具描述
    tool_descriptions = state["tool_descriptions"]

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

    # 提取代码
    code = extract_code_from_markdown(full_response)

    if not code:
        print("\n❌ 未找到可执行的代码块")
        # LangGraph 优势：可以轻松实现重试逻辑
        retry_count = state.get("retry_count", 0) + 1
        if retry_count < 3:
            return {
                **state,
                "retry_count": retry_count,
                "next_action": "generate_code"  # 重试
            }
        else:
            return {
                **state,
                "next_action": "end"  # 放弃
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

    LangGraph 优势：
    - 独立的执行节点，易于监控和调试
    - 可以在执行前后设置检查点
    """
    print("\n" + "=" * 100)
    print("⚙️  节点4: 执行代码")
    print("=" * 100)

    code = state["generated_code"]

    # 从 config 获取工具（不可序列化，不存在 state 中）
    tools = config["configurable"]["tools"]

    # 简化的代码执行器
    exec_globals = {tool_name: tool for tool_name, tool in tools.items()}
    exec_locals = {}

    print("\n执行中...\n")

    try:
        # 捕获 print 输出
        from io import StringIO
        import sys

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

    LangGraph 优势：
    - 可以作为独立的验证步骤
    - 支持人工审核（human-in-the-loop）
    """
    print("\n" + "=" * 100)
    print("✅ 节点5: 验证结果")
    print("=" * 100)

    # 等待页面加载
    print("\n⏳ 等待 2 秒让页面加载...")
    await asyncio.sleep(2)

    # 保存验证截图
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


# ============================================================================
# 条件路由 - LangGraph 的核心优势
# ============================================================================

def route_next_action(state: AndroidAgentState) -> Literal["analyze", "generate_code", "execute", "verify", "__end__"]:
    """
    条件路由函数

    LangGraph 优势：
    - 基于状态的动态路由
    - 类型安全的路由决策
    - 可视化的流程控制
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


# ============================================================================
# 构建工作流图 - LangGraph 的核心
# ============================================================================

def create_android_agent_graph() -> StateGraph:
    """
    创建 Android Agent 工作流图

    LangGraph 优势总结：
    1. 清晰的状态图结构 - 可视化流程
    2. 类型安全的状态管理 - TypedDict
    3. 内置检查点系统 - 自动保存/恢复
    4. 条件路由 - 灵活的流程控制
    5. 易于调试 - 每个节点独立测试
    6. 支持人机交互 - 可以在任意节点暂停
    """
    # 创建状态图
    workflow = StateGraph(AndroidAgentState)

    # 添加节点
    workflow.add_node("capture", capture_screen_node)
    workflow.add_node("analyze", analyze_screen_node)
    workflow.add_node("generate_code", generate_code_node)
    workflow.add_node("execute", execute_code_node)
    workflow.add_node("verify", verify_result_node)

    # 设置入口点
    workflow.add_edge(START, "capture")

    # 添加条件边（基于 next_action 路由）
    workflow.add_conditional_edges(
        "capture",
        route_next_action,
        {
            "analyze": "analyze",
            END: END
        }
    )

    workflow.add_conditional_edges(
        "analyze",
        route_next_action,
        {
            "generate_code": "generate_code",
            END: END
        }
    )

    workflow.add_conditional_edges(
        "generate_code",
        route_next_action,
        {
            "execute": "execute",
            "generate_code": "generate_code",  # 支持重试
            END: END
        }
    )

    workflow.add_conditional_edges(
        "execute",
        route_next_action,
        {
            "verify": "verify",
            END: END
        }
    )

    workflow.add_conditional_edges(
        "verify",
        route_next_action,
        {
            END: END
        }
    )

    return workflow


# ============================================================================
# 主函数
# ============================================================================

async def main_async():
    """主函数（异步版本）"""
    print("=" * 100)
    print("🎯 LangGraph 版本工具调用演示")
    print("=" * 100)
    print()

    # 配置参数
    API_BASE = "http://192.168.18.9:8080/v1"
    MODEL = "/models"

    try:
        # 1. 初始化 LLM（使用 LangChain 的 ChatOpenAI）
        print("🤖 正在连接大模型...")
        llm = ChatOpenAI(
            model=MODEL,
            base_url=API_BASE,
            api_key=os.environ["OPENAI_API_KEY"],
            temperature=0.0,
            max_tokens=4048,
            frequency_penalty=0.05,
            presence_penalty=0.05,
        )
        print("✅ 大模型连接成功")

        # 2. 创建工作流图
        print("\n🔧 构建 LangGraph 工作流...")
        workflow = create_android_agent_graph()

        # 3. 添加检查点支持（LangGraph 核心优势）
        memory = MemorySaver()
        app = workflow.compile(checkpointer=memory)

        print("✅ 工作流构建完成")

        # 可选：打印工作流图结构（复杂图可能绘制失败，用 try-except 处理）
        try:
            print("\n📊 工作流图结构:")
            print(app.get_graph().draw_ascii())
        except Exception as e:
            print(f"⚠️  图结构可视化失败（这不影响执行）: {e}")
            print("📝 工作流节点: capture → analyze → generate_code → execute → verify")

        # 4. 准备工具（不可序列化，通过 config 传递）
        print("\n🔧 准备工具列表...")
        adb_tools = AdbTools(use_tcp=True)
        tool_list = describe_tools(adb_tools, exclude_tools=[])
        demo_tools = {
            "tap_by_index": tool_list["tap_by_index"],
            "swipe": tool_list["swipe"],
            "input_text": tool_list["input_text"],
        }
        print("✅ 工具准备完成")

        # 5. 初始化状态（只包含可序列化的数据）
        initial_state: AndroidAgentState = {
            "messages": [],
            "screenshot": None,
            "ui_state": None,
            "analysis_result": None,
            "extracted_products": None,
            "generated_code": None,
            "execution_result": None,
            "tool_descriptions": None,
            "next_action": None,
            "retry_count": 0
        }

        # 6. 执行工作流（带检查点，工具通过 config 传递）
        config = {
            "configurable": {
                "llm": llm,
                "tools": demo_tools,  # 工具函数通过 config 传递
                "thread_id": "android_agent_demo_001"  # 检查点 ID
            }
        }

        print("\n" + "=" * 100)
        print("🚀 开始执行工作流")
        print("=" * 100)

        # LangGraph 优势：可以逐步执行，每步之间都有检查点
        final_state = await app.ainvoke(initial_state, config)

        print("\n" + "=" * 100)
        print("✅ 工作流执行完成！")
        print("=" * 100)

        # 6. 输出最终状态摘要
        print("\n📋 执行摘要:")
        print(f"- 截图大小: {len(final_state['screenshot']) if final_state['screenshot'] else 0} 字节")
        print(f"- 识别商品数: {len(final_state['extracted_products']) if final_state['extracted_products'] else 0}")
        print(f"- 代码执行: {'成功' if final_state.get('execution_result', {}).get('success') else '失败'}")
        print(f"- 重试次数: {final_state['retry_count']}")

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

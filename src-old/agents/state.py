"""
Agent 状态定义
"""
from typing import Literal, Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


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

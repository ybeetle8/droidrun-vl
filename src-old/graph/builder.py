"""
LangGraph 工作流图构建器
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from ..agents import (
    AndroidAgentState,
    capture_screen_node,
    analyze_screen_node,
    generate_code_node,
    execute_code_node,
    verify_result_node,
    route_next_action
)


def create_android_agent_graph() -> StateGraph:
    """
    创建 Android Agent 工作流图

    LangGraph 优势：
    1. 清晰的状态图结构 - 可视化流程
    2. 类型安全的状态管理 - TypedDict
    3. 内置检查点系统 - 自动保存/恢复
    4. 条件路由 - 灵活的流程控制
    5. 易于调试 - 每个节点独立测试
    6. 支持人机交互 - 可以在任意节点暂停

    Returns:
        配置好的工作流图
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


def compile_graph(workflow: StateGraph, use_checkpointer: bool = True):
    """
    编译工作流图

    Args:
        workflow: 工作流图
        use_checkpointer: 是否使用检查点（支持暂停/恢复）

    Returns:
        编译后的可执行图
    """
    if use_checkpointer:
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)
    else:
        return workflow.compile()

"""
状态管理模块

管理执行过程中的全局状态和上下文
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class State(BaseModel):
    """
    执行状态

    记录当前执行环境的完整状态
    """

    # 屏幕状态
    screenshot: Optional[bytes] = Field(None, description="当前截图")
    ui_tree: Optional[Any] = Field(None, description="UI 树（list 或 dict）")
    current_page: Optional[str] = Field(None, description="当前页面")
    current_app: Optional[str] = Field(None, description="当前应用")

    # 任务状态
    task_description: Optional[str] = Field(None, description="当前任务描述")
    task_progress: float = Field(0.0, ge=0.0, le=1.0, description="任务进度（0-1）")

    # 执行历史
    action_count: int = Field(0, description="已执行的动作数")
    last_action: Optional[str] = Field(None, description="最后执行的动作")
    last_action_result: Optional[str] = Field(None, description="最后动作的结果")

    # 时间信息
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")

    class Config:
        arbitrary_types_allowed = True

    def update(self, **kwargs) -> "State":
        """
        更新状态

        Args:
            **kwargs: 要更新的字段

        Returns:
            更新后的 State 实例
        """
        update_data = kwargs.copy()
        update_data["updated_at"] = datetime.now()

        for key, value in update_data.items():
            if hasattr(self, key):
                setattr(self, key, value)

        return self

    def to_dict(self) -> dict:
        """转换为字典（排除二进制数据）"""
        return self.model_dump(exclude={"screenshot", "ui_tree"})


class ExecutionContext(BaseModel):
    """
    执行上下文

    在策略节点之间传递的上下文信息
    """

    # 当前状态
    current_state: State = Field(..., description="当前状态")

    # 父节点信息
    parent_task: Optional[str] = Field(None, description="父任务描述")
    parent_node_id: Optional[str] = Field(None, description="父节点 ID")
    depth: int = Field(0, description="当前递归深度")

    # 执行前状态（用于前后对比）
    before_screen: Optional[bytes] = Field(None, description="执行前截图")
    before_ui_tree: Optional[dict] = Field(None, description="执行前 UI 树")

    # 共享数据
    shared_data: Dict[str, Any] = Field(default_factory=dict, description="节点间共享数据")

    # 约束条件
    max_depth: int = Field(10, description="最大递归深度")
    timeout_seconds: Optional[float] = Field(None, description="超时限制")

    class Config:
        arbitrary_types_allowed = True

    def create_child_context(
        self, task: str, node_id: str, before_screen: Optional[bytes] = None
    ) -> "ExecutionContext":
        """
        创建子上下文

        Args:
            task: 子任务描述
            node_id: 子节点 ID
            before_screen: 执行前截图

        Returns:
            子上下文
        """
        return ExecutionContext(
            current_state=self.current_state,
            parent_task=task,
            parent_node_id=node_id,
            depth=self.depth + 1,
            before_screen=before_screen,
            shared_data=self.shared_data.copy(),
            max_depth=self.max_depth,
            timeout_seconds=self.timeout_seconds,
        )

    def is_depth_exceeded(self) -> bool:
        """检查是否超过最大深度"""
        return self.depth >= self.max_depth


if __name__ == "__main__":
    import json

    # 测试状态管理
    print("=" * 50)
    print("状态管理测试")
    print("=" * 50)

    # 创建状态
    state = State(
        current_page="Launcher",
        current_app="com.android.launcher",
        task_description="打开设置",
        action_count=0,
        metadata={"device": "Pixel 7", "android_version": "14"},
    )
    print("\n[初始状态]")
    print(json.dumps(state.to_dict(), indent=2, default=str))

    # 更新状态
    state.update(action_count=1, last_action="tap", last_action_result="success")
    print("\n[更新后状态]")
    print(json.dumps(state.to_dict(), indent=2, default=str))

    # 创建执行上下文
    context = ExecutionContext(
        current_state=state, depth=0, max_depth=10, shared_data={"session_id": "test-001"}
    )
    print("\n[执行上下文]")
    print(json.dumps(context.model_dump(exclude={"current_state"}), indent=2, default=str))

    # 创建子上下文
    child_context = context.create_child_context(
        task="打开 Wi-Fi 设置", node_id="node-001"
    )
    print("\n[子上下文]")
    print(json.dumps(child_context.model_dump(exclude={"current_state"}), indent=2, default=str))
    print(f"深度超限: {child_context.is_depth_exceeded()}")

    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)

"""
决策结果数据模型

定义决策系统的输出结构
"""

from typing import Any, List, Optional

from pydantic import BaseModel, Field

from .action import Action
from .strategy import Branch, NodeType


class ReasoningResult(BaseModel):
    """
    推理结果

    决策系统的输出，包含对任务的理解和执行计划
    """

    # 任务理解
    task_understanding: str = Field(..., description="对任务的理解")
    current_situation: str = Field(..., description="当前状态描述")
    goal_reached: bool = Field(False, description="目标是否已达成")

    # 决策类型
    node_type: NodeType = Field(..., description="节点类型（TERMINAL/BRANCH）")

    # TERMINAL 节点：单个动作
    action: Optional[Action] = Field(None, description="要执行的动作（TERMINAL 节点）")
    expected_effect: Optional[str] = Field(None, description="预期效果")

    # BRANCH 节点：多个子分支
    branches: List[Branch] = Field(default_factory=list, description="子分支列表（BRANCH 节点）")

    # 推理过程
    reasoning_steps: List[str] = Field(default_factory=list, description="推理步骤")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="置信度")
    alternative_plans: List[str] = Field(default_factory=list, description="备选方案")

    class Config:
        use_enum_values = True

    def validate_completeness(self) -> bool:
        """验证决策结果的完整性"""
        if self.goal_reached:
            return True

        if self.node_type == NodeType.TERMINAL:
            return self.action is not None
        elif self.node_type == NodeType.BRANCH:
            return len(self.branches) > 0

        return False


class PerceptionResult(BaseModel):
    """
    感知结果

    感知系统的输出，描述当前屏幕状态
    """

    # 基本信息
    screen_description: str = Field(..., description="屏幕内容描述")
    current_page: Optional[str] = Field(None, description="当前页面/应用")

    # UI 元素
    interactive_elements: List[dict] = Field(default_factory=list, description="可交互元素列表")
    visible_text: List[str] = Field(default_factory=list, description="可见文本列表")

    # 状态判断
    is_loading: bool = Field(False, description="是否在加载中")
    has_popup: bool = Field(False, description="是否有弹窗")
    has_error: bool = Field(False, description="是否有错误提示")
    error_message: Optional[str] = Field(None, description="错误信息")

    # 变化分析（用于前后对比）
    screen_changes: Optional[str] = Field(None, description="屏幕变化描述")

    # 原始数据
    screenshot: Optional[bytes] = Field(None, description="屏幕截图（bytes）")
    ui_tree: Optional[Any] = Field(None, description="UI 树原始数据（list 或 dict）")

    class Config:
        arbitrary_types_allowed = True


if __name__ == "__main__":
    import uuid
    from .action import Action

    # 测试决策模型
    print("=" * 50)
    print("决策模型测试")
    print("=" * 50)

    # 测试 TERMINAL 节点决策
    terminal_decision = ReasoningResult(
        task_understanding="需要点击设置按钮进入设置页面",
        current_situation="当前在主屏幕，可以看到设置图标",
        goal_reached=False,
        node_type=NodeType.TERMINAL,
        action=Action.tap(target="设置图标", coordinates=(100, 200)),
        expected_effect="进入设置应用",
        reasoning_steps=["识别到设置图标", "判断需要点击", "生成点击动作"],
        confidence=0.95,
    )
    print("\n[TERMINAL 决策]")
    print(terminal_decision.model_dump_json(indent=2, exclude={"action"}))
    print(f"有效性: {terminal_decision.validate_completeness()}")

    # 测试 BRANCH 节点决策
    from .strategy import Branch

    branch_decision = ReasoningResult(
        task_understanding="需要打开设置并进入 Wi-Fi 页面",
        current_situation="任务需要分解为多个步骤",
        goal_reached=False,
        node_type=NodeType.BRANCH,
        branches=[
            Branch(description="打开设置应用", priority=1),
            Branch(description="点击 Wi-Fi 选项", priority=2),
        ],
        reasoning_steps=["分析任务复杂度", "分解为子任务", "排序优先级"],
        confidence=0.9,
    )
    print("\n[BRANCH 决策]")
    print(branch_decision.model_dump_json(indent=2))
    print(f"有效性: {branch_decision.validate_completeness()}")

    # 测试感知结果
    perception = PerceptionResult(
        screen_description="主屏幕，显示多个应用图标",
        current_page="Launcher",
        interactive_elements=[
            {"type": "icon", "text": "设置", "bounds": [100, 200, 200, 300]},
            {"type": "icon", "text": "相机", "bounds": [300, 200, 400, 300]},
        ],
        visible_text=["设置", "相机", "浏览器"],
        is_loading=False,
        has_popup=False,
        has_error=False,
    )
    print("\n[感知结果]")
    print(perception.model_dump_json(indent=2, exclude={"screenshot", "ui_tree"}))

    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)

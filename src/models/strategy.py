"""
策略节点数据模型

定义策略树的核心数据结构
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """节点类型"""

    TERMINAL = "terminal"  # 终端节点（原子操作）
    BRANCH = "branch"  # 分支节点（需要分解为子策略）


class ExecutionStatus(str, Enum):
    """执行状态"""

    SUCCESS = "success"  # 成功
    PARTIAL = "partial"  # 部分完成
    FAILED = "failed"  # 失败


class Branch(BaseModel):
    """分支描述"""

    description: str = Field(..., description="分支任务描述")
    priority: int = Field(1, description="优先级（数字越大优先级越高）")
    expected_result: Optional[str] = Field(None, description="预期结果")
    reasoning: Optional[str] = Field(None, description="选择此分支的原因")

    class Config:
        use_enum_values = True


class StrategyNodeResult(BaseModel):
    """
    策略节点执行结果

    记录单个节点的执行信息
    """

    # 基本信息
    node_id: str = Field(..., description="节点 ID")
    task_description: str = Field(..., description="任务描述")
    node_type: NodeType = Field(..., description="节点类型")

    # 执行结果
    status: ExecutionStatus = Field(..., description="执行状态")
    error: Optional[str] = Field(None, description="错误信息")

    # 执行路径
    actions: List[Any] = Field(default_factory=list, description="执行的动作列表")
    sub_results: List["StrategyNodeResult"] = Field(
        default_factory=list, description="子节点执行结果"
    )

    # 时间信息
    start_time: Optional[float] = Field(None, description="开始时间（时间戳）")
    end_time: Optional[float] = Field(None, description="结束时间（时间戳）")
    duration_seconds: Optional[float] = Field(None, description="执行耗时（秒）")

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")

    class Config:
        use_enum_values = True

    @property
    def success(self) -> bool:
        """是否成功"""
        return self.status == ExecutionStatus.SUCCESS

    @property
    def depth(self) -> int:
        """计算节点深度"""
        if not self.sub_results:
            return 1
        return 1 + max(sub.depth for sub in self.sub_results)

    @property
    def total_actions(self) -> int:
        """计算总动作数"""
        count = len(self.actions)
        for sub in self.sub_results:
            count += sub.total_actions
        return count


class StrategyContext(BaseModel):
    """
    策略执行上下文

    传递给子节点的上下文信息
    """

    parent_task: Optional[str] = Field(None, description="父任务描述")
    parent_node_id: Optional[str] = Field(None, description="父节点 ID")
    depth: int = Field(0, description="当前深度")
    before_screen: Optional[bytes] = Field(None, description="执行前截图")

    # 共享状态
    shared_state: Dict[str, Any] = Field(default_factory=dict, description="共享状态")

    class Config:
        arbitrary_types_allowed = True


if __name__ == "__main__":
    import uuid
    import json

    # 测试策略模型
    print("=" * 50)
    print("策略模型测试")
    print("=" * 50)

    # 创建分支
    branch = Branch(
        description="打开设置应用",
        priority=1,
        expected_result="进入设置首页",
        reasoning="这是完成任务的第一步",
    )
    print("\n[分支]")
    print(branch.model_dump_json(indent=2))

    # 创建策略节点结果
    result = StrategyNodeResult(
        node_id=str(uuid.uuid4()),
        task_description="打开设置并进入 Wi-Fi 页面",
        node_type=NodeType.BRANCH,
        status=ExecutionStatus.SUCCESS,
        start_time=1000.0,
        end_time=1015.0,
        duration_seconds=15.0,
    )
    print("\n[策略节点结果]")
    print(result.model_dump_json(indent=2))
    print(f"成功: {result.success}")
    print(f"深度: {result.depth}")

    # 创建上下文
    context = StrategyContext(
        parent_task="打开设置",
        depth=1,
        shared_state={"app_opened": True},
    )
    print("\n[执行上下文]")
    print(context.model_dump_json(indent=2))

    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)

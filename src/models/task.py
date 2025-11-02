"""
任务模型

定义用户任务和子任务的数据结构
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """任务状态枚举"""

    PENDING = "pending"  # 等待执行
    RUNNING = "running"  # 执行中
    SUCCESS = "success"  # 成功
    FAILED = "failed"  # 失败
    TIMEOUT = "timeout"  # 超时
    CANCELLED = "cancelled"  # 取消


class TaskIntent(str, Enum):
    """任务意图枚举"""

    SHOPPING = "shopping"  # 购物
    SOCIAL = "social"  # 社交
    ENTERTAINMENT = "entertainment"  # 娱乐
    INFORMATION = "information"  # 信息获取
    SETTINGS = "settings"  # 设置
    OTHER = "other"  # 其他


class Task(BaseModel):
    """
    用户任务模型

    表示用户输入的顶层任务
    """

    # 基本信息
    id: str = Field(..., description="任务 ID")
    description: str = Field(..., description="任务描述")
    intent: Optional[TaskIntent] = Field(None, description="任务意图")

    # 循环任务配置
    loop: bool = Field(False, description="是否为循环任务")
    max_iterations: Optional[int] = Field(None, description="最大循环次数（None 表示无限）")
    current_iteration: int = Field(0, description="当前循环次数")

    # 执行配置
    max_sub_tasks: int = Field(20, description="最大子任务数")
    timeout_seconds: Optional[int] = Field(None, description="超时时间（秒）")

    # 状态
    status: TaskStatus = Field(TaskStatus.PENDING, description="任务状态")

    # 应用信息
    app_name: Optional[str] = Field(None, description="目标应用名称")

    # 元数据
    tags: List[str] = Field(default_factory=list, description="任务标签")
    metadata: dict = Field(default_factory=dict, description="额外元数据")

    class Config:
        use_enum_values = True


class SubTask(BaseModel):
    """
    子任务模型

    由 Master Agent 分解任务后生成的子任务
    """

    # 基本信息
    id: str = Field(..., description="子任务 ID")
    parent_task_id: str = Field(..., description="父任务 ID")
    description: str = Field(..., description="子任务描述")

    # 执行配置
    max_steps: int = Field(50, description="最大执行步数")
    timeout_seconds: int = Field(300, description="超时时间（秒）")

    # 状态
    status: TaskStatus = Field(TaskStatus.PENDING, description="子任务状态")
    current_step: int = Field(0, description="当前步数")

    # 目标条件
    success_criteria: Optional[str] = Field(None, description="成功判定条件")
    expected_state: Optional[str] = Field(None, description="预期达到的状态")

    # 优先级
    priority: int = Field(0, description="优先级（数字越大优先级越高）")

    class Config:
        use_enum_values = True


class ExecutionResult(BaseModel):
    """
    任务执行结果

    记录任务执行的完整信息
    """

    # 任务信息
    task_id: str = Field(..., description="任务 ID")
    status: TaskStatus = Field(..., description="执行状态")

    # 执行统计
    total_steps: int = Field(0, description="总步数")
    total_sub_tasks: int = Field(0, description="子任务数")
    successful_steps: int = Field(0, description="成功步数")
    failed_steps: int = Field(0, description="失败步数")

    # 时间信息
    start_time: Optional[float] = Field(None, description="开始时间（时间戳）")
    end_time: Optional[float] = Field(None, description="结束时间（时间戳）")
    duration_seconds: Optional[float] = Field(None, description="总耗时（秒）")

    # 异常恢复
    recovery_count: int = Field(0, description="异常恢复次数")

    # 结果信息
    error: Optional[str] = Field(None, description="错误信息")
    final_state: Optional[str] = Field(None, description="最终状态描述")

    # 经验信息
    experience_saved: bool = Field(False, description="是否已保存经验")
    experience_id: Optional[str] = Field(None, description="经验 ID")

    class Config:
        use_enum_values = True

    @property
    def success_rate(self) -> float:
        """计算成功率"""
        total = self.successful_steps + self.failed_steps
        if total == 0:
            return 0.0
        return self.successful_steps / total


if __name__ == "__main__":
    import json
    import uuid

    # 测试任务模型
    print("=" * 50)
    print("任务模型测试")
    print("=" * 50)

    # 创建任务
    task = Task(
        id=str(uuid.uuid4()),
        description="到闲鱼购买 200 元以内的 1TB 硬盘",
        intent=TaskIntent.SHOPPING,
        app_name="闲鱼",
        tags=["购物", "硬盘"],
        max_sub_tasks=20,
    )
    print("\n[任务]")
    print(task.model_dump_json(indent=2))

    # 创建子任务
    sub_task = SubTask(
        id=str(uuid.uuid4()),
        parent_task_id=task.id,
        description="打开闲鱼 App",
        max_steps=10,
        success_criteria="成功进入闲鱼首页",
        priority=1,
    )
    print("\n[子任务]")
    print(sub_task.model_dump_json(indent=2))

    # 创建执行结果
    result = ExecutionResult(
        task_id=task.id,
        status=TaskStatus.SUCCESS,
        total_steps=15,
        successful_steps=14,
        failed_steps=1,
        start_time=1000.0,
        end_time=1015.0,
        duration_seconds=15.0,
        recovery_count=1,
    )
    print("\n[执行结果]")
    print(result.model_dump_json(indent=2))
    print(f"成功率: {result.success_rate:.2%}")

    # 循环任务示例
    loop_task = Task(
        id=str(uuid.uuid4()),
        description="访问 Twitter，随机浏览贴文并善意回复",
        intent=TaskIntent.SOCIAL,
        loop=True,
        max_iterations=100,
        app_name="Twitter",
    )
    print("\n[循环任务]")
    print(loop_task.model_dump_json(indent=2))

    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)

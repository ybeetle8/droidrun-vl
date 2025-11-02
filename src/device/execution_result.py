"""
设备操作执行结果模型

用于 AndroidController 返回操作结果
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ExecutionResult(BaseModel):
    """
    设备操作执行结果

    统一的设备操作返回格式，支持：
    - 操作类方法（tap, swipe, input 等）
    - 查询类方法（screenshot, get_ui_tree 等）
    """

    # 执行状态
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="结果描述信息")
    error: Optional[str] = Field(None, description="错误信息（失败时）")

    # 返回数据
    data: Optional[Dict[str, Any]] = Field(None, description="返回数据（查询类方法使用）")

    # 元数据
    operation: Optional[str] = Field(None, description="操作类型（tap/swipe/screenshot 等）")
    duration_ms: Optional[int] = Field(None, description="执行耗时（毫秒）")

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def success_result(
        cls,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        operation: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> "ExecutionResult":
        """
        创建成功结果

        Args:
            message: 成功消息
            data: 返回数据
            operation: 操作类型
            duration_ms: 耗时

        Returns:
            ExecutionResult 实例
        """
        return cls(
            success=True,
            message=message,
            data=data,
            operation=operation,
            duration_ms=duration_ms,
        )

    @classmethod
    def failure_result(
        cls,
        message: str,
        error: str,
        operation: Optional[str] = None,
    ) -> "ExecutionResult":
        """
        创建失败结果

        Args:
            message: 失败消息
            error: 错误详情
            operation: 操作类型

        Returns:
            ExecutionResult 实例
        """
        return cls(
            success=False,
            message=message,
            error=error,
            operation=operation,
        )


if __name__ == "__main__":
    # 测试 ExecutionResult
    print("=" * 50)
    print("ExecutionResult 测试")
    print("=" * 50)

    # 成功结果（操作类）
    tap_result = ExecutionResult.success_result(
        message="Tapped at (100, 200)",
        operation="tap",
        duration_ms=50,
    )
    print("\n[操作成功]")
    print(tap_result.model_dump_json(indent=2))

    # 成功结果（查询类）
    screenshot_result = ExecutionResult.success_result(
        message="Screenshot taken",
        data={"format": "PNG", "size": 1024000},
        operation="screenshot",
        duration_ms=200,
    )
    print("\n[查询成功]")
    print(screenshot_result.model_dump_json(indent=2))

    # 失败结果
    error_result = ExecutionResult.failure_result(
        message="Failed to tap element",
        error="Element not found",
        operation="tap",
    )
    print("\n[操作失败]")
    print(error_result.model_dump_json(indent=2))

    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)

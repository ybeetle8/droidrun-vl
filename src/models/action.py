"""
动作模型

定义 Agent 可以执行的操作类型
"""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """动作类型枚举"""

    TAP = "tap"  # 点击
    SWIPE = "swipe"  # 滑动
    INPUT = "input"  # 输入文本
    PRESS_BACK = "press_back"  # 按返回键
    PRESS_HOME = "press_home"  # 按 Home 键
    WAIT = "wait"  # 等待
    SCROLL = "scroll"  # 滚动


class Action(BaseModel):
    """
    动作模型

    表示一个具体的操作
    """

    # 基本信息
    type: ActionType = Field(..., description="动作类型")
    description: str = Field(..., description="动作描述")

    # 目标信息
    target: Optional[str] = Field(None, description="目标描述（如：搜索框、返回按钮）")
    coordinates: Optional[tuple[int, int]] = Field(None, description="坐标 (x, y)")
    bounds: Optional[tuple[int, int, int, int]] = Field(
        None, description="边界 (left, top, right, bottom)"
    )

    # 参数
    params: Dict[str, Any] = Field(default_factory=dict, description="动作参数")

    # 预期结果
    expected_result: Optional[str] = Field(None, description="预期结果描述")
    expected_ui: Optional[str] = Field(None, description="预期出现的 UI 元素")

    # 元数据
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="置信度")
    risk: float = Field(0.0, ge=0.0, le=1.0, description="风险评估")
    priority: int = Field(0, description="优先级（数字越大优先级越高）")

    class Config:
        use_enum_values = True

    @classmethod
    def tap(
        cls,
        target: str,
        coordinates: Optional[tuple[int, int]] = None,
        description: Optional[str] = None,
        **kwargs,
    ) -> "Action":
        """
        创建点击动作

        Args:
            target: 目标描述
            coordinates: 坐标
            description: 动作描述
            **kwargs: 其他参数

        Returns:
            Action 实例
        """
        return cls(
            type=ActionType.TAP,
            target=target,
            coordinates=coordinates,
            description=description or f"点击 {target}",
            **kwargs,
        )

    @classmethod
    def swipe(
        cls,
        start: tuple[int, int],
        end: tuple[int, int],
        description: Optional[str] = None,
        duration: int = 300,
        **kwargs,
    ) -> "Action":
        """
        创建滑动动作

        Args:
            start: 起点坐标 (x, y)
            end: 终点坐标 (x, y)
            description: 动作描述
            duration: 持续时间（毫秒）
            **kwargs: 其他参数

        Returns:
            Action 实例
        """
        return cls(
            type=ActionType.SWIPE,
            description=description or f"从 {start} 滑动到 {end}",
            params={"start": start, "end": end, "duration": duration},
            **kwargs,
        )

    @classmethod
    def input_text(
        cls,
        text: str,
        target: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs,
    ) -> "Action":
        """
        创建输入文本动作

        Args:
            text: 输入的文本
            target: 目标输入框
            description: 动作描述
            **kwargs: 其他参数

        Returns:
            Action 实例
        """
        return cls(
            type=ActionType.INPUT,
            target=target,
            description=description or f"输入文本: {text}",
            params={"text": text},
            **kwargs,
        )

    @classmethod
    def press_back(cls, description: Optional[str] = None, **kwargs) -> "Action":
        """创建按返回键动作"""
        return cls(
            type=ActionType.PRESS_BACK,
            description=description or "按返回键",
            **kwargs,
        )

    @classmethod
    def press_home(cls, description: Optional[str] = None, **kwargs) -> "Action":
        """创建按 Home 键动作"""
        return cls(
            type=ActionType.PRESS_HOME,
            description=description or "按 Home 键",
            **kwargs,
        )

    @classmethod
    def wait(cls, seconds: float, description: Optional[str] = None, **kwargs) -> "Action":
        """创建等待动作"""
        return cls(
            type=ActionType.WAIT,
            description=description or f"等待 {seconds} 秒",
            params={"seconds": seconds},
            **kwargs,
        )

    @classmethod
    def scroll(
        cls,
        direction: str,
        distance: Optional[int] = None,
        description: Optional[str] = None,
        **kwargs,
    ) -> "Action":
        """
        创建滚动动作

        Args:
            direction: 方向（up/down/left/right）
            distance: 距离（像素）
            description: 动作描述
            **kwargs: 其他参数

        Returns:
            Action 实例
        """
        return cls(
            type=ActionType.SCROLL,
            description=description or f"向 {direction} 滚动",
            params={"direction": direction, "distance": distance},
            **kwargs,
        )


class ActionResult(BaseModel):
    """
    动作执行结果

    记录动作执行后的状态
    """

    # 执行信息
    action: Action = Field(..., description="执行的动作")
    success: bool = Field(..., description="是否成功")
    error: Optional[str] = Field(None, description="错误信息")

    # 时间信息
    start_time: float = Field(..., description="开始时间（时间戳）")
    end_time: float = Field(..., description="结束时间（时间戳）")
    duration_ms: int = Field(..., description="执行耗时（毫秒）")

    # 截图
    screenshot_before: Optional[bytes] = Field(None, description="执行前截图")
    screenshot_after: Optional[bytes] = Field(None, description="执行后截图")

    # 验证信息
    verified: bool = Field(False, description="是否已验证结果")
    verification_result: Optional[str] = Field(None, description="验证结果描述")

    class Config:
        arbitrary_types_allowed = True


if __name__ == "__main__":
    # 测试动作模型
    print("=" * 50)
    print("动作模型测试")
    print("=" * 50)

    # 创建点击动作
    tap_action = Action.tap(
        target="搜索框",
        coordinates=(100, 200),
        expected_ui="输入框激活",
        confidence=0.9,
    )
    print("\n[点击动作]")
    print(tap_action.model_dump_json(indent=2))

    # 创建滑动动作
    swipe_action = Action.swipe(
        start=(100, 500),
        end=(100, 200),
        description="向上滑动",
    )
    print("\n[滑动动作]")
    print(swipe_action.model_dump_json(indent=2))

    # 创建输入动作
    input_action = Action.input_text(
        text="双肩包",
        target="搜索框",
    )
    print("\n[输入动作]")
    print(input_action.model_dump_json(indent=2))

    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)

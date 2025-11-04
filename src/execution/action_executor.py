"""
动作执行器

负责执行具体的设备操作动作
"""

import asyncio
import time
from typing import Optional

from loguru import logger

from ..device.android_controller import AndroidController
from ..device.execution_result import ExecutionResult
from ..models import Action, ActionType


class ActionExecutor:
    """
    动作执行器

    封装 AndroidController，提供统一的动作执行接口
    """

    def __init__(self, controller: AndroidController, feedback_wait_time: float = 0.5):
        """
        初始化动作执行器

        Args:
            controller: Android 控制器
            feedback_wait_time: 即时反馈等待时间（秒）
        """
        self.controller = controller
        self.feedback_wait_time = feedback_wait_time

    async def execute(self, action: Action) -> ExecutionResult:
        """
        执行动作

        Args:
            action: 要执行的动作

        Returns:
            执行结果
        """
        logger.info(f"执行动作: {action.type} - {action.description}")

        start_time = time.time()

        try:
            # 根据动作类型调用相应的方法
            if action.type == ActionType.TAP:
                result = await self._execute_tap(action)

            elif action.type == ActionType.SWIPE:
                result = await self._execute_swipe(action)

            elif action.type == ActionType.INPUT:
                result = await self._execute_input(action)

            elif action.type == ActionType.PRESS_BACK:
                result = await self.controller.press_back()

            elif action.type == ActionType.PRESS_HOME:
                result = await self.controller.press_home()

            elif action.type == ActionType.WAIT:
                result = await self._execute_wait(action)

            elif action.type == ActionType.SCROLL:
                result = await self._execute_scroll(action)

            else:
                raise ValueError(f"不支持的动作类型: {action.type}")

            # 等待即时反馈
            await asyncio.sleep(self.feedback_wait_time)

            duration = time.time() - start_time
            logger.info(f"动作执行完成: {action.type} (耗时: {duration:.2f}s)")

            return result

        except Exception as e:
            logger.error(f"动作执行失败: {action.type} - {e}")
            # 返回失败结果
            return ExecutionResult.failure_result(
                message=f"动作执行失败: {str(e)}", operation=action.type, error=str(e)
            )

    async def _execute_tap(self, action: Action) -> ExecutionResult:
        """执行点击动作"""
        coordinates = action.coordinates

        if not coordinates:
            # 如果没有坐标，尝试从 bounds 计算
            if action.bounds:
                left, top, right, bottom = action.bounds
                x = (left + right) // 2
                y = (top + bottom) // 2
                coordinates = (x, y)
            else:
                raise ValueError(f"点击动作缺少坐标信息: {action.target}")

        x, y = coordinates
        return await self.controller.tap(x, y)

    async def _execute_swipe(self, action: Action) -> ExecutionResult:
        """执行滑动动作"""
        params = action.params

        start = params.get("start")
        end = params.get("end")
        duration = params.get("duration", 300)

        if not start or not end:
            raise ValueError("滑动动作缺少起点或终点坐标")

        start_x, start_y = start
        end_x, end_y = end

        return await self.controller.swipe(start_x, start_y, end_x, end_y, duration)

    async def _execute_input(self, action: Action) -> ExecutionResult:
        """执行输入动作"""
        text = action.params.get("text")

        if not text:
            raise ValueError("输入动作缺少文本内容")

        # 如果指定了目标输入框，先点击激活
        if action.coordinates:
            logger.debug("先点击激活输入框")
            await self.controller.tap(*action.coordinates)
            await asyncio.sleep(0.3)

        return await self.controller.input_text(text)

    async def _execute_wait(self, action: Action) -> ExecutionResult:
        """执行等待动作"""
        seconds = action.params.get("seconds", 1.0)

        logger.debug(f"等待 {seconds} 秒...")
        await asyncio.sleep(seconds)

        return ExecutionResult.success_result(
            message=f"等待 {seconds} 秒", operation="wait", duration_ms=int(seconds * 1000)
        )

    async def _execute_scroll(self, action: Action) -> ExecutionResult:
        """执行滚动动作"""
        direction = action.params.get("direction", "up")
        distance = action.params.get("distance")

        # 默认滚动距离（屏幕高度的一半）
        # 假设屏幕分辨率为 1080x2400
        screen_width = 1080
        screen_height = 2400

        center_x = screen_width // 2
        center_y = screen_height // 2

        if not distance:
            distance = screen_height // 2

        # 根据方向计算起点和终点
        if direction == "up":
            start = (center_x, center_y + distance // 2)
            end = (center_x, center_y - distance // 2)
        elif direction == "down":
            start = (center_x, center_y - distance // 2)
            end = (center_x, center_y + distance // 2)
        elif direction == "left":
            start = (center_x + distance // 2, center_y)
            end = (center_x - distance // 2, center_y)
        elif direction == "right":
            start = (center_x - distance // 2, center_y)
            end = (center_x + distance // 2, center_y)
        else:
            raise ValueError(f"不支持的滚动方向: {direction}")

        return await self.controller.swipe(*start, *end, duration_ms=300)


if __name__ == "__main__":
    import asyncio
    from ..device.android_controller import AndroidController

    async def test():
        """测试动作执行器"""
        print("=" * 50)
        print("动作执行器测试")
        print("=" * 50)

        # 初始化
        controller = AndroidController(use_tcp=False)
        executor = ActionExecutor(controller)

        # 测试点击
        print("\n[测试 1] 点击动作")
        tap_action = Action.tap(target="测试按钮", coordinates=(540, 1200))
        result = await executor.execute(tap_action)
        print(f"结果: {result.success} - {result.message}")

        # 测试等待
        print("\n[测试 2] 等待动作")
        wait_action = Action.wait(seconds=1.0)
        result = await executor.execute(wait_action)
        print(f"结果: {result.success} - {result.message}")

        print("\n" + "=" * 50)
        print("测试完成!")
        print("=" * 50)

    # asyncio.run(test())
    print("动作执行器模块加载成功")

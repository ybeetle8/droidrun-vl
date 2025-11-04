"""
策略树执行器

程序入口，负责初始化所有组件并执行任务
"""

import time
from typing import Optional

from loguru import logger

from ..decision.decision_maker import DecisionMaker
from ..device.android_controller import AndroidController, get_android_controller
from ..execution.action_executor import ActionExecutor
from ..llm.client import LLMClient
from ..memory.working_memory import WorkingMemory
from ..models.strategy import StrategyNodeResult
from ..perception.ui_detector import UIDetector
from ..perception.vision_analyzer import VisionAnalyzer
from ..utils.config import Config
from .state import ExecutionContext, State
from .strategy_node import StrategyNode


class StrategyTree:
    """
    策略树执行器

    职责:
    - 初始化所有组件
    - 管理全局状态
    - 执行用户任务
    """

    def __init__(self, config: Optional[Config] = None, controller: Optional[AndroidController] = None):
        """
        初始化策略树

        Args:
            config: 配置对象（可选，默认使用全局配置）
            controller: Android 控制器（可选，默认创建新实例）
        """
        self.config = config or Config()

        # 初始化 LLM 客户端
        logger.info("初始化 LLM 客户端...")
        self.llm_client = LLMClient()

        # 初始化设备控制器
        logger.info("初始化设备控制器...")
        if controller:
            self.controller = controller
        else:
            self.controller = get_android_controller(use_tcp=False)

        # 初始化各个系统
        logger.info("初始化感知系统...")
        self.vision_analyzer = VisionAnalyzer(self.llm_client)
        self.ui_detector = UIDetector()

        logger.info("初始化决策系统...")
        self.decision_maker = DecisionMaker(self.llm_client)

        logger.info("初始化执行系统...")
        feedback_wait_time = self.config.get("execution", "feedback_wait_time", default=0.5)
        self.action_executor = ActionExecutor(self.controller, feedback_wait_time)

        logger.info("初始化记忆系统...")
        memory_size = self.config.get("memory", "working_memory", "size", default=7)
        loop_threshold = self.config.get("memory", "working_memory", "loop_threshold", default=3)
        self.working_memory = WorkingMemory(capacity=memory_size, loop_threshold=loop_threshold)

        # 创建策略节点
        logger.info("初始化策略树节点...")
        max_depth = self.config.get("strategy_tree", "max_depth", default=10)
        self.root_node = StrategyNode(
            vision_analyzer=self.vision_analyzer,
            ui_detector=self.ui_detector,
            decision_maker=self.decision_maker,
            action_executor=self.action_executor,
            working_memory=self.working_memory,
            max_depth=max_depth,
        )

        logger.info("策略树初始化完成!")

    async def execute_task(self, task: str) -> StrategyNodeResult:
        """
        执行用户任务

        Args:
            task: 任务描述

        Returns:
            执行结果
        """
        logger.info("=" * 60)
        logger.info(f"开始执行任务: {task}")
        logger.info("=" * 60)

        start_time = time.time()

        try:
            # 清空工作记忆
            self.working_memory.clear()

            # 获取初始状态
            initial_state = await self._get_initial_state()

            # 创建执行上下文
            context = ExecutionContext(
                current_state=initial_state,
                depth=0,
                max_depth=self.config.get("strategy_tree", "max_depth", default=10),
                timeout_seconds=self.config.get("strategy_tree", "timeout_seconds", default=None),
            )

            # 执行根节点
            result = await self.root_node.execute(task, context)

            # 统计信息
            duration = time.time() - start_time
            logger.info("=" * 60)
            logger.info(f"任务执行完成!")
            logger.info(f"状态: {result.status if isinstance(result.status, str) else result.status.value}")
            logger.info(f"耗时: {duration:.2f}s")
            logger.info(f"动作数: {result.total_actions}")
            logger.info(f"深度: {result.depth}")
            logger.info("=" * 60)

            return result

        except Exception as e:
            logger.error(f"任务执行失败: {e}", exc_info=True)
            raise

    async def _get_initial_state(self) -> State:
        """
        获取初始状态

        Returns:
            初始状态
        """
        logger.debug("获取初始状态...")

        # 截屏
        screenshot_result = await self.controller.screenshot()
        if not screenshot_result.success:
            raise RuntimeError(f"获取初始状态失败: {screenshot_result.error}")

        screenshot = screenshot_result.data["image_bytes"]

        # 获取 UI 树
        ui_result = await self.controller.get_ui_tree()
        ui_tree = None
        current_app = None

        if ui_result.success:
            ui_tree = ui_result.data.get("a11y_tree")
            phone_state = ui_result.data.get("phone_state", {})
            current_app = phone_state.get("foreground_package")

        state = State(
            screenshot=screenshot,
            ui_tree=ui_tree,
            current_app=current_app,
            action_count=0,
        )

        logger.debug(f"初始状态获取完成 (当前应用: {current_app})")
        return state


if __name__ == "__main__":
    import asyncio

    async def test():
        """测试策略树"""
        print("=" * 50)
        print("策略树测试")
        print("=" * 50)

        # 初始化
        config = Config()
        tree = StrategyTree(config)

        # 执行简单任务
        print("\n[测试] 执行简单任务")
        result = await tree.execute_task("打开设置")

        print(f"\n执行结果:")
        status_str = result.status if isinstance(result.status, str) else result.status.value
        print(f"状态: {status_str}")
        print(f"耗时: {result.duration_seconds:.2f}s")
        print(f"动作数: {result.total_actions}")

        print("\n" + "=" * 50)
        print("测试完成!")
        print("=" * 50)

    # asyncio.run(test())
    print("策略树模块加载成功")

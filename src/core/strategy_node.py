"""
策略节点 - 核心递归结构

Phase 1 版本：基础功能，不包含融合增强（反思、自适应检索等）
"""

import asyncio
import time
import uuid
from typing import List, Optional

from loguru import logger

from ..decision.decision_maker import DecisionMaker
from ..execution.action_executor import ActionExecutor
from ..memory.working_memory import WorkingMemory
from ..models import Action, PerceptionResult, ReasoningResult
from ..models.strategy import (
    ExecutionStatus,
    NodeType,
    StrategyContext,
    StrategyNodeResult,
)
from ..perception.ui_detector import UIDetector
from ..perception.vision_analyzer import VisionAnalyzer
from .state import ExecutionContext, State


class StrategyNode:
    """
    统一策略节点 (Phase 1 基础版本)

    职责:
    1. 观察状态 (感知)
    2. 思考推理 (决策)
    3. 分支决策 (TERMINAL/BRANCH)
    4. 执行动作/子节点
    5. 向上传递结果
    """

    def __init__(
        self,
        vision_analyzer: VisionAnalyzer,
        ui_detector: UIDetector,
        decision_maker: DecisionMaker,
        action_executor: ActionExecutor,
        working_memory: WorkingMemory,
        max_depth: int = 10,
    ):
        """
        初始化策略节点

        Args:
            vision_analyzer: 视觉分析器
            ui_detector: UI 检测器
            decision_maker: 决策生成器
            action_executor: 动作执行器
            working_memory: 工作记忆
            max_depth: 最大递归深度
        """
        self.vision = vision_analyzer
        self.ui_detector = ui_detector
        self.decision = decision_maker
        self.executor = action_executor
        self.memory = working_memory
        self.max_depth = max_depth

    async def execute(
        self, task_description: str, context: ExecutionContext
    ) -> StrategyNodeResult:
        """
        执行策略节点

        Args:
            task_description: 任务描述
            context: 执行上下文

        Returns:
            策略节点执行结果
        """
        node_id = str(uuid.uuid4())
        start_time = time.time()

        logger.info(f"[节点 {node_id[:8]}] 开始执行: {task_description} (深度: {context.depth})")

        # 检查深度限制
        if context.is_depth_exceeded():
            logger.error(f"超过最大递归深度 {self.max_depth}")
            return StrategyNodeResult(
                node_id=node_id,
                task_description=task_description,
                node_type=NodeType.TERMINAL,
                status=ExecutionStatus.FAILED,
                error="超过最大递归深度",
                start_time=start_time,
                end_time=time.time(),
                duration_seconds=time.time() - start_time,
            )

        try:
            # === 步骤 1: 观察状态 ===
            perception = await self._perceive(context.current_state, task_description)

            # === 步骤 2: 思考推理与决策 ===
            reasoning = await self._reason(
                task_description, context.current_state, perception
            )

            # 检查目标是否达成
            if reasoning.goal_reached:
                logger.info(f"[节点 {node_id[:8]}] 目标已达成")
                return StrategyNodeResult(
                    node_id=node_id,
                    task_description=task_description,
                    node_type=reasoning.node_type,
                    status=ExecutionStatus.SUCCESS,
                    start_time=start_time,
                    end_time=time.time(),
                    duration_seconds=time.time() - start_time,
                )

            # === 步骤 3: 根据节点类型执行 ===
            if reasoning.node_type == NodeType.TERMINAL:
                # 执行单个原子操作
                result = await self._execute_terminal(
                    node_id, task_description, reasoning, start_time
                )

            else:  # BRANCH
                # 递归执行子分支
                result = await self._execute_branch(
                    node_id, task_description, reasoning, context, start_time
                )

            status_str = result.status if isinstance(result.status, str) else result.status.value
            logger.info(
                f"[节点 {node_id[:8]}] 执行完成: {status_str} "
                f"(耗时: {result.duration_seconds:.2f}s)"
            )

            return result

        except Exception as e:
            logger.error(f"[节点 {node_id[:8]}] 执行失败: {e}", exc_info=True)

            return StrategyNodeResult(
                node_id=node_id,
                task_description=task_description,
                node_type=NodeType.TERMINAL,
                status=ExecutionStatus.FAILED,
                error=str(e),
                start_time=start_time,
                end_time=time.time(),
                duration_seconds=time.time() - start_time,
            )

    async def _perceive(
        self, state: State, task_context: str
    ) -> PerceptionResult:
        """
        步骤 1: 感知当前状态

        Args:
            state: 当前状态
            task_context: 任务上下文

        Returns:
            感知结果
        """
        logger.debug("开始感知屏幕状态...")

        # 获取截图（如果状态中没有）
        if not state.screenshot:
            screenshot_result = await self.executor.controller.screenshot()
            if not screenshot_result.success:
                raise RuntimeError(f"截屏失败: {screenshot_result.error}")
            screenshot = screenshot_result.data["image_bytes"]
            state.screenshot = screenshot
        else:
            screenshot = state.screenshot

        # 使用 VL 模型分析屏幕
        perception = await self.vision.analyze_screen(screenshot, task_context)

        # 获取 UI 树并提取交互元素
        ui_result = await self.executor.controller.get_ui_tree()
        if ui_result.success:
            ui_tree = ui_result.data["a11y_tree"]
            interactive_elements = self.ui_detector.extract_interactive_elements(ui_tree)

            # 合并到感知结果
            perception.ui_tree = ui_tree
            perception.interactive_elements = interactive_elements

            logger.debug(f"感知完成: {len(interactive_elements)} 个交互元素")

        return perception

    async def _reason(
        self, task: str, state: State, perception: PerceptionResult
    ) -> ReasoningResult:
        """
        步骤 2: 推理决策

        Args:
            task: 任务描述
            state: 当前状态
            perception: 感知结果

        Returns:
            推理结果
        """
        logger.debug("开始推理决策...")

        # 获取历史操作
        history = self.memory.get_recent(5)
        history_strs = [str(item) for item in history]

        # 调用决策生成器
        reasoning = await self.decision.make_decision(
            task=task,
            current_state=state,
            screen_description=perception.screen_description,
            interactive_elements=perception.interactive_elements,
            visible_text=perception.visible_text,
            history=history_strs,
        )

        node_type_str = reasoning.node_type if isinstance(reasoning.node_type, str) else reasoning.node_type.value
        logger.debug(f"决策完成: {node_type_str} (置信度: {reasoning.confidence:.2f})")

        return reasoning

    async def _execute_terminal(
        self,
        node_id: str,
        task: str,
        reasoning: ReasoningResult,
        start_time: float,
    ) -> StrategyNodeResult:
        """
        执行 TERMINAL 节点 (单个原子操作)

        Args:
            node_id: 节点 ID
            task: 任务描述
            reasoning: 推理结果
            start_time: 开始时间

        Returns:
            执行结果
        """
        logger.info(f"[节点 {node_id[:8]}] 执行 TERMINAL: {reasoning.action.description}")

        # 执行动作
        exec_result = await self.executor.execute(reasoning.action)

        # 记录到工作记忆
        self.memory.add(
            f"{reasoning.action.type}: {reasoning.action.description}",
            metadata={"success": exec_result.success},
        )

        # 检测循环
        if self.memory.detect_loop():
            logger.warning("检测到循环操作，标记为失败")
            return StrategyNodeResult(
                node_id=node_id,
                task_description=task,
                node_type=NodeType.TERMINAL,
                status=ExecutionStatus.FAILED,
                error="检测到循环操作",
                actions=[reasoning.action],
                start_time=start_time,
                end_time=time.time(),
                duration_seconds=time.time() - start_time,
            )

        # 判断执行状态
        status = (
            ExecutionStatus.SUCCESS if exec_result.success else ExecutionStatus.FAILED
        )

        return StrategyNodeResult(
            node_id=node_id,
            task_description=task,
            node_type=NodeType.TERMINAL,
            status=status,
            error=exec_result.error if not exec_result.success else None,
            actions=[reasoning.action],
            start_time=start_time,
            end_time=time.time(),
            duration_seconds=time.time() - start_time,
        )

    async def _execute_branch(
        self,
        node_id: str,
        task: str,
        reasoning: ReasoningResult,
        context: ExecutionContext,
        start_time: float,
    ) -> StrategyNodeResult:
        """
        执行 BRANCH 节点 (递归执行子分支)

        Args:
            node_id: 节点 ID
            task: 任务描述
            reasoning: 推理结果
            context: 执行上下文
            start_time: 开始时间

        Returns:
            执行结果
        """
        logger.info(f"[节点 {node_id[:8]}] 执行 BRANCH: {len(reasoning.branches)} 个子任务")

        sub_results = []
        all_actions = []

        # 串行执行子分支
        for i, branch in enumerate(reasoning.branches):
            logger.info(f"[节点 {node_id[:8]}] 执行子分支 {i+1}/{len(reasoning.branches)}: {branch.description}")

            # 创建子上下文
            child_context = context.create_child_context(
                task=branch.description, node_id=node_id
            )

            # 递归执行子节点
            sub_result = await self.execute(branch.description, child_context)

            sub_results.append(sub_result)
            all_actions.extend(sub_result.actions)

            # 根据子节点结果决定是否继续
            if sub_result.status == ExecutionStatus.SUCCESS:
                logger.debug(f"子分支 {i+1} 成功")
                continue

            elif sub_result.status == ExecutionStatus.FAILED:
                logger.warning(f"子分支 {i+1} 失败: {sub_result.error}")
                # 尝试下一个分支 (自然容错)
                continue

        # 判断整体状态
        success_count = sum(1 for r in sub_results if r.status == ExecutionStatus.SUCCESS)

        if success_count == len(sub_results):
            status = ExecutionStatus.SUCCESS
        elif success_count > 0:
            status = ExecutionStatus.PARTIAL
        else:
            status = ExecutionStatus.FAILED

        return StrategyNodeResult(
            node_id=node_id,
            task_description=task,
            node_type=NodeType.BRANCH,
            status=status,
            actions=all_actions,
            sub_results=sub_results,
            start_time=start_time,
            end_time=time.time(),
            duration_seconds=time.time() - start_time,
        )


if __name__ == "__main__":
    print("策略节点模块加载成功")
    print("这是 Phase 1 基础版本，不包含融合增强功能")

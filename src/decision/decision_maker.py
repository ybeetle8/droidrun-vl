"""
决策生成器

核心决策系统，负责分析状态并生成执行计划
"""

import re
from typing import List, Optional

from loguru import logger

from ..core.state import State
from ..llm.client import LLMClient
from ..llm.prompts.decision_prompts import get_decision_prompt
from ..models import Action, ReasoningResult
from ..models.strategy import Branch, NodeType
from .branching import BranchingGenerator


class DecisionMaker:
    """
    决策生成器

    基于 LLM 的决策系统，分析当前状态并生成执行计划
    """

    def __init__(self, llm_client: LLMClient):
        """
        初始化决策生成器

        Args:
            llm_client: LLM 客户端
        """
        self.llm = llm_client
        self.branching = BranchingGenerator(llm_client)

    async def make_decision(
        self,
        task: str,
        current_state: State,
        screen_description: str,
        interactive_elements: List[dict],
        visible_text: List[str],
        history: Optional[List[str]] = None,
    ) -> ReasoningResult:
        """
        生成决策

        Args:
            task: 任务描述
            current_state: 当前状态
            screen_description: 屏幕描述
            interactive_elements: 可交互元素列表
            visible_text: 可见文本列表
            history: 历史操作列表

        Returns:
            推理结果
        """
        try:
            # 构建 Prompt
            prompt = get_decision_prompt(
                task=task,
                screen_description=screen_description,
                interactive_elements=interactive_elements,
                visible_text=visible_text,
                history=history,
            )

            # 调用 LLM（传递截图）
            logger.debug("生成决策中...")
            response = await self.llm.generate_with_image(
                prompt=prompt,
                image_data=current_state.screenshot,
                max_tokens=1500,
            )

            # 解析响应
            reasoning_result = await self._parse_decision(
                response, task, screen_description, interactive_elements
            )

            node_type_str = reasoning_result.node_type if isinstance(reasoning_result.node_type, str) else reasoning_result.node_type.value
            logger.info(
                f"决策生成完成: {node_type_str} "
                f"(置信度: {reasoning_result.confidence:.2f})"
            )

            return reasoning_result

        except Exception as e:
            logger.error(f"决策生成失败: {e}")
            # 返回默认决策（降级策略）
            return self._create_fallback_decision(task)

    async def _parse_decision(
        self, response: str, task: str, screen_description: str, interactive_elements: List[dict]
    ) -> ReasoningResult:
        """
        解析 LLM 决策响应

        Args:
            response: LLM 响应文本
            task: 任务描述
            screen_description: 屏幕描述
            interactive_elements: 可交互元素列表

        Returns:
            推理结果
        """
        # 提取节点类型
        node_type_match = re.search(r"节点类型:\s*(TERMINAL|BRANCH)", response, re.IGNORECASE)
        node_type_str = node_type_match.group(1).upper() if node_type_match else "TERMINAL"

        try:
            node_type = NodeType(node_type_str.lower())
        except ValueError:
            logger.warning(f"未识别的节点类型: {node_type_str}，默认为 TERMINAL")
            node_type = NodeType.TERMINAL

        # 提取目标是否达成
        goal_match = re.search(r"目标已达成:\s*(是|否|yes|no)", response, re.IGNORECASE)
        goal_reached = False
        if goal_match:
            goal_text = goal_match.group(1).lower()
            goal_reached = goal_text in ["是", "yes"]

        # 提取推理过程
        reasoning_steps = self._extract_reasoning_steps(response)

        # 提取置信度
        confidence = self._extract_confidence(response)

        # 根据节点类型解析不同的内容
        if node_type == NodeType.TERMINAL:
            # 解析动作
            action = self._parse_action(response, interactive_elements)
            expected_effect = self._extract_expected_effect(response)

            return ReasoningResult(
                task_understanding=task,
                current_situation=screen_description,
                goal_reached=goal_reached,
                node_type=node_type,
                action=action,
                expected_effect=expected_effect,
                reasoning_steps=reasoning_steps,
                confidence=confidence,
            )

        else:  # BRANCH
            # 解析子任务分支
            branches = self._parse_branches(response)

            # 如果没有解析到分支，使用 branching generator
            if not branches:
                logger.warning("未解析到分支，使用分支生成器")
                reasoning_text = "\n".join(reasoning_steps)
                branches = await self.branching.generate_branches(
                    task, screen_description, reasoning_text
                )

            return ReasoningResult(
                task_understanding=task,
                current_situation=screen_description,
                goal_reached=goal_reached,
                node_type=node_type,
                branches=branches,
                reasoning_steps=reasoning_steps,
                confidence=confidence,
            )

    def _parse_action(
        self, response: str, interactive_elements: Optional[List[dict]] = None
    ) -> Optional[Action]:
        """解析动作"""
        if interactive_elements is None:
            interactive_elements = []

        # 提取动作类型
        action_type_match = re.search(
            r"动作类型:\s*(tap|swipe|input|press_back|press_home|wait)",
            response,
            re.IGNORECASE,
        )

        if not action_type_match:
            logger.warning("未找到动作类型")
            return None

        action_type_str = action_type_match.group(1).lower()

        # 提取目标元素
        target_match = re.search(r"目标元素:\s*(.+?)(?:\n|$)", response)
        target = target_match.group(1).strip() if target_match else "未指定"

        # 根据动作类型创建动作
        if action_type_str == "tap":
            # 尝试从交互元素中找到坐标
            coordinates = self._find_element_coordinates(target, interactive_elements)
            return Action.tap(target=target, coordinates=coordinates)

        elif action_type_str == "swipe":
            # 提取方向
            direction_match = re.search(
                r"方向:\s*(up|down|left|right)", response, re.IGNORECASE
            )
            direction = direction_match.group(1) if direction_match else "up"
            # 暂时使用默认坐标
            return Action.swipe(start=(540, 1200), end=(540, 400), description=f"向{direction}滑动")

        elif action_type_str == "input":
            # 提取输入内容
            input_match = re.search(r"输入内容:\s*(.+?)(?:\n|$)", response)
            text = input_match.group(1).strip() if input_match else ""
            return Action.input_text(text=text, target=target)

        elif action_type_str == "press_back":
            return Action.press_back()

        elif action_type_str == "press_home":
            return Action.press_home()

        elif action_type_str == "wait":
            # 提取等待时间
            wait_match = re.search(r"等待时间:\s*(\d+\.?\d*)", response)
            seconds = float(wait_match.group(1)) if wait_match else 1.0
            return Action.wait(seconds=seconds)

        return None

    def _find_element_coordinates(
        self, target: str, interactive_elements: List[dict]
    ) -> Optional[tuple]:
        """从交互元素列表中查找目标元素的坐标"""
        target_lower = target.lower()

        for elem in interactive_elements:
            elem_text = str(elem.get("text", "")).lower()
            if target_lower in elem_text or elem_text in target_lower:
                bounds = elem.get("bounds")
                if bounds and len(bounds) == 4:
                    # 计算中心坐标
                    x = (bounds[0] + bounds[2]) // 2
                    y = (bounds[1] + bounds[3]) // 2
                    logger.debug(f"找到元素 '{target}' 的坐标: ({x}, {y})")
                    return (x, y)

        logger.warning(f"未找到元素 '{target}' 的坐标")
        return None

    def _parse_branches(self, response: str) -> List[Branch]:
        """解析分支列表"""
        branches = []

        # 查找子任务列表
        match = re.search(r"子任务列表:\s*\n(.*?)(?:\n\n|推理过程:|$)", response, re.DOTALL)

        if not match:
            return branches

        task_section = match.group(1)
        lines = task_section.split("\n")

        for line in lines:
            line = line.strip()
            # 匹配格式: "1. 描述"
            match = re.match(r"^\d+\.\s*(.+?)$", line)
            if match:
                description = match.group(1).strip()
                branches.append(Branch(description=description, priority=len(branches) + 1))

        return branches

    def _extract_reasoning_steps(self, response: str) -> List[str]:
        """提取推理步骤"""
        steps = []

        # 查找推理过程部分
        match = re.search(r"推理过程:\s*\n(.*?)(?:\n\n|$)", response, re.DOTALL)

        if match:
            reasoning_section = match.group(1)
            lines = reasoning_section.split("\n")

            for line in lines:
                line = line.strip()
                # 移除数字前缀
                line = re.sub(r"^\d+\.\s*", "", line)
                if line:
                    steps.append(line)

        return steps if steps else ["[未提供推理过程]"]

    def _extract_confidence(self, response: str) -> float:
        """提取置信度"""
        match = re.search(r"置信度:\s*(\d+\.?\d*)", response)
        if match:
            confidence = float(match.group(1))
            return min(max(confidence, 0.0), 1.0)  # 限制在 0-1 范围
        return 0.8  # 默认置信度

    def _extract_expected_effect(self, response: str) -> Optional[str]:
        """提取预期效果"""
        match = re.search(r"预期效果:\s*(.+?)(?:\n|$)", response)
        if match:
            return match.group(1).strip()
        return None

    def _create_fallback_decision(self, task: str) -> ReasoningResult:
        """创建降级决策（发生错误时）"""
        return ReasoningResult(
            task_understanding=task,
            current_situation="决策生成失败",
            goal_reached=False,
            node_type=NodeType.TERMINAL,
            action=Action.wait(seconds=1.0, description="等待并重试"),
            reasoning_steps=["决策生成失败", "使用降级策略：等待"],
            confidence=0.3,
        )


if __name__ == "__main__":
    import asyncio
    from ..utils.config import Config
    from ..core.state import State

    async def test():
        """测试决策生成器"""
        print("=" * 50)
        print("决策生成器测试")
        print("=" * 50)

        # 初始化
        config = Config()
        llm = LLMClient(config)
        decision_maker = DecisionMaker(llm)

        # 创建测试状态
        state = State(
            current_page="Launcher",
            current_app="com.android.launcher",
            task_description="打开设置",
        )

        # 测试决策生成
        print("\n[测试] 生成 TERMINAL 决策")
        result = await decision_maker.make_decision(
            task="打开设置",
            current_state=state,
            screen_description="主屏幕，显示多个应用图标",
            interactive_elements=[{"type": "icon", "text": "设置", "bounds": [100, 200, 200, 300]}],
            visible_text=["设置", "相机"],
        )

        print(f"\n决策结果:")
        node_type_str = result.node_type if isinstance(result.node_type, str) else result.node_type.value
        print(f"节点类型: {node_type_str}")
        print(f"目标达成: {result.goal_reached}")
        print(f"置信度: {result.confidence}")
        if result.action:
            print(f"动作: {result.action.type} - {result.action.description}")

        print("\n" + "=" * 50)
        print("测试完成!")
        print("=" * 50)

    # asyncio.run(test())
    print("决策生成器模块加载成功")

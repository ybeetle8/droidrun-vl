"""
分支生成器

负责将复杂任务分解为子分支
"""

import re
from typing import List

from loguru import logger

from ..llm.client import LLMClient
from ..llm.prompts.decision_prompts import get_branch_generation_prompt
from ..models.strategy import Branch


class BranchingGenerator:
    """
    分支生成器

    使用 LLM 将复杂任务分解为多个子任务分支
    """

    def __init__(self, llm_client: LLMClient):
        """
        初始化分支生成器

        Args:
            llm_client: LLM 客户端
        """
        self.llm = llm_client

    async def generate_branches(
        self, task: str, screen_state: str, reasoning: str = ""
    ) -> List[Branch]:
        """
        生成子任务分支

        Args:
            task: 任务描述
            screen_state: 屏幕状态描述
            reasoning: 已有推理过程

        Returns:
            分支列表
        """
        try:
            # 构建 Prompt
            prompt = get_branch_generation_prompt(task, screen_state, reasoning)

            # 调用 LLM
            logger.debug("生成分支中...")
            response = await self.llm.generate_text(prompt, max_tokens=800)

            # 解析响应
            branches = self._parse_branches(response)

            logger.info(f"生成 {len(branches)} 个分支")
            return branches

        except Exception as e:
            logger.error(f"分支生成失败: {e}")
            # 返回默认分支（降级策略）
            return [Branch(description=task, priority=1, reasoning="生成失败，使用默认分支")]

    def _parse_branches(self, response: str) -> List[Branch]:
        """
        解析 LLM 响应中的分支

        Args:
            response: LLM 响应文本

        Returns:
            分支列表
        """
        branches = []

        # 查找 "子任务列表:" 部分
        match = re.search(r"子任务列表:\s*\n(.*?)(?:\n\n|推理说明:|$)", response, re.DOTALL)

        if not match:
            logger.warning("未找到子任务列表，尝试按行解析")
            # 尝试直接按行解析
            lines = response.split("\n")
        else:
            task_section = match.group(1)
            lines = task_section.split("\n")

        for line in lines:
            line = line.strip()

            # 匹配格式: "1. 描述 - 优先级: 2 - 预期结果: ..."
            match = re.match(
                r"^\d+\.\s*(.+?)(?:\s*-\s*优先级:\s*(\d+))?(?:\s*-\s*预期结果:\s*(.+))?$", line
            )

            if match:
                description = match.group(1).strip()
                priority_str = match.group(2)
                expected_result = match.group(3)

                priority = int(priority_str) if priority_str else 1

                branch = Branch(
                    description=description,
                    priority=priority,
                    expected_result=expected_result.strip() if expected_result else None,
                )

                branches.append(branch)
                logger.debug(f"解析分支: {description}")

        # 如果没有解析到分支，尝试简单分割
        if not branches:
            logger.warning("标准解析失败，使用简单分割")
            for line in lines:
                line = line.strip()
                # 移除数字前缀
                line = re.sub(r"^\d+\.\s*", "", line)
                if line and len(line) > 3:
                    branches.append(Branch(description=line, priority=1))

        return branches


if __name__ == "__main__":
    import asyncio
    from ..llm.client import LLMClient
    from ..utils.config import Config

    async def test():
        """测试分支生成器"""
        print("=" * 50)
        print("分支生成器测试")
        print("=" * 50)

        # 初始化
        config = Config()
        llm = LLMClient(config)
        generator = BranchingGenerator(llm)

        # 测试分支生成
        print("\n[测试] 生成分支")
        branches = await generator.generate_branches(
            task="打开设置并进入 Wi-Fi 页面",
            screen_state="当前在主屏幕",
            reasoning="任务复杂，需要分解为多个步骤",
        )

        print(f"\n生成了 {len(branches)} 个分支:")
        for i, branch in enumerate(branches):
            print(f"\n分支 {i+1}:")
            print(branch.model_dump_json(indent=2))

        print("\n" + "=" * 50)
        print("测试完成!")
        print("=" * 50)

    # asyncio.run(test())
    print("分支生成器模块加载成功")

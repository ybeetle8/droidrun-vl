"""
视觉分析器

使用 VL 模型分析屏幕内容
"""

import re
from typing import List, Optional

from loguru import logger

from ..core.state import State
from ..llm.client import LLMClient
from ..llm.prompts.perception_prompts import (
    get_change_analysis_prompt,
    get_screen_analysis_prompt,
)
from ..models import PerceptionResult


class VisionAnalyzer:
    """
    视觉分析器

    使用 VL 模型理解屏幕内容
    """

    def __init__(self, llm_client: LLMClient):
        """
        初始化视觉分析器

        Args:
            llm_client: LLM 客户端（支持多模态）
        """
        self.llm = llm_client

    async def analyze_screen(
        self, screenshot: bytes, task_context: Optional[str] = None
    ) -> PerceptionResult:
        """
        分析屏幕内容

        Args:
            screenshot: 屏幕截图（bytes）
            task_context: 任务上下文（可选）

        Returns:
            感知结果
        """
        try:
            # 构建 Prompt
            prompt = get_screen_analysis_prompt(task_context or "")

            # 调用 VL 模型
            logger.debug("分析屏幕内容...")
            response = await self.llm.generate_with_image(
                prompt=prompt, image_data=screenshot, max_tokens=1500
            )

            # 解析响应
            perception = self._parse_screen_analysis(response, screenshot)

            logger.info(f"屏幕分析完成: {perception.current_page}")
            return perception

        except Exception as e:
            logger.error(f"屏幕分析失败: {e}")
            # 返回默认感知结果
            return self._create_fallback_perception(screenshot)

    async def analyze_changes(
        self,
        before_screenshot: bytes,
        after_screenshot: bytes,
        action_description: str,
        expected_effect: str,
    ) -> tuple[str, str]:
        """
        分析前后屏幕变化

        Args:
            before_screenshot: 操作前截图
            after_screenshot: 操作后截图
            action_description: 动作描述
            expected_effect: 预期效果

        Returns:
            (status, feedback) - 状态和反馈
            status: "SUCCESS" | "FAILURE" | "INEFFECTIVE"
        """
        try:
            # 构建 Prompt
            prompt = get_change_analysis_prompt(action_description, expected_effect)

            # 调用 VL 模型（传递两张图片）
            logger.debug("分析屏幕变化...")
            response = await self.llm.generate_with_images(
                prompt=prompt,
                image_data_list=[before_screenshot, after_screenshot],
                max_tokens=800,
            )

            # 解析状态和反馈
            status = self._extract_status(response)
            feedback = self._extract_change_description(response)

            logger.info(f"变化分析完成: {status}")
            return status, feedback

        except Exception as e:
            logger.error(f"变化分析失败: {e}")
            return "INEFFECTIVE", f"分析失败: {str(e)}"

    def _parse_screen_analysis(
        self, response: str, screenshot: bytes
    ) -> PerceptionResult:
        """
        解析屏幕分析响应

        Args:
            response: LLM 响应文本
            screenshot: 原始截图

        Returns:
            感知结果
        """
        # 提取屏幕描述
        screen_description = self._extract_section(response, "屏幕描述", "当前页面")
        if not screen_description:
            screen_description = "无法识别屏幕内容"

        # 提取当前页面
        current_page = self._extract_section(response, "当前页面", "可交互元素")
        if current_page:
            current_page = current_page.strip()

        # 提取可交互元素
        interactive_elements = self._extract_interactive_elements(response)

        # 提取可见文本
        visible_text = self._extract_visible_text(response)

        # 提取状态判断
        is_loading = self._extract_boolean_status(response, "加载中")
        has_popup = self._extract_boolean_status(response, "弹窗")
        has_error = self._extract_boolean_status(response, "错误")
        error_message = self._extract_error_message(response)

        return PerceptionResult(
            screen_description=screen_description,
            current_page=current_page,
            interactive_elements=interactive_elements,
            visible_text=visible_text,
            is_loading=is_loading,
            has_popup=has_popup,
            has_error=has_error,
            error_message=error_message,
            screenshot=screenshot,
        )

    def _extract_section(
        self, text: str, start_marker: str, end_marker: Optional[str] = None
    ) -> str:
        """提取文本中的特定部分"""
        pattern = rf"#{1,3}\s*\d*\.?\s*{re.escape(start_marker)}.*?\n(.*?)(?=#{1,3}|$)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)

        if match:
            content = match.group(1).strip()
            # 如果指定了结束标记，进一步截取
            if end_marker:
                end_match = re.search(
                    rf"#{1,3}\s*\d*\.?\s*{re.escape(end_marker)}", content, re.IGNORECASE
                )
                if end_match:
                    content = content[: end_match.start()].strip()
            return content

        return ""

    def _extract_interactive_elements(self, response: str) -> List[dict]:
        """提取可交互元素"""
        elements = []

        # 查找可交互元素部分
        elements_section = self._extract_section(response, "可交互元素", "可见文本")

        if not elements_section:
            return elements

        # 解析每一行
        lines = elements_section.split("\n")
        for line in lines:
            line = line.strip()

            # 匹配格式: - [类型] "文本" - 位于位置
            match = re.match(r"^-\s*\[([^\]]+)\]\s*[\"']?([^\"'-]+)[\"']?\s*-?\s*(.*)$", line)

            if match:
                elem_type = match.group(1).strip()
                elem_text = match.group(2).strip()
                location = match.group(3).strip()

                # 移除 "位于" 前缀
                location = re.sub(r"^位于\s*", "", location)

                elements.append(
                    {"type": elem_type, "text": elem_text, "location": location, "bounds": None}
                )

        return elements

    def _extract_visible_text(self, response: str) -> List[str]:
        """提取可见文本"""
        text_section = self._extract_section(response, "可见文本", "状态判断")

        if not text_section:
            return []

        # 匹配 ["text1", "text2", ...] 格式
        match = re.search(r'\[([^\]]+)\]', text_section)
        if match:
            text_list_str = match.group(1)
            # 分割并清理
            texts = [
                t.strip().strip('"').strip("'") for t in text_list_str.split(",") if t.strip()
            ]
            return texts

        # 尝试按行分割
        lines = text_section.split("\n")
        texts = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                # 移除列表前缀
                line = re.sub(r"^-\s*", "", line)
                line = line.strip('"').strip("'")
                if line:
                    texts.append(line)

        return texts

    def _extract_boolean_status(self, response: str, keyword: str) -> bool:
        """提取布尔状态"""
        # 查找 "关键词：是/否"
        pattern = rf"{re.escape(keyword)}[：:]\s*(是|否|yes|no)"
        match = re.search(pattern, response, re.IGNORECASE)

        if match:
            value = match.group(1).lower()
            return value in ["是", "yes"]

        return False

    def _extract_error_message(self, response: str) -> Optional[str]:
        """提取错误信息"""
        # 查找错误信息部分
        match = re.search(r"错误信息[：:]\s*(.+?)(?:\n|$)", response, re.IGNORECASE)
        if match:
            msg = match.group(1).strip()
            if msg and msg not in ["无", "否", "none", "-"]:
                return msg
        return None

    def _extract_status(self, response: str) -> str:
        """从变化分析中提取状态"""
        # 查找 "变化判断: SUCCESS/FAILURE/INEFFECTIVE"
        match = re.search(
            r"变化判断[：:]\s*(成功|失败|无效|SUCCESS|FAILURE|INEFFECTIVE)",
            response,
            re.IGNORECASE,
        )

        if match:
            status_text = match.group(1).upper()
            if "SUCCESS" in status_text or "成功" in status_text:
                return "SUCCESS"
            elif "FAILURE" in status_text or "失败" in status_text:
                return "FAILURE"
            else:
                return "INEFFECTIVE"

        return "INEFFECTIVE"

    def _extract_change_description(self, response: str) -> str:
        """提取变化描述"""
        desc = self._extract_section(response, "变化描述", "原因分析")
        if not desc:
            desc = "无法分析变化"
        return desc

    def _create_fallback_perception(self, screenshot: bytes) -> PerceptionResult:
        """创建降级感知结果（发生错误时）"""
        return PerceptionResult(
            screen_description="分析失败，无法识别屏幕内容",
            current_page=None,
            interactive_elements=[],
            visible_text=[],
            is_loading=False,
            has_popup=False,
            has_error=False,
            screenshot=screenshot,
        )


if __name__ == "__main__":
    import asyncio
    from ..utils.config import Config

    async def test():
        """测试视觉分析器"""
        print("=" * 50)
        print("视觉分析器测试")
        print("=" * 50)

        # 初始化
        config = Config()
        llm = LLMClient(config)
        analyzer = VisionAnalyzer(llm)

        # 由于没有实际截图，这里只测试模块加载
        print("\n视觉分析器初始化成功")
        print("需要实际截图才能测试完整功能")

        print("\n" + "=" * 50)
        print("测试完成!")
        print("=" * 50)

    # asyncio.run(test())
    print("视觉分析器模块加载成功")

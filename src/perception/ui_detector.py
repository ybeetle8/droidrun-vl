"""
UI 元素检测器

从 UI 树中提取和过滤可交互元素
"""

from typing import Any, Dict, List, Optional

from loguru import logger


class UIDetector:
    """
    UI 元素检测器

    从无障碍树（a11y tree）中提取可交互元素
    """

    def __init__(self):
        """初始化 UI 检测器"""
        self.interactive_properties = ["clickable", "long-clickable", "checkable", "focusable"]

    def extract_interactive_elements(
        self, ui_tree: List[Dict[str, Any]], filter_invisible: bool = True
    ) -> List[dict]:
        """
        提取可交互元素

        Args:
            ui_tree: UI 树（来自无障碍服务）
            filter_invisible: 是否过滤不可见元素

        Returns:
            可交互元素列表
        """
        elements = []

        for node in ui_tree:
            self._traverse_tree(node, elements, filter_invisible)

        logger.debug(f"提取到 {len(elements)} 个可交互元素")
        return elements

    def _traverse_tree(
        self, node: Dict[str, Any], elements: List[dict], filter_invisible: bool
    ) -> None:
        """递归遍历 UI 树"""
        # 检查是否可交互
        if self._is_interactive(node):
            # 检查是否可见
            if not filter_invisible or self._is_visible(node):
                element = self._extract_element_info(node)
                elements.append(element)

        # 递归处理子节点
        children = node.get("children", [])
        for child in children:
            self._traverse_tree(child, elements, filter_invisible)

    def _is_interactive(self, node: Dict[str, Any]) -> bool:
        """判断节点是否可交互"""
        # 检查交互属性
        for prop in self.interactive_properties:
            if node.get(prop) is True:
                return True

        # 检查是否有重要内容
        if node.get("text") or node.get("content-desc"):
            # 某些元素虽然没有标记 clickable，但实际可点击
            class_name = node.get("class", "").lower()
            if any(
                keyword in class_name
                for keyword in ["button", "imagebutton", "textview", "imageview"]
            ):
                return True

        return False

    def _is_visible(self, node: Dict[str, Any]) -> bool:
        """判断节点是否可见"""
        # 检查 visible-to-user 属性
        if not node.get("visible-to-user", True):
            return False

        # 检查边界是否有效
        bounds = node.get("bounds")
        if bounds:
            if isinstance(bounds, list) and len(bounds) == 4:
                # bounds: [left, top, right, bottom]
                width = bounds[2] - bounds[0]
                height = bounds[3] - bounds[1]
                # 过滤掉太小的元素
                if width < 10 or height < 10:
                    return False

        return True

    def _extract_element_info(self, node: Dict[str, Any]) -> dict:
        """提取元素信息"""
        # 获取文本内容
        text = node.get("text", "")
        content_desc = node.get("content-desc", "")
        display_text = text or content_desc or ""

        # 获取类型
        class_name = node.get("class", "")
        elem_type = self._classify_element_type(class_name, node)

        # 获取边界
        bounds = node.get("bounds")

        # 计算位置描述
        location = self._describe_location(bounds) if bounds else "位置未知"

        # 获取资源 ID
        resource_id = node.get("resource-id", "")

        return {
            "type": elem_type,
            "text": display_text,
            "bounds": bounds,
            "location": location,
            "resource_id": resource_id,
            "class": class_name,
            "clickable": node.get("clickable", False),
            "long-clickable": node.get("long-clickable", False),
            "checkable": node.get("checkable", False),
            "checked": node.get("checked", False),
            "enabled": node.get("enabled", True),
        }

    def _classify_element_type(self, class_name: str, node: Dict[str, Any]) -> str:
        """分类元素类型"""
        class_lower = class_name.lower()

        if "button" in class_lower:
            return "按钮"
        elif "edittext" in class_lower or "edit" in class_lower:
            return "输入框"
        elif "checkbox" in class_lower:
            return "复选框"
        elif "radiobutton" in class_lower:
            return "单选按钮"
        elif "switch" in class_lower:
            return "开关"
        elif "imageview" in class_lower or "image" in class_lower:
            return "图标"
        elif "textview" in class_lower or "text" in class_lower:
            return "文本"
        elif "listview" in class_lower or "recyclerview" in class_lower:
            return "列表"
        elif "scrollview" in class_lower:
            return "滚动视图"
        else:
            # 根据属性判断
            if node.get("checkable"):
                return "可选项"
            elif node.get("clickable"):
                return "可点击项"
            else:
                return "元素"

    def _describe_location(self, bounds: List[int]) -> str:
        """描述元素位置"""
        if not bounds or len(bounds) != 4:
            return "位置未知"

        # bounds: [left, top, right, bottom]
        left, top, right, bottom = bounds

        # 计算中心点
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2

        # 假设屏幕尺寸为 1080x2400 (常见分辨率)
        # 实际应该从设备信息获取
        screen_width = 1080
        screen_height = 2400

        # 水平位置
        if center_x < screen_width * 0.33:
            h_pos = "左侧"
        elif center_x < screen_width * 0.67:
            h_pos = "中间"
        else:
            h_pos = "右侧"

        # 垂直位置
        if center_y < screen_height * 0.33:
            v_pos = "顶部"
        elif center_y < screen_height * 0.67:
            v_pos = "中部"
        else:
            v_pos = "底部"

        return f"{v_pos}{h_pos}"

    def find_element_by_text(
        self, elements: List[dict], text: str, fuzzy: bool = True
    ) -> Optional[dict]:
        """
        根据文本查找元素

        Args:
            elements: 元素列表
            text: 要查找的文本
            fuzzy: 是否模糊匹配

        Returns:
            匹配的元素，如果没找到返回 None
        """
        text_lower = text.lower()

        for elem in elements:
            elem_text = elem.get("text", "").lower()

            if fuzzy:
                # 模糊匹配：文本包含关键词
                if text_lower in elem_text or elem_text in text_lower:
                    return elem
            else:
                # 精确匹配
                if elem_text == text_lower:
                    return elem

        return None

    def find_elements_by_type(self, elements: List[dict], elem_type: str) -> List[dict]:
        """
        根据类型查找元素

        Args:
            elements: 元素列表
            elem_type: 元素类型（如 "按钮"、"输入框"）

        Returns:
            匹配的元素列表
        """
        return [elem for elem in elements if elem.get("type") == elem_type]


if __name__ == "__main__":
    # 测试 UI 检测器
    print("=" * 50)
    print("UI 检测器测试")
    print("=" * 50)

    detector = UIDetector()

    # 模拟 UI 树数据
    mock_ui_tree = [
        {
            "class": "android.widget.Button",
            "text": "确定",
            "clickable": True,
            "visible-to-user": True,
            "bounds": [100, 200, 300, 300],
        },
        {
            "class": "android.widget.EditText",
            "text": "",
            "content-desc": "搜索框",
            "clickable": True,
            "visible-to-user": True,
            "bounds": [50, 50, 500, 150],
        },
        {
            "class": "android.widget.ImageView",
            "content-desc": "设置",
            "clickable": True,
            "visible-to-user": True,
            "bounds": [900, 100, 1000, 200],
        },
    ]

    # 测试提取元素
    print("\n[测试 1] 提取可交互元素")
    elements = detector.extract_interactive_elements(mock_ui_tree)
    print(f"找到 {len(elements)} 个元素:")
    for i, elem in enumerate(elements):
        print(f"{i+1}. [{elem['type']}] {elem['text']} - {elem['location']}")

    # 测试查找元素
    print("\n[测试 2] 根据文本查找元素")
    result = detector.find_element_by_text(elements, "确定")
    if result:
        print(f"找到: [{result['type']}] {result['text']}")
    else:
        print("未找到")

    # 测试按类型查找
    print("\n[测试 3] 根据类型查找元素")
    buttons = detector.find_elements_by_type(elements, "按钮")
    print(f"找到 {len(buttons)} 个按钮")

    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)

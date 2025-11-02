"""
视觉分析工具
用于屏幕截图分析、UI 元素识别等
"""
from typing import Tuple
from droidrun.tools.adb import AdbTools
from ..utils.ui_processor import process_ui_overlaps


def capture_screenshot(use_tcp: bool = True, hide_overlay: bool = True) -> Tuple[str, bytes]:
    """
    捕获屏幕截图

    Args:
        use_tcp: 是否使用 TCP 连接
        hide_overlay: 是否隐藏悬浮窗

    Returns:
        (临时文件路径, 图片字节数据)
    """
    adb_tools = AdbTools(use_tcp=use_tcp)
    return adb_tools.take_screenshot(hide_overlay=hide_overlay)


def get_ui_state(use_tcp: bool = True) -> dict:
    """
    获取 UI 状态信息（自动添加元素重叠检测信息）

    Args:
        use_tcp: 是否使用 TCP 连接

    Returns:
        UI 状态字典（包含 is_covered 和 covered_by 字段）
    """
    adb_tools = AdbTools(use_tcp=use_tcp)
    ui_state = adb_tools.get_state()

    # 处理元素重叠，添加 is_covered 和 covered_by 字段
    ui_state = process_ui_overlaps(ui_state)

    return ui_state

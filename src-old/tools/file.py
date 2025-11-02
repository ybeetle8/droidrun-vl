"""
文件操作工具
用于保存截图、日志等
"""
from pathlib import Path
from datetime import datetime


def save_screenshot(screenshot_bytes: bytes, output_dir: str = "test/analysis_output", prefix: str = "verification") -> Path:
    """
    保存截图到文件

    Args:
        screenshot_bytes: 截图字节数据
        output_dir: 输出目录
        prefix: 文件名前缀

    Returns:
        保存的文件路径
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_file = output_path / f"{prefix}_{timestamp}.png"

    with open(screenshot_file, "wb") as f:
        f.write(screenshot_bytes)

    return screenshot_file

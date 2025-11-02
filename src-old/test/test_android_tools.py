"""
测试 Android 工具功能
"""
import time
import logging
import sys
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.android import SimpleAdbTools

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_basic_operations():
    """测试基本操作：截屏和滑动"""

    logger.info("=== 开始测试 Android 工具 ===")

    # 初始化工具（使用 TCP 连接）
    logger.info("初始化 ADB 工具...")
    adb_tools = SimpleAdbTools(use_tcp=True)

    # 1. 截取屏幕
    logger.info("\n[1/3] 截取屏幕...")
    try:
        img_format, img_bytes = adb_tools.take_screenshot()
        logger.info(f"✓ 截屏成功！格式: {img_format}, 大小: {len(img_bytes)} 字节")

        # 保存截图
        output_dir = Path("src/test/output")
        output_dir.mkdir(exist_ok=True)

        screenshot_path = output_dir / f"screenshot_{int(time.time())}.png"
        with open(screenshot_path, "wb") as f:
            f.write(img_bytes)
        logger.info(f"  截图已保存到: {screenshot_path}")

    except Exception as e:
        logger.error(f"✗ 截屏失败: {e}")
        return False

    # 2. 获取屏幕尺寸（从设备状态中）
    logger.info("\n[2/3] 获取屏幕信息...")
    try:
        state = adb_tools.get_state()
        if "phone_state" in state:
            phone_state = state["phone_state"]
            screen_width = phone_state.get("screenWidth", 1080)
            screen_height = phone_state.get("screenHeight", 1920)
            logger.info(f"✓ 屏幕尺寸: {screen_width}x{screen_height}")
        else:
            logger.warning("⚠ 无法获取屏幕尺寸，使用默认值")
            screen_width = 1080
            screen_height = 1920
    except Exception as e:
        logger.error(f"✗ 获取屏幕信息失败: {e}")
        screen_width = 1080
        screen_height = 1920

    # 3. 左右滑动测试
    logger.info("\n[3/3] 执行左右滑动...")

    # 计算滑动坐标（在屏幕中间高度，从右到左）
    start_x = int(screen_width * 0.8)
    end_x = int(screen_width * 0.2)
    y = int(screen_height * 0.5)

    try:
        # 向左滑动
        logger.info(f"  向左滑动: ({start_x}, {y}) -> ({end_x}, {y})")
        result = adb_tools.swipe(start_x, y, end_x, y, duration_ms=300)
        logger.info(f"✓ {result}")

        time.sleep(1)

        # 向右滑动（返回）
        logger.info(f"  向右滑动: ({end_x}, {y}) -> ({start_x}, {y})")
        result = adb_tools.swipe(end_x, y, start_x, y, duration_ms=300)
        logger.info(f"✓ {result}")

    except Exception as e:
        logger.error(f"✗ 滑动失败: {e}")
        return False

    logger.info("\n=== 测试完成！所有功能正常 ✓ ===")
    return True


if __name__ == "__main__":
    success = test_basic_operations()
    exit(0 if success else 1)
